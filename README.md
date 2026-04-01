# Higilabor Agents

> **Higilabor Growth OS** — máquina de produção de conteúdo comercialmente útil para geração de demanda qualificada e aumento de vendas pela internet.

![CI](https://github.com/octavioadv/higilabor-agents/actions/workflows/ci.yml/badge.svg)

## Missão oficial

Transformar o repositório da Higilabor em uma operação de conteúdo focada em resultado comercial:

- **Páginas de SEO** por serviço (ranqueamento orgânico)
- **Posts de LinkedIn** com autoridade técnica
- **Artigos de blog** evergreen e de intenção
- **Conteúdo recorrente sobre eSocial + SST**
- **Geração de demanda qualificada** e aumento de pedidos de orçamento pela internet

## North Star KPI

> **Pedidos de orçamento qualificados vindos do orgânico por mês**

Meta inicial: **8/mês**. Esse KPI obriga SEO, LinkedIn, blog e eSocial/SST a convergirem para resultado comercial — não para vaidade de alcance.

→ KPIs completos, fórmulas, metas e fontes de dados: [`context/kpis.md`](context/kpis.md)

## Regra-mãe de priorização

Nenhuma task entra no ciclo se não responder claramente a pelo menos uma destas perguntas:

1. Isso aumenta a chance de **ranqueamento orgânico**?
2. Isso aumenta a **autoridade digital** da Higilabor?
3. Isso aumenta a chance de **contato comercial qualificado**?

Se a resposta for "não" para todas, vai para backlog.

## Escopo da V1

**Motores prioritários:**

| Motor | Agente | Meta mensal |
|-------|--------|-------------|
| SEO por serviço | 03-seo-local | 2 páginas/mês |
| LinkedIn | 04-linkedin | 8 posts/mês |
| Blog | 05-blog | 4 artigos/mês |
| eSocial + SST | 04 + 05 | 4 peças/mês |

**Escopo secundário:** Depoimentos (01) e Cases (02) continuam como ativos de apoio à conversão — só fazem sentido se reforçarem páginas SEO, posts ou confiança comercial.

## Estrutura do Repositório

```
higilabor-agents/
├─ agents/
│  ├─ 00-orquestrador/   # Plano estratégico e encadeamento
│  ├─ 01-depoimentos/    # Prova social e coleta
│  ├─ 02-cases/          # Narrativas comerciais
│  ├─ 03-seo-local/      # Páginas e pautas com intenção local
│  ├─ 04-linkedin/       # Autoridade técnica e posts
│  └─ 05-blog/           # Conteúdo evergreen e SEO
├─ context/              # Contexto institucional centralizado
│  └─ kpis.md            # ← North Star KPI, metas e regras operacionais
├─ tasks/                # Tasks JSON com envelope padronizado
├─ tests/                # Testes automatizados (pytest)
├─ outputs/              # Saídas organizadas por YYYY-MM/
├─ scripts/
│  ├─ run_agent.py       # Executa um agente individual
│  └─ orchestrate.py     # Executa agente 00 e encadeia sub-agentes
├─ .github/workflows/ci.yml
├─ .env.example
├─ requirements.txt
└─ README.md
```

## Quick Start — Passo a passo real

### 1. Clonar e configurar

```bash
git clone https://github.com/octavioadv/higilabor-agents.git
cd higilabor-agents
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edite `.env` e preencha sua chave do Google Gemini:

```
GEMINI_API_KEY=sua-chave-aqui
GEMINI_MODEL=gemini-2.5-flash
```

### 2. Rodar um agente individual

```bash
python scripts/run_agent.py --task tasks/exemplo-depoimentos.json
```

O que acontece:
1. Valida o envelope da task (agent_id, schema_version, inputs)
2. Valida os inputs contra o `input-schema.json` do agente
3. Monta o prompt com agent.md + context/ + templates + output-schema
4. Chama a API do Google Gemini
5. Parseia o JSON da resposta
6. Valida o output contra o `output-schema.json` do agente
7. Salva artefatos em `outputs/YYYY-MM/run-TIMESTAMP-AGENTE/`:
   - `raw.md` — resposta bruta do modelo
   - `parsed.json` — JSON validado
   - `meta.json` — metadados (modelo, duração, sucesso/erro)

Se a task ou o output forem inválidos, a execução falha com exit code 1 e salva o erro no `meta.json`.

### 3. Rodar o orquestrador (fluxo completo)

```bash
python scripts/orchestrate.py --task tasks/exemplo-plano-90-dias.json
```

O que acontece:
1. Executa o Agente 00 (orquestrador) para gerar um `plano_execucao`
2. Para cada etapa do plano, gera uma subtask JSON com base no input-schema do agente alvo
3. Executa cada sub-agente na ordem definida
4. Salva tudo em `outputs/YYYY-MM/round-TIMESTAMP/manifest.json`

### 4. Rodar os testes

```bash
pip install pytest
pytest tests/ -v
```

Os testes cobrem:
- **Validação de input**: tasks sem campos obrigatórios falham antes da API
- **Validação de output**: respostas que não obedecem ao schema são rejeitadas
- **Execução com mock**: fluxo completo sem chamar a API real
- **Orquestrador**: geração de subtasks e validação do plano de execução

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
- **`task`**: descrição legível da tarefa (opcional, para rastreabilidade)
- **`inputs`**: objeto com os campos definidos no `input-schema.json` do agente

Os campos obrigatórios de `inputs` para cada agente estão documentados em `agents/<id>/input-schema.json`. Veja exemplos prontos em `tasks/`.

## Agentes

| ID | Agente | Função | Prioridade V1 |
|----|--------|--------|--------------|
| 00 | Orquestrador | Plano estratégico e encadeamento | ● núcleo |
| 01 | Depoimentos | Prova social e coleta | ○ apoio |
| 02 | Cases | Narrativas comerciais | ○ apoio |
| 03 | SEO Local | Páginas e pautas com intenção local | ● motor |
| 04 | LinkedIn | Autoridade técnica e posts | ● motor |
| 05 | Blog | Conteúdo evergreen e SEO | ● motor |

## Definição de pronto (v1)

- [ ] Input inválido falha antes de qualquer chamada à API
- [ ] Output inválido é rejeitado antes de ser aceito como resultado
- [ ] Task válida gera output validado e artefatos salvos
- [ ] Orquestrador devolve obrigatoriamente: north_star_kpi, kpis_secundarios, metas numéricas, prazo, fonte de dado e responsável
- [ ] Qualquer pessoa consegue clonar, configurar `.env` e rodar um fluxo básico

## Convenções

- `main`: versão estável
- Branches: `feat/`, `test/`, `fix/`
- `outputs` são salvos por data (`YYYY-MM/`)
- Alterações em agentes devem ser revisadas por PR
- CI roda automaticamente em push e PR para `main`

## Próximos agentes (v2)

- 06-youtube
- 07-lead-magnet
- 08-parcerias-juridicas
- 09-newsletter
- 10-verticalizacao-setorial
