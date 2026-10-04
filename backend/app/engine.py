"""Deterministic SOP engine: which policies apply is decided here, never by the model."""
import operator
import os
import re
from pathlib import Path

import yaml

from .weather import METRICS

SOP_PATH = Path(os.getenv("SOP_PATH", Path(__file__).resolve().parent.parent / "sops.yaml"))
SEVERITIES = ["info", "low", "moderate", "high", "critical"]
VERDICT = {"critical": "avoid", "high": "avoid", "moderate": "caution", "low": "go", "info": "go"}
OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt, "==": operator.eq}
SCORE_FIELDS = {"score", "max_score", "misses"}


def load(path=None):
    """Read and validate the SOP file. Re-read on every request so policy edits apply without a restart."""
    doc = yaml.safe_load(Path(path or SOP_PATH).read_text(encoding="utf-8"))
    glossary, sops = doc["activities"], doc["sops"]
    seen = set()
    for s in sops:
        _validate(s, glossary, seen)
    return glossary, sops


def _validate(s, glossary, seen):
    sid = s.get("id", "<missing id>")

    def need(ok, msg):
        if not ok:
            raise ValueError(f"{sid}: {msg}")

    need(sid not in seen, "duplicate id")
    seen.add(sid)
    for key in ("id", "title", "category", "activities"):
        need(key in s, f"missing '{key}'")
    acts = s["activities"]
    need(acts == "*" or (isinstance(acts, list) and set(acts) <= set(glossary)),
         f"activities must be \"*\" or tags from the glossary {sorted(glossary)}")
    if "score" in s:
        for f in s["score"]["factors"]:
            need(f["metric"] in METRICS, f"unknown metric '{f['metric']}'")
            need(len(f["good"]) == 2, "factor 'good' must be [low, high]")
        for b in s["score"]["bands"]:
            need(b["severity"] in SEVERITIES, f"severity must be one of {SEVERITIES}")
            _check_placeholders(b["advice"], need, SCORE_FIELDS)
        return
    need(s.get("severity") in SEVERITIES, f"severity must be one of {SEVERITIES}")
    need("advice" in s, "missing 'advice'")
    need("when" in s or s.get("fallback"), "needs a 'when' condition (or fallback: true)")
    if "when" in s:
        _check_condition(s["when"], need)
    _check_placeholders(s["advice"], need, set())


def _check_condition(c, need):
    need(isinstance(c, dict), f"bad condition {c!r}")
    if "all" in c or "any" in c:
        for sub in c.get("all", c.get("any")):
            _check_condition(sub, need)
        return
    need(c.get("metric") in METRICS, f"unknown metric '{c.get('metric')}', known: {sorted(METRICS)}")
    need(c.get("op") in OPS, f"op must be one of {list(OPS)}")
    need("value" in c, "condition missing 'value'")


def _check_placeholders(text, need, extra):
    for name in re.findall(r"{(\w+)}", text):
        need(name in METRICS or name in extra, f"advice uses unknown placeholder {{{name}}}")


def _eval(c, facts):
    """Return the satisfied leaf conditions as (metric, actual, op, value), or None if the condition is not met."""
    if "all" in c:
        parts = [_eval(sub, facts) for sub in c["all"]]
        return None if any(p is None for p in parts) else sum(parts, [])
    if "any" in c:
        parts = [p for p in (_eval(sub, facts) for sub in c["any"]) if p is not None]
        return sum(parts, []) if parts else None
    actual = facts.get(c["metric"])
    if actual is None or not OPS[c["op"]](actual, c["value"]):
        return None
    return [(c["metric"], actual, c["op"], c["value"])]


def _hit(s, severity, advice, values, leaves=(), reasons=()):
    """leaves -> 'reasons' (human why) and 'evidence' (live values the reply must report)."""
    reasons = list(reasons) + [f"{METRICS[m]} is {a} (rule: {m} {op} {v})" for m, a, op, v in leaves]
    evidence = {m: a for m, a, _, _ in leaves if not isinstance(a, bool)}
    return {"id": s["id"], "title": s["title"], "category": s["category"], "severity": severity,
            "lead": bool(s.get("lead")), "advice": " ".join(advice.format_map(values).split()), "reasons": reasons,
            "evidence": evidence}


def _score(s, facts):
    factors = s["score"]["factors"]
    misses = [f["label"] for f in factors if not f["good"][0] <= facts[f["metric"]] <= f["good"][1]]
    score = len(factors) - len(misses)
    band = next(b for b in sorted(s["score"]["bands"], key=lambda b: -b["min"]) if score >= b["min"])
    values = {**facts, "score": score, "max_score": len(factors), "misses": ", ".join(misses) or "nothing"}
    reason = f"comfort score {score}/{len(factors)}, short on: {values['misses']}"
    return _hit(s, band["severity"], band["advice"], values, reasons=[reason])


def match(sops, facts, activities):
    """All SOPs that apply to these activities under these facts: lead first, then most severe first."""
    acts = set(activities)
    relevant = [s for s in sops if s["activities"] == "*" or acts & set(s["activities"])]
    hits = []
    for s in relevant:
        if s.get("fallback"):
            continue
        if "score" in s:
            hits.append(_score(s, facts))
        elif (leaves := _eval(s["when"], facts)) is not None:
            hits.append(_hit(s, s["severity"], s["advice"], facts, leaves))
    if not hits:
        hits = [_hit(s, s["severity"], s["advice"], facts, reasons=["no risk condition triggered"])
                for s in relevant if s.get("fallback")]
    return sorted(hits, key=lambda h: (not h["lead"], -SEVERITIES.index(h["severity"])))


def verdict(hits):
    return VERDICT[max((h["severity"] for h in hits), key=SEVERITIES.index)] if hits else "none"


if __name__ == "__main__":  # python -m app.engine  -> validate sops.yaml and list it
    glossary, sops = load()
    for s in sops:
        print(f"{s['id']:<12} {s.get('severity', 'scored'):<9} {s['category']:<11} {s['title']}")
    print(f"\nOK: {len(sops)} SOPs, {len(glossary)} activity tags")
