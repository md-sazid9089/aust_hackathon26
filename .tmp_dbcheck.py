import asyncio, sys
sys.path.insert(0, "backend")
import os
os.chdir("backend")
from sqlalchemy import text
from app.db.session import get_engine

async def main():
    eng = get_engine()
    async with eng.connect() as c:
        try:
            v = (await c.execute(text("select version_num from alembic_version"))).scalars().all()
        except Exception as e:
            v = f"ERR {type(e).__name__}: {str(e)[:120]}"
        print("alembic:", v)
        tables = (await c.execute(text("select table_name from information_schema.tables where table_schema='public' order by 1"))).scalars().all()
        print("tables:", tables)
        for t in ("profiles", "courses", "artefacts", "runs", "findings", "program_outcomes"):
            if t in tables:
                n = (await c.execute(text(f"select count(*) from {t}"))).scalar()
                print(t, n)
        if "profiles" in tables:
            print((await c.execute(text("select email, role from profiles"))).all())
    await eng.dispose()

asyncio.run(main())
