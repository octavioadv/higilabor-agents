import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import Draft202012Validator
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
    """Garante agent_id, schema_version e inputs antes de qualquer chamada."""
    for key in ["agent_id", "schema_version", "inputs"]:
        if key not in task_data:
            raise ValueError(f"Task inválida: campo obrigatório ausente '{key}'")

    if not isinstance(task_data["agent_id"], str) or not task_data["agent_id"].strip():
        raise ValueError("Task inválida: 'agent_id' deve ser string não vazia")

    if not isinstance(task_data["schema_version"], str) or not task_data["schema_version"].strip():
        raise ValueError("Task inválida: 'schema_version' deve ser string não vazia")

    if not isinstance(task_data["inputs"], dict):
        raise ValueError("Task inválida: 'inputs' deve ser um objeto JSON")


# ---------------------------------------------------------------------------
# Validação com JSON Schema
# ---------------------------------------------------------------------------

def validate_with_schema(instance: dict, schema: dict, label: str) -> None:
    """Valida instance contra schema; falha com mensagem legível."""
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)

    if not errors:
        return

    messages = []
    for err in errors:
        field_path = ".".join(str(p) for p in err.path) or "<root>"
        messages.append(f"- {label}: campo '{field_path}': {err.message}")

    raise ValueError("\n".join(messages))


# ---------------------------------------------------------------------------
# Carregamento dos arquivos do agente
# ---------------------------------------------------------------------------

def load_agent_files(agent_dir: Path) -> dict:
    """Carrega agent.md, templates.md, checklist.md, input/output schemas."""
    return {
        "agent_md": load_text_if_exists(agent_dir / "agent.md"),
        "templates_md": load_text_if_exists(agent_dir / "templates.md"),
        "checklist_md": load_text_if_exists(agent_dir / "checklist.md"),
        "input_schema": load_json(agent_dir / "input-schema.json"),
        "output_schema": load_json(agent_dir / "output-schema.json"),
    }


# ---------------------------------------------------------------------------
# Stub: restante do pipeline (próximo commit)
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

    agent_files = load_agent_files(agent_dir)

    # Valida inputs com o input-schema do agente
    validate_with_schema(task_data["inputs"], agent_files["input_schema"], "input-schema")

    print(f"[inputs OK] agent_id={agent_id}")
    print("TODO: montagem do prompt, chamada ao modelo e validação de output (próximo commit)")


if __name__ == "__main__":
    main()
