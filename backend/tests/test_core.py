"""Deterministic checks (no API key needed): facts, SOP engine, grounding check, graph failure branches."""
import re

import pytest

from app import engine, graph, llm, weather
from evals.fixtures import fake_forecast

_, SOPS = engine.load()


def facts(**kw):
    return weather.compute_facts(fake_forecast(**kw), "today", "now")[0]


def ids(hits):
    return [h["id"] for h in hits]


def test_facts_cover_every_metric_and_sum_rain():
    f = facts(precipitation=2.0)
    assert set(f) == set(weather.METRICS)
    assert f["rain_past24h_mm"] == 48.0 and f["rain_next24h_mm"] == 48.0 and f["rain_72h_mm"] == 144.0
    assert f["rain_window_mm"] == 6.0  # now + next 2 hours


def test_past_window_rolls_to_tomorrow():
    _, label = weather.compute_facts(fake_forecast(now="2026-09-03T22:10"), "today", "evening")
    assert label.startswith("tomorrow evening")


def test_bad_sop_is_rejected(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("activities: {cycling: bikes}\nsops:\n  - {id: X-1, title: t, category: c, severity: high, "
                 "activities: [cycling], when: {metric: pollen, op: '>', value: 1}, advice: a}\n")
    with pytest.raises(ValueError, match="unknown metric 'pollen'"):
        engine.load(p)


def test_two_rules_both_surface_ranked_by_severity():
    hits = engine.match(SOPS, facts(wind_speed_10m=45, uv_index=9), ["cycling"])
    assert ids(hits) == ["SOP-EX-03", "SOP-EX-01"]
    assert engine.verdict(hits) == "avoid"


def test_rain_system_leads_even_for_picnic():
    hits = engine.match(SOPS, facts(precipitation=3.5), ["picnic"])
    assert ids(hits)[0] == "SOP-GEN-01" and "SOP-LEI-01" in ids(hits)
    assert "84.0 mm" in hits[0]["advice"]
    assert engine.verdict(hits) == "avoid"


def test_calm_day_uses_all_clear_fallback():
    hits = engine.match(SOPS, facts(), ["cycling"])
    assert ids(hits) == ["SOP-GEN-02"] and engine.verdict(hits) == "go"


def test_picnic_score_bands():
    good = engine.match(SOPS, facts(), ["picnic"])[0]
    poor = engine.match(SOPS, facts(temperature_2m=36, wind_speed_10m=30, uv_index=10), ["picnic"])[0]
    assert good["severity"] == "info" and poor["severity"] == "moderate"
    assert "light wind" in poor["advice"]


def test_grounding_check():
    hits = engine.match(SOPS, facts(wind_speed_10m=45), ["cycling"])
    f = facts(wind_speed_10m=45)
    assert graph.grounding_problems("Wind hits 45 km/h, don't ride [SOP-EX-03].", hits, f) == []
    assert graph.grounding_problems("Wind hits 60 km/h [SOP-EX-03].", hits, f)  # invented number
    assert graph.grounding_problems("Fine to ride [SOP-99-1] [SOP-EX-03] [SOP-X-99].", hits, f)  # unknown id
    assert graph.grounding_problems("Wind hits 45 km/h.", hits, f)  # no citation
    assert graph.grounding_problems("Don't ride today [SOP-EX-03].", hits, f)  # hides the number that triggered it


@pytest.fixture
def bot(monkeypatch):
    """Graph with the LLM stubbed: tests routing and memory, not wording."""
    intents = []
    monkeypatch.setattr(llm, "extract_intent", lambda *a: intents.pop(0))
    monkeypatch.setattr(weather, "geocode", lambda name: {"name": name, "lat": 1.0, "lon": 2.0})
    g = graph.build()
    return g, intents


def intent(**kw):
    return {"on_topic": True, "asks_why": False, "location": None, "activities": [], "day": None, "part": None} | kw


def test_unreachable_weather_api_fails_honestly(bot, monkeypatch):
    g, intents = bot
    monkeypatch.setattr(weather, "FORECAST_URL", "http://127.0.0.1:9/v1/forecast")
    intents.append(intent(location="Bhopal", activities=["cycling"]))
    out = graph.ask(g, "s1", "safe to cycle in Bhopal?")
    assert out["verdict"] == "unavailable" and not re.search(r"\d", out["reply"]) and out["hits"] == []


def test_followup_memory_and_template_fallback(bot, monkeypatch):
    g, intents = bot
    monkeypatch.setattr(weather, "fetch_forecast", lambda lat, lon: fake_forecast(wind_speed_10m=45))
    monkeypatch.setattr(llm, "compose", lambda *a: "Wind is only 12 km/h, ride on [SOP-EX-03].")  # lies
    intents += [intent(location="Bhopal", activities=["cycling"], day="today"), intent(part="evening"),
                intent(asks_why=True)]
    first = graph.ask(g, "s2", "cycle in Bhopal today?")
    assert first["source"] == "template" and "45" in first["reply"]  # the lie was rejected
    second = graph.ask(g, "s2", "what about this evening instead?")
    assert second["ctx"] == {"location": "Bhopal", "activities": ["cycling"], "day": "today", "part": "evening"}
    why = graph.ask(g, "s2", "why did you say that?")
    assert "SOP-EX-03" in why["reply"] and "45" in why["reply"]


def test_off_topic_never_fetches_weather(bot, monkeypatch):
    g, intents = bot
    monkeypatch.setattr(weather, "get_weather", lambda *a: pytest.fail("fetched weather for off-topic"))
    intents.append(intent(on_topic=False, location="Paris"))
    assert graph.ask(g, "s3", "capital of France?")["verdict"] == "none"
