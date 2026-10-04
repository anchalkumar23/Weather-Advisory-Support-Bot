from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import engine
from .graph import ask, build

app = FastAPI(title="Weather-Advisory Support Bot")
bot = build()


class ChatIn(BaseModel):
    session_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,64}$")
    message: str = Field(min_length=1, max_length=500)


@app.post("/api/chat")
def chat(body: ChatIn):
    try:
        return ask(bot, body.session_id, body.message.strip())
    except (ValueError, yaml.YAMLError) as e:  # a broken sops.yaml edit: say exactly what is wrong
        raise HTTPException(500, f"SOP file is invalid: {e}") from e


@app.get("/api/health")
def health():
    _, sops = engine.load()
    return {"ok": True, "sops": len(sops)}


dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if dist.is_dir():  # after `npm run build`, one server hosts both API and UI
    app.mount("/", StaticFiles(directory=dist, html=True), name="ui")
