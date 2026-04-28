# Roadmap: Agent Runtime Especializado em Mercados

## Visão

Evoluir o poly-bot de um conjunto estático de 3 agents analíticos (Sports, Esports, Odds) para um **runtime dinâmico de agents especialistas**, inspirado na arquitetura do Multica. Cada aposta deve spawnar agents de pesquisa contextual que buscam dados externos antes de calcular probabilidades — transformando o bot de um "adivinhador" em um "analista informado".

> **Regra de ouro**: *Sempre que for apostar em algo, pesquisar primeiro. Nenhuma análise acontece no vácuo.*

---

## Motivação

Hoje o poly-bot avalia mercados com base em:
- Dados brutos do Polymarket (preço, volume, data de resolução)
- Conhecimento estático do LLM (treinamento, não dados em tempo real)

Isso funciona para esportes (onde o LLM já conhece times e jogadores), mas falha para mercados que dependem de **dados externos em tempo real**:
- "Temperatura em Seul amanhã" → precisa da previsão do tempo atual
- "Preço do barril de petróleo na sexta" → precisa da cotação atual do WTI/Brent
- "Taxa de desemprego dos EUA" → precisa do último relatório do BLS
- "Vencedor do Oscar" → precisa das odds atuais e buzz crítico

---

## Arquitetura Proposta

### Conceito Central: Task-per-Market + Agent Registry

Adaptamos o padrão Multica de "daemon + runtime" para o contexto do poly-bot:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         scanner.py (orquestrador)                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Para cada mercado promissor:                                │   │
│  │  1. Classifica o tipo de mercado (weather, commodity, etc.)  │   │
│  │  2. Spawna agents de pesquisa especializados                 │   │
│  │  3. Agrega resultados → injeta no prompt do analista         │   │
│  │  4. Executa agents analíticos tradicionais                   │   │
│  │  5. Decision gate com dados enriquecidos                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌──────────┐    ┌──────────┐    ┌──────────┐
            │ Weather  │    │Commodity │    │  News    │
            │ Agent    │    │  Agent   │    │  Agent   │
            └──────────┘    └──────────┘    └──────────┘
```

### Camadas

| Camada | Responsabilidade | Inspiração Multica |
|--------|------------------|-------------------|
| **Agent Registry** | Cataloga agents disponíveis, suas capabilities e triggers | `server/pkg/agent/models.go` — registro dinâmico de providers |
| **Market Classifier** | Determina qual(is) agent(s) de pesquisa são necessários para um mercado | Task dispatch do daemon |
| **Research Agents** | Executam pesquisa externa (APIs, web scraping) em paralelo | Backends especializados (claude, codex, etc.) |
| **Analysis Agents** | Recebem dados enriquecidos e calculam probabilidades | `BaseAgent` atual com prompt dinâmico |
| **Result Aggregator** | Combina múltiplas fontes em um contexto unificado | `executeAndDrain()` + merge de usage |
| **Decision Gate** | Avalia edge com probabilidade ajustada pelos dados reais | `decision.py` com inputs enriquecidos |

---

## Fases de Implementação

### Fase 1: Agent Registry e Classificação de Mercado (Semana 1-2)

**Objetivo**: Saber *qual* agent chamar para *qual* mercado.

#### 1.1 Criar `agents/registry.py`

Registro central onde cada agent declara:
- `name`: identificador único
- `description`: o que o agent faz
- `triggers`: lista de palavras-chave/gatilhos que ativam este agent
- `required_apis`: quais APIs externas ele usa
- `priority`: ordem de execução (research antes de analysis)

```python
# Exemplo de registro
AGENT_REGISTRY = {
    "weather_researcher": {
        "name": "WeatherResearcher",
        "description": "Busca previsão do tempo para cidades específicas",
        "triggers": ["temperatura", "clima", "tempo", "weather", "chuva", "neve", "celsius", "fahrenheit"],
        "required_apis": ["OPENWEATHER_API_KEY"],
        "category": "research",
        "priority": 1,
    },
    "commodity_researcher": {
        "name": "CommodityResearcher", 
        "description": "Busca cotações atuais de commodities (petróleo, ouro, etc.)",
        "triggers": ["petróleo", "barril", "ouro", "prata", "commodity", "oil", "gold", "wti", "brent"],
        "required_apis": ["ALPHA_VANTAGE_API_KEY"],
        "category": "research",
        "priority": 1,
    },
    # ... etc
}
```

#### 1.2 Criar `agents/classifier.py`

Classifica um mercado com base na `question` e `description`:

```python
class MarketClassifier:
    def classify(self, market_question: str) -> list[str]:
        """Retorna lista de agent_ids necessários para este mercado."""
        # 1. Matching por keywords (rápido, deterministico)
        # 2. Fallback: LLM classifica se keywords não baterem
```

**Entregável**: Dado "Temperatura máxima em Seul amanhã", retorna `["weather_researcher"]`.

---

### Fase 2: Research Agents — Framework de Pesquisa (Semana 3-4)

**Objetivo**: Agents que buscam dados reais, não apenas "pensam".

#### 2.1 Base para Research Agents

Criar `agents/research_base.py`:

```python
class ResearchAgent(BaseAgent):
    """Agent especializado em buscar dados externos, não em calcular probabilidades."""
    
    async def research(self, context: dict) -> ResearchResult:
        """Executa pesquisa e retorna dados estruturados."""
        raise NotImplementedError
    
    async def analyze(self, context: dict) -> dict:
        """Research agents não calculam probabilidades — retornam fatos."""
        result = await self.research(context)
        return {
            "type": "research_result",
            "agent": self.name,
            "data": result.to_dict(),
            "confidence": result.confidence,
        }
```

#### 2.2 Implementar Agents Concretos

**WeatherResearcher** (`agents/research/weather.py`):
- Extrai cidade e data do texto do mercado
- Chama OpenWeatherMap / WeatherAPI
- Retorna: temperatura prevista, condições, probabilidade de chuva, fonte

**CommodityResearcher** (`agents/research/commodity.py`):
- Extrai commodity (petróleo, ouro, etc.) do texto
- Chama Alpha Vantage / Yahoo Finance API
- Retorna: preço spot atual, variação 24h/7d, fonte

**NewsResearcher** (`agents/research/news.py`):
- Busca notícias recentes sobre o tema do mercado
- Chama NewsAPI / GNews
- Retorna: headlines recentes, sentimento, fontes

**PoliticalPollResearcher** (`agents/research/polls.py`):
- Para mercados de eleição
- Busca polling averages (FiveThirtyEight, RealClearPolitics)
- Retorna: últimas pesquisas, margem de erro, tendência

**SportsInjuryResearcher** (`agents/research/sports_injuries.py`):
- Para mercados esportivos
- Busca lista de lesionados, escalações confirmadas
- Retorna: jogadores fora, dúvidas, últimas escalações

```python
# Exemplo de resultado estruturado
@dataclass
class ResearchResult:
    query: str                    # o que foi pesquisado
    data: dict                    # dados brutos
    summary: str                  # resumo em linguagem natural
    confidence: float             # 0-1, quão confiável é a fonte
    source: str                   # URL ou identificador da fonte
    timestamp: datetime           # quando a pesquisa foi feita
```

#### 2.3 Configuração de APIs

Adicionar ao `config.py`:

```python
OPENWEATHER_API_KEY: str | None = None
ALPHA_VANTAGE_API_KEY: str | None = None
NEWSAPI_KEY: str | None = None
SPORTS_API_KEY: str | None = None  # TheSportsDB ou similar
```

---

### Fase 3: Integração com Scanner (Semana 5-6)

**Objetivo**: O scanner orquestra research + analysis automaticamente.

#### 3.1 Novo fluxo do Scanner

```python
def scan(self) -> int:
    markets = self._client.fetch_active_markets(limit=200)
    value_bets = self._filter_markets(markets)
    
    for market in value_bets:
        # PASSO NOVO: Classifica e pesquisa
        needed_research = self._classifier.classify(market.question)
        research_results = self._run_research_agents(market, needed_research)
        
        # PASSO EXISTENTE: Análise com contexto enriquecido
        enriched_context = {
            "market": market,
            "research": research_results,  # NOVO!
        }
        ai_probability, ai_analysis = self._run_analysis_agents(enriched_context)
        
        # Decision gate com dados reais
        decision = self._decision_gate.evaluate(...)
```

#### 3.2 `ResearchOrchestrator`

Criar `scanner.py` → método `_run_research_agents()`:

```python
async def _run_research_agents(self, market, agent_ids: list[str]) -> list[dict]:
    """Executa todos os research agents necessários em paralelo."""
    agents = [self._registry.get(a) for a in agent_ids]
    tasks = [agent.research({"market": market}) for agent in agents]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filtra falhas, loga erros
    return [r for r in results if not isinstance(r, Exception)]
```

#### 3.3 Prompt Dinâmico para Analysis Agents

Atualizar `BaseAgent.prompt` (ou criar `EnrichedAnalysisAgent`) para incluir dados de pesquisa:

```python
@property
def prompt(self) -> str:
    return f"""You are {self.name}, {self.role}

You are analyzing a prediction market. In addition to your own knowledge,
you have access to REAL-TIME RESEARCH DATA collected specifically for this market.

## Market
Question: {{market.question}}
Underdog price: {{market.underdog_price:.2%}}

## External Research Data
{% for result in research_results %}
### {{ result.agent }}
{{ result.summary }}
Source: {{ result.source }} (confidence: {{ result.confidence }})
{% endfor %}

## Your Task
Estimate the TRUE probability of the underdog winning, INCORPORATING the
research data above. If the research contradicts your prior knowledge,
trust the research data (it's from authoritative sources fetched just now).

Respond ONLY with JSON:
{{"probability": 0.XX, "confidence": 0.XX, "reasoning": "Brief explanation"}}
"""
```

---

### Fase 4: Cache e Resiliência (Semana 7-8)

**Objetivo**: Não pesquisar a mesma coisa 2x; sobreviver a falhas de API.

#### 4.1 Cache de Pesquisa

Tabela `research_cache` no PostgreSQL:

```sql
CREATE TABLE research_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_hash TEXT NOT NULL UNIQUE,  -- hash normalizado da query
    agent_type TEXT NOT NULL,
    result_json JSONB NOT NULL,
    fetched_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,    -- TTL por tipo (clima: 1h, commodity: 15min)
    hit_count INT DEFAULT 1
);

CREATE INDEX idx_research_cache_lookup ON research_cache(query_hash, agent_type);
```

Políticas de TTL:
- Weather: 1 hora (previsão não muda drasticamente em minutos)
- Commodity: 15 minutos (preços são voláteis)
- News: 30 minutos (notícias envelhecem rápido)
- Sports: 2 horas (escalações não mudam a cada minuto)

#### 4.2 Circuit Breaker

Se uma API externa falhar 3x seguidas:
- Desativa o agent por 10 minutos
- Loga o erro
- O scanner continua com os outros agents / sem pesquisa

```python
class CircuitBreaker:
    def call(self, fn, *args, **kwargs):
        if self.is_open:
            raise CircuitBreakerOpen(f"{self.name} is temporarily disabled")
        try:
            return fn(*args, **kwargs)
        except Exception:
            self.record_failure()
            raise
```

#### 4.3 Fallback para Analysis "Puro"

Se TODOS os research agents falharem:
- O scanner cai no comportamento atual: analysis com apenas dados do mercado
- Log: "Research unavailable, falling back to static analysis"

---

### Fase 5: Novos Tipos de Mercado (Semana 9-10)

**Objetivo**: Expandir para mercados que hoje o bot ignora por falta de dados.

#### 5.1 Agents Novos (pós-MVP)

| Agent | API | Mercados |
|-------|-----|----------|
| `CryptoResearcher` | CoinGecko / CoinMarketCap | Preço de BTC, ETH, etc. |
| `EconomicDataResearcher` | FRED (Federal Reserve) | Taxa de juros, inflação, PIB |
| `SocialSentimentResearcher` | Twitter/X API, Reddit | Buzz social, tendências |
| `FlightDelayResearcher` | AviationStack | Atrasos de voos específicos |
| `EarthquakeResearcher` | USGS | Terremotos por magnitude/região |

#### 5.2 Detecção Automática de Entidades

Usar NER (Named Entity Recognition) — ou simplesmente LLM — para extrair do texto do mercado:
- **Localização**: "Seul", "Nova York", "Tokyo"
- **Data**: "amanhã", "próxima sexta", "15 de maio"
- **Commodity**: "WTI", "Brent", "ouro", "prata"
- **Evento**: "Oscar", "Super Bowl", "eleição presidencial"

Isso permite que o agent saiba *o quê* pesquisar sem regex frágil.

---

## Estrutura de Diretórios Final

```
poly-bot/
├── agents/
│   ├── __init__.py
│   ├── base.py                    # BaseAgent (analysis)
│   ├── research_base.py           # ResearchAgent (pesquisa externa)
│   ├── registry.py                # AgentRegistry + classificação
│   ├── classifier.py              # MarketClassifier (NER/keywords)
│   ├── orchestrator.py            # ResearchOrchestrator (async gather)
│   ├── cache.py                   # ResearchCache (PostgreSQL)
│   ├── circuit_breaker.py         # Resiliência de APIs
│   ├── sports_analyst.py          # existente
│   ├── esports_analyst.py         # existente
│   ├── odds_analyst.py            # existente
│   └── research/                  # NOVO: agents de pesquisa
│       ├── __init__.py
│       ├── weather.py             # WeatherResearcher
│       ├── commodity.py           # CommodityResearcher
│       ├── news.py                # NewsResearcher
│       ├── polls.py               # PoliticalPollResearcher
│       ├── sports_injuries.py     # SportsInjuryResearcher
│       └── crypto.py              # CryptoResearcher (fase 5)
├── db/
│   ├── schema.sql                 # + research_cache table
│   └── repository.py              # + ResearchCacheRepository
├── scanner.py                     # refatorado: research + analysis
├── config.py                      # + API keys
└── docs/
    └── roadmap.md                 # este arquivo
```

---

## Exemplo de Execução Completa

### Mercado: "Temperatura máxima em Seul > 25°C amanhã?"

**Passo 1 — Classificação**:
```python
classifier.classify("Temperatura máxima em Seul > 25°C amanhã?")
# → ["weather_researcher"]
```

**Passo 2 — Pesquisa**:
```python
weather_researcher.research({
    "city": "Seoul",
    "country": "KR", 
    "date": "2026-04-29",
    "metric": "max_temp"
})
# → ResearchResult(
#     query="max temp Seoul 2026-04-29",
#     data={"temp_c": 23, "condition": "Partly cloudy", "humidity": 65},
#     summary="Previsão: máxima de 23°C, parcialmente nublado. Probabilidade de >25°C: baixa (~15%)",
#     confidence=0.9,
#     source="OpenWeatherMap",
#     timestamp=now()
# )
```

**Passo 3 — Análise Enriquecida**:
```python
sports_analyst.analyze({
    "market": market,
    "research": [weather_result]
})
# O prompt agora inclui: "Previsão: máxima de 23°C... Probabilidade de >25°C: baixa (~15%)"
# → {"probability": 0.12, "confidence": 0.85, "reasoning": "Weather data shows max 23°C, 2 degrees below threshold"}
```

**Passo 4 — Decision Gate**:
- Market implied prob: 35% (preço do "Yes")
- AI prob: 12%
- Edge: negativo
- **Decisão**: REJECT (ou apostar no "No" se houver edge invertido)

---

## Dependências Novas

```
# requirements.txt additions
python-weather  # ou requests + openweather endpoint
yfinance        # commodity prices
newsapi-python  # notícias
httpx           # já usado, mas necessário para APIs async
```

---

## Métricas de Sucesso

| Métrica | Target |
|---------|--------|
| Mercados com research data | >80% dos mercados value-bet |
| Cache hit rate | >60% (evita chamadas repetidas) |
| API failure recovery | <5% de mercados perdidos por falha de API |
| Latência de scan | <30s adicional por ciclo (com pesquisa paralela) |
| ROI improvement | >10% relativo ao baseline (sem research) |

---

## Decisões de Design Importantes

1. **Research é obrigatório quando possível**: se um mercado tem agent de pesquisa disponível, ele DEVE rodar. Analysis "puro" só é fallback.
2. **Paralelismo máximo**: todos os research agents rodam ao mesmo tempo com `asyncio.gather`, igual ao `scanner.py` atual.
3. **Prompt enriquecido, não substituído**: o analysis agent ainda usa seu expertise, mas com dados reais no contexto.
4. **Cada API é isolada**: falha na API de clima não quebra a API de commodities.
5. **Cache inteligente**: TTL adaptativo por tipo de dado.
6. **Observabilidade**: cada research result é logado e enviado ao Telegram como parte do alerta.

---

## Próximos Passos Imediatos

1. [ ] Criar `agents/registry.py` com os 5 research agents iniciais
2. [ ] Implementar `MarketClassifier` com keyword matching + LLM fallback
3. [ ] Criar `WeatherResearcher` como MVP (OpenWeatherMap, gratuito)
4. [ ] Refatorar `scanner.py` para chamar research antes de analysis
5. [ ] Adicionar tabela `research_cache` e `ResearchCacheRepository`
6. [ ] Testar com 10 mercados de clima reais do Polymarket
7. [ ] Medir ROI com vs. sem research nos primeiros 7 dias

---

*Documento criado em: 2026-04-28*
*Baseado na análise do runtime de agents do Multica (multica-ai/multica)*
