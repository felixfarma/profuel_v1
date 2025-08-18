# scripts/snapshot.py
from pathlib import Path
import shutil, subprocess, sys, zipfile, time

ROOT = Path(__file__).resolve().parents[1]
ts = time.strftime("%Y%m%d-%H%M%S")
bdir = ROOT / "backups"
bdir.mkdir(exist_ok=True)

db_src = ROOT / "instance" / "nutricional.db"
db_dst = bdir / f"nutricional-{ts}.db"
if db_src.exists():
    shutil.copy2(db_src, db_dst)

req = ROOT / f"requirements-freeze-{ts}.txt"
subprocess.run([sys.executable, "-m", "pip", "freeze"], check=True, stdout=req.open("w", encoding="utf-8"))

zip_path = bdir / f"profuel-safe-{ts}.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in ["app", "scripts", "templates", "static", "requirements.txt"]:
        p = ROOT / rel
        if p.exists():
            if p.is_dir():
                for file in p.rglob("*"):
                    if file.is_file():
                        z.write(file, file.relative_to(ROOT))
            else:
                z.write(p, p.relative_to(ROOT))
    if db_dst.exists():
        z.write(db_dst, db_dst.relative_to(ROOT))
    z.write(req, req.relative_to(ROOT))

print(f"[backup] DB -> {db_dst if db_src.exists() else 'no db found'}")
print(f"[backup] Freeze -> {req}")
print(f"[backup] ZIP -> {zip_path}")
