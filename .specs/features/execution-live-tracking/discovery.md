# Discovery: Execution Live Tracking

## Problema do Usuário
- **Quem sofre:** Operador do bot (quem monitora o dashboard)
- **O que acontece:** Hoje a ExecutionsPage mostra cards estáticos. Para ver o que o agent fez passo a passo, precisa expandir o card e esperar o polling de 5s carregar os steps. Não há feedback visual em tempo real do que o agent está fazendo (tool calls, thinking, outputs). A experiência é reativa e desconectada — o usuário não consegue acompanhar o raciocínio do agent conforme ele acontece.
- **Evidência:** Comparado ao multica (onde o AgentLiveCard mostra streaming em tempo real com timeline colorida), a ExecutionsPage atual é estática e oferece pouca visibilidade.
- **Frequência:** Diário — o operador acompanha múltiplas execuções por scan.

## Hipótese
Acreditamos que substituir os ExecutionCards estáticos por LiveExecutionCards com streaming WebSocket em tempo real (steps coloridos por tipo, auto-scroll, output final) vai melhorar a visibilidade e confiança do operador nas decisões do bot, porque ele poderá acompanhar o raciocínio do agent passo a passo, como se estivesse vendo um terminal ao vivo.

## Métricas de Sucesso
| Métrica | Baseline | Target | Como medir | Prazo |
|---------|----------|--------|------------|-------|
| Tempo para entender uma execução | ~30s (expandir + esperar poll) | <5s (streaming imediato) | Observação | 1 semana |
| Steps visíveis em tempo real | 0 (só polling) | 100% (WebSocket) | Logs de WS | Imediato |

## Critério de Sucesso/Falha
- **Sucesso:** Steps aparecem no card em <500ms após o agent produzi-los. Timeline colorida e output final funcionam.
- **Pivotar:** Se WebSocket não for viável, usar polling mais agressivo (1s) como fallback.

## MVP Scope
- Inclui: WebSocket endpoint por execution, LiveExecutionCard com timeline, auto-scroll, output final
- NÃO inclui: Transcript dialog full-screen (pode vir depois), export de logs, filtros avançados

## Alternativas Consideradas
- Fazer polling 1s em vez de WebSocket: descartada porque sobrecarrega o servidor com múltiplas execuções simultâneas
- Usar Server-Sent Events: descartada porque já temos infra de WebSocket no projeto
- Não fazer nada: risco de operador perder confiança no bot por falta de visibilidade

## Prioridade de Produto
Impacto: Alto × Confiança: Alta / Esforço: Médio
Score: Alta — referência clara (multica), infra de WS já existe, mudança focada em um componente.
