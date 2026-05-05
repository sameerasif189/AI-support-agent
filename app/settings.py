import json
import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"


def _load_json(name: str) -> dict:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


GUARDRAILS = _load_json("guardrails.json")
INTENTS_POLICY = _load_json("intents_policy.json")

APP_PORT = int(os.getenv("APP_PORT", "8000"))
DATABASE_URL = os.getenv("DATABASE_URL", "")
ERP_BASE_URL = os.getenv("ERP_BASE_URL", "")
ERP_API_KEY = os.getenv("ERP_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
