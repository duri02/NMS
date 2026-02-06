from __future__ import annotations

from typing import Protocol


class STTEngine(Protocol):
    def transcribe(self, audio_pcm_16k_mono_bytes: bytes) -> str:
        ...


class TTSEngine(Protocol):
    def synthesize(self, text: str) -> bytes:
        ...
