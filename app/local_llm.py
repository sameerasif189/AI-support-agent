"""In-process local LLM via llama.cpp (GGUF on GPU). No Ollama required."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional


def _prepare_windows_dll_paths() -> None:
    """CUDA + llama.cpp DLLs must be on the search path before import."""
    if sys.platform != "win32":
        return
    candidates: list[Path] = []
    for env_key in ("CUDA_PATH", "CUDA_HOME"):
        base = os.environ.get(env_key, "").strip()
        if base:
            candidates.extend(
                Path(base) / sub for sub in ("bin", "bin/x64", "lib/x64")
            )
    candidates.append(
        Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin")
    )
    candidates.append(
        Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin\x64")
    )
    try:
        import importlib.util

        spec = importlib.util.find_spec("llama_cpp")
        if spec and spec.origin:
            pkg = Path(spec.origin).parent
            candidates.append(pkg / "lib")
            candidates.append(pkg.parent / "bin")
    except Exception:
        pass
  # Pip NVIDIA CUDA 12 runtime wheels (needed when only CUDA 13.x toolkit is installed)
    try:
        import site as _site

        for sp in _site.getsitepackages():
            nvidia_root = Path(sp) / "nvidia"
            if nvidia_root.is_dir():
                for sub in nvidia_root.rglob("bin"):
                    if sub.is_dir():
                        candidates.append(sub)
    except Exception:
        pass

    for path in candidates:
        if path.is_dir():
            try:
                os.add_dll_directory(str(path))
            except OSError:
                pass
    # PATH fallback for transitive DLL loads on Windows
    extra = os.pathsep.join(str(p) for p in candidates if p.is_dir())
    if extra:
        os.environ["PATH"] = extra + os.pathsep + os.environ.get("PATH", "")

from .settings import (
    LOCAL_GGUF_PATH,
    LOCAL_LLM_BACKEND,
    LOCAL_LLM_HF_MODEL,
    LOCAL_LLM_N_CTX,
    LOCAL_LLM_N_GPU_LAYERS,
    ROOT,
)

logger = logging.getLogger(__name__)

_engine: Optional["NativeLocalEngine"] = None
_engine_lock = Lock()


def native_local_configured() -> bool:
    if LOCAL_LLM_BACKEND != "native":
        return False
    if LOCAL_GGUF_PATH:
        p = Path(LOCAL_GGUF_PATH)
        if not p.is_absolute():
            p = ROOT / p
        return p.is_file()
    return bool(LOCAL_LLM_HF_MODEL)


def get_native_engine() -> "NativeLocalEngine":
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = NativeLocalEngine()
        return _engine


class NativeLocalEngine:
    def __init__(self) -> None:
        self._llama: Any = None
        self._ready = False
        self._error: Optional[str] = None
        self._model_label = LOCAL_GGUF_PATH or LOCAL_LLM_HF_MODEL or "not configured"

    def status(self) -> Dict[str, Any]:
        return {
            "backend": "native",
            "engine": "llama.cpp",
            "model": self._model_label,
            "ready": self._ready,
            "error": self._error,
            "reachable": self._ready or native_local_configured(),
            "model_ready": self._ready,
            "gpu_active": self._ready and LOCAL_LLM_N_GPU_LAYERS != 0,
            "n_gpu_layers": LOCAL_LLM_N_GPU_LAYERS,
        }

    def _resolve_gguf_path(self) -> Path:
        if not LOCAL_GGUF_PATH:
            raise FileNotFoundError(
                "Set LOCAL_GGUF_PATH to a .gguf file (see scripts/download_native_model.ps1)"
            )
        path = Path(LOCAL_GGUF_PATH)
        if not path.is_absolute():
            path = ROOT / path
        if not path.is_file():
            raise FileNotFoundError(f"GGUF not found: {path}")
        return path

    def ensure_loaded(self) -> None:
        if self._ready:
            return
        try:
            _prepare_windows_dll_paths()
            from llama_cpp import Llama

            path = self._resolve_gguf_path()
            logger.info("Loading native GGUF on GPU: %s", path)
            self._llama = Llama(
                model_path=str(path),
                n_ctx=LOCAL_LLM_N_CTX,
                n_gpu_layers=LOCAL_LLM_N_GPU_LAYERS,
                verbose=False,
            )
            self._model_label = path.name
            self._ready = True
            self._error = None
            logger.info("Native local model ready: %s", self._model_label)
        except ImportError:
            self._error = "Install: pip install llama-cpp-python"
            raise
        except Exception as exc:
            self._error = str(exc)
            raise

    def generate_sync(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        self.ensure_loaded()
        assert self._llama is not None
        out = self._llama.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        choices = out.get("choices") or []
        if not choices:
            raise RuntimeError("Native model returned no choices")
        msg = choices[0].get("message") or {}
        text = msg.get("content")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError("Native model returned empty content")
        return text.strip()

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        return await asyncio.to_thread(self.generate_sync, system_prompt, user_prompt, max_tokens)
