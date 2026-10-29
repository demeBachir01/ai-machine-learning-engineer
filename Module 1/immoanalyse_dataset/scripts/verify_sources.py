"""Vérifie que data/raw et data/referentiels n'ont pas été modifiés (critère de validation)."""
import hashlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ok = True
for ligne in (ROOT / "docs" / "checksums_sources.txt").read_text().splitlines():
    attendu, chemin = ligne.split(maxsplit=1)
    reel = hashlib.sha256((ROOT / "data" / chemin.strip().lstrip("*")).read_bytes()).hexdigest()
    if reel != attendu:
        ok = False
        print(f"MODIFIÉ : {chemin}")
print("Sources intactes." if ok else "ATTENTION : des sources ont changé.")
sys.exit(0 if ok else 1)
