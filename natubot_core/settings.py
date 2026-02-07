from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Project root = folder containing this repository (natubot_v5_project)
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Always load .env from project root so it works regardless of current working directory
load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

def _get_bool(name: str, default: str = "false") -> bool:
    v = os.getenv(name, default).strip().lower()
    return v in {"1", "true", "yes", "y", "on"}

@dataclass(frozen=True)
class Settings:
    # Gemini
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_chat_model: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    gemini_embed_model: str = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
    embed_dim: int = int(os.getenv("EMBED_DIM", "768"))

    # Pinecone
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_index_name: str = os.getenv("PINECONE_INDEX_NAME", "natubot-index")
    pinecone_index_host: str = os.getenv("PINECONE_INDEX_HOST", "")
    pinecone_namespace: str = os.getenv("PINECONE_NAMESPACE", "natubot")

    # Runtime / CORS
    default_top_k: int = int(os.getenv("DEFAULT_TOP_K", "5"))
    max_top_k: int = int(os.getenv("MAX_TOP_K", "10"))
    cors_allow_origins: str = os.getenv("CORS_ALLOW_ORIGINS", "*")

    # Kiosk: Terms (versioned)
    terms_version: str = os.getenv("TERMS_VERSION", "2026-01-12_v1")
    terms_file: str = os.getenv("TERMS_FILE", "terms_es.md")

    # Kiosk: Rate limiting
    rate_limit_rpm: int = int(os.getenv("RATE_LIMIT_RPM", "30"))
    rate_limit_window_sec: int = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "60"))

    # Kiosk: Auth/registry
    require_kiosk_auth: bool = _get_bool("REQUIRE_KIOSK_AUTH", "true")
    kiosk_registry_file: str = os.getenv("KIOSK_REGISTRY_FILE", "kiosks.json")

    # UI config
    bot_name: str = os.getenv("BOT_NAME", "NatuBot")
    offline_message: str = os.getenv("OFFLINE_MESSAGE", "Sin internet. Este servicio no funciona sin conexión.")
    max_message_chars: int = int(os.getenv("MAX_MESSAGE_CHARS", "4000"))

    # UI config: Saludo inicial (configurable vía /config)
    welcome_message: str = os.getenv(
        "WELCOME_MESSAGE",
        "Hola, soy NatuBot.\nEstoy aquí para ayudarte a conocer nuestros suplementos naturales.\n\n¿En qué puedo ayudarte hoy?"
    )
    welcome_message_version: str = os.getenv("WELCOME_MESSAGE_VERSION", "v1")


    # Logging
    log_dir: str = os.getenv("LOG_DIR", "logs")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    # Speech pipeline
    stt_mode: str = os.getenv("STT_MODE", "local").strip().lower()
    tts_mode: str = os.getenv("TTS_MODE", "silero").strip().lower()
    azure_speech_key: str = os.getenv("AZURE_SPEECH_KEY", "")
    azure_speech_region: str = os.getenv("AZURE_SPEECH_REGION", "")
    azure_speech_language: str = os.getenv("AZURE_SPEECH_LANGUAGE", "es-ES")

    models_dir: str = os.getenv("MODELS_DIR", "models")
    vosk_model_path: str = os.getenv("VOSK_MODEL_PATH", "models/vosk-es")

    audio_sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", "16000"))
    vad_enabled: bool = _get_bool("VAD_ENABLED", "true")
    vad_aggressiveness: int = int(os.getenv("VAD_AGGRESSIVENESS", "2"))
    vad_frame_ms: int = int(os.getenv("VAD_FRAME_MS", "30"))
    vad_end_silence_ms: int = int(os.getenv("VAD_END_SILENCE_MS", "800"))

    silero_language: str = os.getenv("SILERO_LANGUAGE", "es")
    silero_speaker: str = os.getenv("SILERO_SPEAKER", "v3_es")
    tts_chunk_chars: int = int(os.getenv("TTS_CHUNK_CHARS", "700"))

def get_settings() -> Settings:
    s = Settings()
    missing = []
    if not s.gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if not s.pinecone_api_key:
        missing.append("PINECONE_API_KEY")
    if not s.pinecone_index_name:
        missing.append("PINECONE_INDEX_NAME")
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
    return s
