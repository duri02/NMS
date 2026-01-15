from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

def load_kiosk_registry(path: Path) -> Dict[str, Dict[str, Any]]:
    """kiosks.json: device_id -> {token, location, name}"""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, dict):
            out[k] = v
    return out

def verify_kiosk(device_id: str, token: str, registry: Dict[str, Dict[str, Any]]) -> bool:
    info = registry.get(device_id) or {}
    expected = (info.get("token") or "").strip()
    return bool(expected) and token == expected

def get_kiosk_info(device_id: str, registry: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return registry.get(device_id)
