import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# ---------------------------------------------------------------------------
# Helpers: leitura segura
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_text_if_exists(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""


# ---------------------------------------------------------------------------
# Validação do envelope da task
# ---------------------------------------------------------------------------

def validate_task_envelope(task_data: dict) -> None:
    """Garante que a task tem agent_id, schema_version e inputs antes de qualquer
    chamada ao modelo ou carregamento de schema do agente."""
    required_top = ["agent_id", "schema_version", "inputs"]

    for key in required_top:
        if key not in task_data:
            raise ValueError(f"Task inválida: campo obrigatório ausente '{key}'")

    if not isinstance(task_data["agent_id"], str) or not task_data["agent_id"].strip():
        raise ValueError("Task inválida: 'agent_id' deve ser string não vazia")

    if not isinstance(task_data["schema_version"], str) or not task_data["schema_version"].strip():
        raise ValueError("Task inválida: 'schema_version' deve ser string não vazia")

    if not isinstance(task_data["inputs"], dict):
        raise ValueError("Task inválida: 'inputs' deve ser um objeto JSON")


# ---------------------------------------------------------------------------
# Stub: restante do pipeline (será preenchido nos próximos commits)
# ---------------------------------------------------------------------------

def main():
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="Caminho para o arquivo de task JSON")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    task_path = Path(args.task).resolve()

    if not task_path.exists():
        raise FileNotFoundError(f"Task não encontrada: {task_path}")

    task_data = load_json(task_path)
    validate_task_envelope(task_data)

    agent_id = task_data["agent_id"]
    agent_dir = repo_root / "agents" / agent_id

    if not agent_dir.exists():
        raise FileNotFoundError(f"Diretório do agente não encontrado: {agent_dir}")

    print(f"[envelope OK] agent_id={agent_id}, schema_version={task_data['schema_version']}")
    print("TODO: validação de inputs, chamada ao modelo e validação de output (próximos commits)")


if __name__ == "__main__":
    main()
