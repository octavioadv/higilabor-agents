"""
Testes de execução: task válida gera output validado (mock da API).
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest  # pyre-ignore

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_agent import (  # pyre-ignore
    build_messages,
    create_run_dir,
    load_agent_files,
    load_global_context,
    load_json,
    main as run_agent_main,
    save_artifacts,
    validate_task_envelope,
    validate_with_schema,
)
from tests.fixtures import MOCK_DEPOIMENTOS_OUTPUT  # pyre-ignore


# ===================================================================
# 3. Execução simples com task válida
# ===================================================================

class TestBuildMessages:
    """Verifica montagem correta do prompt."""

    def test_messages_have_system_and_user(self, tmp_repo):
        task_data = {
            "agent_id": "01-depoimentos",
            "schema_version": "1.0",
            "task": "Teste",
            "inputs": {
                "nome_cliente": "Empresa Teste",
                "segmento": "Indústria",
                "servico_prestado": "PGR",
            },
        }
        agent_dir = tmp_repo / "agents" / "01-depoimentos"
        agent_files = load_agent_files(agent_dir)
        global_context = load_global_context(tmp_repo / "context")
        system_instruction, user_content = build_messages(task_data, agent_files, global_context)

        assert "Higilabor" in system_instruction
        assert "OUTPUT_SCHEMA" in system_instruction

    def test_user_message_contains_inputs(self, tmp_repo):
        task_data = {
            "agent_id": "01-depoimentos",
            "schema_version": "1.0",
            "task": "Teste",
            "inputs": {"nome_cliente": "ACME Corp", "segmento": "Saúde",
                       "servico_prestado": "PCMSO"},
        }
        agent_files = load_agent_files(tmp_repo / "agents" / "01-depoimentos")
        system_instruction, user_content = build_messages(task_data, agent_files, "")

        assert "ACME Corp" in user_content
        assert "Saúde" in user_content


class TestCreateRunDir:
    """Verifica criação do diretório de execução."""

    def test_run_dir_created(self, tmp_repo):
        run_id, run_dir = create_run_dir(tmp_repo, "01-depoimentos")

        assert run_dir.exists()
        assert run_dir.is_dir()
        assert "01-depoimentos" in run_id
        assert "run-" in run_id


class TestSaveArtifacts:
    """Verifica que artefatos são salvos corretamente."""

    def test_artifacts_saved(self, tmp_repo):
        _, run_dir = create_run_dir(tmp_repo, "01-depoimentos")
        parsed = {"mensagem_solicitacao": "Teste"}
        meta = {"run_id": "test-run", "success": True}

        save_artifacts(run_dir, "raw text output", parsed, meta)

        assert (run_dir / "raw.md").exists()
        assert (run_dir / "parsed.json").exists()
        assert (run_dir / "meta.json").exists()

        saved_parsed = json.loads((run_dir / "parsed.json").read_text())
        assert saved_parsed["mensagem_solicitacao"] == "Teste"


class TestEndToEndWithMock:
    """Fluxo completo: task válida → mock API → output validado → artefatos salvos."""

    def test_valid_task_produces_valid_output(self, valid_depoimentos_task, tmp_repo):
        """Fluxo completo: task válida → mock API → output validado → artefatos salvos."""
        task_data = load_json(valid_depoimentos_task)
        validate_task_envelope(task_data)

        agent_dir = tmp_repo / "agents" / task_data["agent_id"]
        agent_files = load_agent_files(agent_dir)
        validate_with_schema(task_data["inputs"], agent_files["input_schema"], "input-schema")

        global_context = load_global_context(tmp_repo / "context")
        system_instruction, user_content = build_messages(task_data, agent_files, global_context)

        raw_output = MOCK_DEPOIMENTOS_OUTPUT
        from run_agent import parse_model_json  # pyre-ignore
        parsed_output = parse_model_json(raw_output)
        validate_with_schema(parsed_output, agent_files["output_schema"], "output-schema")

        _, run_dir = create_run_dir(tmp_repo, task_data["agent_id"])
        meta = {"run_id": "test", "success": True}
        save_artifacts(run_dir, raw_output, parsed_output, meta)

        # Verificações
        assert (run_dir / "parsed.json").exists()
        saved = json.loads((run_dir / "parsed.json").read_text(encoding="utf-8"))
        assert "mensagem_solicitacao" in saved
        assert "roteiro_perguntas" in saved
        assert len(saved["roteiro_perguntas"]) >= 5
        assert "depoimento_curto" in saved
        assert "depoimento_expandido" in saved

    def test_pipeline_validates_output_schema(self, tmp_repo):
        """Output que não obedece ao schema deve ser rejeitado mesmo que seja JSON válido."""
        agent_files = load_agent_files(tmp_repo / "agents" / "01-depoimentos")
        incomplete_output = {"mensagem_solicitacao": "Olá"}

        with pytest.raises(ValueError, match="output-schema"):
            validate_with_schema(
                incomplete_output, agent_files["output_schema"], "output-schema"
            )
