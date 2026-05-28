"""Download native GGUF from Hugging Face (verified repo/file)."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from huggingface_hub import hf_hub_download, hf_hub_url

from app.settings import HF_GGUF_FILENAME, HF_GGUF_REPO, LOCAL_GGUF_PATH, ROOT as APP_ROOT


def main() -> None:
    dest = Path(LOCAL_GGUF_PATH)
    if not dest.is_absolute():
        dest = APP_ROOT / dest
    dest.parent.mkdir(parents=True, exist_ok=True)

    url = hf_hub_url(repo_id=HF_GGUF_REPO, filename=HF_GGUF_FILENAME)
    print(f"Repo:  {HF_GGUF_REPO}")
    print(f"File:  {HF_GGUF_FILENAME}")
    print(f"URL:   {url}")
    print(f"Save:  {dest}")

    if dest.is_file():
        print(f"Already exists ({dest.stat().st_size / 1e9:.2f} GB). Skipping download.")
        return

    print("Downloading…")
    cached = hf_hub_download(repo_id=HF_GGUF_REPO, filename=HF_GGUF_FILENAME)
    shutil.copy2(cached, dest)
    print(f"Done: {dest} ({dest.stat().st_size / 1e9:.2f} GB)")


if __name__ == "__main__":
    main()
