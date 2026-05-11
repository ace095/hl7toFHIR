import { useMemo, useState } from 'react'
import './App.css'

const sampleMessage = `MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r
PID|1||123456^^^HOSP^MR||DOE^JOHN||19800101|M\r
PV1|1|I|W^389^1^UABH||||1234^PHYSICIAN^ONE|||||||||||VN12345`

const sampleFeeds = [
  {
    key: 'admit-baseline',
    label: 'A01 Admit (baseline)',
    message: `MSH|^~\\&|ADT_APP|HOSP_A|EHR|HOSP_A|20260510113010||ADT^A01|100002|P|2.5\r
PID|1||900001^^^HOSP_A^MR||DOE^JANE^A||19880514|F\r
PV1|1|I|3N^312^1^HOSP_A||||12345^SMITH^ALAN^^^^^NPI|||||||||||V000001^^^HOSP_A^VN`,
  },
  {
    key: 'mapped-warnings',
    label: 'A03 with warning triggers',
    message: `MSH|^~\\&|ADT_APP|HOSP_A|EHR|HOSP_A|20260510124500||ADT^A03|100003|P|2.5\r
PID|1||900001^^^HOSP_A^MR||DOE^JANE^A||19880514|X\r
PV1|1|Z|3N^312^1^HOSP_A||||12345^SMITH^ALAN^^^^^NPI|||||||||||V000001^^^HOSP_A^VN`,
  },
  {
    key: 'unsupported',
    label: 'Negative test (unsupported ORM)',
    message: `MSH|^~\\&|ORM_APP|HOSP_A|EHR|HOSP_A|20260510141500||ORM^O01|100009|P|2.5\r
PID|1||900001^^^HOSP_A^MR||DOE^JANE^A||19880514|F`,
  },
]

// Load API base URL from environment variable (configurable per deployment)
// Default: http://127.0.0.1:8000 for local development
// Set VITE_API_BASE_URL in .env files to customize for other environments
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

function App() {
  const [hl7Message, setHl7Message] = useState(sampleMessage)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [selectedFeed, setSelectedFeed] = useState(sampleFeeds[0].key)

  const parsedLines = useMemo(
    () => hl7Message.split(/\r\n|\n|\r/).filter((line) => line.trim().length > 0),
    [hl7Message],
  )

  const segmentNames = useMemo(() => parsedLines.map((line) => line.split('|')[0].trim()).filter(Boolean), [parsedLines])

  const hasRequiredSegments = segmentNames.includes('MSH') && segmentNames.includes('PID')

  const resultJson = useMemo(() => (result ? JSON.stringify(result, null, 2) : ''), [result])
  const warningItems = useMemo(() => {
    const occurrences = new Map()
    return (result?.warnings ?? []).map((warning) => {
      const count = (occurrences.get(warning) ?? 0) + 1
      occurrences.set(warning, count)
      return { warning, key: `${warning}-${count}` }
    })
  }, [result])

  const applySelectedFeed = () => {
    const selected = sampleFeeds.find((feed) => feed.key === selectedFeed)
    if (selected) {
      setHl7Message(selected.message)
      setResult(null)
      setError('')
    }
  }

  const copyResult = async () => {
    if (!resultJson) return
    try {
      await navigator.clipboard.writeText(resultJson)
    } catch (clipboardError) {
      console.error(clipboardError)
    }
  }

  const convertMessage = async () => {
    setResult(null)
    setError('')
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/convert`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hl7_message: hl7Message }),
      })
      const payload = await response.json()
      if (!response.ok) {
        setError(payload.detail || 'Conversion failed.')
        return
      }
      setResult(payload)
    } catch (error) {
      console.error(error)
      setError(`Unable to reach backend API at ${API_BASE_URL}. Confirm FastAPI is running, or set VITE_API_BASE_URL environment variable.`)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="container">
      <header className="hero">
        <p className="eyebrow">HL7 v2 to FHIR R4</p>
        <h1>Message Converter Workbench</h1>
        <p className="subtitle">Paste an ADT message or load a sample feed, then inspect warnings and converted FHIR output side by side.</p>
      </header>

      <section className="controls">
        <label htmlFor="feed-select">Sample feed</label>
        <div className="control-row">
          <select id="feed-select" value={selectedFeed} onChange={(event) => setSelectedFeed(event.target.value)}>
            {sampleFeeds.map((feed) => (
              <option key={feed.key} value={feed.key}>
                {feed.label}
              </option>
            ))}
          </select>
          <button type="button" className="secondary" onClick={applySelectedFeed}>
            Load Sample
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setHl7Message(sampleMessage)
              setResult(null)
              setError('')
            }}
          >
            Reset
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setHl7Message('')
              setResult(null)
              setError('')
            }}
          >
            Clear
          </button>
        </div>
      </section>

      <section className="workbench">
        <section className="editor-panel">
          <div className="editor-meta">
            <span>{parsedLines.length} segment line(s)</span>
            <span>Detected: {segmentNames.join(', ') || 'none'}</span>
            <span className={hasRequiredSegments ? 'ok' : 'warn'}>{hasRequiredSegments ? 'MSH/PID present' : 'MSH and PID required'}</span>
          </div>
          <textarea
            value={hl7Message}
            onChange={(event) => setHl7Message(event.target.value)}
            placeholder="Paste HL7 message here..."
          />
          <div className="action-row">
            <button type="button" onClick={convertMessage} disabled={isLoading || !hl7Message.trim()}>
              {isLoading ? 'Converting...' : 'Convert to FHIR Bundle'}
            </button>
          </div>
        </section>

        <section className="results">
          {error && <p className="error">{error}</p>}

          {!result && !error && (
            <div className="empty-state">
              <h2>Output Pane</h2>
              <p>Converted FHIR resources will appear here after you run the message.</p>
              <ol>
                <li>Load or paste an HL7 message.</li>
                <li>Click Convert to FHIR Bundle.</li>
                <li>Review warnings and copy JSON.</li>
              </ol>
            </div>
          )}

          {result && (
            <>
              <div className="summary-grid">
                <article>
                  <h3>Patient</h3>
                  <p>{result.bundle?.entry?.[0]?.resource?.id || 'N/A'}</p>
                </article>
                <article>
                  <h3>Encounter</h3>
                  <p>{result.bundle?.entry?.[1]?.resource?.id || 'N/A'}</p>
                </article>
                <article>
                  <h3>Warnings</h3>
                  <p>{result.warnings?.length ?? 0}</p>
                </article>
              </div>

              {result.warnings?.length > 0 && (
                <div className="warnings">
                  <h2>Warnings</h2>
                  <ul>
                    {warningItems.map(({ warning, key }) => (
                      <li key={key}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="json-header">
                <h2>FHIR Bundle JSON</h2>
                <button type="button" className="secondary" onClick={copyResult}>
                  Copy JSON
                </button>
              </div>
              <pre>{resultJson}</pre>
            </>
          )}
        </section>
      </section>
    </main>
  )
}

export default App
