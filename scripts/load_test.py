import asyncio
import time
import httpx


URL = "http://127.0.0.1:8000/chat"


async def one_call(client: httpx.AsyncClient, i: int) -> float:
    payload = {"user_id": f"u-{i}", "channel": "web", "message": "need invoice copy"}
    start = time.perf_counter()
    r = await client.post(URL, json=payload)
    r.raise_for_status()
    return time.perf_counter() - start


async def run(total: int = 40, concurrent: int = 8) -> None:
    sem = asyncio.Semaphore(concurrent)
    latencies = []

    async with httpx.AsyncClient(timeout=20) as client:
        async def wrapped(i: int):
            async with sem:
                latencies.append(await one_call(client, i))

        await asyncio.gather(*[wrapped(i) for i in range(total)])

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    print(f"requests={total} concurrent={concurrent} p50={p50:.3f}s p95={p95:.3f}s")


if __name__ == "__main__":
    asyncio.run(run())
