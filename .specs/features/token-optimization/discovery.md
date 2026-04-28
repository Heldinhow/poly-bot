# Discovery: Token Optimization & Execution Visibility

## Problema do Usuário

- **Quem sofre:** Operador do bot (Helder)
- **O que acontece:** O bot consome ~49% das requests do MiniMax em 5 horas (735/1500)
- **Evidência:**
  - 20 execuções totais, 10 completadas
  - 380,218 tokens de input usados (média de 38,000 por execução)
  - Cada execução do Claude Code consome 34,000-70,000 tokens porque spawna uma sessão completa com MCP servers, plugins, hooks, etc.
  - Scan roda a cada 60 segundos, analisando TODOS os mercados filtrados
- **Frequência:** A cada 60 segundos (scan interval)

## Causa Raiz

1. **Claude Code é overkill para análise simples:** O CLI spawna uma sessão completa com:
   - MCP servers (pencil, exa, context7, memory, etc.)
   - Plugins (oh-my-claudecode, everything-claude-code, warp)
   - Hooks de startup
   - Contexto de sessão anterior
   - Tudo isso para uma simples estimativa de probabilidade!

2. **Filtros estáticos muito amplos:**
   - `max_price: 0.35` (underdog até 35%)
   - `max_odds: 20.0` (odds até 20:1)
   - `scan_interval_secs: 60` (a cada minuto)
   - Resultado: muitos mercados passam para análise AI

3. **Sem visibilidade:** Não consigo ver:
   - Qual prompt foi enviado para o agent
   - Qual agent específico analisou cada mercado
   - Quanto cada análise custou em tokens

## Hipótese

Se substituirmos o Claude Code por chamadas diretas à API do MiniMax (que já temos configurada) e apertarmos os filtros estáticos, podemos:
- Reduzir consumo de tokens em 90%+ (de ~38,000 para ~2,000 por análise)
- Manter qualidade de análise (usando prompts focados)
- Adicionar visibilidade completa do fluxo

## Métricas de Sucesso

| Métrica | Baseline (atual) | Target | Como medir | Prazo |
|---------|------------------|--------|------------|-------|
| Tokens por análise | ~38,000 | <3,000 | Logs de execução | 1 dia |
| Análises por hora | ~10 | <3 | Contagem de execuções | 1 dia |
| Requests MiniMax/dia | ~735 (5h) | <200 (24h) | Dashboard MiniMax | 1 dia |
| Visibilidade | 0% | 100% | Logs com prompt+agent+resultado | 1 dia |

## Critério de Sucesso/Falha

- **Sucesso:** <200 requests/dia com análise de qualidade
- **Pivotar:** Se qualidade cair muito, ajustar prompts
- **Abandonar:** Se API do MiniMax não suportar o formato necessário

## MVP Scope

### Inclui:
1. **Filtros estáticos mais rigorosos** (max_price, max_odds, odds sweet spot)
2. **Usar MiniMax API direto** em vez de Claude Code CLI
3. **Logging detalhado** (prompt, agent, resultado, tokens)
4. **Menos scans** (intervalo maior)

### NÃO inclui (depois):
- Análise em batch (múltiplos mercados por prompt)
- Cache de resultados
- Rate limiting inteligente

## Alternativas Consideradas

- **Claude Code com --no-mcp:** Não suportado, CLI sempre carrega plugins
- **OpenCode CLI:** Mesmo problema, overhead de sessão
- **Prompt engineering para reduzir tokens:** Marginal, não resolve o overhead do CLI
- **Não fazer nada:** Risco de esgotar quota e perder oportunidades

## Decisão de Design

**Usar MiniMax API direto** (via `httpx`) em vez de qualquer CLI de coding agent.

### Por quê?
1. **Controle total do contexto:** Enviamos apenas o prompt necessário
2. **Sem overhead de sessão:** Sem MCP, sem plugins, sem hooks
3. **Custo previsível:** ~2,000 tokens por análise vs ~38,000 atual
4. **Mais rápido:** Resposta em 2-5s vs 30-70s com Claude Code
5. **Mesma qualidade:** O modelo MiniMax pode estimar probabilidades tão bem quanto Claude

### Trade-off:
- Perdemos capacidade de usar tools (web search, bash)
- Ganhamos economia massiva de tokens e velocidade
- Para estimar probabilidade, não precisamos de tools - o modelo já tem conhecimento suficiente

## Prioridade de Produto

Impacto: **Alto** × Confiança: **Alta** / Esforço: **Baixo**

Score: **H×A/L = Muito Alta** — deve ser a primeira coisa a fazer
