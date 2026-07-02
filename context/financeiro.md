# Contexto Financeiro — DRE Gerencial da Higilabor

> Fonte de verdade para consolidação do resultado financeiro da Higilabor a partir dos dados exportados do ERP.
> Usado exclusivamente pelo Agente 06 (Financeiro DRE). Não se aplica aos agentes de conteúdo.

---

## Estrutura padrão da DRE gerencial

A cascata segue sempre esta ordem, da receita bruta ao lucro líquido:

1. **Receita Bruta**
2. (–) **Deduções** (impostos sobre vendas, devoluções, descontos)
3. (=) **Receita Líquida**
4. (–) **Custos (CPV/CSP)**
5. (=) **Lucro Bruto**
6. (–) **Despesas Operacionais** (comerciais, administrativas, outras)
7. (=) **EBITDA**
8. (–) **Depreciação e Amortização**
9. (=) **EBIT (Resultado Operacional)**
10. (+/–) **Resultado Financeiro** (receitas – despesas financeiras)
11. (–) **Impostos sobre o Lucro** (IR/CSLL)
12. (=) **Lucro Líquido**

---

## Definições

- **Receita Líquida** = Receita Bruta – Deduções
- **Lucro Bruto** = Receita Líquida – Custos (CPV/CSP)
- **EBITDA** = Lucro Bruto – Despesas Operacionais (lucro antes de juros, impostos, depreciação e amortização)
- **EBIT** = EBITDA – Depreciação e Amortização
- **Lucro Líquido** = EBIT +/– Resultado Financeiro – Impostos sobre o Lucro

### Margens (sempre sobre a Receita Líquida)

- **Margem Bruta** = Lucro Bruto ÷ Receita Líquida
- **Margem EBITDA** = EBITDA ÷ Receita Líquida
- **Margem Líquida** = Lucro Líquido ÷ Receita Líquida

---

## Limites e thresholds para alertas

| Indicador | Limite | Severidade sugerida |
|-----------|--------|--------------------|
| Margem bruta | abaixo de 40% | atenção |
| Margem bruta | abaixo de 30% | crítico |
| Margem EBITDA | abaixo de 15% | atenção |
| Margem EBITDA | abaixo de 8% | crítico |
| Margem líquida | negativa (prejuízo) | crítico |
| Despesas operacionais | acima de 35% da receita líquida | atenção |
| EBITDA vs meta | abaixo da meta em mais de 10% | atenção |
| EBITDA vs meta | abaixo da meta em mais de 25% | crítico |
| Receita líquida vs período anterior | queda superior a 10% | atenção |

Alertas positivos (severidade `info`) devem destacar superação de meta ou crescimento relevante vs período anterior.

---

## Regras de consolidação

- Nunca inventar números — usar apenas os dados exportados do ERP e informados na task.
- Valores monetários com 2 casas decimais, na moeda informada (padrão BRL).
- Percentuais de margem calculados sobre a receita líquida.
- Variações percentuais calculadas como (atual – referência) ÷ referência × 100.
- A cascata da DRE deve fechar aritmeticamente: cada subtotal é resultado direto das linhas anteriores.
