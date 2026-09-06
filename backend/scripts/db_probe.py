import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import get_settings  # noqa: E402


async def main() -> None:
    url = get_settings().database_url
    print("driver:", url.split("://")[0])
    if url.startswith("sqlite"):
        print("sqlite ok")
        return
    import asyncpg
    dsn = url.replace("postgresql+asyncpg://", "postgresql://")
    t = time.perf_counter()
    try:
        conn = await asyncio.wait_for(asyncpg.connect(dsn, statement_cache_size=0), timeout=12)
        v = await conn.fetchval("select version()")
        tables = await conn.fetch("select tablename from pg_tables where schemaname='public' order by 1")
        await conn.close()
        print(f"connected in {time.perf_counter()-t:.1f}s:", v[:40])
        print("tables:", [r[0] for r in tables])
    except Exception as e:  # noqa: BLE001
        print(f"FAILED after {time.perf_counter()-t:.1f}s: {type(e).__name__}: {e}")


asyncio.run(main())
