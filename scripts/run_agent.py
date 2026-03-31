import argparse
import json
import os
import re
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
# Contexto global
# ---------------------------------------------------------------------------

def load_global_context(context_dir: Path) -> str:
    if not context_dir.exists():
        return ""

    parts = []
    for file in sorted(context_dir.glob("*.md")):
        content = file.read_text(encoding="utf-8").strip()
        if content:
            parts.append(f"# {file.name}\n{content}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Montagem do prompt
# ---------------------------------------------------------------------------

def build_messages(task_data: dict, agent_files: dict, global_context: str) -> list:
    system_parts = [
        "Você é um agente especializado do sistema Higilabor.",
        "Responda exclusivamente com JSON válido.",
        "Não use markdown.",
        "Não use blocos de código.",
        "Não escreva comentários fora do JSON.",
        "A saída deve obedecer exatamente ao output schema fornecido."
    ]

    if agent_files["agent_md"]:
        system_parts.append("\n# AGENT\n" + agent_files["agent_md"])

    if global_context:
        system_parts.append("\n# CONTEXT\n" + global_context)

    if agent_files["templates_md"]:
        system_parts.append("\n# TEMPLATE\n" + agent_files["templates_md"])

    if agent_files["checklist_md"]:
        system_parts.append("\n# CHECKLIST\n" + agent_files["checklist_md"])

    system_parts.append(
        "\n# OUTPUT_SCHEMA\n" + json.dumps(agent_files["output_schema"], ensure_ascii=False, indent=2)
    )

    user_payload = {
        "task": task_data.get("task", ""),
        "inputs": task_data["inputs"]
    }

    return [
        {"role": "system", "content": "\n\n".join(system_parts)},
        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)}
    ]


# ---------------------------------------------------------------------------
# Chamada ao modelo
# ---------------------------------------------------------------------------

def call_model(messages: list, model: str) -> str:
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Parse seguro da saída JSON do modelo
# ---------------------------------------------------------------------------

def extract_json_text(raw_text: str) -> str:
    text = raw_text.strip()

    fence_match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    if text.startswith("{") or text.startswith("["):
        return text

    obj_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if obj_match:
        return obj_match.group(1).strip()

    raise ValueError("Resposta do modelo não contém JSON válido detectável")


def parse_model_json(raw_text: str) -> dict:
    json_text = extract_json_text(raw_text)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Saída inválida: JSON malformado na linha {e.lineno}, coluna {e.colno}: {e.msg}")


# ---------------------------------------------------------------------------
# Ponto de entrada principal
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

    # Valida inputs antes da chamada ao modelo
    validate_with_schema(task_data["inputs"], agent_files["input_schema"], "input-schema")

    # Monta prompt
    global_context = load_global_context(repo_root / "context")
    messages = build_messages(task_data, agent_files, global_context)

    # Chama o modelo
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    raw_output = call_model(messages, model)

    if not raw_output.strip():
        raise ValueError("Saída vazia do modelo")

    # Parseia e valida o output
    parsed_output = parse_model_json(raw_output)
    validate_with_schema(parsed_output, agent_files["output_schema"], "output-schema")

    # Salva a saída validada
    outputs_dir = repo_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    output_file = outputs_dir / f"{agent_id}-output.json"
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(parsed_output, f, ensure_ascii=False, indent=2)

    print(f"OK: saída validada salva em {output_file}")


if __name__ == "__main__":
    main()
