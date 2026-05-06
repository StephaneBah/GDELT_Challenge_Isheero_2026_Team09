"""Bootstrap reproductible — création du venv et installation des dépendances.

Alternative cross-plateforme au Makefile pour les environnements sans `make`
(notamment Windows par défaut). Ce script ne dépend que de la stdlib Python.

Usage :
    python bootstrap.py              # crée .venv + installe requirements.txt
    python bootstrap.py --ml         # ajoute requirements-ml.txt (lourd)
    python bootstrap.py --check      # vérifie l'environnement sans rien installer

Une fois exécuté, lancer les commandes du projet via le binaire du venv :
    .venv/Scripts/python.exe -m src.pipeline.discover_codes   (Windows)
    .venv/bin/python -m src.pipeline.discover_codes           (Unix)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
REQUIREMENTS_ML = ROOT / "requirements-ml.txt"


def venv_python() -> Path:
    """Renvoie le chemin du binaire python à l'intérieur du venv."""
    if os.name == "nt":  # Windows
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def venv_exists() -> bool:
    return (VENV_DIR / "pyvenv.cfg").is_file()


def run(cmd: list[str], desc: str) -> None:
    print(f"\n>>> {desc}")
    print(f"    $ {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"    [FAIL] code={result.returncode}. Arret.", file=sys.stderr)
        sys.exit(result.returncode)
    print("    OK")


def create_venv() -> None:
    if venv_exists():
        print(f"[OK] .venv existe deja a {VENV_DIR}")
        return
    print(f"Création du venv à {VENV_DIR} (Python : {sys.executable})")
    run([sys.executable, "-m", "venv", str(VENV_DIR)], "Création du venv")


def upgrade_pip() -> None:
    py = venv_python()
    run(
        [str(py), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"],
        "Mise à jour de pip / setuptools / wheel",
    )


def install_requirements(req_file: Path, label: str) -> None:
    if not req_file.exists():
        print(f"⚠ {req_file.name} introuvable — saut.")
        return
    py = venv_python()
    run(
        [str(py), "-m", "pip", "install", "-r", str(req_file)],
        f"Installation de {label}",
    )


def check_env() -> None:
    print("--- Vérification environnement ---")
    print(f"Python système : {sys.version.split()[0]} ({sys.executable})")
    print(f"Plateforme     : {sys.platform}")
    print(f"Repo root      : {ROOT}")
    print(f"Venv attendu   : {VENV_DIR}  ({'présent' if venv_exists() else 'absent'})")
    print(f"requirements   : {'présent' if REQUIREMENTS.exists() else 'absent'}")
    print(f"requirements-ml: {'présent' if REQUIREMENTS_ML.exists() else 'absent'}")

    env_file = ROOT / ".env"
    print(f".env           : {'présent' if env_file.exists() else 'ABSENT — copier depuis .env.example'}")

    creds = ROOT / "gcp-credentials.json"
    print(f"gcp-credentials.json : {'présent' if creds.exists() else 'ABSENT (mode ADC requis)'}")

    if venv_exists():
        py = venv_python()
        print(f"\nBinaire venv   : {py}")
        try:
            subprocess.run([str(py), "--version"], check=True)
        except Exception as e:
            print(f"  ⚠ Binaire injoignable : {e}")


def print_next_steps() -> None:
    py = venv_python()
    py_rel = py.relative_to(ROOT)
    print()
    print("=" * 70)
    print("  Setup termine avec succes.")
    print("=" * 70)
    print()
    print("Commandes utiles (depuis la racine du repo) :")
    print()
    print(f"  {py_rel} -m src.pipeline.discover_codes      # audit codes BigQuery")
    print(f"  {py_rel} -m src.pipeline.extract             # snapshot 12 mois")
    print(f"  {py_rel} -m src.pipeline.clean")
    print(f"  {py_rel} -m src.pipeline.enrich")
    print(f"  {py_rel} -m src.pipeline.stories")
    print(f"  {py_rel} -m streamlit run dashboard/app.py   # dashboard local")
    print()
    print("Ou, si vous activez le venv :")
    if os.name == "nt":
        print("  .venv\\Scripts\\activate.bat                 # cmd.exe")
        print("  .venv\\Scripts\\Activate.ps1                 # PowerShell")
        print("  source .venv/Scripts/activate              # Git Bash")
    else:
        print("  source .venv/bin/activate")
    print("  python -m src.pipeline.discover_codes")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ml", action="store_true", help="Installer aussi requirements-ml.txt")
    parser.add_argument("--check", action="store_true", help="Vérifier sans installer")
    args = parser.parse_args()

    if args.check:
        check_env()
        return

    create_venv()
    upgrade_pip()
    install_requirements(REQUIREMENTS, "dépendances core (requirements.txt)")
    if args.ml:
        install_requirements(REQUIREMENTS_ML, "dépendances ML (requirements-ml.txt)")

    print_next_steps()


if __name__ == "__main__":
    main()
