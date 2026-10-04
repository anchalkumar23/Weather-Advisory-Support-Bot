# Weather-Advisory Support Bot Implementation Plan

**Goal:** LangGraph chat bot that answers outdoor-safety questions strictly from YAML SOPs over live Open-Meteo data, with a React chat UI and an eval suite.

**Architecture:** LLM extracts a structured intent (closed tag vocabulary read from `sops.yaml`) → code fetches weather and computes window facts → code matches SOPs → LLM phrases → code verifies every number/SOP id, else deterministic template. Failure paths are separate graph branches.

**Tech Stack:** Python 3.13, FastAPI, LangGraph (MemorySaver), langchain-groq, httpx, PyYAML · Vite + React · pytest.

Spec: `docs/specs/2026-10-04-weather-advisory-bot-design.md`

## File map
| File | Responsibility |
|---|---|
| `backend/sops.yaml` | Activity glossary + all SOPs (the only file to edit for policy) |
| `backend/app/weather.py` | Geocode, forecast fetch, window facts (`METRICS` = vocabulary SOPs may use) |
| `backend/app/engine.py` | Load/validate SOPs, evaluate conditions + score SOPs, rank, verdict |
| `backend/app/llm.py` | Groq client, intent extraction prompt, compose prompt |
| `backend/app/graph.py` | LangGraph state, nodes, routing, `verify` grounding check |
| `backend/app/main.py` | FastAPI `/api/chat`, `/api/health`, serves built frontend |
| `backend/tests/test_core.py` | No-LLM checks: engine, facts, verify, failure routing |
| `backend/evals/run_evals.py` | Eval suite (real LLM, fixture + live weather) → `evals/RESULTS.md` |
| `frontend/` | Vite React chat page (verdict chip, headline, "Why?" drawer) |

## Tasks
- [ ] 1. `weather.py`: `geocode`, `fetch_forecast`, `window_range`, `compute_facts`, `get_weather`; raise `WeatherError` on empty geocode, HTTP error, `error:true`.
- [ ] 2. `sops.yaml` (12+ SOPs, 4 categories, fuzzy score SOP, lead rain-system SOP, all-clear fallback) + `engine.py` with load-time validation (unknown metric / activity / severity → `ValueError`).
- [ ] 3. `tests/test_core.py`: engine matching, ranking, fuzzy bands, fallback, facts window maths, verify accepts/rejects. Run `pytest` → pass.
- [ ] 4. `llm.py` + `graph.py`: nodes `understand, fetch_weather, match_sops, compose, verify, template_reply, no_guidance, ask_location, unavailable, explain`; conditional edges; MemorySaver.
- [ ] 5. Extend tests: graph with stubbed LLM + unreachable forecast URL → `unavailable`, no digits in reply.
- [ ] 6. `main.py` + `requirements.txt` + `.env.example` + `.gitignore`.
- [ ] 7. Frontend (impeccable skill): Vite React, proxy `/api` → 8000, build passes.
- [ ] 8. `evals/run_evals.py` (≥12 cases) → run with key, write `RESULTS.md` honestly.
- [ ] 9. README (setup/run, SOP format + why YAML, design decisions, conflict policy, grounding enforcement, eval notes, known gaps). Security review pass.
