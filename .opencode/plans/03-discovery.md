# Discovery: Agent Runtime

## Problema do Usuário

- **Quem sofre**: O operador do bot que quer analisar mercados além do escopo dos 3 agents legados (Sports, Esports, Odds)
- **O que acontece**: Hoje os agents de análise são embarcados em código Python e usam apenas conhecimento estático do LLM (MiniMax). Isso limita o bot a tópicos onde o LLM já é bem informado. Mercados de clima, commodities, política com dados recentes, etc. não podem ser analisados com precisão.
- **Evidência**: O roadmap identifica explicitamente essa limitação. Os agents atuais não têm acesso a web search, APIs externas ou dados em tempo real.
- **Frequência**: A cada scan cycle (a cada 5 minutos), mercados potencialmente valiosos são ignorados porque nenhum agent legado consegue avaliá-los com dados reais.

## Hipótese

Acreditamos que substituir os agents estáticos embarcados por um **runtime de coding agents configuráveis** vai aumentar o ROI em >15% para o operador, porque cada mercado ganhará um agent dedicado que pode pesquisar dados reais antes de calcular probabilidades.

## Métricas de Sucesso

| Métrica | Baseline (atual) | Target | Como medir | Prazo |
|---------|------------------|--------|------------|-------|
| ROI mensal | baseline atual | +15% | Portfolio stats no DB | 4 semanas |
| Taxa de acerto (underdog) | baseline atual | +10% | resolved bets stats | 4 semanas |
| Mercados analisáveis | ~30% (sports/esports/odds) | >80% | contagem de execuções por categoria | 2 semanas |
| Tasks completadas com sucesso | 0% (não existe) | >90% | execution_logs status | 2 semanas |
| Latência task dispatch | N/A | <2s | timestamp diff (queued → started) | 1 semana |

## Critério de Sucesso/Falha

- **Sucesso**: ROI atinge +15% em 4 semanas com >90% de tasks completadas
- **Pivotar**: Se taxa de acerto não melhorar em 2 semanas, revisar qualidade dos prompts/skills
- **Abandonar**: Se <50% de tasks completam com sucesso após 3 semanas, revisar arquitetura do runtime

## MVP Scope (menor experimento que valida hipótese)

- Inclui:
  - 1 runtime funcional (Claude Code)
  - 1 skill funcional (weather)
  - Tracking básico (execution_logs)
  - Scanner despachando 1 mercado de clima real para o agent
  - Fallback automático para agents legados se falhar
- NÃO inclui:
  - Dashboard completo (apenas API endpoints)
  - Todos os 4 runtimes (Claude Code é suficiente para validar)
  - Skills de commodity/news (weather basta para MVP)
  - Classificador inteligente de mercado (matching manual no MVP)

## Alternativas Consideradas

- **Opção A — Manter agents legados e apenas melhorar prompts**: Descartada porque não resolve o problema fundamental de falta de dados reais
- **Opção B — Usar APIs diretamente no código Python (sem agent runtime)**: Descartada porque perde flexibilidade — cada novo tipo de mercado exigiria mudança de código, recompilação e deploy. O runtime de agents permite adicionar skills via dashboard.
- **Opção C — LangChain/LangGraph em vez de coding agents**: Descartada porque o foco é research com tools reais (browser, bash), não apenas chain de LLM calls. Coding agents têm acesso ao sistema operacional.
- Não fazer nada: Risco de continuar perdendo oportunidades em mercados não-sports e eventual obsolescência do bot

## Prioridade de Produto

Impacto: **Alto** × Confiança: **Média** / Esforço: **Alto**
Score: Alto × Média / Alto = **Médio-Alto**

Justificativa: O impacto é alto porque expande drasticamente o endereçável market do bot. A confiança é média porque a tecnologia de coding agents é madura mas a integração com o bot atual é não-trivial. O esforço é alto porque toca DB, backend, frontend e infra.
