import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"
OUTPUTS_DIR = BASE_DIR / "outputs"


# ---------------------------------------------------------------------------
# Helpers I/O
# ---------------------------------------------------------------------------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Manifesto da rodada
# ---------------------------------------------------------------------------

def create_round_dir(master_task_path: Path) -> Path:
    """Cria outputs/YYYY-MM/round-TIMESTAMP/ com manifest.json inicial."""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    round_dir = OUTPUTS_DIR / datetime.now().strftime("%Y-%m") / f"round-{ts}"
    round_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "round_id": round_dir.name,
        "created_at": utc_now_iso(),
        "master_task_file": str(master_task_path),
        "status": "running",
        "runs": [],
        "subtasks": [],
        "errors": [],
    }
    save_json(round_dir / "manifest.json", manifest)
    return round_dir


def update_manifest(round_dir: Path, **fields: Any) -> None:
    """Atualiza campos no manifest.json de uma rodada."""
    manifest_path = round_dir / "manifest.json"
    manifest = load_json(manifest_path)
    manifest.update(fields)
    save_json(manifest_path, manifest)


def append_manifest_list(round_dir: Path, field: str, item: Any) -> None:
    """Acrescenta um item a uma lista no manifest.json."""
    manifest_path = round_dir / "manifest.json"
    manifest = load_json(manifest_path)
    manifest.setdefault(field, [])
    manifest[field].append(item)
    save_json(manifest_path, manifest)


# ---------------------------------------------------------------------------
# Ponto de entrada (stub - sera expandido nos proximos commits)
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/orchestrate.py --task tasks/exemplo-plano-90-dias.json")
    print("[orchestrate] manifesto pronto - implementacao completa nos proximos commits")


if __name__ == "__main__":
    main()
