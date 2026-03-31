# Higilabor Agents

> **Higilabor Growth OS** — sistema de agentes de IA para gerar prova social, cases, SEO local e conteúdo comercial com consistência e escala.

## Estrutura do Repositório

```
higilabor-agents/
├─ agents/              ← o que cada agente sabe fazer
│  ├─ 00-orquestrador/
│  ├─ 01-depoimentos/
│  ├─ 02-cases/
│  └─ 03-seo-local/
├─ context/             ← quem é a Higilabor de verdade
│  ├─ empresa.md
│  ├─ posicionamento.md
│  ├─ servicos.md
│  ├─ publico-alvo.md
│  ├─ concorrencia.md
│  └─ restricoes.md
├─ tasks/               ← o pedido concreto
│  └─ exemplo-task.json
├─ outputs/             ← o que foi produzido
│  └─ 2026-03/
├─ scripts/             ← quem executa
│  ├─ run_agent.py
│  └─ orchestrate.py
├─ .env
├─ requirements.txt
└─ README.md
```

## Como Funciona

1. **`agents/`** — cada pasta é um agente com contrato claro: missão, entradas, saídas, regras.
2. **`context/`** — arquivos fixos com a identidade real da Higilabor. Todo agente lê isso.
3. **`tasks/`** — o pedido concreto em JSON: qual agente rodar e com quais parâmetros.
4. **`scripts/`** — junta agente + contexto + tarefa e chama o modelo da OpenAI.
5. **`outputs/`** — respostas salvas por data para rastreabilidade.

## Como Rodar

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar chave da OpenAI
export OPENAI_API_KEY="sua-chave-aqui"

# Rodar um agente
python scripts/run_agent.py
```

## Agentes Disponíveis

| # | Agente | Missão |
|---|--------|--------|
| 00 | Orquestrador | Coordena os demais agentes e quebra metas em execuções |
| 01 | Depoimentos | Coleta e transforma depoimentos em prova social de alta conversão |
| 02 | Cases | Estrutura casos de sucesso em materiais comerciais |
| 03 | SEO Local | Gera conteúdo otimizado para ranqueamento local da Higilabor |

## Fluxo de Trabalho

```
Fase 1 (simples): rodar agentes manualmente via run_agent.py
Fase 2 (semi): tasks padronizadas + outputs organizados + PR review
Fase 3 (orquestração): agente 00 quebrando metas + execução encadeada
```

## Branches

- `main` — agentes estáveis e aprovados
- `dev` — testes e experimentos
- `feat/agente-nome` — novo agente em desenvolvimento
- `fix/agente-nome` — correção de prompt ou regra

---

*GitHub é o repositório normativo: auditoria, versionamento e governança. O agente é a combinação de agent.md + context + task.json + script + modelo.*
