import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import Draft202012Validator
from google import genai
from google.genai import types

from utils import load_json, load_text_if_exists, utc_now_iso, logger

# ---------------------------------------------------------------------------
# Validacao do envelope da task
# ---------------------------------------------------------------------------
def validate_task_envelope(task_data: dict) -> None:
    for key in ["agent_id", "schema_version", "inputs"]:
        if key not in task_data:
            raise ValueError(f"Task invalida: campo obrigatorio ausente '{key}'")
    if not isinstance(task_data["agent_id"], str) or not task_data["agent_id"].strip():
        raise ValueError("Task invalida: 'agent_id' deve ser string nao vazia")
    if not isinstance(task_data["schema_version"], str) or not task_data["schema_version"].strip():
        raise ValueError("Task invalida: 'schema_version' deve ser string nao vazia")
    if not isinstance(task_data["inputs"], dict):
        raise ValueError("Task invalida: 'inputs' deve ser um objeto JSON")


# ---------------------------------------------------------------------------
# Validacao com JSON Schema
# ---------------------------------------------------------------------------
def validate_with_schema(instance: dict, schema: dict, label: str) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
    if not errors:
        return
    messages = []
    for err in errors:
        field_path = ".".join(str(p) for p in err.path) or ""
        messages.append(f"- {label}: campo '{field_path}': {err.message}")
    raise ValueError("\n".join(messages))


# ---------------------------------------------------------------------------
# Carregamento dos arquivos do agente
# ---------------------------------------------------------------------------
def load_agent_files(agent_dir: Path) -> dict:
    return {
        "agent_md": load_text_if_exists(agent_dir / "agent.md"),
        "templates_md": load_text_if_exists(agent_dir / "templates.md"),
        "checklist_md": load_text_if_exists(agent_dir / "checklist.md"),
        "input_schema": load_json(agent_dir / "input-schema.json"),
        "output_schema": load_json(agent_dir / "output-schema.json"),
        "context_files": _load_context_list(agent_dir),
    }


def _load_context_list(agent_dir: Path) -> list[str]:
    """Retorna lista de nomes de arquivos de contexto relevantes para o agente.
    Lido de agent-context.json se existir, senao usa todos os arquivos."""
    cfg_path = agent_dir / "agent-context.json"
    if cfg_path.exists():
        data = load_json(cfg_path)
        return data.get("context_files", [])
    return []  # vazio = carregar tudo (comportamento legado)


# ---------------------------------------------------------------------------
# Contexto global (seletivo por agente)
# ---------------------------------------------------------------------------
def load_global_context(context_dir: Path, allowed_files: list[str] | None = None) -> str:
    if not context_dir.exists():
        return ""
    parts = []
    for file in sorted(context_dir.glob("*.md")):
        if isinstance(allowed_files, list) and file.name not in allowed_files:
            continue
        content = file.read_text(encoding="utf-8").strip()
        if content:
            parts.append(f"# {file.name}\n{content}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Montagem do prompt
# ---------------------------------------------------------------------------
def build_messages(task_data: dict, agent_files: dict, global_context: str) -> tuple[str, str]:
    system_parts = [
        "Voce e um agente especializado do sistema Higilabor.",
        "Responda exclusivamente com JSON valido conforme o output schema.",
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
    
    system_instruction = "\n\n".join(system_parts)
    user_content = json.dumps(user_payload, ensure_ascii=False, indent=2)
    return system_instruction, user_content


# ---------------------------------------------------------------------------
# Chamada ao modelo com retry e backoff exponencial
# ---------------------------------------------------------------------------
def call_model(system_instruction: str, user_content: str, model: str, retries: int = 3) -> str:
    client = genai.Client()
    last_exc = None
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2,
                    response_mime_type="application/json",
                )
            )
            return response.text or ""
        except Exception as exc:
            last_exc = exc
            wait = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f"call_model tentativa {attempt + 1}/{retries} falhou: {exc} — aguardando {wait}s")
            if attempt < retries - 1:
                time.sleep(wait)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("call_model failed sem exceções registradas")


# ---------------------------------------------------------------------------
# Parse seguro da saida JSON do modelo
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
    raise ValueError("Resposta do modelo nao contem JSON valido detectavel")


def parse_model_json(raw_text: str) -> dict:
    json_text = extract_json_text(raw_text)
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Saida invalida: JSON malformado na linha {e.lineno}, coluna {e.colno}: {e.msg}")


# ---------------------------------------------------------------------------
# Bloco 1: Geracao do run_id e diretorio de execucao
# ---------------------------------------------------------------------------
def create_run_dir(repo_root: Path, agent_id: str) -> tuple[str, Path]:
    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    run_id = f"run-{timestamp}-{agent_id}"
    month_dir = now.strftime("%Y-%m")
    run_dir = repo_root / "outputs" / month_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_id, run_dir


# ---------------------------------------------------------------------------
# Bloco 2: Salvar artefatos da execucao
# ---------------------------------------------------------------------------
def save_artifacts(
    run_dir: Path,
    raw_output: str,
    parsed_output: dict,
    meta: dict,
) -> None:
    (run_dir / "raw.md").write_text(raw_output, encoding="utf-8")
    with (run_dir / "parsed.json").open("w", encoding="utf-8") as f:
        json.dump(parsed_output, f, ensure_ascii=False, indent=2)
    with (run_dir / "meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Bloco 3: Salvar meta de erro auditavel
# ---------------------------------------------------------------------------
def save_error_meta(run_dir, meta: dict, error_msg: str) -> None:
    if run_dir is None:
        return
    meta["success"] = False
    meta["error"] = error_msg
    meta.setdefault("finished_at", utc_now_iso())
    try:
        with (run_dir / "meta.json").open("w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


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
    run_dir = None
    meta = {}

    try:
        if not task_path.exists():
            raise FileNotFoundError(f"Task nao encontrada: {task_path}")

        task_data = load_json(task_path)
        validate_task_envelope(task_data)

        agent_id = task_data["agent_id"]
        agent_dir = repo_root / "agents" / agent_id
        if not agent_dir.exists():
            raise FileNotFoundError(f"Diretorio do agente nao encontrado: {agent_dir}")

        agent_files = load_agent_files(agent_dir)
        validate_with_schema(task_data["inputs"], agent_files["input_schema"], "input-schema")

        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        run_id, run_dir = create_run_dir(repo_root, agent_id)
        start_ts = datetime.now(timezone.utc)
        meta = {
            "run_id": run_id,
            "agent_id": agent_id,
            "schema_version": task_data["schema_version"],
            "task_file": str(task_path.relative_to(repo_root)),
            "model": model,
            "started_at": start_ts.isoformat(),
            "input_valid": True,
        }

        global_context = load_global_context(
            repo_root / "context",
            allowed_files=agent_files["context_files"] or None,
        )
        system_instruction, user_content = build_messages(task_data, agent_files, global_context)
        raw_output = call_model(system_instruction, user_content, model)

        if not raw_output.strip():
            raise ValueError("Saida vazia do modelo")

        parsed_output = parse_model_json(raw_output)
        validate_with_schema(parsed_output, agent_files["output_schema"], "output-schema")

        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - start_ts).total_seconds() * 1000)
        meta.update({
            "finished_at": finished_at.isoformat(),
            "duration_ms": duration_ms,
            "output_valid": True,
            "success": True,
        })
        save_artifacts(run_dir, raw_output, parsed_output, meta)
        logger.info(f"execucao_ok run_id={run_id} agent={agent_id} duration_ms={duration_ms}")
        print(f"OK: execucao {run_id} salva em {run_dir}")

    except Exception as exc:
        error_msg = str(exc)
        save_error_meta(run_dir, meta, error_msg)
        logger.error(f"execucao_erro agent={meta.get('agent_id', '?')} error={error_msg}")
        print(f"ERRO: {error_msg}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
