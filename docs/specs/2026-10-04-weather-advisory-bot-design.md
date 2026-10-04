# Weather-Advisory Support Bot — Design

Date: 2026-10-04 · Status: approved

## Goal
Chat bot that answers outdoor-activity safety questions using live Open-Meteo data, where every piece of advice comes from a written SOP (never the model), and SOPs can be added/changed without touching code.

## Stack
- Backend: Python 3.13, FastAPI, LangGraph, `langchain-groq` (default model `llama-3.3-70b-versatile`, override with `GROQ_MODEL`), `httpx`, `pyyaml`.
- Frontend: Vite + React (single chat page), talks to `POST /api/chat`.
- Secrets: `GROQ_API_KEY` in `.env`, `.env` in `.gitignore`.

## Responsibilities: code vs model
| Decision | Owner |
|---|---|
| Parse question → location, activity tags (closed enum from YAML), time window, off-topic flag | LLM (structured output) |
| Fetch weather, compute facts for the window | Code |
| Which SOPs apply | Code (`engine.py`, pure function of YAML + facts + tags) |
| Severity ranking / verdict | Code |
| Wording of the reply | LLM |
| Every number and SOP id in the reply exists in facts / matched set | Code (`verify` node) |

## SOP format (`backend/sops.yaml`)
```yaml
- id: SOP-RAIN-SYSTEM
  title: Active heavy-rain system
  category: general
  severity: critical        # info < low < moderate < high < critical
  lead: true                # always rendered first
  activities: "*"           # or list of tags
  when:                     # all/any trees of {metric, op, value}
    any:
      - {metric: rain_24h_mm, op: ">=", value: 64.5}
  advice: "..."
```
Fuzzy SOPs use `score:` instead of `when:` — a list of comfort factors, each `{metric, good: [lo, hi], points}`; total points mapped to bands with their own advice and severity.

Activity tags vocabulary = union of all `activities` lists in the YAML, injected into the extraction prompt at runtime → a new SOP with a new tag needs no code change. Metrics vocabulary is fixed by `weather.py` (documented limitation: an SOP needing an uncomputed metric needs a one-line code change).

## Graph
```
understand → [off_topic|no activity] → no_guidance
           → [no location after memory merge] → ask_location
           → fetch_weather → [geocode miss / HTTP error] → weather_unavailable
                           → match_sops → [none] → no_guidance
                                        → compose → verify → [fail] → template_reply
                                                           → [ok] → END
```
All terminal nodes write `reply`, `verdict`, `citations`, `facts`.

## Memory
LangGraph `MemorySaver`, `thread_id` = browser session id. State carries `location`, `activities`, `window`, last `citations`. The understand node sees the prior structured context; missing fields inherit from it. Resets on server restart.

## Conflict policy
Surface all matched SOPs, sorted: `lead` first, then severity desc. Verdict = max severity → `critical/high: Avoid`, `moderate: Caution`, `low/info: Go`.

## Grounding enforcement
`verify` extracts all numbers from the LLM reply; each must equal (±0.05) a value in the facts dict or appear in a cited SOP's text (thresholds). SOP ids mentioned must be in the matched set. Failure → deterministic template.

## Failure handling
Geocode empty/error and forecast HTTP error/`error:true` both route to `weather_unavailable`: plain statement, no numbers, no advice.

## Frontend
Verdict-first: coloured chip (Go / Caution / Avoid / No guidance / Unavailable), one-sentence headline, collapsible "Why?" with SOP cards and live numbers. Suggested question chips on empty state. Session id in `sessionStorage`.

## Evals (`backend/evals/run_evals.py`)
Fixture-weather cases (deterministic): clear SOP hit ×2, paraphrase ×2, fuzzy picnic, multi-SOP conflict, no-SOP, follow-up memory, prompt injection, unreachable API. Live case: real Open-Meteo for a set of candidate cities, checks reply numbers ⊆ API facts and cited SOPs = engine output. Results written to `evals/RESULTS.md`.
