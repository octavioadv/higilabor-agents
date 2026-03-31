# Roadmap v1 Estável

Este documento define os 5 PRs sequenciais que compõem a v1 estável do higilabor-agents.

Regra: **não comece o próximo PR enquanto o anterior não estiver funcional.**

---

## PR 1 — Contratos e tasks coerentes

**Branch:** `feat/v1-contracts` → `main`  
**Closes:** #1  
**Objetivo:** Fazer todos os agentes 00–05 falarem a mesma língua.

Escopo:
- Padronizar formato das tasks com `agent_id`, `schema_version`, `inputs`
- Alinhar `input-schema.json` e `output-schema.json` de todos os agentes
- Reescrever tasks de exemplo
- Atualizar README com contrato oficial

Definição de pronto: uma task de exemplo válida para cada agente 00–05.

---

## PR 2 — Runner com validação de input e output

**Branch:** `feat/v1-runner-validation` → `main`  
**Closes:** #3  
**Objetivo:** Parar de executar task inválida e parar de aceitar saída solta.

Escopo:
- Runner carrega e valida `input-schema.json` antes da chamada
- Exige saída em JSON estruturado
- Valida output com `output-schema.json`
- Erros mostram qual campo falhou

Definição de pronto: task inválida falha antes da API; task válida executa e gera saída validada.

---

## PR 3 — Artefatos de execução e rastreabilidade

**Branch:** `feat/v1-execution-artifacts` → `main`  
**Closes:** #2  
**Objetivo:** Deixar cada execução auditável.

Escopo:
- Criar `run_id` único por execução
- Salvar `raw.md` (resposta bruta)
- Salvar `parsed.json` (JSON validado)
- Salvar `meta.json` (agente, modelo, timestamp, status, task)
- Estrutura: `outputs/YYYY-MM/run-<id>/`

Definição de pronto: toda execução deixa rastro completo e legível.

---

## PR 4 — Orquestrador real

**Branch:** `feat/v1-orchestration` → `main`  
**Closes:** #4  
**Objetivo:** Fazer o Agente 00 virar orquestrador de verdade.

Escopo:
- `orchestrate.py` executa agente 00
- Lê `plano_execucao` da saída validada
- Gera subtasks automaticamente
- Executa agentes seguintes em ordem
- Registra sucesso/falha por agente

Definição de pronto: uma task mestre gera e executa pelo menos 2 agentes dependentes sem intervenção manual.

---

## PR 5 — Testes mínimos e fechamento da v1

**Branch:** `test/v1-stability` → `main`  
**Closes:** #5  
**Objetivo:** Provar que a v1 funciona de verdade.

Escopo:
- Teste: input inválido falha antes da API
- Teste: output inválido é rejeitado
- Teste: execução simples com task válida
- Teste: fluxo mínimo do orquestrador
- README com exemplo real de execução ponta a ponta
- Pipeline CI/CD (GitHub Actions)

Definição de pronto: qualquer pessoa consegue clonar, configurar `.env` e rodar um fluxo básico.

---

## Marco final

Quando os 5 PRs estiverem merged:
1. Fechar milestone `v1 estável`
2. Criar tag `v1.0.0`
3. Gravar exemplo real no README
4. Abrir backlog da v2
