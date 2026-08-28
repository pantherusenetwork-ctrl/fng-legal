"""Point d'entrée RackForgePrime.

    python run.py            → http://127.0.0.1:8137
    python run.py --port N   → port custom

Local uniquement : le serveur n'écoute que sur 127.0.0.1.
"""

import argparse
import sys
from pathlib import Path

# Le package vit dans backend/ ; on l'ajoute au path sans installation.
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))


def main() -> None:
    parser = argparse.ArgumentParser(description="RackForgePrime — serveur local")
    parser.add_argument("--port", type=int, default=8137)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    import uvicorn
    print(f"RackForgePrime → http://{args.host}:{args.port}")
    uvicorn.run("app:app", host=args.host, port=args.port,
                app_dir=str(Path(__file__).resolve().parent / "backend"))


if __name__ == "__main__":
    main()
