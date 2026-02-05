from __future__ import annotations

import audioop
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Tuple

TARGET_SAMPLE_RATE = 16000
TARGET_SAMPLE_WIDTH = 2
TARGET_CHANNELS = 1



def decode_audio_to_pcm(audio_bytes: bytes, source_name: str = "audio.wav") -> Tuple[bytes, int, int, int]:
    """
    Return tuple: (pcm_bytes, sample_rate, sample_width, channels).
    Supports WAV natively and falls back to ffmpeg for other formats.
    """
    header = audio_bytes[:12]
    is_wav = header[:4] == b"RIFF" and header[8:12] == b"WAVE"

    if is_wav:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = Path(tmp.name)
        try:
            with wave.open(str(tmp_path), "rb") as wf:
                channels = wf.getnchannels()
                sample_rate = wf.getframerate()
                sample_width = wf.getsampwidth()
                frames = wf.readframes(wf.getnframes())
                return frames, sample_rate, sample_width, channels
        finally:
            tmp_path.unlink(missing_ok=True)

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
    out = pcm_bytes

    if sample_width != TARGET_SAMPLE_WIDTH:
        out = audioop.lin2lin(out, sample_width, TARGET_SAMPLE_WIDTH)
        sample_width = TARGET_SAMPLE_WIDTH

    if channels > 1:
        out = audioop.tomono(out, sample_width, 0.5, 0.5)
        channels = 1

    if sample_rate != target_sample_rate:
        out, _ = audioop.ratecv(out, sample_width, channels, sample_rate, target_sample_rate, None)

    return out


def pcm16_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        with wave.open(str(tmp_path), "wb") as wf:
            wf.setnchannels(TARGET_CHANNELS)
            wf.setsampwidth(TARGET_SAMPLE_WIDTH)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def normalize_audio_bytes(audio_bytes: bytes, source_name: str = "audio.wav", target_sample_rate: int = TARGET_SAMPLE_RATE) -> bytes:
    pcm, sr, sw, ch = decode_audio_to_pcm(audio_bytes, source_name=source_name)
    return ensure_pcm16_mono_16k(
        pcm,
        sample_rate=sr,
        sample_width=sw,
        channels=ch,
        target_sample_rate=target_sample_rate,
    )
