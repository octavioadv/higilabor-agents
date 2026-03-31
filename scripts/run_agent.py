import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
AGENTS_DIR = BASE_DIR / "agents"
CONTEXT_DIR = BASE_DIR / "context"
OUTPUTS_DIR = BASE_DIR / "outputs"

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY não encontrada no ambiente.")

client = OpenAI(api_key=API_KEY)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_context() -> str:
    context_parts = []
    for file in sorted(CONTEXT_DIR.glob("*.md")):
        content = read_text(file)
        context_parts.append(f"\n## CONTEXTO: {file.name}\n{content}")
    return "\n".join(context_parts)


def load_task(task_path: Path) -> dict:
    with open(task_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(agent_md: str, context_md: str, task_data: dict) -> str:
    return f"""
Você está executando um agente operacional da Higilabor.

# ESPECIFICAÇÃO DO AGENTE
{agent_md}

# CONTEXTO INSTITUCIONAL
{context_md}

# TAREFA
{json.dumps(task_data, ensure_ascii=False, indent=2)}

# INSTRUÇÕES FINAIS
- produza uma saída pronta para uso empresarial
- seja específico
- respeite as regras do agente
- organize a resposta em blocos claros
- não invente fatos
"""


def generate_output(prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def save_output(agent_id: str, content: str) -> Path:
    folder = OUTPUTS_DIR / datetime.now().strftime("%Y-%m")
    folder.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_path = folder / f"{agent_id}-{timestamp}.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/run_agent.py tasks/exemplo-depoimentos.json")

    task_path = Path(sys.argv[1]).resolve()
    task_data = load_task(task_path)

    agent_id = task_data["agent_id"]
    agent_md_path = AGENTS_DIR / agent_id / "agent.md"
    agent_md = read_text(agent_md_path)
    context_md = load_context()

    if not agent_md.strip():
        raise RuntimeError(f"agent.md não encontrado para {agent_id}")

    prompt = build_prompt(agent_md, context_md, task_data)
    output_text = generate_output(prompt)
    saved_file = save_output(agent_id, output_text)

    print(f"Saída salva em: {saved_file}")


if __name__ == "__main__":
    main()
