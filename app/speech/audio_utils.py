from __future__ import annotations

import io
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Tuple

import numpy as np

TARGET_SAMPLE_RATE = 16000
TARGET_SAMPLE_WIDTH = 2
TARGET_CHANNELS = 1


def _pcm_bytes_to_float32(pcm_bytes: bytes, sample_width: int) -> np.ndarray:
    if not pcm_bytes:
        return np.zeros((0,), dtype=np.float32)

    if sample_width == 1:
        arr = np.frombuffer(pcm_bytes, dtype=np.uint8).astype(np.float32)
        return (arr - 128.0) / 128.0

    if sample_width == 2:
        arr = np.frombuffer(pcm_bytes, dtype='<i2').astype(np.float32)
        return arr / 32768.0

    if sample_width == 3:
        raw = np.frombuffer(pcm_bytes, dtype=np.uint8)
        triples = raw.reshape(-1, 3)
        val = (triples[:, 0].astype(np.int32)
               | (triples[:, 1].astype(np.int32) << 8)
               | (triples[:, 2].astype(np.int32) << 16))
        sign = val & 0x800000
        val = val - (sign << 1)
        return (val.astype(np.float32) / 8388608.0)

    if sample_width == 4:
        arr = np.frombuffer(pcm_bytes, dtype='<i4').astype(np.float32)
        return arr / 2147483648.0

    raise RuntimeError(f"Sample width no soportado: {sample_width} bytes")


def _float32_to_pcm16_bytes(samples: np.ndarray) -> bytes:
    if samples.size == 0:
        return b""
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16).tobytes()


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


def decode_audio_to_pcm(audio_bytes: bytes, source_name: str = "audio.wav") -> Tuple[bytes, int, int, int]:
    """
    Return tuple: (pcm_bytes, sample_rate, sample_width, channels).
    Supports WAV natively and falls back to ffmpeg for other formats.
    """
    header = audio_bytes[:12]
    is_wav = header[:4] == b"RIFF" and header[8:12] == b"WAVE"

    if is_wav:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
            return frames, sample_rate, sample_width, channels

    src_suffix = Path(source_name).suffix or ".bin"
    with tempfile.NamedTemporaryFile(suffix=src_suffix, delete=False) as src:
        src.write(audio_bytes)
        src_path = Path(src.name)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out:
        out_path = Path(out.name)

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(src_path),
            "-ac",
            "1",
            "-ar",
            str(TARGET_SAMPLE_RATE),
            "-f",
            "wav",
            str(out_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError("No se pudo decodificar audio. Verifica formato o instala ffmpeg.")
        with wave.open(str(out_path), "rb") as wf:
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())
            return frames, sample_rate, sample_width, channels
    finally:
        src_path.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)


def ensure_pcm16_mono_16k(
    pcm_bytes: bytes,
    *,
    sample_rate: int,
    sample_width: int,
    channels: int,
    target_sample_rate: int = TARGET_SAMPLE_RATE,
) -> bytes:
    samples = _pcm_bytes_to_float32(pcm_bytes, sample_width)

    if channels > 1 and samples.size > 0:
        usable = (samples.size // channels) * channels
        samples = samples[:usable].reshape(-1, channels).mean(axis=1).astype(np.float32)

    samples = _resample_float32(samples, sample_rate, target_sample_rate)
    return _float32_to_pcm16_bytes(samples)


def pcm16_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(TARGET_CHANNELS)
        wf.setsampwidth(TARGET_SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return bio.getvalue()


def normalize_audio_bytes(audio_bytes: bytes, source_name: str = "audio.wav", target_sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    pcm, sr, sw, ch = decode_audio_to_pcm(audio_bytes, source_name=source_name)
    return ensure_pcm16_mono_16k(
        pcm,
        sample_rate=sr,
        sample_width=sw,
        channels=ch,
        target_sample_rate=target_sample_rate,
    )
