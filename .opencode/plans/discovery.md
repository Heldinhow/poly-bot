# Discovery: Persistence & Trading Mode

## Problema do Usuário
- **Quem sofre**: O operador do bot (eu) que precisa auditar, analisar e escalar o sistema
- **O que acontece**: Todas as apostas são salvas em CSV (`paper_trades.csv`), sem versionamento, sem queries complexas, sem concorrência segura. Não há distinção clara entre apostas simuladas e futuras apostas reais.
- **Evidência**: CSV de 6 linhas, sem indices, sem schema enforcement, race conditions potenciais se o bot escalar. Impossível fazer analytics eficiente.
- **Frequência**: A cada ciclo do bot (a cada 5 minutos) o CSV é reescrito por completo.

## Hipótese
Acreditamos que migrar a persistência para PostgreSQL + Redis e introduzir um campo explícito de trading mode vai permitir:
- Analytics e auditoria robustas sobre performance
- Transição segura e reversível entre paper e live trading
- Cache de dados de mercado para reduzir chamadas de API
- Fundação sólida para escalar o bot sem perda de dados

## Métricas de Sucesso
| Métrica | Baseline (atual) | Target | Como medir | Prazo |
|---------|------------------|--------|------------|-------|
| Tempo de escrita por bet | ~50ms (CSV rewrite) | <20ms | Timer no código | 1 semana |
| Tempo de leitura de open bets | ~10ms (CSV parse) | <5ms | Timer no código | 1 semana |
| Consistência de dados | Nenhuma garantia | ACID | Testes de integração | 1 semana |
| Downtime na migração | N/A | Zero | Log de execução | 1 dia |

## Critério de Sucesso/Falha
- **Sucesso**: Todas as bets existentes migradas, novas bets persistindo em PostgreSQL, Redis cache ativo, modo paper funcionando identicamente ao anterior
- **Pivotar**: Se PostgreSQL adicionar complexidade demais para um bot single-threaded, avaliar SQLite
- **Abandonar**: Não aplicável — persistência é obrigatória para live trading

## MVP Scope
- Inclui: PostgreSQL schema, Redis cache para dados de mercado, campo `trading_mode`, ENV toggle, migração de CSV existente
- NÃO inclui: Live trading execution, wallet integration, circuit breakers

## Alternativas Consideradas
- **SQLite**: descartado porque queremos analytics concorrentes e possível multi-instância no futuro
- **MongoDB**: descartado — dados são fortemente estruturados, relacional é mais natural
- **Manter CSV + adicionar JSON**: descartado — não resolve concorrência nem queries

## Prioridade de Produto
Impacto: Alto × Confiança: Alta / Esforço: Médio
Score: Alta (fundação para todos os próximos milestones)
