import json
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)
CONFIG_DIR = ROOT / "config"

# Vercel / AWS Lambda: no local GPU, no background feed loop
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip().strip('"').strip("'") if value else default


def _load_json(name: str) -> dict:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


GUARDRAILS = _load_json("guardrails.json")
INTENTS_POLICY = _load_json("intents_policy.json")

APP_PORT = int(_env("APP_PORT", "8000"))
DATABASE_URL = _env("DATABASE_URL")
ERP_BASE_URL = _env("ERP_BASE_URL")
ERP_API_KEY = _env("ERP_API_KEY")
LLM_API_BASE = _env("LLM_API_BASE", "https://api.openai.com/v1")
LLM_API_KEY = _env("LLM_API_KEY")
LLM_MODEL = _env("LLM_MODEL", "gpt-4.1-mini")
# Local LLM: native = llama.cpp GGUF in-process (no Ollama)
LOCAL_LLM_BACKEND = _env("LOCAL_LLM_BACKEND", "native").lower()
# Verified on Hugging Face: https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF
HF_GGUF_REPO = _env("HF_GGUF_REPO", "bartowski/Qwen2.5-7B-Instruct-GGUF")
HF_GGUF_FILENAME = _env("HF_GGUF_FILENAME", "Qwen2.5-7B-Instruct-Q4_K_M.gguf")
LOCAL_GGUF_PATH = _env("LOCAL_GGUF_PATH", f"models/{HF_GGUF_FILENAME}")
LOCAL_LLM_HF_MODEL = _env("LOCAL_LLM_HF_MODEL", "")
LOCAL_LLM_N_CTX = int(_env("LOCAL_LLM_N_CTX", "4096"))
LOCAL_LLM_N_GPU_LAYERS = int(_env("LOCAL_LLM_N_GPU_LAYERS", "-1"))
LOCAL_LLM_PRELOAD = _env("LOCAL_LLM_PRELOAD", "false").lower() in ("1", "true", "yes")
LOCAL_LLM_API_BASE = _env("LOCAL_LLM_API_BASE", "http://127.0.0.1:11434/v1")
LOCAL_LLM_API_KEY = _env("LOCAL_LLM_API_KEY", "ollama")
LOCAL_LLM_MODEL = _env("LOCAL_LLM_MODEL", HF_GGUF_FILENAME)
LOCAL_LLM_TIMEOUT_SEC = float(_env("LOCAL_LLM_TIMEOUT_SEC", "180"))
LLM_API_TIMEOUT_SEC = float(_env("LLM_API_TIMEOUT_SEC", "25"))
# auto order when llm_mode=auto: "local,api" = GPU first, then Groq; "api,local" = cloud first
LLM_ORDER = _env("LLM_ORDER", "api" if IS_SERVERLESS else "local,api")

# RAG: background API feed sync + learn from successful chats
_default_feed_sync = "false" if IS_SERVERLESS else "true"
RAG_FEED_SYNC_ENABLED = _env("RAG_FEED_SYNC_ENABLED", _default_feed_sync).lower() in ("1", "true", "yes")
RAG_FEED_SYNC_TICK_SEC = int(_env("RAG_FEED_SYNC_TICK_SEC", "60"))
RAG_FEED_AUTO_BOOTSTRAP = _env("RAG_FEED_AUTO_BOOTSTRAP", "true").lower() in ("1", "true", "yes")
RAG_FEED_DEFAULT_URL = _env("RAG_FEED_DEFAULT_URL", "http://127.0.0.1:8000/")
RAG_FEED_CURATE_WITH_API = _env("RAG_FEED_CURATE_WITH_API", "true").lower() in ("1", "true", "yes")
LEARN_FROM_CHAT = _env("LEARN_FROM_CHAT", "true").lower() in ("1", "true", "yes")
LEARN_MIN_CONFIDENCE = float(_env("LEARN_MIN_CONFIDENCE", "0.72"))
LEARN_CUSTOMER_MEMORY = _env("LEARN_CUSTOMER_MEMORY", "true").lower() in ("1", "true", "yes")
CHAT_MEMORY_IN_PROMPT = _env("CHAT_MEMORY_IN_PROMPT", "true").lower() in ("1", "true", "yes")
CHAT_HISTORY_TURNS = int(_env("CHAT_HISTORY_TURNS", "6"))
# Distill chat Q&A into KB articles via Groq (LLM_API_*), not the local GPU model
LEARN_EXPAND_WITH_API = _env("LEARN_EXPAND_WITH_API", "true").lower() in ("1", "true", "yes")
KNOWLEDGE_WEBHOOK_KEY = _env("KNOWLEDGE_WEBHOOK_KEY", "")

# Vector RAG on Neon (pgvector): chunk → embed → store → cosine search
RAG_VECTOR_ENABLED = _env("RAG_VECTOR_ENABLED", "true").lower() in ("1", "true", "yes")
RAG_RETRIEVAL_MODE = _env("RAG_RETRIEVAL_MODE", "hybrid")  # hybrid | vector | fts
RAG_CHUNK_SIZE_TOKENS = int(_env("RAG_CHUNK_SIZE_TOKENS", "400"))
RAG_CHUNK_OVERLAP_TOKENS = int(_env("RAG_CHUNK_OVERLAP_TOKENS", "60"))
RAG_VECTOR_TOP_K = int(_env("RAG_VECTOR_TOP_K", "8"))
EMBEDDING_API_BASE = _env("EMBEDDING_API_BASE", "https://api.openai.com/v1")
EMBEDDING_API_KEY = _env("EMBEDDING_API_KEY", "")
EMBEDDING_MODEL = _env("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(_env("EMBEDDING_DIM", "1536"))
EMBEDDING_BATCH_SIZE = int(_env("EMBEDDING_BATCH_SIZE", "32"))
EMBEDDING_TIMEOUT_SEC = float(_env("EMBEDDING_TIMEOUT_SEC", "60"))

# Meta WhatsApp Cloud API (Vercel demo)
WHATSAPP_ACCESS_TOKEN = _env("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = _env("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = _env("WHATSAPP_VERIFY_TOKEN", "erp-ai-verify")
WHATSAPP_APP_SECRET = _env("WHATSAPP_APP_SECRET")
WHATSAPP_API_VERSION = _env("WHATSAPP_API_VERSION", "v21.0")
# Demo: treat all WhatsApp senders as this seeded customer id (e.g. 1 = cust1 in seed_db)
WHATSAPP_DEMO_ERP_UID = _env("WHATSAPP_DEMO_ERP_UID", "1")
