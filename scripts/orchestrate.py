import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
TASKS_DIR = BASE_DIR / "tasks"


def load_task(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Uso: python scripts/orchestrate.py tasks/exemplo-plano-90-dias.json")

    master_task_path = Path(sys.argv[1]).resolve()
    master_task = load_task(master_task_path)

    print("Executando Agente 0...")
    subprocess.run(
        [sys.executable, str(BASE_DIR / "scripts" / "run_agent.py"), str(master_task_path)],
        check=True
    )

    print("Orquestração básica concluída.")
    print("Próximo passo: usar a saída do Agente 0 para gerar novas tasks encadeadas.")


if __name__ == "__main__":
    main()
