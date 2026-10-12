"""
Backend API — exposes the agent (Step 5: memory) via HTTP,
so the React interface can call it.

Run with:
    uvicorn main:app --reload --port 8000

Endpoints:
    POST /research   { "topic": "Compare RAG and Fine-tuning..." } -> ResearchReport
    GET  /memory      -> memory statistics (known sources, history)
"""

import os
import json
import uuid
import time
import csv
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.arxiv import ArxivTools

load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is missing. Check your .env file")

MAX_FREE_REQUESTS_PER_CLIENT = 1

# Global limit: once this total number of requests (across all
# users) is reached, the app refuses all requests.
GLOBAL_MAX_REQUESTS = 10

# Optional secret token: if the frontend sends this token (X-Owner-Token
# header), the limits (both per-user AND global) are ignored.
# This is for your own testing without consuming the quota
# reserved for your testers.
OWNER_TOKEN = os.getenv("OWNER_TOKEN")

# Report cache validity period — after this time, a fresh search
# is performed even if the topic is already cached.
CACHE_TTL_DAYS = 7

GEMINI_MODEL_ID = "gemini-3.5-flash-lite"

GEMINI_PRICE_INPUT_PER_M = 1.50
GEMINI_PRICE_OUTPUT_PER_M = 9.00

# CSV file where every search (successful or not) is automatically
# logged for system evaluation (time, tokens, cost).
# Open this file directly in Excel/Google Sheets.
EVAL_LOG_FILE = Path("eval_log.csv")


def log_evaluation_entry(
    topic: str,
    success: bool,
    duration_seconds: float | None,
    input_tokens: int | None,
    output_tokens: int | None,
    note: str = "",
):
    """Adds one line to the evaluation log for each search."""
    cost = None
    if input_tokens is not None and output_tokens is not None:
        cost = (
            (input_tokens / 1_000_000) * GEMINI_PRICE_INPUT_PER_M
            + (output_tokens / 1_000_000) * GEMINI_PRICE_OUTPUT_PER_M
        )

    is_new_file = not EVAL_LOG_FILE.exists()
    with open(EVAL_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow([
                "timestamp", "topic", "success", "duration_seconds",
                "input_tokens", "output_tokens", "total_tokens",
                "cost_usd", "note",
            ])
        writer.writerow([
            datetime.now(timezone.utc).isoformat(),
            topic,
            success,
            round(duration_seconds, 2) if duration_seconds is not None else "",
            input_tokens if input_tokens is not None else "",
            output_tokens if output_tokens is not None else "",
            (input_tokens + output_tokens) if (input_tokens is not None and output_tokens is not None) else "",
            round(cost, 6) if cost is not None else "",
            note,
        ])



# Pydantic schema


class Source(BaseModel):
    title: str = Field(description="Title of the paper or article")
    url: str = Field(description="Source URL (e.g., Arxiv link)")
    relevance: str = Field(description="Why this source is relevant, in one sentence")


class ComparisonPoint(BaseModel):
    criterion: str = Field(description="The comparison criterion (e.g., 'Cost', 'Accuracy')")
    approach_a: str = Field(description="How the first approach performs on this criterion")
    approach_b: str = Field(description="How the second approach performs on this criterion")


class ResearchReport(BaseModel):
    title: str
    overview: str
    comparison_points: list[ComparisonPoint]
    pros_approach_a: list[str]
    cons_approach_a: list[str]
    pros_approach_b: list[str]
    cons_approach_b: list[str]
    recommendation: str
    sources: list[Source]



# Memory

MEMORY_FILE = Path("memory.json")


class ResearchMemory:
    def __init__(self, path: Path = MEMORY_FILE):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"known_sources": {}, "report_history": []}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def known_sources_summary(self) -> str:
        sources = self.data["known_sources"]
        if not sources:
            return "No known sources yet — this is your first search."
        lines = [f"- {s['title']} ({url})" for url, s in sources.items()]
        return "Sources already seen in previous searches:\n" + "\n".join(lines)

    def add_report(self, topic: str, report: ResearchReport) -> int:
        new_sources_count = 0
        for source in report.sources:
            if source.url not in self.data["known_sources"]:
                new_sources_count += 1
            self.data["known_sources"][source.url] = {
                "title": source.title,
                "relevance": source.relevance,
            }
        self.data["report_history"].append({
            "topic": topic,
            "date": datetime.now(timezone.utc).isoformat(),
            "title": report.title,
            "num_sources": len(report.sources),
        })

        normalized = topic.strip().lower()
        self.data.setdefault("report_cache", {})[normalized] = {
            "report": report.model_dump(),
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }

        self._save()
        return new_sources_count

    def get_cached_report(self, topic: str) -> "ResearchReport | None":
        normalized = topic.strip().lower()
        entry = self.data.get("report_cache", {}).get(normalized)
        if not entry:
            return None

        cached_at = datetime.fromisoformat(entry["cached_at"])
        age_days = (datetime.now(timezone.utc) - cached_at).total_seconds() / 86400
        if age_days > CACHE_TTL_DAYS:
            return None

        return ResearchReport(**entry["report"])

    def stats(self) -> dict:
        return {
            "known_sources_count": len(self.data["known_sources"]),
            "reports_generated": len(self.data["report_history"]),
            "history": self.data["report_history"],
        }


memory = ResearchMemory()


# Usage tracking


USAGE_FILE = Path("usage.json")


class UsageTracker:
    def __init__(self, path: Path = USAGE_FILE):
        self.path = path
        self.data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def get_count(self, client_id: str) -> int:
        return self.data.get(client_id, {}).get("count", 0)

    def get_global_count(self) -> int:
        return self.data.get("_global", {}).get("count", 0)

    def increment(self, client_id: str):
        entry = self.data.setdefault(client_id, {"count": 0, "first_seen": None})
        if entry["first_seen"] is None:
            entry["first_seen"] = datetime.now(timezone.utc).isoformat()
        entry["count"] += 1

        global_entry = self.data.setdefault("_global", {"count": 0})
        global_entry["count"] += 1

        self._save()


usage = UsageTracker()



# Agent — Gemini natively handles tools + structured output together,


def build_agent() -> Agent:
    instructions = [
        "You are an AI Research Assistant specialized in comparing technical approaches.",
        "Always respond in English, regardless of the language of the topic given.",
        "Use ArxivTools to find scientific papers and theoretical foundations for technical claims.",
        "Search once with a clear, specific query. Do not repeat searches with slightly reworded queries.",
        "Be precise and avoid vague generalities — give concrete technical details.",
        "Fill EVERY field of the output schema thoughtfully — do not leave lists empty.",
        "Write in a professional, academic tone suitable for a research report.",
        "When citing a quantitative finding from a source, use the specific number or "
        "range reported in that source rather than vague phrases like 'orders of magnitude' "
        "or 'significantly better' — e.g. say 'up to 1200x lower emissions in some tasks' "
        "rather than just 'much lower emissions'.",
        "Where relevant, note at least one limitation or caveat of the cited studies "
        "(e.g. small sample size, specific hardware used, estimated rather than measured "
        "metrics) rather than presenting every finding as absolute and unqualified.",
        memory.known_sources_summary(),
        "If a relevant source is already listed above as known, you may reuse it "
        "directly in your report instead of searching for it again.",
    ]
    return Agent(
        model=Gemini(id=GEMINI_MODEL_ID, api_key=GEMINI_API_KEY),
        instructions=instructions,
        tools=[ArxivTools(enable_read_arxiv_papers=False)],
        tool_call_limit=2,
        output_schema=ResearchReport,
        markdown=True,
    )


# API FastAPI


app = FastAPI(title="AI Research Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    topic: str


@app.post("/research", response_model=ResearchReport)
def research(
    request: ResearchRequest,
    x_client_id: str = Header(default=None),
    x_owner_token: str = Header(default=None),
):
    if not request.topic or not request.topic.strip():
        raise HTTPException(status_code=400, detail="The topic cannot be empty.")

    if not x_client_id:
        raise HTTPException(status_code=400, detail="Missing client ID.")

    is_owner = bool(OWNER_TOKEN) and x_owner_token == OWNER_TOKEN

    
    if not is_owner:
        current_count = usage.get_count(x_client_id)

        if current_count >= MAX_FREE_REQUESTS_PER_CLIENT:
            raise HTTPException(
                status_code=403,
                detail="You have already used your free research request. "
                    "Contact us for extended access.",
            )


    cached_report = memory.get_cached_report(request.topic)
    if cached_report is not None:
        if not is_owner:
            usage.increment(x_client_id)
        return cached_report

    start_time = time.time()
    input_tokens = None
    output_tokens = None

    try:
        agent = build_agent()
        response = agent.run(request.topic)
        candidate = response.content

        # Agno already calculates the tokens used — we retrieve them for
        # the evaluation log (cost, tracking).
        if getattr(response, "metrics", None):
            input_tokens = getattr(response.metrics, "input_tokens", None)
            output_tokens = getattr(response.metrics, "output_tokens", None)
    except Exception:
        candidate = None

    duration = time.time() - start_time
    report = candidate if isinstance(candidate, ResearchReport) else None

    log_evaluation_entry(
        topic=request.topic,
        success=report is not None,
        duration_seconds=duration,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        note="" if report is not None else "failed (503/invalid response)",
    )

    if report is None:
        raise HTTPException(
            status_code=503,
            detail="The model is currently overloaded. Please wait a moment and try again — "
                   "this attempt was not counted against your free try.",
        )

    memory.add_report(request.topic, report)
    if not is_owner:
        usage.increment(x_client_id)
    return report


@app.get("/memory")
def get_memory_stats():
    return memory.stats()


@app.get("/usage")
def get_usage(x_client_id: str = Header(default=None)):
    if not x_client_id:
        raise HTTPException(status_code=400, detail="Missing client ID.")
    count = usage.get_count(x_client_id)
    return {
        "used": count,
        "limit": MAX_FREE_REQUESTS_PER_CLIENT,
        "remaining": max(0, MAX_FREE_REQUESTS_PER_CLIENT - count),
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
