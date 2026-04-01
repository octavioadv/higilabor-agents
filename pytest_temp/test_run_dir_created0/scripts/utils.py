"""utils.py — helpers compartilhados entre run_agent.py e orchestrate.py."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Logger estruturado
# ---------------------------------------------------------------------------
logging.basicConfig(
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    level=logging.INFO,
)
logger = logging.getLogger("higilabor")


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_text_if_exists(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


# ---------------------------------------------------------------------------
# Tempo
# ---------------------------------------------------------------------------
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
