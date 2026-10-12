# AI Research Assistant

An AI-powered research assistant that compares two technical approaches, searches scientific literature, and generates structured research reports to support technical decision-making.

Built with **React**, **FastAPI**, **Agno**, and **Google Gemini**, the application uses arXiv to discover relevant scientific papers and produces comparisons with advantages, limitations, recommendations, and source references.

## Key Features

- **Technical Approach Comparison:** Compare two approaches using relevant technical criteria.
- **Scientific Literature Search:** Search arXiv for relevant scientific papers and theoretical foundations.
- **Structured Research Reports:** Generate reports containing an overview, comparison points, advantages, disadvantages, recommendations, and references.
- **PDF and Word Export:** Download generated research reports in PDF or Word format.
- **Source Memory:** Keep track of previously encountered sources, including their titles, URLs, and relevance descriptions.
- **Research History:** Record metadata about generated reports, including their topics, dates, titles, and source counts.
- **Seven-Day Report Cache:** Reuse cached reports for matching topics while the cache is valid. After seven days, a fresh search can be performed to account for newly available publications.
- **Evaluation and Report History:** Access evaluation results and previously generated or downloaded reports through the evaluation+reports file or section.
- **Usage Limits:** Apply configurable per-client and global request limits for the current testing version.
- **Evaluation Logging:** Automatically record request outcomes, execution duration, token usage, and estimated API costs.
- **REST API:** Expose research, memory statistics, usage information, and health-check endpoints.

## Technology Stack

### Frontend
- React
- JavaScript or TypeScript, depending on the frontend configuration

### Backend
- Python
- FastAPI
- Agno
- Google Gemini
- arXiv tools
- Pydantic
- Python-dotenv

### Deployment
- Vercel for the React frontend
- Render for the FastAPI backend

## Architecture

The application uses a frontend–backend architecture.

1. The user submits a technical research topic through the React interface.
2. The frontend sends a request to the FastAPI backend.
3. The backend validates the request and checks the client's usage limits.
4. The application checks whether a valid cached report exists for the requested topic.
5. If no valid cached report exists, an Agno agent uses Google Gemini and arXiv tools to research the topic.
6. The agent generates a structured report using a Pydantic output schema.
7. The backend logs evaluation metrics and updates the research memory.
8. The report is returned to the frontend.

## Research Report Structure

Each report follows a structured schema containing:

| Field | Description |
|---|---|
| `title` | Report title |
| `overview` | Overview of the topic and approaches |
| `comparison_points` | Comparison across technical criteria |
| `pros_approach_a` | Advantages of the first approach |
| `cons_approach_a` | Limitations of the first approach |
| `pros_approach_b` | Advantages of the second approach |
| `cons_approach_b` | Limitations of the second approach |
| `recommendation` | Final recommendation |
| `sources` | Scientific references, URLs, and relevance descriptions |

The agent is instructed to provide concrete technical details, use scientific sources to support technical claims, and acknowledge relevant limitations in the cited studies.

## Research Memory and Caching

The backend uses `memory.json` to maintain research-related information.

The memory has three main components:

- **`known_sources`:** Stores previously encountered sources, including their URLs, titles, and relevance descriptions. It helps the agent keep track of sources from earlier searches.
- **`report_history`:** Stores report metadata, including the research topic, generation date, title, and number of sources.
- **`report_cache`:** Stores complete structured reports and their cache timestamps so that valid reports can be reused.

The cache validity period is seven days. Once a cached report expires, the application can conduct a new search instead of returning the expired report.

The cache is based on a normalized topic: leading and trailing whitespace are removed, and the topic is converted to lowercase.

## Evaluation and Monitoring

The backend automatically writes request-level evaluation records to `eval_log.csv`.

The log includes:

- Timestamp
- Research topic
- Success or failure status
- Execution duration
- Input tokens
- Output tokens
- Total tokens
- Estimated API cost
- Additional notes

The estimated cost is calculated from token counts and the pricing values configured in the backend. It is an estimate, not necessarily the final amount charged by the API provider.

In addition to the automatically generated evaluation log, a separate evaluation spreadsheet can be used to assess report quality according to predefined evaluation criteria.

The evaluation log is generated at runtime and does not need to be committed to the public repository.

## Current Testing Limitations

This version is intended for testing and demonstration.

- Each client is limited to one request.
- The application has a global limit of ten requests.
- An optional owner token allows authorized owner testing without consuming these quotas.
- Usage tracking is based on client identifiers and local JSON storage.
- Research memory and usage information are stored in local JSON files.
- The cache expires after seven days.

These limits are defined in the backend and can be adjusted as the application evolves.

The current client identifier mechanism is not a substitute for user authentication. A production version would require stronger controls for identity, quotas, and abuse prevention.

## Project Structure

The following is a simplified overview; adapt it to match the actual repository structure.

```text
ai-research-assistant/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── package-lock.json
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10 or a compatible version supported by the dependencies
- Node.js and npm
- A Google Gemini API key
- Internet access for Gemini API requests and arXiv searches

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ai-research-assistant
```

Replace the placeholder with your actual GitHub repository URL.

### 2. Set Up the Backend

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv myenv
```

On Windows, activate it with:

```bash
myenv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source myenv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the backend directory:

```env
GEMINI_API_KEY=your_gemini_api_key
OWNER_TOKEN=your_private_owner_token
```

`GEMINI_API_KEY` is required. `OWNER_TOKEN` is optional and is intended for owner testing.

Never commit your actual `.env` file or expose either secret in the frontend.

### 3. Start the Backend

From the backend directory, run:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at:

`http://localhost:8000`

Interactive API documentation:

`http://localhost:8000/docs`

### 4. Set Up the React Frontend

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

The frontend development URL depends on the scripts configured in `package.json`.

Ensure the frontend is configured to send API requests to the backend URL.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/research` | Generate or retrieve a research report |
| `GET` | `/memory` | Retrieve source statistics and report history |
| `GET` | `/usage` | Retrieve usage information for a client |
| `GET` | `/health` | Check API health |

### Research Request Example

**Endpoint:** `POST /research`

Request body:

```json
{
  "topic": "Compare RAG and fine-tuning for domain-specific AI assistants."
}
```

The request must include an `X-Client-Id` header.

The endpoint returns a structured `ResearchReport` object. The generated content depends on the topic, the available scientific literature, and the model response.

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Authenticates requests to Google Gemini |
| `OWNER_TOKEN` | No | Allows owner-level testing without consuming request quotas |

The model identifier, token pricing estimates, request limits, and cache duration are configured in the backend code.

## Deployment

### Backend — Render

1. Create a new web service linked to the GitHub repository.
2. Set the root directory to `backend`.
3. Install dependencies using `pip install -r requirements.txt`.
4. Configure the start command as `uvicorn main:app --host 0.0.0.0 --port $PORT`.
5. Add `GEMINI_API_KEY` and, if needed, `OWNER_TOKEN` as private environment variables.
6. Configure the service's allowed frontend origin before using it publicly.

**Important:** The current implementation stores memory, usage data, and evaluation logs in local files. Verify Render's filesystem persistence before relying on these files across restarts and redeployments.

### Frontend — Vercel

1. Import the GitHub repository into Vercel.
2. Set the root directory to `frontend`.
3. Configure the framework preset and build settings according to `package.json`.
4. Set the frontend's API base URL to the deployed Render backend URL.
5. Deploy the frontend and verify that API requests succeed.

Never put `OWNER_TOKEN` or `GEMINI_API_KEY` in frontend environment variables. The owner token must remain private on the backend.

## Future Improvements

Potential improvements for a production version include:

- Persistent database storage for research history, cached reports, and usage tracking.
- Stronger user authentication and per-user quota enforcement.
- More robust error handling and retry strategies for temporary model overload.
- Automated evaluation of relevance, accuracy, comparison quality, and citation correctness.
- Improved observability and cost monitoring.
- More advanced search and source-quality validation.

SQLite could be suitable for a small single-instance deployment, provided persistent storage is configured. A managed database such as PostgreSQL may be more appropriate if the application grows or requires concurrent access across multiple instances.

## Author

**Lara Rmayti**

AI Engineer | Machine Learning | Natural Language Processing | Agentic AI

- LinkedIn: https://linkedin.com/in/lara-rmayti-16508024a/
- GitHub: https://github.com/rmayti
