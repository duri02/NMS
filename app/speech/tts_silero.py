from __future__ import annotations

import audioop
from typing import List

import numpy as np
import torch

from .audio_utils import pcm16_to_wav_bytes


class SileroTTS:
    def __init__(
        self,
        language: str = "es",
        speaker: str = "v3_es",
        sample_rate: int = 16000,
        chunk_chars: int = 700,
    ):
        self.language = language
        self.speaker = speaker
        self.target_sample_rate = sample_rate
        self.chunk_chars = max(200, chunk_chars)
        self.model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-models",
            model="silero_tts",
            language=language,
            speaker=speaker,
        )

    def _chunk_text(self, text: str) -> List[str]:
        text = (text or "").strip()
        if len(text) <= self.chunk_chars:
            return [text] if text else []

        chunks: List[str] = []
        current = []
        size = 0
        for word in text.split():
            wlen = len(word) + 1
            if size + wlen > self.chunk_chars and current:
                chunks.append(" ".join(current).strip())
                current = [word]
                size = len(word)
            else:
                current.append(word)
                size += wlen
        if current:
            chunks.append(" ".join(current).strip())
        return chunks

    def _tensor_to_pcm16(self, tensor: torch.Tensor, source_sr: int = 48000) -> bytes:
        arr = tensor.detach().cpu().numpy().astype(np.float32)
        arr = np.clip(arr, -1.0, 1.0)
        pcm16 = (arr * 32767.0).astype(np.int16).tobytes()
        if source_sr != self.target_sample_rate:
            pcm16, _ = audioop.ratecv(pcm16, 2, 1, source_sr, self.target_sample_rate, None)
        return pcm16

    def synthesize(self, text: str) -> bytes:
        chunks = self._chunk_text(text)
        if not chunks:
            return pcm16_to_wav_bytes(b"", sample_rate=self.target_sample_rate)

        pcm_parts = []
        for piece in chunks:
            audio = self.model.apply_tts(text=piece, speaker=self.speaker, sample_rate=48000)
            pcm_parts.append(self._tensor_to_pcm16(audio, source_sr=48000))

        merged_pcm = b"".join(pcm_parts)
        return pcm16_to_wav_bytes(merged_pcm, sample_rate=self.target_sample_rate)
