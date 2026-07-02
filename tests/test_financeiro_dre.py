"""
Testes do agente 06-financeiro-dre e do fluxo DRE → Slack.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest  # pyre-ignore
from jsonschema import Draft7Validator  # pyre-ignore

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from run_agent import load_json, validate_with_schema  # pyre-ignore
from post_to_slack import build_slack_payload  # pyre-ignore

AGENT_DIR = REPO_ROOT / "agents" / "06-financeiro-dre"


# ===================================================================
# Schemas do agente 06
# ===================================================================

class TestSchemasFinanceiro:
    """Os schemas do agente 06 devem ser draft-07 válidos."""

    def test_input_schema_valido(self):
        schema = load_json(AGENT_DIR / "input-schema.json")
        Draft7Validator.check_schema(schema)

    def test_output_schema_valido(self):
        schema = load_json(AGENT_DIR / "output-schema.json")
        Draft7Validator.check_schema(schema)


class TestExemploTask:
    """A task de exemplo deve validar contra o input-schema do agente 06."""

    def test_exemplo_valida_no_input_schema(self):
        task = load_json(REPO_ROOT / "tasks" / "exemplo-financeiro-dre.json")
        schema = load_json(AGENT_DIR / "input-schema.json")

        assert task["agent_id"] == "06-financeiro-dre"
        assert task["schema_version"] == "1.0"
        # Não deve levantar exceção
        validate_with_schema(task["inputs"], schema, "input-schema")

    def test_exemplo_tem_comparativos(self):
        task = load_json(REPO_ROOT / "tasks" / "exemplo-financeiro-dre.json")
        assert "comparativos" in task["inputs"]
        assert "meta" in task["inputs"]["comparativos"]
        assert "periodo_anterior" in task["inputs"]["comparativos"]


# ===================================================================
# post_to_slack.py — montagem do payload
# ===================================================================

class TestBuildSlackPayload:
    """A montagem do payload deve preferir blocks quando presentes."""

    def test_payload_texto(self):
        parsed = {"mensagem_slack": {"texto": "DRE de Junho/2026"}}
        payload = build_slack_payload(parsed)
        assert payload == {"text": "DRE de Junho/2026"}

    def test_payload_blocks(self):
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "DRE"}}]
        parsed = {"mensagem_slack": {"texto": "fallback", "blocks": blocks}}
        payload = build_slack_payload(parsed)
        assert payload == {"blocks": blocks}

    def test_payload_sem_mensagem_falha(self):
        with pytest.raises(ValueError, match="mensagem_slack"):
            build_slack_payload({"periodo": {"label": "Junho/2026"}})


# ===================================================================
# post_to_slack.py --dry-run (smoke test via subprocess)
# ===================================================================

class TestPostToSlackDryRun:
    """O --dry-run deve imprimir o payload sem postar e sem exigir webhook."""

    def test_dry_run_imprime_payload(self, tmp_path):
        parsed = {
            "periodo": {"label": "Junho/2026"},
            "moeda": "BRL",
            "mensagem_slack": {"texto": ":bar_chart: *DRE Gerencial — Junho/2026*"},
        }
        parsed_path = tmp_path / "parsed.json"
        parsed_path.write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "post_to_slack.py"),
             "--input", str(parsed_path), "--dry-run"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "DRE Gerencial" in result.stdout
