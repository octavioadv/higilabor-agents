import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = BASE_DIR / "scripts"
AGENTS_DIR = BASE_DIR / "agents"
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
# Geracao de tasks para sub-agentes
# ---------------------------------------------------------------------------

def generate_subtask(step: dict, round_dir: Path) -> Path:
    """
    Gera um arquivo task JSON para o agente especificado em step.
    step deve ter: {"agente": "01-depoimentos", "objetivo": "...", "insumos": [...]}
    """
    agent_id = step["agente"]
    agent_dir = AGENTS_DIR / agent_id
    if not agent_dir.exists():
        raise FileNotFoundError(f"Agente nao encontrado: {agent_id}")

    # Carrega input-schema.json do agente para saber quais campos sao esperados
    input_schema_path = agent_dir / "input-schema.json"
    if not input_schema_path.exists():
        raise FileNotFoundError(f"input-schema.json nao encontrado para {agent_id}")
    input_schema = load_json(input_schema_path)

    # Monta inputs genericos com base no schema
    # Assume que o agente aceita "objetivo" e "insumos" como campos comuns
    # Se o schema requerer campos especificos, eles devem ser fornecidos pelo orquestrador
    inputs = {
        "objetivo": step.get("objetivo", ""),
        "insumos": step.get("insumos", []),
    }

    # Se o schema tiver propriedades obrigatorias alem de objetivo/insumos,
    # preencha-as com valores vazios (ou adapte conforme necessario)
    required_fields = input_schema.get("required", [])
    for field in required_fields:
        if field not in inputs:
            # Valores default por tipo
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
# Encadeamento dos sub-agentes
# ---------------------------------------------------------------------------

def execute_subtasks(plano_execucao: list, round_dir: Path) -> None:
    """
    Para cada etapa no plano_execucao:
    1. Gera a task JSON
    2. Executa run_agent.py
    3. Localiza o run_dir da execucao
    4. Atualiza o manifesto
    """
    for step in plano_execucao:
        agent_id = step["agente"]
        ordem = step.get("ordem", 0)
        print(f"\nExecutando sub-agente {ordem}: {agent_id}...")

        try:
            # Gera o arquivo de task
            task_path = generate_subtask(step, round_dir)
            print(f"  Task gerada: {task_path.name}")

            # Executa o agente
            subtask_started = datetime.now(timezone.utc)
            result = run_agent(task_path)

            # Localiza o run_dir da execucao
            run_dir = find_latest_agent_run(agent_id, started_after=subtask_started)
            print(f"  Run concluido: {run_dir.name}")

            # Atualiza manifesto
            append_manifest_list(round_dir, "subtasks", {
                "ordem": ordem,
                "agent_id": agent_id,
                "task_file": task_path.name,
                "run_dir": str(run_dir),
                "status": "success",
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            })

        except Exception as e:
            print(f"  ERRO ao executar {agent_id}: {e}")
            append_manifest_list(round_dir, "errors", {
                "ordem": ordem,
                "agent_id": agent_id,
                "error": str(e),
            })
            # Continua para proxima etapa (ou pode usar 'raise' para abortar)

# ---------------------------------------------------------------------------
# Ponto de entrada
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

        # Executa agente 00 (orquestrador)
        print("Executando Agente 00 (orquestrador)...")
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
        print(f"\nPlano de execucao possui {len(plano_execucao)} etapas.")

        # Encadeia sub-agentes
        execute_subtasks(plano_execucao, round_dir)

        update_manifest(round_dir, status="finished", finished_at=utc_now_iso())
        print(f"\nOrquestracao completa. Manifesto salvo em: {round_dir / 'manifest.json'}")

    except Exception as e:
        append_manifest_list(round_dir, "errors", {"fatal": str(e)})
        update_manifest(round_dir, status="failed", finished_at=utc_now_iso())
        raise

if __name__ == "__main__":
    main()
