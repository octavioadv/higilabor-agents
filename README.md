# Higilabor Agents

> **Higilabor Growth OS** — sistema multiagente para operação de marketing, autoridade, conteúdo, SEO e vendas consultivas da Higilabor.

## Objetivo

Transformar diagnósticos estratégicos em execução contínua por agentes especializados, com contexto institucional centralizado, versionamento em GitHub e outputs reaproveitáveis.

## Estrutura do Repositório

```
higilabor-agents/
├─ agents/
│ ├─ 00-orquestrador/
│ ├─ 01-depoimentos/
│ ├─ 02-cases/
│ ├─ 03-seo-local/
│ ├─ 04-linkedin/
│ └─ 05-blog/
├─ context/
│ ├─ empresa.md
│ ├─ posicionamento.md
│ ├─ servicos.md
│ ├─ publico-alvo.md
│ ├─ concorrencia.md
│ ├─ metas.md
│ └─ restricoes.md
├─ tasks/
│ ├─ exemplo-plano-90-dias.json
│ ├─ exemplo-depoimentos.json
│ ├─ exemplo-cases.json
│ ├─ exemplo-seo.json
│ ├─ exemplo-linkedin.json
│ └─ exemplo-blog.json
├─ outputs/
│ └─ .gitkeep
├─ scripts/
│ ├─ run_agent.py
│ └─ orchestrate.py
├─ .env.example
├─ .gitignore
├─ requirements.txt
└─ README.md
```

## Como funciona

1. Cada agente possui: missão, regras, entradas esperadas, saídas obrigatórias e critérios de qualidade.
2. O contexto institucional da Higilabor fica centralizado em `/context`.
3. Cada tarefa é definida em um arquivo JSON dentro de `/tasks`.
4. O script `run_agent.py` lê o agente + contexto + tarefa, monta o prompt e salva a saída em `/outputs`.
5. O script `orchestrate.py` executa o Agente 0 e encadeia os demais.

## Payload oficial das tasks

Todas as tasks seguem o mesmo envelope JSON:

```json
{
  "agent_id": "nome-do-agente",
  "schema_version": "1.0",
  "task": "descrição opcional da tarefa",
  "inputs": {}
}
```

- **`agent_id`**: ID do agente alvo (ex: `04-linkedin`)
- **`schema_version`**: sempre `"1.0"` nesta versão
- **`task`**: descrição legivel da tarefa (opcional, para rastreabilidade)
- **`inputs`**: objeto com os campos definidos no `input-schema.json` do agente

Os campos obrigatórios de `inputs` para cada agente estão documentados em `agents/<id>/input-schema.json`. Veja exemplos prontos em `tasks/`.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Preencha OPENAI_API_KEY no .env
```

## Rodar um agente

```bash
python scripts/run_agent.py tasks/exemplo-depoimentos.json
python scripts/run_agent.py tasks/exemplo-linkedin.json
python scripts/run_agent.py tasks/exemplo-blog.json
```

## Rodar o orquestrador

```bash
python scripts/orchestrate.py tasks/exemplo-plano-90-dias.json
```

## Agentes

| ID | Agente | Função |
|----|--------|--------|
| 00 | Orquestrador | Plano estratégico e encadeamento |
| 01 | Depoimentos | Prova social e coleta |
| 02 | Cases | Narrativas comerciais |
| 03 | SEO Local | Páginas e pautas com intenção local |
| 04 | LinkedIn | Autoridade técnica e posts |
| 05 | Blog | Conteúdo evergreen e SEO |

## Convenções

- `main`: versão estável
- `dev`: testes e desenvolvimento
- `outputs` são salvos por data (`YYYY-MM/`)
- alterações em agentes devem ser revisadas por PR

## Próximos agentes (v2)

- 06-youtube
- 07-lead-magnet
- 08-parcerias-juridicas
- 09-newsletter
- 10-verticalizacao-setorial
