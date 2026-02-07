from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import requests

DEFAULT_URL = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"


def download_and_extract(url: str, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"Descargando modelo desde {url}...")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        root_names = sorted({Path(n).parts[0] for n in zf.namelist() if n.strip()})
        zf.extractall(target_dir)

    if root_names:
        extracted_root = target_dir / root_names[0]
        final_path = target_dir / "vosk-es"
        if final_path.exists() and final_path.is_dir():
            print(f"Ruta destino ya existe: {final_path}")
        else:
            extracted_root.rename(final_path)
        print(f"Modelo listo en: {final_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Descarga modelo Vosk español para Natubot")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--target", default="models")
    args = parser.parse_args()

    download_and_extract(args.url, Path(args.target))


if __name__ == "__main__":
    main()
