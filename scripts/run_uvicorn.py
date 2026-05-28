"""Start uvicorn with Windows-safe asyncio policy (before any event loop exists)."""
from __future__ import annotations

import asyncio
import sys


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    import uvicorn

    uvicorn.main.main()


if __name__ == "__main__":
    main()
