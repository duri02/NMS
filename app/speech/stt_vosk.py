from __future__ import annotations

import json
from pathlib import Path

from vosk import KaldiRecognizer, Model


class VoskSTT:
    def __init__(self, model_path: str, sample_rate: int = 16000):
        path = Path(model_path)
        if not path.exists():
            raise RuntimeError(
                f"Modelo Vosk no encontrado en {path}. Descárgalo en esa ruta o cambia VOSK_MODEL_PATH."
            )
        self.sample_rate = sample_rate
        self.model = Model(str(path))

    def transcribe(self, audio_pcm_16k_mono_bytes: bytes) -> str:
        if not audio_pcm_16k_mono_bytes:
            return ""
        recognizer = KaldiRecognizer(self.model, self.sample_rate)
        recognizer.SetWords(False)

        chunk = 4000
        for i in range(0, len(audio_pcm_16k_mono_bytes), chunk):
            recognizer.AcceptWaveform(audio_pcm_16k_mono_bytes[i : i + chunk])

        final = recognizer.FinalResult()
        payload = json.loads(final) if final else {}
        return (payload.get("text") or "").strip()
