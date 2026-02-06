from __future__ import annotations

from dataclasses import dataclass

import webrtcvad


@dataclass(frozen=True)
class VADConfig:
    enabled: bool = True
    aggressiveness: int = 2
    frame_ms: int = 30
    end_silence_ms: int = 800
    sample_rate: int = 16000


def trim_to_speech(pcm16_mono: bytes, config: VADConfig) -> bytes:
    if not config.enabled:
        return pcm16_mono

    frame_size = int(config.sample_rate * (config.frame_ms / 1000.0) * 2)
    if frame_size <= 0:
        return pcm16_mono

    vad = webrtcvad.Vad(max(0, min(3, int(config.aggressiveness))))
    silence_limit_frames = max(1, int(config.end_silence_ms / config.frame_ms))

    frames = [pcm16_mono[i : i + frame_size] for i in range(0, len(pcm16_mono), frame_size)]
    frames = [f for f in frames if len(f) == frame_size]
    if not frames:
        return pcm16_mono

    started = False
    silence_count = 0
    selected = bytearray()

    for frame in frames:
        is_speech = vad.is_speech(frame, config.sample_rate)
        if is_speech:
            started = True
            silence_count = 0
            selected.extend(frame)
            continue

        if started:
            silence_count += 1
            if silence_count >= silence_limit_frames:
                break
            selected.extend(frame)

    if not selected:
        return pcm16_mono
    return bytes(selected)
