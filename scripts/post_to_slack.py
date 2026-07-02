"""post_to_slack.py — publica a mensagem_slack de uma execução do agente
06-financeiro-dre em um canal do Slack via Incoming Webhook.

Fluxo: DRE <-> ERP -> Slack. O agente 06 consolida a DRE gerencial e devolve
um campo `mensagem_slack` no parsed.json; este script lê esse campo e o posta.

Uso:
    python scripts/post_to_slack.py --input outputs/2026-06/run-...-06-financeiro-dre/parsed.json
    python scripts/post_to_slack.py                # auto-descobre o run mais recente
    python scripts/post_to_slack.py --dry-run      # imprime o payload sem postar

Sem dependências externas — apenas biblioteca padrão.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = REPO_ROOT / "outputs"
AGENT_ID = "06-financeiro-dre"

# Reaproveita o logger estruturado compartilhado do repositório.
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from utils import load_json, logger  # pyre-ignore


# ---------------------------------------------------------------------------
# Localização do parsed.json mais recente do agente financeiro
# ---------------------------------------------------------------------------
def find_latest_parsed(agent_id: str = AGENT_ID) -> Path:
    """Descobre o parsed.json mais recente em outputs/**/run-*-<agent_id>/."""
    if not OUTPUTS_DIR.exists():
        raise FileNotFoundError("Diretorio outputs/ nao encontrado")
    candidates = [
        p for p in OUTPUTS_DIR.glob(f"*/run-*-{agent_id}/parsed.json") if p.is_file()
    ]
    if not candidates:
        raise FileNotFoundError(
            f"Nenhum parsed.json encontrado para o agente {agent_id} em outputs/"
        )
    # Ordena por mtime e depois por nome para desempate estavel.
    candidates.sort(key=lambda p: (p.parent.stat().st_mtime, p.parent.name))
    return candidates[-1]


# ---------------------------------------------------------------------------
# Montagem do payload do Slack a partir do parsed.json
# ---------------------------------------------------------------------------
def build_slack_payload(parsed: dict) -> dict:
    mensagem = parsed.get("mensagem_slack")
    if not isinstance(mensagem, dict):
        raise ValueError("parsed.json nao contem o objeto 'mensagem_slack'")

    blocks = mensagem.get("blocks")
    if isinstance(blocks, list) and blocks:
        return {"blocks": blocks}

    texto = mensagem.get("texto")
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("'mensagem_slack' sem 'texto' nem 'blocks' utilizaveis")
    return {"text": texto}


# ---------------------------------------------------------------------------
# Envio ao webhook do Slack
# ---------------------------------------------------------------------------
def post_to_slack(payload: dict, webhook_url: str) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8", errors="replace").strip()
        if response.status >= 300:
            raise RuntimeError(
                f"Slack respondeu status {response.status}: {body}"
            )
        logger.info(f"slack_post_ok status={response.status} body={body}")


# ---------------------------------------------------------------------------
# Ponto de entrada principal
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Publica a mensagem_slack de uma execucao do agente 06-financeiro-dre."
    )
    parser.add_argument(
        "--input",
        help="Caminho para um parsed.json. Se omitido, descobre o run mais recente.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Imprime o payload em vez de postar no Slack.",
    )
    args = parser.parse_args()

    try:
        if args.input:
            parsed_path = Path(args.input).resolve()
            if not parsed_path.exists():
                raise FileNotFoundError(f"parsed.json nao encontrado: {parsed_path}")
        else:
            parsed_path = find_latest_parsed()
            logger.info(f"parsed_auto_descoberto path={parsed_path}")

        parsed = load_json(parsed_path)
        payload = build_slack_payload(parsed)

        if args.dry_run:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            logger.info("slack_dry_run payload_impresso")
            return

        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook_url or not webhook_url.strip():
            raise EnvironmentError(
                "Variavel de ambiente SLACK_WEBHOOK_URL nao definida — "
                "configure o webhook do Slack antes de postar."
            )

        post_to_slack(payload, webhook_url.strip())
        print(f"OK: mensagem publicada no Slack a partir de {parsed_path}")

    except Exception as exc:
        logger.error(f"slack_post_erro error={exc}")
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
