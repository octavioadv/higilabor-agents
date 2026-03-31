import argparse
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
    manifest_path = round_dir / "manifest.json"
    manifest = load_json(manifest_path)
    manifest.update(fields)
    save_json(manifest_path, manifest)


def append_manifest_list(round_dir: Path, field: str, item: Any) -> None:
    manifest_path = round_dir / "manifest.json"
    manifest = load_json(manifest_path)
    manifest.setdefault(field, [])
    manifest[field].append(item)
    save_json(manifest_path, manifest)


# ---------------------------------------------------------------------------
# Execucao de agente e localizacao do run mais recente
# ---------------------------------------------------------------------------

def run_agent(task_path: Path) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "run_agent.py"),
        "--task",
        str(task_path),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=True)


def find_latest_agent_run(agent_id: str, started_after: datetime | None = None) -> Path:
    if not OUTPUTS_DIR.exists():
        raise FileNotFoundError("Diretorio outputs/ nao encontrado")
    candidates: list[tuple[float, Path]] = []
    for month_dir in OUTPUTS_DIR.glob("*"):
        if not month_dir.is_dir():
            continue
        for run_dir in month_dir.glob("run-*"):
            if not run_dir.is_dir():
                continue
            meta_path = run_dir / "meta.json"
            parsed_path = run_dir / "parsed.json"
            if not meta_path.exists() or not parsed_path.exists():
                continue
            try:
                meta = load_json(meta_path)
            except Exception:
                continue
            if meta.get("agent_id") != agent_id:
                continue
            if started_after and meta.get("started_at"):
                try:
                    started = datetime.fromisoformat(
                        meta["started_at"].replace("Z", "+00:00")
                    )
                    if started < started_after:
                        continue
                except Exception:
                    pass
            candidates.append((run_dir.stat().st_mtime, run_dir))
    if not candidates:
        raise FileNotFoundError(
            f"Nenhuma execucao encontrada para o agente {agent_id}"
        )
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def read_parsed_output(run_dir: Path) -> dict:
    parsed_path = run_dir / "parsed.json"
    if not parsed_path.exists():
        raise FileNotFoundError(f"parsed.json nao encontrado em {run_dir}")
    return load_json(parsed_path)


def validate_orchestrator_output(data: dict) -> None:
    if "plano_execucao" not in data:
        raise ValueError("Saida do agente 00 sem 'plano_execucao'")
    if not isinstance(data["plano_execucao"], list) or not data["plano_execucao"]:
        raise ValueError("'plano_execucao' vazio ou invalido")
    if "criterios_sucesso" not in data:
        raise ValueError("Saida do agente 00 sem 'criterios_sucesso'")


# ---------------------------------------------------------------------------
# Ponto de entrada (stub - subtasks e encadeamento no proximo commit)
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="Task mestre do agente 00")
    args = parser.parse_args()

    master_task_path = Path(args.task).resolve()
    if not master_task_path.exists():
        raise FileNotFoundError(f"Task mestre nao encontrada: {master_task_path}")

    round_dir = create_round_dir(master_task_path)

    try:
        master_task = load_json(master_task_path)
        if master_task.get("agent_id") != "00-orquestrador":
            raise ValueError("A task mestre deve apontar para o agente 00-orquestrador")

        orchestration_started = datetime.now(timezone.utc)
        result = run_agent(master_task_path)

        orchestrator_run_dir = find_latest_agent_run(
            "00-orquestrador", started_after=orchestration_started
        )
        append_manifest_list(round_dir, "runs", {
            "agent_id": "00-orquestrador",
            "run_dir": str(orchestrator_run_dir),
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "status": "success",
        })

        orchestrator_output = read_parsed_output(orchestrator_run_dir)
        validate_orchestrator_output(orchestrator_output)

        update_manifest(round_dir, status="finished", finished_at=utc_now_iso())
        print("OK: agente 00 executado - subtasks no proximo commit")

    except Exception as e:
        append_manifest_list(round_dir, "errors", {"fatal": str(e)})
        update_manifest(round_dir, status="failed", finished_at=utc_now_iso())
        raise


if __name__ == "__main__":
    main()
