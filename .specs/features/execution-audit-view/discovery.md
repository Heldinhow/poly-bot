# Discovery: Execution Audit Trail View

## Problema do Usuário

- **Quem sofre:** Operador do bot de trading que precisa entender por que cada aposta foi feita ou rejeitada
- **O que acontece:** Ao expandir um execution card na tela de Executions, não há visibilidade sobre os **truth claims** (fatos usados pelo agente) e **decision factors** (edge, probabilities, reject_reason)
- **Evidência:** A tela mostra reasoning textual mas não estrutura os fatos nem os parâmetros da decisão
- **Frequência:** Toda vez que o operador analisa uma execução

## Hipótese

Adicionar Truth Claims + Decision Factors como секções expandidas no ExecutionCard vai permitir ao operador validar se o agente usa fatos corretos e se a decisão está alinhada com o edge esperado.

## Métricas de Sucesso

| Métrica | Baseline | Target | Como medir |
|---------|----------|--------|------------|
| Tempo para entender decisão | ~2min | <30s | Observação direta |
| % executions com truth_claims | 0% | >80% | Query truth_claims |

## Critério de Sucesso
- **Sucesso:** Operador vê truth_claims + decision factors em < 30s
- **Pivotar:** < 50% com claims após 2 semanas → revisar prompt
- **Abandonar:** Não usado após 1 mês

## MVP Scope
- Hook `useTruthClaims(executionId)` + `useDecisionFactors(executionId)`
- секция "Truth Claims" no ExecutionCard
- секção "Decision Factors" no ExecutionCard (edge badge, reject_reason)
- Badges visuais: decision level HIGH/MEDIUM/LOW/REJECT

## Prioridade de Produto
Impacto: **Alto** × Confiança: **Alta** / Esforço: **Médio** = Score: **6**