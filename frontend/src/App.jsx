import { useEffect, useRef, useState } from 'react'
import { ArrowUp, ChevronDown, CircleCheck, CircleSlash, CloudOff, MapPin, OctagonX, RotateCcw, TriangleAlert } from 'lucide-react'

const VERDICTS = {
  avoid: { word: 'Avoid', Icon: OctagonX, tone: 'avoid' },
  caution: { word: 'Caution', Icon: TriangleAlert, tone: 'caution' },
  go: { word: 'Go', Icon: CircleCheck, tone: 'go' },
  none: { word: 'No guidance', Icon: CircleSlash, tone: 'quiet' },
  ask: { word: 'Which place?', Icon: MapPin, tone: 'quiet' },
  unavailable: { word: 'Unavailable', Icon: CloudOff, tone: 'quiet' },
}
const SEVERITY_TONE = { critical: 'avoid', high: 'avoid', moderate: 'caution', low: 'go', info: 'go' }
const READINGS = [
  ['temp_max_c', 'Temperature, high', '°C'],
  ['feels_like_max_c', 'Feels like, high', '°C'],
  ['feels_like_min_c', 'Feels like, low', '°C'],
  ['rain_prob_max_pct', 'Rain chance', '%'],
  ['rain_window_mm', 'Rain in window', 'mm'],
  ['rain_past24h_mm', 'Rain, last 24 h', 'mm'],
  ['rain_next24h_mm', 'Rain, next 24 h', 'mm'],
  ['wind_max_kmh', 'Wind', 'km/h'],
  ['gust_max_kmh', 'Gusts', 'km/h'],
  ['uv_max', 'UV index', ''],
  ['thunder_in_window', 'Thunderstorm', ''],
]
const SAMPLES = [
  'Is it safe to cycle to work in Bhopal today?',
  'Good day for a picnic in Bengaluru tomorrow?',
  'Can I take my kids to the park in Delhi this afternoon?',
  'Should I walk my dog in Chennai this evening?',
]

function newSessionId() {
  return crypto.randomUUID().replaceAll('-', '')
}

function storedSessionId() {
  try {
    const id = sessionStorage.getItem('wrx-session') || newSessionId()
    sessionStorage.setItem('wrx-session', id)
    return id
  } catch {
    return newSessionId()
  }
}

export default function App() {
  const [sessionId, setSessionId] = useState(storedSessionId)
  const [turns, setTurns] = useState([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [turns, busy])

  async function ask(text) {
    const message = text.trim()
    if (!message || busy) return
    setDraft('')
    setTurns(t => [...t, { role: 'user', text: message }])
    setBusy(true)
    let data
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message }),
      })
      data = await res.json()
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The request was rejected.')
    } catch (e) {
      data = { verdict: 'unavailable', reply: `I couldn't reach the advisory service (${e.message}). Nothing was checked, so I can't advise. Try again in a moment.`, hits: [] }
    }
    setTurns(t => [...t, { role: 'bot', data }])
    setBusy(false)
    inputRef.current?.focus()
  }

  function reset() {
    const id = newSessionId()
    try { sessionStorage.setItem('wrx-session', id) } catch { /* private mode: keep it in memory */ }
    setSessionId(id)
    setTurns([])
    inputRef.current?.focus()
  }

  let labelNo = 0
  return (
    <div className="shell">
      <header className="masthead">
        <div className="brand">
          <span className="rx" aria-hidden="true">R<span>x</span></span>
          <div>
            <h1>Weather Rx</h1>
            <p>Outdoor safety advice, dispensed only from written policy and live weather.</p>
          </div>
        </div>
        {turns.length > 0 && (
          <button className="ghost" onClick={reset}><RotateCcw size={16} aria-hidden="true" />New session</button>
        )}
      </header>

      <main className="thread" aria-live="polite">
        {turns.length === 0 && <EmptyLabel onPick={ask} />}
        {turns.map((t, i) => t.role === 'user'
          ? <p key={i} className="ask-line"><span className="sr-only">You asked: </span>{t.text}</p>
          : <Label key={i} data={t.data} no={++labelNo} />)}
        {busy && <Printing />}
        <div ref={endRef} />
      </main>

      <form className="composer" onSubmit={e => { e.preventDefault(); ask(draft) }}>
        <label htmlFor="q" className="sr-only">Ask about an outdoor plan</label>
        <input id="q" ref={inputRef} value={draft} onChange={e => setDraft(e.target.value)} maxLength={500}
          placeholder="Ask about an outdoor plan…" autoComplete="off" autoFocus />
        <button type="submit" disabled={busy || !draft.trim()} aria-label="Ask"><ArrowUp size={20} aria-hidden="true" /></button>
      </form>
    </div>
  )
}

function EmptyLabel({ onPick }) {
  return (
    <section className="label blank">
      <h2>What are you planning?</h2>
      <p>Name the activity, the place and when. I check live Open-Meteo data against our written safety policies and tell you which one applies. If no policy covers it, I say so.</p>
      <div className="samples">
        {SAMPLES.map(s => <button key={s} className="sample" onClick={() => onPick(s)}>{s}</button>)}
      </div>
    </section>
  )
}

function Printing() {
  return (
    <div className="label printing" role="status">
      <span className="feed" aria-hidden="true" />
      Checking live weather against policy…
    </div>
  )
}

function Label({ data, no }) {
  const v = VERDICTS[data.verdict] || VERDICTS.none
  const hits = data.hits || []
  const [open, setOpen] = useState(false)
  const whyId = `why-${no}`
  return (
    <article className={`label tone-${v.tone}`}>
      <div className="label-meta">
        <span>No. {String(no).padStart(4, '0')}</span>
        {data.place && <span>{data.place.name}</span>}
        {data.window && <span>{data.window}</span>}
      </div>

      <h2 className="verdict"><v.Icon className="verdict-icon" aria-hidden="true" strokeWidth={2.4} />{v.word}</h2>
      <p className="instruction"><Cited text={data.reply || ''} /></p>

      {hits.length > 0 && (
        <>
          <ul className="stickers" aria-label="Policies applied">
            {hits.map(h => (
              <li key={h.id} className={`sticker tone-${SEVERITY_TONE[h.severity]}`}>
                <b>{h.severity}</b><span className="sop-id">{h.id}</span>{h.title}
              </li>
            ))}
          </ul>
          <div className="stub">
            <button className="why" aria-expanded={open} aria-controls={whyId} onClick={() => setOpen(o => !o)}>
              Why? <span>Rule and live readings</span><ChevronDown size={18} aria-hidden="true" className="chev" />
            </button>
            {open && <Why id={whyId} data={data} />}
          </div>
        </>
      )}
    </article>
  )
}

function Cited({ text }) {
  return text.split(/(\[SOP-[A-Z]+-\d+\])/).map((part, i) =>
    /^\[SOP-/.test(part) ? <span key={i} className="sop-id inline">{part.slice(1, -1)}</span> : part)
}

function Why({ id, data }) {
  const facts = data.facts || {}
  // Which readings tripped a rule: reasons end with "(rule: metric op value)".
  const tripped = {}
  for (const h of data.hits) for (const r of h.reasons) {
    const m = r.match(/rule: (\w+) (\S+) (\S+)\)/)
    if (m) tripped[m[1]] = `${m[2]} ${m[3]} · ${h.id}`
  }
  return (
    <div id={id} className="why-body">
      <ol className="prescribed">
        {data.hits.map(h => (
          <li key={h.id}>
            <p><span className="sop-id">{h.id}</span> <b>{h.title}</b> · severity {h.severity}</p>
            <p className="reason">Triggered because {h.reasons.join('; ')}.</p>
            <p className="policy-text">Policy text: “{h.advice}”</p>
          </li>
        ))}
      </ol>
      {Object.keys(facts).length > 0 && (
        <>
          <DayStrip window={data.window} />
          <table className="readout">
            <caption>Live Open-Meteo readings for {data.place?.name}, {data.window}</caption>
            <tbody>
              {READINGS.filter(([k]) => k in facts).map(([k, label, unit]) => (
                <tr key={k} className={tripped[k] ? 'tripped' : ''}>
                  <th scope="row">{label}</th>
                  <td>{typeof facts[k] === 'boolean' ? (facts[k] ? 'yes' : 'no') : `${facts[k]} ${unit}`}</td>
                  <td>{tripped[k] ? `rule ${tripped[k]}` : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      {data.source === 'template' && (
        <p className="note">The model’s wording failed the number and citation check, so this reply uses the policy text directly.</p>
      )}
    </div>
  )
}

function DayStrip({ window }) {
  const m = window?.match(/\((\d{2}):00–(\d{2}):00\)/)
  if (!m) return null
  const [from, to] = [Number(m[1]), Number(m[2])]
  const end = to >= from ? to + 1 : 24 // window crosses midnight: draw to end of day
  return (
    <figure className="strip" aria-label={`Window checked: ${m[1]}:00 to ${m[2]}:00`}>
      <div className="strip-track">
        <span className="strip-window" style={{ left: `${(from / 24) * 100}%`, width: `${((end - from) / 24) * 100}%` }} />
      </div>
      <figcaption>{[0, 6, 12, 18, 24].map(h => <span key={h}>{String(h).padStart(2, '0')}</span>)}</figcaption>
    </figure>
  )
}
