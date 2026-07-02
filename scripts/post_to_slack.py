"""post_to_slack.py — publica a mensagem_slack de uma execução do agente
06-financeiro-dre em um canal do Slack.

Fluxo: DRE <-> ERP -> Slack. O agente 06 consolida a DRE gerencial e devolve
um campo `mensagem_slack` no parsed.json; este script lê esse campo e o posta.

Dois tipos de URL são aceitos via SLACK_WEBHOOK_URL, distinguidos pelo caminho:

  * Incoming Webhook clássico  (https://hooks.slack.com/services/...)
      Aceita o formato nativo do Slack: envia `blocks` quando disponíveis,
      caso contrário `{"text": ...}`.

  * Slack Workflow trigger      (https://hooks.slack.com/triggers/...)
      NÃO é um webhook clássico. Dispara um workflow do Slack Workflow Builder
      e espera um JSON cujas CHAVES correspondem exatamente às variáveis
      definidas no gatilho do workflow. O trigger normalmente não renderiza
      Block Kit, então enviamos apenas o texto puro em uma única variável.
      O nome dessa variável é configurável via --payload-key / SLACK_PAYLOAD_KEY
      (padrão: "text") e DEVE bater com o nome da variável no Workflow Builder,
      senão o Slack rejeita a chamada.

Uso:
    python scripts/post_to_slack.py --input outputs/2026-06/run-...-06-financeiro-dre/parsed.json
    python scripts/post_to_slack.py                     # auto-descobre o run mais recente
    python scripts/post_to_slack.py --dry-run           # imprime o payload sem postar
    python scripts/post_to_slack.py --payload-key resumo  # variável do trigger = "resumo"

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
DEFAULT_PAYLOAD_KEY = "text"

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
def is_trigger_url(url: str) -> bool:
    """True se a URL for um gatilho do Slack Workflow (/triggers/), e não um
    Incoming Webhook clássico (/services/)."""
    return isinstance(url, str) and "/triggers/" in url


def build_slack_payload(
    parsed: dict,
    *,
    trigger: bool = False,
    payload_key: str = DEFAULT_PAYLOAD_KEY,
) -> dict:
    """Monta o corpo JSON a ser postado.

    - Webhook clássico (trigger=False): prefere `blocks`, senão `{"text": ...}`.
    - Trigger de workflow (trigger=True): envia somente o texto puro sob a
      chave `payload_key`, que deve corresponder à variável do Workflow Builder
      (triggers geralmente não renderizam Block Kit, por isso não enviamos
      `blocks`).
    """
    mensagem = parsed.get("mensagem_slack")
    if not isinstance(mensagem, dict):
        raise ValueError("parsed.json nao contem o objeto 'mensagem_slack'")

    if trigger:
        texto = mensagem.get("texto")
        if not isinstance(texto, str) or not texto.strip():
            raise ValueError(
                "'mensagem_slack' sem 'texto' — obrigatorio para o trigger do Slack"
            )
        return {payload_key: texto}

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
    parser.add_argument(
        "--payload-key",
        default=None,
        help=(
            "Nome da variavel usada ao postar em um trigger do Slack Workflow "
            "(/triggers/). Deve bater com a variavel do Workflow Builder. "
            "Padrao: SLACK_PAYLOAD_KEY ou 'text'. Ignorado para webhooks classicos."
        ),
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

        webhook_url = (os.getenv("SLACK_WEBHOOK_URL") or "").strip()
        payload_key = (
            args.payload_key
            or os.getenv("SLACK_PAYLOAD_KEY")
            or DEFAULT_PAYLOAD_KEY
        )
        trigger = is_trigger_url(webhook_url)
        payload = build_slack_payload(
            parsed, trigger=trigger, payload_key=payload_key
        )

        if args.dry_run:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            logger.info(
                f"slack_dry_run payload_impresso trigger={trigger} key={payload_key}"
            )
            return

        if not webhook_url:
            raise EnvironmentError(
                "Variavel de ambiente SLACK_WEBHOOK_URL nao definida — "
                "configure o webhook (/services/) ou o trigger (/triggers/) "
                "do Slack antes de postar."
            )

        post_to_slack(payload, webhook_url)
        destino = "trigger" if trigger else "webhook"
        print(
            f"OK: mensagem publicada no Slack ({destino}) a partir de {parsed_path}"
        )

    except Exception as exc:
        logger.error(f"slack_post_erro error={exc}")
        print(f"ERRO: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
