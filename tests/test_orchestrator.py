"""
Testes do fluxo mínimo do orquestrador (orchestrate.py).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from orchestrate import (
    create_round_dir,
    generate_subtask,
    load_json,
    save_json,
    update_manifest,
    append_manifest_list,
    validate_orchestrator_output,
)
from tests.fixtures import MOCK_ORCHESTRATOR_OUTPUT


# ===================================================================
# 4. Fluxo mínimo do orquestrador
# ===================================================================

class TestOrchestratorValidation:
    """Verifica que a saída do agente 00 é validada corretamente."""

    def test_valid_orchestrator_output(self):
        data = json.loads(MOCK_ORCHESTRATOR_OUTPUT)
        # Não deve levantar exceção
        validate_orchestrator_output(data)

    def test_missing_plano_execucao(self):
        with pytest.raises(ValueError, match="plano_execucao"):
            validate_orchestrator_output({"criterios_sucesso": ["test"]})

    def test_empty_plano_execucao(self):
        with pytest.raises(ValueError, match="plano_execucao"):
            validate_orchestrator_output(
                {"plano_execucao": [], "criterios_sucesso": ["test"]}
            )

    def test_missing_criterios_sucesso(self):
        with pytest.raises(ValueError, match="criterios_sucesso"):
            validate_orchestrator_output(
                {"plano_execucao": [{"agente": "01", "ordem": 1}]}
            )


class TestRoundDir:
    """Verifica criação do diretório e manifesto da rodada."""

    def test_round_dir_created(self, tmp_repo):
        # Precisa que orchestrate.py use tmp_repo como base
        with patch("orchestrate.OUTPUTS_DIR", tmp_repo / "outputs"):
            round_dir = create_round_dir(tmp_repo / "tasks" / "test.json")

        assert round_dir.exists()
        manifest = load_json(round_dir / "manifest.json")
        assert manifest["status"] == "running"
        assert "round_id" in manifest

    def test_update_manifest(self, tmp_repo):
        with patch("orchestrate.OUTPUTS_DIR", tmp_repo / "outputs"):
            round_dir = create_round_dir(tmp_repo / "tasks" / "test.json")
            update_manifest(round_dir, status="finished")

        manifest = load_json(round_dir / "manifest.json")
        assert manifest["status"] == "finished"

    def test_append_manifest_list(self, tmp_repo):
        with patch("orchestrate.OUTPUTS_DIR", tmp_repo / "outputs"):
            round_dir = create_round_dir(tmp_repo / "tasks" / "test.json")
            append_manifest_list(round_dir, "runs", {"agent_id": "00", "status": "ok"})

        manifest = load_json(round_dir / "manifest.json")
        assert len(manifest["runs"]) == 1
        assert manifest["runs"][0]["agent_id"] == "00"


class TestSubtaskGeneration:
    """Verifica geração de tasks para sub-agentes."""

    def test_generates_valid_subtask(self, tmp_repo):
        step = {
            "ordem": 1,
            "agente": "01-depoimentos",
            "objetivo": "Coletar depoimentos",
            "insumos": ["lista de clientes"],
        }
        with patch("orchestrate.AGENTS_DIR", tmp_repo / "agents"):
            round_dir = tmp_repo / "outputs" / "test-round"
            round_dir.mkdir(parents=True)
            task_path = generate_subtask(step, round_dir)

        assert task_path.exists()
        task_data = load_json(task_path)
        assert task_data["agent_id"] == "01-depoimentos"
        assert task_data["schema_version"] == "1.0"
        assert "nome_cliente" in task_data["inputs"]
        assert "segmento" in task_data["inputs"]
        assert "servico_prestado" in task_data["inputs"]

    def test_subtask_for_nonexistent_agent_fails(self, tmp_repo):
        step = {"ordem": 1, "agente": "99-inexistente", "objetivo": "Fail"}
        with patch("orchestrate.AGENTS_DIR", tmp_repo / "agents"):
            round_dir = tmp_repo / "outputs" / "test-round-2"
            round_dir.mkdir(parents=True)
            with pytest.raises(FileNotFoundError, match="99-inexistente"):
                generate_subtask(step, round_dir)

    def test_subtask_fills_required_fields(self, tmp_repo):
        """Campos obrigatórios do schema devem receber pelo menos valores default."""
        step = {
            "ordem": 1,
            "agente": "01-depoimentos",
            "objetivo": "Teste",
            "insumos": [],
        }
        with patch("orchestrate.AGENTS_DIR", tmp_repo / "agents"):
            round_dir = tmp_repo / "outputs" / "test-round-3"
            round_dir.mkdir(parents=True)
            task_path = generate_subtask(step, round_dir)

        task_data = load_json(task_path)
        schema_path = tmp_repo / "agents" / "01-depoimentos" / "input-schema.json"
        schema = load_json(schema_path)
        required = schema.get("required", [])

        for field in required:
            assert field in task_data["inputs"], f"Campo obrigatório ausente: {field}"


class TestOrchestratorFlow:
    """Testa o fluxo orquestrador→sub-agentes com mocks."""

    @patch("orchestrate.run_agent")
    @patch("orchestrate.find_latest_agent_run")
    @patch("orchestrate.read_parsed_output")
    def test_full_flow_with_mocks(
        self, mock_read, mock_find, mock_run, valid_orchestrator_task, tmp_repo
    ):
        orchestrator_output = json.loads(MOCK_ORCHESTRATOR_OUTPUT)

        # Mock: run_agent retorna sucesso
        mock_run.return_value = MagicMock(
            stdout="OK: execucao test salva", stderr="", returncode=0
        )

        # Mock: find_latest_agent_run retorna um diretório fake
        fake_run_dir = tmp_repo / "outputs" / "2026-03" / "run-test-00"
        fake_run_dir.mkdir(parents=True)
        (fake_run_dir / "parsed.json").write_text(MOCK_ORCHESTRATOR_OUTPUT)
        (fake_run_dir / "meta.json").write_text('{"success": true}')
        mock_find.return_value = fake_run_dir

        # Mock: read_parsed_output retorna o output do orquestrador
        mock_read.return_value = orchestrator_output

        # Valida que o output do orquestrador é aceito
        validate_orchestrator_output(orchestrator_output)

        # Valida geração de subtasks para cada etapa
        with patch("orchestrate.AGENTS_DIR", tmp_repo / "agents"):
            round_dir = tmp_repo / "outputs" / "test-flow"
            round_dir.mkdir(parents=True)

            for step in orchestrator_output["plano_execucao"]:
                task_path = generate_subtask(step, round_dir)
                assert task_path.exists()
                task_data = load_json(task_path)
                assert task_data["agent_id"] == step["agente"]
