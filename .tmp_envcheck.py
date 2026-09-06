import os, re
from pathlib import Path
env = Path("backend/.env").read_text(encoding="utf-8")
for line in env.splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        k = k.strip()
        if k == "DATABASE_URL":
            print(k, "->", re.sub(r"://([^:]+):[^@]+@", r"://\1:***@", v.strip()))
        elif k in ("AUTH_MODE", "ENV", "SUPABASE_URL", "LLM_PROVIDER", "EMBED_BASE_URL", "SEED_DATA_DIR", "CORS_ORIGINS"):
            print(k, "->", v.strip())
        else:
            print(k, "-> set" if v.strip() else "-> EMPTY")
print("---gitignore---")
gi = Path(".gitignore").read_text(encoding="utf-8") if Path(".gitignore").exists() else ""
print([l for l in gi.splitlines() if "env" in l or "seed" in l or "local" in l])
bgi = Path("backend/.gitignore")
print("backend/.gitignore:", bgi.read_text(encoding="utf-8").splitlines() if bgi.exists() else None)
fe = Path("frontend/.env")
print("frontend/.env:", [l.split("=")[0] for l in fe.read_text().splitlines() if "=" in l] if fe.exists() else None)
print("frontend/.env.example:", Path("frontend/.env.example").exists())
