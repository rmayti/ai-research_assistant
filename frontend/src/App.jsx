import { useState, useEffect } from 'react'
import { exportReportAsWord } from './exportWord.js'

// En dev, l'API tourne en local. En prod, remplace via une variable
// d'environnement Vite (VITE_API_URL) pointant vers ton backend déployé.
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Optionnel : si toi (le propriétaire) définis VITE_OWNER_TOKEN dans ton
// .env local, tes propres requêtes ignorent les limites. Reste vide/absent
// pour tes testeurs — ils n'ont jamais ce token.
const OWNER_TOKEN = import.meta.env.VITE_OWNER_TOKEN || null

// ID anonyme unique à ce navigateur, généré une seule fois et
// réutilisé ensuite — permet au backend de compter les essais
// gratuits sans avoir besoin d'un vrai système de compte.
function getClientId() {
  let id = localStorage.getItem('ara_client_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('ara_client_id', id)
  }
  return id
}

const EXAMPLE_TOPICS = [
  'Compare RAG and Fine-tuning for an educational AI application.',
  'Compare Machine Learning and Deep Learning .',
  'Compare GraphRag and ShortRag .',
]

const LOADING_MESSAGES = [
  'Searching Arxiv for relevant papers…',
  'Reading through the literature…',
  'Comparing both approaches…',
  'Structuring the final report…',
]

function ComparisonTable({ points }) {
  return (
    <div className="comparison-table">
      <div className="comparison-row comparison-header">
        <div className="comparison-cell">Criterion</div>
        <div className="comparison-cell">Approach A</div>
        <div className="comparison-cell">Approach B</div>
      </div>
      {points.map((point, i) => (
        <div className="comparison-row" key={i}>
          <div className="comparison-cell">{point.criterion}</div>
          <div className="comparison-cell">{point.approach_a}</div>
          <div className="comparison-cell">{point.approach_b}</div>
        </div>
      ))}
    </div>
  )
}

function ApproachCard({ label, variant, pros, cons }) {
  return (
    <div className={`approach-card ${variant}`}>
      <p className="approach-name">{label}</p>
      {pros?.length > 0 && (
        <ul className="pros-list">
          {pros.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )}
      {cons?.length > 0 && (
        <ul className="cons-list">
          {cons.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function SourcesList({ sources }) {
  return (
    <div className="sources-list">
      {sources.map((source, i) => (
        <a
          key={i}
          className="source-item"
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
        >
          <div className="source-title">{source.title}</div>
          <div className="source-relevance">{source.relevance}</div>
          <span className="source-url">{source.url}</span>
        </a>
      ))}
    </div>
  )
}

function ReportView({ report }) {
  return (
    <div className="report">
      <div className="report-header-row">
        <h1 className="report-title">{report.title}</h1>
        <div className="export-buttons no-print">
          <button className="export-button" onClick={() => window.print()}>
            Export PDF
          </button>
          <button className="export-button" onClick={() => exportReportAsWord(report)}>
            Export Word
          </button>
        </div>
      </div>

      <div className="report-section">
        <p className="section-label">Overview</p>
        <p className="report-overview">{report.overview}</p>
      </div>

      <div className="report-section">
        <p className="section-label">Comparison</p>
        <ComparisonTable points={report.comparison_points} />
      </div>

      <div className="report-section">
        <p className="section-label">Strengths &amp; Weaknesses</p>
        <div className="pros-cons-grid">
          <ApproachCard
            label="Approach A"
            variant="a"
            pros={report.pros_approach_a}
            cons={report.cons_approach_a}
          />
          <ApproachCard
            label="Approach B"
            variant="b"
            pros={report.pros_approach_b}
            cons={report.cons_approach_b}
          />
        </div>
      </div>

      <div className="report-section">
        <p className="section-label">Recommendation</p>
        <div className="recommendation-box">
          <p>{report.recommendation}</p>
        </div>
      </div>

      <div className="report-section">
        <p className="section-label">Sources</p>
        <SourcesList sources={report.sources} />
      </div>
    </div>
  )
}

export default function App() {
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingMsgIndex, setLoadingMsgIndex] = useState(0)
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const [remaining, setRemaining] = useState(null)

  useEffect(() => {
    fetch(`${API_URL}/usage`, { headers: { 'X-Client-Id': getClientId() } })
      .then((res) => res.json())
      .then((data) => setRemaining(data.remaining))
      .catch(() => {})
  }, [])

  async function runResearch(query) {
    const finalTopic = query ?? topic
    if (!finalTopic.trim() || loading) return

    setLoading(true)
    setError(null)
    setReport(null)
    setLoadingMsgIndex(0)

    const interval = setInterval(() => {
      setLoadingMsgIndex((i) => (i + 1) % LOADING_MESSAGES.length)
    }, 3000)

    try {
      const res = await fetch(`${API_URL}/research`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Client-Id': getClientId(),
          ...(OWNER_TOKEN ? { 'X-Owner-Token': OWNER_TOKEN } : {}),
        },
        body: JSON.stringify({ topic: finalTopic }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Request failed (${res.status})`)
      }

      const data = await res.json()
      setReport(data)
      setRemaining((r) => (r !== null ? Math.max(0, r - 1) : r))
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.')
    } finally {
      clearInterval(interval)
      setLoading(false)
    }
  }

  function handleSubmit(e) {
    e.preventDefault()
    runResearch()
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">AI Research Assistant</h1>
        <p className="app-subtitle">
          Give it a topic — it searches Arxiv for relevant papers,
          analyzes both approaches, and returns a structured comparison
          report with sources.
        </p>
      </header>

      <form className="search-form" onSubmit={handleSubmit}>
        <input
          className="search-input"
          type="text"
          placeholder="e.g. Compare RAG and Fine-tuning for an educational AI application."
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          disabled={loading}
        />
        <button className="search-button" type="submit" disabled={loading}>
          {loading ? 'Researching…' : 'Compare'}
        </button>
      </form>

      <div className="examples-row">
        {EXAMPLE_TOPICS.map((example) => (
          <button
            key={example}
            type="button"
            className="example-chip"
            onClick={() => {
              setTopic(example)
              runResearch(example)
            }}
            disabled={loading}
          >
            {example.replace('Compare ', '').replace(/\.$/, '')}
          </button>
        ))}
      </div>

      {remaining !== null && (
        <p className="memory-note">
          {remaining > 0
            ? `${remaining} free ${remaining === 1 ? 'try' : 'tries'} remaining`
            : 'Free limit reached — contact us for extended access'}
        </p>
      )}

      {loading && (
        <div className="loading-block">
          <div className="loading-spinner" />
          <p className="loading-text">{LOADING_MESSAGES[loadingMsgIndex]}</p>
        </div>
      )}

      {error && <div className="error-block">⚠ {error}</div>}

      {report && !loading && <ReportView report={report} />}

      <footer className="app-footer">
        Built with Agno and Gemini. Sources from Arxiv.
      </footer>
    </div>
  )
}
