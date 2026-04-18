import { useState } from 'react'
import './App.css'

const sampleMessage = `MSH|^~\\&|ADT1|MCM|IFENG|IFENG|20060529090131||ADT^A01|599102|P|2.3\r
PID|1||123456^^^HOSP^MR||DOE^JOHN||19800101|M\r
PV1|1|I|W^389^1^UABH||||1234^PHYSICIAN^ONE|||||||||||VN12345`

function App() {
  const [hl7Message, setHl7Message] = useState(sampleMessage)
  const [result, setResult] = useState('')
  const [error, setError] = useState('')

  const convertMessage = async () => {
    setResult('')
    setError('')
    try {
      const response = await fetch('http://127.0.0.1:8000/api/v1/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hl7_message: hl7Message }),
      })
      const payload = await response.json()
      if (!response.ok) {
        setError(payload.detail || 'Conversion failed.')
        return
      }
      setResult(JSON.stringify(payload, null, 2))
    } catch {
      setError('Unable to reach backend API. Confirm FastAPI is running on port 8000.')
    }
  }

  return (
    <main className="container">
      <h1>HL7 v2 to FHIR Converter MVP</h1>
      <p>Paste an HL7 ADT message with MSH/PID/PV1 segments.</p>
      <textarea
        value={hl7Message}
        onChange={(event) => setHl7Message(event.target.value)}
      />
      <button type="button" onClick={convertMessage}>
        Convert to FHIR Bundle
      </button>
      {error && <p className="error">{error}</p>}
      {result && (
        <>
          <h2>FHIR Bundle JSON</h2>
          <pre>{result}</pre>
        </>
      )}
    </main>
  )
}

export default App
