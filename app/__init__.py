# Windows: must run before any asyncio loop / psycopg pool is created (incl. uvicorn --reload worker)
import sys

if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
