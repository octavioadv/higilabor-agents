"""
Testes de validação do run_agent.py — inputs inválidos devem falhar
ANTES de qualquer chamada à API.
"""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Importa funções do runner para testes unitários
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from run_agent import (
    validate_task_envelope,
    validate_with_schema,
    load_agent_files,
    parse_model_json,
    extract_json_text,
)


# ===================================================================
# 1. Input inválido falha antes da API
# ===================================================================

class TestEnvelopeValidation:
    """Task sem campos obrigatórios deve falhar na validação do envelope."""

    def test_missing_agent_id(self):
        with pytest.raises(ValueError, match="agent_id"):
            validate_task_envelope({"schema_version": "1.0", "inputs": {}})

    def test_missing_schema_version(self):
        with pytest.raises(ValueError, match="schema_version"):
            validate_task_envelope({"agent_id": "01-depoimentos", "inputs": {}})

    def test_missing_inputs(self):
        with pytest.raises(ValueError, match="inputs"):
            validate_task_envelope(
                {"agent_id": "01-depoimentos", "schema_version": "1.0"}
            )

    def test_empty_agent_id(self):
        with pytest.raises(ValueError, match="agent_id"):
            validate_task_envelope(
                {"agent_id": "", "schema_version": "1.0", "inputs": {}}
            )

    def test_inputs_not_dict(self):
        with pytest.raises(ValueError, match="inputs"):
            validate_task_envelope(
                {"agent_id": "01-depoimentos", "schema_version": "1.0", "inputs": "not a dict"}
            )

    def test_valid_envelope_passes(self):
        # Não deve levantar exceção
        validate_task_envelope(
            {"agent_id": "01-depoimentos", "schema_version": "1.0", "inputs": {}}
        )


class TestInputSchemaValidation:
    """Inputs que não obedecem ao schema do agente devem ser rejeitados."""

    def test_missing_required_fields(self):
        schema = {
            "type": "object",
            "required": ["nome_cliente", "segmento", "servico_prestado"],
            "properties": {
                "nome_cliente": {"type": "string"},
                "segmento": {"type": "string"},
                "servico_prestado": {"type": "string"},
            },
        }
        with pytest.raises(ValueError, match="input-schema"):
            validate_with_schema(
                {"contato_autorizado": False}, schema, "input-schema"
            )

    def test_wrong_type(self):
        schema = {
            "type": "object",
            "required": ["nome_cliente"],
            "properties": {"nome_cliente": {"type": "string"}},
        }
        with pytest.raises(ValueError, match="input-schema"):
            validate_with_schema({"nome_cliente": 123}, schema, "input-schema")

    def test_valid_input_passes(self):
        schema = {
            "type": "object",
            "required": ["nome_cliente"],
            "properties": {"nome_cliente": {"type": "string"}},
        }
        # Não deve levantar exceção
        validate_with_schema({"nome_cliente": "Teste"}, schema, "input-schema")


class TestRunnerRejectsBeforeAPI:
    """Execução via subprocess: tasks inválidas devem falhar com exit code 1
    sem jamais chamar o modelo."""

    def test_invalid_envelope_exits_1(self, invalid_task_missing_fields, tmp_repo):
        result = subprocess.run(
            [sys.executable, str(tmp_repo / "scripts" / "run_agent.py"),
             "--task", str(invalid_task_missing_fields)],
            capture_output=True, text=True,
            cwd=str(tmp_repo),
            env={"PATH": "", "PYTHONPATH": str(tmp_repo)},
        )
        assert result.returncode == 1
        assert "ERRO" in result.stderr or "invalida" in result.stderr.lower()

    def test_invalid_input_schema_exits_1(self, invalid_task_bad_input, tmp_repo):
        result = subprocess.run(
            [sys.executable, str(tmp_repo / "scripts" / "run_agent.py"),
             "--task", str(invalid_task_bad_input)],
            capture_output=True, text=True,
            cwd=str(tmp_repo),
            env={"PATH": "", "PYTHONPATH": str(tmp_repo)},
        )
        assert result.returncode == 1
        assert "ERRO" in result.stderr or "input-schema" in result.stderr.lower()


# ===================================================================
# 2. Output inválido é rejeitado
# ===================================================================

class TestOutputValidation:
    """Respostas do modelo que não obedecem ao output-schema devem ser rejeitadas."""

    def test_missing_required_output_fields(self):
        schema = {
            "type": "object",
            "required": ["mensagem_solicitacao", "roteiro_perguntas",
                         "depoimento_curto", "depoimento_expandido"],
            "properties": {
                "mensagem_solicitacao": {"type": "string"},
                "roteiro_perguntas": {"type": "array", "items": {"type": "string"}},
                "depoimento_curto": {"type": "string"},
                "depoimento_expandido": {"type": "string"},
            },
        }
        incomplete = {"mensagem_solicitacao": "Olá"}
        with pytest.raises(ValueError, match="output-schema"):
            validate_with_schema(incomplete, schema, "output-schema")

    def test_wrong_output_type(self):
        schema = {
            "type": "object",
            "required": ["plano_execucao", "criterios_sucesso"],
            "properties": {
                "plano_execucao": {"type": "array"},
                "criterios_sucesso": {"type": "array"},
            },
        }
        bad = {"plano_execucao": "not an array", "criterios_sucesso": []}
        with pytest.raises(ValueError, match="output-schema"):
            validate_with_schema(bad, schema, "output-schema")


class TestJsonParsing:
    """O parser deve extrair JSON válido de respostas com markdown ou lixo."""

    def test_clean_json(self):
        raw = '{"key": "value"}'
        assert parse_model_json(raw) == {"key": "value"}

    def test_json_in_fences(self):
        raw = '```json\n{"key": "value"}\n```'
        assert parse_model_json(raw) == {"key": "value"}

    def test_json_with_surrounding_text(self):
        raw = 'Here is the output:\n{"key": "value"}\nEnd of output.'
        assert parse_model_json(raw) == {"key": "value"}

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="JSON"):
            parse_model_json("This is just plain text without any JSON")

    def test_malformed_json_raises(self):
        with pytest.raises(ValueError, match="malformado|JSON"):
            parse_model_json('{"key": value_without_quotes}')
