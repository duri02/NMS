from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from natubot_core.logging_utils import log_event

from .audio_utils import normalize_audio_bytes, pcm16_to_wav_bytes
from .interfaces import STTEngine, TTSEngine
from .stt_azure import AzureSTT
from .stt_vosk import VoskSTT
from .tts_silero import SileroTTS
from .vad import VADConfig, trim_to_speech


class STTRouter:
    def __init__(
        self,
        mode: str,
        local_engine: STTEngine,
        azure_engine: Optional[AzureSTT] = None,
    ):
        self.mode = (mode or "local").strip().lower()
        self.local_engine = local_engine
        self.azure_engine = azure_engine

    def transcribe(self, *, wav_bytes: bytes, pcm16_mono: bytes) -> Dict[str, Any]:
        fallback_used = False
        mode_used = "local"

        if self.mode == "azure" and self.azure_engine is not None:
            try:
                text = self.azure_engine.transcribe_wav_bytes(wav_bytes)
                mode_used = "azure"
                return {
                    "text": text,
                    "stt_mode_used": mode_used,
                    "fallback_used": False,
                }
            except Exception:
                fallback_used = True

        text = self.local_engine.transcribe(pcm16_mono)
        return {
            "text": text,
            "stt_mode_used": mode_used,
            "fallback_used": fallback_used,
        }


@dataclass
class VoicePipelineResult:
    stt_text: str
    bot_text: str
    audio_wav: Optional[bytes]
    stt_mode_used: str
    fallback_used: bool
    stt_latency_ms: int
    llm_latency_ms: int
    tts_latency_ms: int


class VoiceTurnPipeline:
    def __init__(self, stt_router: STTRouter, tts_engine: TTSEngine, vad_config: VADConfig):
        self.stt_router = stt_router
        self.tts_engine = tts_engine
        self.vad_config = vad_config

    def run_turn(
        self,
        *,
        audio_bytes: bytes,
        source_name: str,
        include_audio: bool,
        chat_callable,
        logger,
    ) -> VoicePipelineResult:
        pcm = normalize_audio_bytes(audio_bytes, source_name=source_name, target_sample_rate=self.vad_config.sample_rate)
        processed_pcm = trim_to_speech(pcm, self.vad_config)
        wav_16k = pcm16_to_wav_bytes(processed_pcm, sample_rate=self.vad_config.sample_rate)

        stt_start = time.time()
        stt_res = self.stt_router.transcribe(wav_bytes=wav_16k, pcm16_mono=processed_pcm)
        stt_latency_ms = int((time.time() - stt_start) * 1000)
        stt_text = (stt_res.get("text") or "").strip()

        llm_start = time.time()
        bot_text = chat_callable(stt_text)
        llm_latency_ms = int((time.time() - llm_start) * 1000)

        tts_latency_ms = 0
        wav_out = None
        if include_audio:
            tts_start = time.time()
            wav_out = self.tts_engine.synthesize(bot_text)
            tts_latency_ms = int((time.time() - tts_start) * 1000)

        payload = {
            "event": "voice_turn",
            "stt_mode_used": stt_res.get("stt_mode_used"),
            "fallback_used": stt_res.get("fallback_used", False),
            "stt_latency_ms": stt_latency_ms,
            "llm_latency_ms": llm_latency_ms,
            "tts_latency_ms": tts_latency_ms,
        }
        log_event(logger, payload)

        return VoicePipelineResult(
            stt_text=stt_text,
            bot_text=bot_text,
            audio_wav=wav_out,
            stt_mode_used=stt_res.get("stt_mode_used", "local"),
            fallback_used=bool(stt_res.get("fallback_used", False)),
            stt_latency_ms=stt_latency_ms,
            llm_latency_ms=llm_latency_ms,
            tts_latency_ms=tts_latency_ms,
        )


def build_voice_pipeline(settings) -> VoiceTurnPipeline:
    local_stt = VoskSTT(settings.vosk_model_path, sample_rate=settings.audio_sample_rate)

    azure_engine = None
    if settings.stt_mode == "azure":
        try:
            azure_engine = AzureSTT(
                key=settings.azure_speech_key,
                region=settings.azure_speech_region,
                language=settings.azure_speech_language,
            )
        except Exception:
            azure_engine = None

    stt_router = STTRouter(mode=settings.stt_mode, local_engine=local_stt, azure_engine=azure_engine)

    if settings.tts_mode != "silero":
        raise RuntimeError(f"TTS_MODE no soportado actualmente: {settings.tts_mode}")

    tts_engine = SileroTTS(
        language=settings.silero_language,
        speaker=settings.silero_speaker,
        sample_rate=settings.audio_sample_rate,
        chunk_chars=settings.tts_chunk_chars,
    )

    vad_cfg = VADConfig(
        enabled=settings.vad_enabled,
        aggressiveness=settings.vad_aggressiveness,
        frame_ms=settings.vad_frame_ms,
        end_silence_ms=settings.vad_end_silence_ms,
        sample_rate=settings.audio_sample_rate,
    )

    return VoiceTurnPipeline(stt_router=stt_router, tts_engine=tts_engine, vad_config=vad_cfg)
