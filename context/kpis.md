# KPIs Oficiais do Repositório

> Este arquivo é a fonte de verdade dos indicadores de desempenho do Higilabor Growth OS.
> Todo agente e toda task deve respeitar esta hierarquia antes de planejar qualquer ação.

---

## North Star KPI

**Pedidos de orçamento qualificados vindos do orgânico por mês**

Este é o KPI central porque ele obriga SEO, LinkedIn, blog e eSocial/SST a convergirem para resultado comercial — não para vaidade de alcance.

### Definição

Conta quantos contatos, no mês:
- vieram de canal orgânico (Google, blog, LinkedIn orgânico, conteúdo eSocial/SST)
- pediram orçamento, diagnóstico ou reunião
- pertencem ao ICP da Higilabor (empresas com CNPJ, acima de 10 funcionários, setores com obrigatoriedade de SST)

### O que NÃO conta

- curtida
- visita sem CTA acionado
- mensagem genérica sem intenção de compra
- lead sem aderência ao ICP

**Meta inicial:** 8/mês  
**Cadência de revisão:** mensal

---

## Hierarquia de KPIs

A leitura correta é sempre nesta ordem. Publicar muito sem pedido de orçamento subindo **não é vitória**.

1. Pedidos de orçamento qualificados do orgânico
2. Taxa de conversão orgânico → contato
3. Sessões orgânicas em páginas comerciais
4. Produção de conteúdo (páginas SEO, posts, artigos, eSocial/SST)

---

## KPIs de Resultado

São os que mandam na operação.

| KPI | Fórmula | Meta inicial | Cadência |
|-----|---------|-------------|----------|
| Pedidos de orçamento qualificados do orgânico | nº de leads qualificados orgânicos no mês | 8/mês | mensal |
| Taxa de conversão orgânico → contato | contatos orgânicos ÷ sessões orgânicas | 1,5% | mensal |
| Taxa de conversão contato → proposta | propostas ÷ contatos qualificados | 35% | mensal |
| Taxa de conversão proposta → venda | contratos ÷ propostas | 25% | mensal |

---

## KPIs de Eficiência

Mostram se o conteúdo está atraindo o público certo.

| KPI | Fórmula | Meta inicial | Cadência |
|-----|---------|-------------|----------|
| Sessões orgânicas em páginas comerciais | sessões nas páginas de serviço | +15% ao mês | mensal |
| CTR orgânico das páginas de serviço | cliques ÷ impressões no Google | 3% | mensal |
| Tempo médio nas páginas de serviço | média por página | 1min30 | mensal |
| Engajamento qualificado no LinkedIn | comentários + compartilhamentos + cliques | 5% por post | semanal |
| Cliques do LinkedIn para site | cliques em links do post | 20/mês | mensal |

---

## KPIs de Produção

Garantem disciplina operacional. São os mínimos viáveis — não o objetivo final.

| KPI | Fórmula | Meta inicial | Cadência |
|-----|---------|-------------|----------|
| Páginas SEO por serviço publicadas | nº de páginas no mês | 2/mês | mensal |
| Posts de LinkedIn publicados | nº de posts no mês | 8/mês | mensal |
| Artigos de blog publicados | nº de artigos no mês | 4/mês | mensal |
| Conteúdos eSocial + SST publicados | nº de peças específicas no mês | 4/mês | mensal |
| Percentual de reaproveitamento | peças derivadas ÷ peças-base | 60% | mensal |

---

## Sinais de Alerta

### 🟢 Sinal verde (no caminho certo)
Acontecem ao mesmo tempo:
- páginas SEO sobem no ranking
- visitas qualificadas às páginas de serviço sobem
- pedidos de orçamento orgânicos sobem

### 🟡 Sinal amarelo (conteúdo bonito mas fraco comercialmente)
Sobem: alcance, curtidas, impressões, visitas genéricas  
**Mas não sobe:** pedido de orçamento qualificado

---

## Regra-Mãe de Priorização

Nenhuma task entra no ciclo se não responder claramente a pelo menos uma destas perguntas:

1. Isso aumenta a chance de **ranqueamento orgânico**?
2. Isso aumenta a **autoridade digital** da Higilabor?
3. Isso aumenta a chance de **contato comercial qualificado**?

Se a resposta for "não" para todas — vai para backlog.

---

## Fontes de Dados

| KPI | Fonte |
|-----|-------|
| Sessões orgânicas | Google Analytics 4 |
| Impressões e CTR | Google Search Console |
| Pedidos de orçamento | CRM / formulário do site |
| Engajamento LinkedIn | LinkedIn Analytics nativo |
| Conversão contato → proposta | Planilha comercial / CRM |

---

## Output obrigatório do Orquestrador (Agente 00)

A cada ciclo, o Agente 00 deve devolver obrigatoriamente:

```json
{
  "north_star_kpi": "Pedidos de orçamento qualificados vindos do orgânico por mês",
  "kpis_secundarios": [
    "Sessões orgânicas em páginas de serviço",
    "Taxa de conversão orgânico -> contato",
    "Posts de LinkedIn publicados",
    "Artigos de blog publicados"
  ],
  "metas": {
    "pedidos_organicos_qualificados_mes": 8,
    "sessoes_organicas_paginas_servico": "crescer 15% ao mês",
    "taxa_conversao_organico_contato": "1,5%",
    "posts_linkedin_mes": 8,
    "artigos_blog_mes": 4
  },
  "prazo": "30 dias (ciclo mensal)",
  "fonte_de_dado": {
    "pedidos_organicos": "CRM / formulário do site",
    "sessoes_organicas": "Google Analytics 4",
    "taxa_conversao": "GA4 + CRM cruzado"
  },
  "responsavel": "gestor do repositório"
}
```
