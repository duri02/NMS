from __future__ import annotations

import tempfile
from pathlib import Path

import azure.cognitiveservices.speech as speechsdk


class AzureSTT:
    def __init__(self, key: str, region: str, language: str = "es-ES"):
        if not key or not region:
            raise RuntimeError("Azure STT requiere AZURE_SPEECH_KEY y AZURE_SPEECH_REGION.")
        self.speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        self.speech_config.speech_recognition_language = language

    def transcribe_wav_bytes(self, wav_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            wav_path = Path(tmp.name)

        try:
            audio_config = speechsdk.audio.AudioConfig(filename=str(wav_path))
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config,
            )
            result = recognizer.recognize_once()
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return (result.text or "").strip()
            if result.reason == speechsdk.ResultReason.NoMatch:
                return ""
            if result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                raise RuntimeError(
                    f"Azure STT cancelado: {cancellation.reason} - {cancellation.error_details or 'sin detalle'}"
                )
            return ""
        finally:
            wav_path.unlink(missing_ok=True)
