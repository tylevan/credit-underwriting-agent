"""
Application Settings.
Load từ environment variables, fallback sang defaults.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── API Keys ──
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    
    # ── LLM Config ──
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0"))
    
    # ── Data ──
    DATA_PATH: str = os.getenv("DATA_PATH", "data/bank_churn_dataset_80k.csv")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/assessments.db")
    
    # ── Database (Production: Supabase PostgreSQL) ──
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # ── Server ──
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # ── CORS ──
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # ── Logging ──
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
