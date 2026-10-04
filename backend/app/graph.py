"""LangGraph agent. Each failure mode is its own branch; the model never decides which policy applies.

understand ─┬─ model down ──────────────────────────────► unavailable
            ├─ "why did you say that?" ─────────────────► explain
            ├─ off-topic / no covered activity ─────────► no_guidance
            ├─ no location (none remembered either) ────► ask_location
            └─► fetch_weather ─┬─ geocode/API failure ──► unavailable
                               └─► match_sops ─┬─ none ─► no_guidance
                                               └─► compose ► verify ─┬─ grounded ─► END
                                                                     └─ not ──────► template_reply
"""
import logging
import re
from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from . import engine, llm, weather

log = logging.getLogger("advisor")
NUM = re.compile(r"\d+(?:\.\d+)?")
SOP_ID = re.compile(r"SOP-[A-Z]+-\d+")


class State(TypedDict, total=False):
    message: str
    history: list      # earlier user messages (last few)
    ctx: dict          # remembered across turns: location, activities, day, part
    last: dict         # previous answer, so "why?" can cite it
    intent: dict
    error: str
    place: dict
    facts: dict
    window: str
    hits: list
    draft: str
    grounded: bool
    reply: str
    verdict: str
    source: str        # llm | template | fixed: how the reply text was produced


def _answer(state, reply, verdict, source="fixed", hits=()):
    hits = list(hits)
    return {"reply": reply, "verdict": verdict, "source": source, "hits": hits,
            "last": {"hits": hits, "verdict": verdict, "place": state.get("place"), "window": state.get("window"),
                     "facts": state.get("facts")}}


# ---------- nodes ----------

def understand(state):
    glossary, _ = engine.load()
    ctx, msg = state.get("ctx") or {}, state["message"]
    reset = {"error": "", "place": None, "facts": {}, "window": "", "hits": [], "draft": "", "grounded": False,
             "history": (state.get("history") or [])[-3:] + [msg]}
    try:
        it = llm.extract_intent(msg, glossary, ctx, state.get("history") or [])
    except Exception as e:  # any model/network failure takes the honest path
        log.warning("intent extraction failed: %s", e)
        return {**reset, "intent": {}, "error": "model"}
    acts = [a for a in it["activities"] or [] if a in glossary]  # closed vocabulary, enforced in code
    new_place = it["location"] and it["location"].strip().lower() != (ctx.get("location") or "").lower()
    # A follow-up keeps the remembered place/activity/time unless this message changes them.
    ctx = {
        "location": it["location"] or ctx.get("location"),
        "activities": acts or ctx.get("activities") or [],
        "day": it["day"] or (not new_place and ctx.get("day")) or "today",
        "part": it["part"] or (not new_place and not it["day"] and ctx.get("part")) or ("all_day" if it["day"] else "now"),
    }
    return {**reset, "intent": {**it, "activities": acts}, "ctx": ctx}


def route_intent(state):
    it, ctx = state["intent"], state.get("ctx") or {}
    if state["error"]:
        return "unavailable"
    if it["asks_why"] and not it["activities"] and not it["location"]:  # naming a plan makes it a new question
        return "explain"
    if not it["on_topic"] or not ctx.get("activities"):
        return "no_guidance"
    if not ctx.get("location"):
        return "ask_location"
    return "fetch_weather"


def fetch_weather(state):
    c = state["ctx"]
    try:
        place, facts, window = weather.get_weather(c["location"], c["day"], c["part"])
    except weather.WeatherError as e:
        return {"error": str(e)}
    return {"place": place, "facts": facts, "window": window}


def match_sops(state):
    _, sops = engine.load()
    return {"hits": engine.match(sops, state["facts"], state["ctx"]["activities"])}


def compose(state):
    try:
        draft = llm.compose(state["place"]["name"], state["window"], state["ctx"]["activities"], state["facts"],
                            state["hits"])
    except Exception as e:
        log.warning("compose failed: %s", e)
        draft = ""
    return {"draft": draft}


def grounding_problems(text, hits, facts, window=""):
    """Every number must come from the live facts / policy text, every SOP id must be one that matched, all must be
    cited, and the live values that triggered each SOP must be reported (an answer without them isn't grounded)."""
    if not text.strip():
        return ["empty reply"]
    ids, cited = {h["id"] for h in hits}, set(SOP_ID.findall(text))
    problems = [f"cites a policy that did not match: {i}" for i in sorted(cited - ids)]
    problems += [f"does not cite {i}" for i in sorted(ids - cited)]
    sources = [str(v) for v in facts.values()] + [h["advice"] for h in hits] + [window]
    allowed = {float(n) for src in sources for n in NUM.findall(src)}
    for n in NUM.findall(SOP_ID.sub("", text)):
        if not any(abs(float(n) - a) < 0.051 or float(n) == round(a) for a in allowed):
            problems.append(f"number {n} is not in the live data or policy")
    said = [float(n) for n in NUM.findall(text)]
    for h in hits:
        for metric, value in h.get("evidence", {}).items():
            if not any(abs(s - value) < 0.051 or s == round(value) for s in said):
                problems.append(f"{h['id']} fired on {metric} = {value} but the reply doesn't say so")
    return problems


def verify(state):
    problems = grounding_problems(state["draft"], state["hits"], state["facts"], state["window"])
    if problems:
        log.warning("draft rejected, using template: %s", problems)
        return {"grounded": False}
    return {"grounded": True, **_answer(state, state["draft"], engine.verdict(state["hits"]), "llm", state["hits"])}


def template_reply(state):
    text = "\n".join(f"{h['advice']} [{h['id']}]" for h in state["hits"])
    return _answer(state, text, engine.verdict(state["hits"]), "template", state["hits"])


def no_guidance(state):
    if not state["intent"].get("on_topic"):
        text = ("I can only help with outdoor-activity safety, like \"Is it safe to cycle in Pune this evening?\" "
                "or \"Is today good for a picnic in Delhi?\"")
    else:
        glossary, _ = engine.load()
        covered = ", ".join(k.replace("_", " ") for k in glossary)
        text = (f"I don't have a policy that covers that, so I won't guess. "
                f"I can advise on: {covered}.")
    return _answer(state, text, "none")


def ask_location(state):
    return _answer(state, "Which city or town is this for? I need it to check the live weather.", "ask")


def unavailable(state):
    if state["error"] == "model":
        text = "I can't process questions right now because my language service is unavailable. Please try again shortly."
    else:
        text = (f"I couldn't get live weather: {state['error']}. I won't guess at conditions, "
                f"so I can't give advice right now. Please check the place name or try again shortly.")
    return _answer(state, text, "unavailable")


def explain(state):
    last = state.get("last") or {}
    if not last.get("hits"):
        return {"reply": "My previous answer wasn't based on any policy, so there's nothing to cite. "
                         "Ask about an outdoor plan and I'll show the policy behind the answer.",
                "verdict": "none", "source": "fixed", "hits": []}
    where = f"{last['place']['name']}, {last['window']}"
    lines = [f"{h['id']} ({h['title']}, severity {h['severity']}): {'; '.join(h['reasons'])}." for h in last["hits"]]
    text = f"That answer came from these policies, checked against live Open-Meteo data for {where}:\n" + "\n".join(lines)
    return {"reply": text, "verdict": last["verdict"], "source": "fixed", "hits": last["hits"],
            "facts": last["facts"], "place": last["place"], "window": last["window"]}


# ---------- wiring ----------

def build(checkpointer=None):
    g = StateGraph(State)
    for fn in (understand, fetch_weather, match_sops, compose, verify, template_reply, no_guidance, ask_location,
               unavailable, explain):
        g.add_node(fn.__name__, fn)
    g.add_edge(START, "understand")
    g.add_conditional_edges("understand", route_intent,
                            ["unavailable", "explain", "no_guidance", "ask_location", "fetch_weather"])
    g.add_conditional_edges("fetch_weather", lambda s: "unavailable" if s["error"] else "match_sops",
                            ["unavailable", "match_sops"])
    g.add_conditional_edges("match_sops", lambda s: "compose" if s["hits"] else "no_guidance",
                            ["compose", "no_guidance"])
    g.add_edge("compose", "verify")
    g.add_conditional_edges("verify", lambda s: END if s["grounded"] else "template_reply", [END, "template_reply"])
    for n in ("template_reply", "no_guidance", "ask_location", "unavailable", "explain"):
        g.add_edge(n, END)
    # ponytail: in-memory sessions, lost on restart and never evicted; swap for SqliteSaver/Redis if it ever runs long-lived.
    return g.compile(checkpointer=checkpointer or MemorySaver())


def ask(graph, session_id, message):
    s = graph.invoke({"message": message}, {"configurable": {"thread_id": session_id}})
    return {k: s.get(k) for k in ("reply", "verdict", "source", "hits", "facts", "place", "window")} | {"ctx": s.get("ctx")}
