# Spec: Token Optimization & Execution Visibility

## Requisitos Funcionais

### FR-1: Filtros Estáticos Mais Rigorosos
O scanner deve aplicar filtros mais rigorosos ANTES de chamar qualquer AI:

**Parâmetros atuais:**
- `max_price: 0.35` (underdog até 35%)
- `max_odds: 20.0` (odds até 20:1)

**Novos parâmetros:**
- `max_price: 0.25` (underdog até 25%)
- `max_odds: 10.0` (odds até 10:1)
- `min_odds: 2.0` (odds mínimas 2:1)
- `min_volume: 20000` (volume mínimo $20k)

### FR-2: Usar MiniMax API Direto
Substituir Claude Code CLI por chamadas diretas à API do MiniMax:

**Endpoint:** `POST https://api.minimax.chat/v1/text/chatcompletion_v2`

**Prompt padrão:**
```
You are a probability estimator for prediction markets.

Market: {question}
Yes price: {yes_price}%
No price: {no_price}%
Volume 24h: ${volume}

Estimate the TRUE probability of the "Yes" outcome.

Consider:
- Historical base rates for similar events
- Current market sentiment (price reflects crowd wisdom)
- Time until resolution (sooner = more predictable)

Respond with ONLY a JSON object:
{"probability": 0.XX, "confidence": 0.XX, "reasoning": "brief explanation"}
```

**Modelo:** `MiniMax-M2.7` (já configurado)

### FR-3: Logging Detalhado de Execução
Cada execução deve registrar:

1. **No `execution_logs`:**
   - `agent_name` (nome do agent que analisou)
   - `prompt_used` (prompt enviado)
   - `model_used` (modelo usado)
   - `tokens_input` / `tokens_output`
   - `duration_ms`

2. **No log do scanner:**
   ```
   [AgentRunner] Analyzing: "Will WTI hit $110?"
     Agent: CommodityBot (MiniMax-M2.7)
     Prompt: "You are a probability estimator..."
     Result: probability=0.25, confidence=0.70
     Tokens: 1,234 in / 456 out
     Duration: 2.3s
   ```

### FR-4: Intervalo de Scan Maior
- `scan_interval_secs: 300` (5 minutos em vez de 1)

### FR-5: Cache de Análise (Evitar Re-análises)
Não analisar novamente um mercado que já foi analisado e rejeitado, a menos que o preço tenha mudado significativamente:

**Regras:**
1. Se um mercado foi analisado nos últimos 30 minutos E o preço não mudou mais que 5%, pular
2. Se o preço mudou mais que 5%, re-analisar
3. Se nunca foi analisado, analisar
4. Se foi analisado mas deu erro, tentar novamente após 5 minutos

**Implementação:**
- Tabela `market_analysis_cache` com:
  - `market_id` (PK)
  - `question`
  - `yes_price_at_analysis`
  - `no_price_at_analysis`
  - `probability` (resultado)
  - `confidence`
  - `reasoning`
  - `agent_name`
  - `analyzed_at` (timestamp)
  - `decision` (ACCEPT/REJECT/SKIP)

**Lógica:**
```python
def should_analyze(market) -> bool:
    cache = get_cache(market.id)
    if not cache:
        return True  # Nunca analisado
    
    if cache.decision == "ACCEPT":
        return False  # Já apostado, não re-analisar
    
    # Verificar se preço mudou significativamente
    price_change = abs(market.yes_price - cache.yes_price_at_analysis)
    if price_change < 0.05:
        return False  # Preço estável, não re-analisar
    
    # Preço mudou mais que 5%, re-analisar
    return True
```

## Requisitos Não Funcionais

### NFR-1: Performance
- Análise deve completar em <5 segundos
- Tokens por análise <3,000

### NFR-2: Observabilidade
- 100% das execuções devem ter log completo
- Dashboard deve mostrar prompt, agent, resultado

### NFR-3: Custo
- <200 requests/dia ao MiniMax
- <50,000 tokens/dia

## Acceptance Criteria

1. [ ] Scanner usa filtros mais rigorosos (max_price=0.25, max_odds=10.0)
2. [ ] AgentRunner chama MiniMax API direto em vez de Claude Code
3. [ ] Cada execução loga: agent_name, prompt, resultado, tokens, duração
4. [ ] Dashboard mostra detalhes da execução (prompt, agent, resultado)
5. [ ] Intervalo de scan aumentado para 5 minutos
6. [ ] Consumo de tokens <3,000 por análise
7. [ ] <200 requests/dia ao MiniMax
8. [ ] Cache de análise evita re-análises desnecessárias
9. [ ] Mercados com preço estável (<5% mudança) não são re-analisados

## Dependências

- `config.py` — novos parâmetros de filtro
- `scanner.py` — usar novos filtros + cache
- `agents/runtime/runner.py` — chamar MiniMax API direto
- `db/cache_repository.py` — NOVO: cache de análises
- `db/schema.sql` — nova tabela `market_analysis_cache`
- `api.py` — expor detalhes da execução
- `frontend/src/pages/ExecutionsPage.tsx` — mostrar prompt, agent, resultado

## Edge Cases

1. **MiniMax API falha:** Fallback para legacy agents
2. **Resposta não é JSON válido:** Logar erro, marcar como failed
3. **Mercado sem agent匹配:** Pular, não analisar
4. **Rate limit atingido:** Pausar scan até reset
5. **Preço muda durante análise:** Usar preço no início da análise

## Não Inclui (Future)

- Análise em batch (múltiplos mercados por prompt)
- Cache de resultados por market_id
- Rate limiting inteligente baseado em quota restante
- Suporte a outros modelos (OpenAI, Anthropic direto)
