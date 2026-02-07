from __future__ import annotations

import re
from typing import List

import numpy as np
import torch

from .audio_utils import pcm16_to_wav_bytes


def _resample_float32(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or samples.size == 0:
        return samples

    src_len = samples.shape[0]
    dst_len = int(round(src_len * (dst_rate / src_rate)))
    if dst_len <= 0:
        return np.zeros((0,), dtype=np.float32)

    x_old = np.linspace(0.0, 1.0, num=src_len, endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=dst_len, endpoint=False)
    return np.interp(x_new, x_old, samples).astype(np.float32)


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

    @staticmethod
    def _supported_speakers_from_error(err: Exception) -> List[str]:
        msg = str(err)
        # Supports errors like:
        # - "`speaker` should be in es_0, es_1, es_2, random"
        # - "Speaker not in the supported list ['v3_es', ...]"
        m = re.search(r"should be in\s+(.+)$", msg)
        if m:
            raw = m.group(1)
            return [s.strip(" '`\"[]") for s in raw.split(",") if s.strip()]

        m = re.search(r"supported list\s*\[(.+)\]", msg)
        if m:
            raw = m.group(1)
            return [s.strip(" '`\"") for s in raw.split(",") if s.strip()]
        return []

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
        samples = tensor.detach().cpu().numpy().astype(np.float32)
        samples = np.clip(samples, -1.0, 1.0)
        samples = _resample_float32(samples, source_sr, self.target_sample_rate)
        return (samples * 32767.0).astype(np.int16).tobytes()

    def synthesize(self, text: str) -> bytes:
        chunks = self._chunk_text(text)
        if not chunks:
            return pcm16_to_wav_bytes(b"", sample_rate=self.target_sample_rate)

        pcm_parts = []
        for piece in chunks:
            try:
                audio = self.model.apply_tts(text=piece, speaker=self.speaker, sample_rate=48000)
            except Exception as e:
                supported = self._supported_speakers_from_error(e)
                if not supported:
                    raise
                fallback_speaker = supported[0]
                audio = self.model.apply_tts(text=piece, speaker=fallback_speaker, sample_rate=48000)
                self.speaker = fallback_speaker
            pcm_parts.append(self._tensor_to_pcm16(audio, source_sr=48000))

        merged_pcm = b"".join(pcm_parts)
        return pcm16_to_wav_bytes(merged_pcm, sample_rate=self.target_sample_rate)
