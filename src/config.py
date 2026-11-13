from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", ROOT / "data" / "raw"))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", ROOT / "data" / "chroma"))
SUBSET_SIZE = int(os.getenv("SUBSET_SIZE", "0"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_RATE_DELAY = float(os.getenv("LLM_RATE_DELAY", "1.0"))
API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "20"))

