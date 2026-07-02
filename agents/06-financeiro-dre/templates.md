# Estrutura da mensagem de Slack (mrkdwn)

Modelo de referência para o campo `mensagem_slack.texto`. Usar mrkdwn do Slack (`*negrito*`, `>` citação, emojis). Nunca inventar números — preencher apenas com os valores consolidados.

```
:bar_chart: *DRE Gerencial — {periodo.label}* ({moeda})

*Resumo*
> Receita Líquida: *{receita_liquida}*
> Lucro Bruto: *{lucro_bruto}*  (margem bruta {margem_bruta}%)
> EBITDA: *{ebitda}*  (margem EBITDA {margem_ebitda}%)
> Lucro Líquido: *{lucro_liquido}*  (margem líquida {margem_liquida}%)

*Variações*
> vs meta — Receita {vs_meta.receita_liquida_pct}% · EBITDA {vs_meta.ebitda_pct}% · Lucro {vs_meta.lucro_liquido_pct}%
> vs mês anterior — Receita {vs_periodo_anterior.receita_liquida_pct}% · EBITDA {vs_periodo_anterior.ebitda_pct}% · Lucro {vs_periodo_anterior.lucro_liquido_pct}%

*Alertas*
> :red_circle: {alerta_critico}
> :warning: {alerta_atencao}
> :information_source: {alerta_info}
```

## Convenções de emojis
- `:bar_chart:` cabeçalho da DRE
- `:red_circle:` alerta crítico
- `:warning:` alerta de atenção
- `:information_source:` alerta informativo
- `:chart_with_upwards_trend:` / `:chart_with_downwards_trend:` variação positiva / negativa

## Regras de formatação
- valores monetários com 2 casas e na moeda informada
- percentuais com 1 casa decimal
- se não houver alertas, exibir `> :white_check_mark: Sem alertas no período`
- manter o texto enxuto e executivo — leitura em menos de 30 segundos
