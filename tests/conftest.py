"""
Fixtures compartilhadas para todos os testes do Higilabor Agents.
"""
import json
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Diretório temporário que replica a estrutura mínima do repositório
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_repo(tmp_path):
    """Cria uma cópia enxuta do repositório em diretório temporário."""
    dirs_to_copy = ["agents", "context", "tasks"]
    for d in dirs_to_copy:
        src = REPO_ROOT / d
        if src.exists():
            shutil.copytree(src, tmp_path / d)

    # Cria outputs/
    (tmp_path / "outputs").mkdir(exist_ok=True)

    # Copia scripts/
    shutil.copytree(REPO_ROOT / "scripts", tmp_path / "scripts")

    # .env mínimo (sem chave real — testes que precisam da API usam mock)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=test-key\nGEMINI_MODEL=gemini-2.5-flash\n")

    return tmp_path


# ---------------------------------------------------------------------------
# Tasks válidas e inválidas prontas para uso
# ---------------------------------------------------------------------------

@pytest.fixture()
def valid_depoimentos_task(tmp_repo):
    """Task válida para o agente 01-depoimentos."""
    task = {
        "agent_id": "01-depoimentos",
        "schema_version": "1.0",
        "task": "Teste automatizado",
        "inputs": {
            "nome_cliente": "Empresa Teste LTDA",
            "segmento": "Indústria",
            "servico_prestado": "PGR e LTCAT",
            "resultado_obtido": "Conformidade total",
            "canal_publicacao": ["site", "linkedin"],
            "contato_autorizado": True,
        },
    }
    path = tmp_repo / "tasks" / "test-depoimentos.json"
    path.write_text(json.dumps(task, ensure_ascii=False, indent=2))
    return path


@pytest.fixture()
def valid_orchestrator_task(tmp_repo):
    """Task válida para o agente 00-orquestrador."""
    task = {
        "agent_id": "00-orquestrador",
        "schema_version": "1.0",
        "task": "Plano de teste automatizado",
        "inputs": {
            "objetivo_ciclo": "Testar pipeline ponta a ponta",
            "duracao_dias": 30,
            "restricoes": ["nao chamar API real"],
            "agentes_disponiveis": ["01-depoimentos", "02-cases"],
        },
    }
    path = tmp_repo / "tasks" / "test-orchestrator.json"
    path.write_text(json.dumps(task, ensure_ascii=False, indent=2))
    return path


@pytest.fixture()
def invalid_task_missing_fields(tmp_repo):
    """Task sem campos obrigatórios (falta agent_id, schema_version)."""
    task = {"inputs": {"nome_cliente": "Teste"}}
    path = tmp_repo / "tasks" / "test-invalid-envelope.json"
    path.write_text(json.dumps(task))
    return path


@pytest.fixture()
def invalid_task_bad_input(tmp_repo):
    """Task com envelope válido mas inputs inválidos (falta campos required)."""
    task = {
        "agent_id": "01-depoimentos",
        "schema_version": "1.0",
        "task": "Teste com input ruim",
        "inputs": {
            # Faltam nome_cliente, segmento, servico_prestado (required)
            "contato_autorizado": False,
        },
    }
    path = tmp_repo / "tasks" / "test-invalid-input.json"
    path.write_text(json.dumps(task, ensure_ascii=False, indent=2))
    return path
