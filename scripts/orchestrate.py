import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from utils import load_json, save_json, utc_now_iso, logger

BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"
AGENTS_DIR = BASE_DIR / "agents"
OUTPUTS_DIR = BASE_DIR / "outputs"

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
# Geracao de tasks para sub-agentes
# ---------------------------------------------------------------------------
def generate_subtask(step: dict, round_dir: Path) -> Path:
    """Gera um arquivo task JSON para o agente especificado em step.
    Usa inputs fornecidos diretamente pelo orquestrador quando disponiveis.
    """
    agent_id = step["agente"]
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        raise FileNotFoundError(f"Agente nao encontrado: {agent_id}")

    input_schema_path = agent_dir / "input-schema.json"
    if not input_schema_path.exists():
        raise FileNotFoundError(f"input-schema.json nao encontrado para {agent_id}")
    input_schema = load_json(input_schema_path)

    # Preferencia: usar inputs completos fornecidos pelo agente 00
    if "inputs" in step and isinstance(step["inputs"], dict):
        inputs = step["inputs"]
    else:
        # Fallback: montar inputs genericos com base no schema
        inputs = {
            "objetivo": step.get("objetivo", ""),
            "insumos": step.get("insumos", []),
        }
        required_fields = input_schema.get("required", [])
        for field in required_fields:
            if field not in inputs:
                field_schema = input_schema.get("properties", {}).get(field, {})
                field_type = field_schema.get("type", "string")
                if field_type == "array":
                    inputs[field] = []
                elif field_type == "object":
                    inputs[field] = {}
                elif field_type == "integer":
                    inputs[field] = 0
                else:
                    inputs[field] = ""

    task_data = {
        "agent_id": agent_id,
        "schema_version": "1.0",
        "task": step.get("objetivo", f"Tarefa gerada para {agent_id}"),
        "inputs": inputs,
    }
    task_filename = f"subtask-{step.get('ordem', 0)}-{agent_id}.json"
    task_path = round_dir / task_filename
    save_json(task_path, task_data)
    return task_path


# ---------------------------------------------------------------------------
# Execucao de um unico step (usado pelo executor paralelo)
# ---------------------------------------------------------------------------
def _execute_single_step(step: dict, round_dir: Path) -> dict:
    agent_id = step["agente"]
    ordem = step.get("ordem", 0)
    logger.info(f"subtask_start ordem={ordem} agent={agent_id}")

    task_path = generate_subtask(step, round_dir)
    subtask_started = datetime.now(timezone.utc)
    result = run_agent(task_path)
    run_dir = find_latest_agent_run(agent_id, started_after=subtask_started)

    logger.info(f"subtask_ok ordem={ordem} agent={agent_id} run={run_dir.name}")
    return {
        "ordem": ordem,
        "agent_id": agent_id,
        "task_file": task_path.name,
        "run_dir": str(run_dir),
        "status": "success",
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


# ---------------------------------------------------------------------------
# Encadeamento dos sub-agentes (paralelo com ThreadPoolExecutor)
# ---------------------------------------------------------------------------
def execute_subtasks(plano_execucao: list, round_dir: Path, max_workers: int = 3) -> None:
    """Executa sub-agentes em paralelo respeitando o campo 'depends_on' quando presente.
    Etapas sem dependencias rodam simultaneamente; etapas com depends_on aguardam
    a conclusao das etapas listadas.
    """
    # Separar etapas independentes das dependentes
    independent = [s for s in plano_execucao if not s.get("depends_on")]
    dependent = [s for s in plano_execucao if s.get("depends_on")]

    def _run_group(steps: list) -> None:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_execute_single_step, step, round_dir): step for step in steps}
            for future in as_completed(futures):
                step = futures[future]
                try:
                    record = future.result()
                    append_manifest_list(round_dir, "subtasks", record)
                except Exception as e:
                    agent_id = step["agente"]
                    logger.error(f"subtask_erro agent={agent_id} error={e}")
                    append_manifest_list(round_dir, "errors", {
                        "ordem": step.get("ordem", 0),
                        "agent_id": agent_id,
                        "error": str(e),
                    })

    _run_group(independent)
    if dependent:
        _run_group(dependent)  # segundo passo apos independentes concluirem


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="Task mestre do agente 00")
    parser.add_argument("--max-workers", type=int, default=3, help="Paralelismo maximo dos sub-agentes")
    args = parser.parse_args()

    master_task_path = Path(args.task).resolve()
    if not master_task_path.exists():
        raise FileNotFoundError(f"Task mestre nao encontrada: {master_task_path}")

    round_dir = create_round_dir(master_task_path)
    try:
        master_task = load_json(master_task_path)
        if master_task.get("agent_id") != "00-orquestrador":
            raise ValueError("A task mestre deve apontar para o agente 00-orquestrador")

        logger.info("orchestration_start")
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
        plano_execucao = orchestrator_output["plano_execucao"]
        logger.info(f"orchestration_plan etapas={len(plano_execucao)}")
        print(f"\nPlano de execucao possui {len(plano_execucao)} etapas.")

        execute_subtasks(plano_execucao, round_dir, max_workers=args.max_workers)

        update_manifest(round_dir, status="finished", finished_at=utc_now_iso())
        logger.info(f"orchestration_ok round={round_dir.name}")
        print(f"\nOrquestracao completa. Manifesto salvo em: {round_dir / 'manifest.json'}")

    except Exception as e:
        append_manifest_list(round_dir, "errors", {"fatal": str(e)})
        update_manifest(round_dir, status="failed", finished_at=utc_now_iso())
        logger.error(f"orchestration_erro error={e}")
        raise


if __name__ == "__main__":
    main()
