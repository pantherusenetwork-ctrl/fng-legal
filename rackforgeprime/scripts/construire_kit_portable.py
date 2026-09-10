#!/usr/bin/env python3
"""Assemble (et optionnellement compile) le kit portable RackForgePrime.

Usage
-----
  python scripts/construire_kit_portable.py
      → dist/RackForgePrime-Portable/  (lanceurs + LISEZMOI + workspace stub)

  python scripts/construire_kit_portable.py --build
      → en plus, PyInstaller **onedir** (Windows). L'exe atterrit dans le kit.

  python scripts/construire_kit_portable.py --workspace CHEMIN
      → copie ce workspace dans le kit (vos projets + catalogue).

Pourquoi onedir, pas onefile
----------------------------
Le onefile extrait les DLL dans %TEMP% à chaque lancement. Sur un autre PC
ou une clé USB : antivirus, TEMP plein, SmartScreen = l'exe « ne s'ouvre
pas ». Le onedir pose _internal\\ à côté de l'exe : rien n'est extrait.

Recette manuelle équivalente (chemins ABSOLUS, workpath COURT) :

  .venv\\Scripts\\python.exe -m PyInstaller --noconfirm --onedir --clean --noconsole ^
    --name RackForgePrime --icon <abs>\\assets\\icon.ico --paths <abs>\\backend ^
    --add-data "<abs>\\frontend;frontend" --collect-all uvicorn ^
    --collect-all reportlab --collect-all svglib ^
    --workpath <court>\\rfp-build\\build --distpath <court>\\rfp-build\\dist ^
    --specpath <court>\\rfp-build\\spec  <abs>\\run.py

Puis copier dist\\RackForgePrime\\* dans RackForgePrime-Portable\\,
et y ajouter portable\\LANCER-*.bat, _commun.cmd, LISEZMOI.txt,
GUIDE-UTILISATEUR.md.
Bumper VERSION (app.py) + badge (index.html) AVANT de compiler.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORTABLE_SRC = ROOT / "portable"
DEFAULT_DIST = ROOT / "dist" / "RackForgePrime-Portable"
LAUNCHERS = (
    "LANCER-PC.bat",
    "LANCER-WEB.bat",
    "LANCER-PHONE.bat",
    "_commun.cmd",
    "LISEZMOI.txt",
    "GUIDE-UTILISATEUR.md",
)


def _copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def assemble(dest: Path, workspace: Path | None = None) -> Path:
    """Construit l'arbre du kit (sans forcément l'exe)."""
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    for name in LAUNCHERS:
        src = PORTABLE_SRC / name
        if name == "GUIDE-UTILISATEUR.md":
            # Source de vérité à la racine du projet ; portable/ en est une copie.
            root_guide = ROOT / "GUIDE-UTILISATEUR.md"
            if root_guide.is_file():
                src = root_guide
        if not src.is_file():
            raise FileNotFoundError(f"Lanceur manquant : {src}")
        _copy_file(src, dest / name)
    ws = dest / "RackForgePrime-Workspace"
    for sub in ("projets", "exports", "catalogue/images-officielles",
                "catalogue/types-officiels", "catalogue/formes",
                "datasheets", "sauvegardes"):
        (ws / sub).mkdir(parents=True, exist_ok=True)
    if workspace:
        workspace = workspace.resolve()
        if not workspace.is_dir():
            raise FileNotFoundError(f"Workspace source introuvable : {workspace}")
        shutil.copytree(workspace, ws, dirs_exist_ok=True)
    marker = dest / "KIT-PORTABLE.txt"
    marker.write_text(
        "Kit portable RackForgePrime.\n"
        "Copiez CE dossier en entier (exe + _internal + workspace + lanceurs).\n",
        encoding="utf-8",
    )
    return dest


def pyinstaller_cmd(work: Path) -> list[str]:
    icon = ROOT / "assets" / "icon.ico"
    frontend = ROOT / "frontend"
    backend = ROOT / "backend"
    run_py = ROOT / "run.py"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--onedir", "--clean", "--noconsole",
        "--name", "RackForgePrime",
        "--paths", str(backend),
        "--add-data", f"{frontend}{os.pathsep}frontend",
        "--collect-all", "uvicorn",
        "--collect-all", "reportlab",
        "--collect-all", "svglib",
        "--workpath", str(work / "build"),
        "--distpath", str(work / "dist"),
        "--specpath", str(work / "spec"),
        str(run_py),
    ]
    if icon.is_file():
        idx = cmd.index("--noconsole") + 1
        cmd[idx:idx] = ["--icon", str(icon)]
    return cmd


def build_exe(dest: Path, work: Path) -> Path:
    if os.name != "nt":
        raise SystemExit(
            "La compilation de l'exe Windows (--build) se fait sur un PC "
            "Windows. Ici : assemblage du kit seulement."
        )
    work.mkdir(parents=True, exist_ok=True)
    cmd = pyinstaller_cmd(work)
    print("PyInstaller :", " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))
    built = work / "dist" / "RackForgePrime"
    exe = built / "RackForgePrime.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"Exe introuvable après build : {exe}")
    # Fusionner onedir dans le kit (exe + _internal).
    shutil.copy2(exe, dest / "RackForgePrime.exe")
    internal = built / "_internal"
    if internal.is_dir():
        target = dest / "_internal"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(internal, target)
    return dest / "RackForgePrime.exe"


def main() -> int:
    parser = argparse.ArgumentParser(description="Kit portable RackForgePrime")
    parser.add_argument("--dest", type=Path, default=DEFAULT_DIST,
                        help="dossier du kit (défaut dist/RackForgePrime-Portable)")
    parser.add_argument("--workspace", type=Path, default=None,
                        help="workspace existant à copier dans le kit")
    parser.add_argument("--build", action="store_true",
                        help="compiler l'exe (PyInstaller onedir, Windows)")
    parser.add_argument("--workpath", type=Path, default=None,
                        help="dossier de build COURT (évite la limite 260 car.)")
    args = parser.parse_args()

    dest = assemble(args.dest, args.workspace)
    print(f"Kit assemblé : {dest}")
    if args.build:
        work = args.workpath or (Path(os.environ.get("TEMP", "/tmp")) / "rfp-build")
        exe = build_exe(dest, work)
        print(f"Exe : {exe}")
    else:
        print("Pas d'exe (ajoutez --build sur Windows). Les lanceurs")
        print("retombent sur python run.py si on les lance depuis portable\\.")
    print()
    print("À copier sur l'USB / l'autre PC : tout le dossier")
    print(f"  {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
