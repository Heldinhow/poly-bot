# Project: Poly-Bot Agent Runtime

## Vision

Transformar o poly-bot em um **Agent Runtime** no estilo Multica, onde cada mercado promissor gera uma *task* que é despachada para um **coding agent** configurável (Claude Code, OpenClaw, Hermes, OpenCode). O agent executa de forma isolada, com prompt e skills configuráveis, realiza pesquisa externa via tools (web search, bash, APIs), toma decisões documentadas e reporta resultados — tudo rastreável e gerenciável via dashboard.

> **Regra de ouro**: *Cada aposta é uma task. Cada task é executada por um agent configurável. Cada execução é rastreável.*

## Goals

1. **Extensibilidade**: Permitir que o bot analise qualquer tipo de mercado, não apenas os onde o LLM já tem conhecimento estático
2. **Observabilidade**: 100% das execuções de agents são rastreáveis passo a passo via dashboard
3. **Configurabilidade**: Agents, skills e prompts editáveis via dashboard sem reiniciar o bot
4. **Isolamento**: Cada task roda em workdir próprio com variáveis de ambiente isoladas
5. **Fallback**: Se o runtime falhar, o scanner usa agents legados (sports_analyst, etc.)

## Success Metrics

| Metric | Target |
|--------|--------|
| Runtimes registered | 4/4 (Claude, OpenClaw, Hermes, OpenCode) |
| Tasks completed successfully | >90% |
| Executions tracked (steps) | 100% of tasks |
| Dashboard functional | CRUD agents + skills + executions |
| Task dispatch latency | <2s from scanner to agent start |
| ROI improvement | >15% relative to baseline (agents with tools) |

## Scope

### In Scope
- Backend runtime para 4 coding agents (Claude Code, OpenClaw, Hermes, OpenCode)
- Ambiente isolado por task (workdir + context files + skills)
- Tracking granular de execuções (execution_logs + execution_steps)
- Dashboard React para gestão de agents, skills e monitoramento de execuções
- Integração com scanner existente (task dispatch + decision gate)
- Fallback para agents legados
- Skills padrão (weather, commodity, news)

### Out of Scope
- Suporte a Codex, Copilot, Cursor, Gemini, Pi, Kimi, Kiro
- Blockchain execution (live trading continua como tag-only)
- Autoscaling de workers
- Multi-instance deployment

## Constraints

- Python 3.14, PostgreSQL 16, React 19 + TypeScript
- Sync code with async only for concurrent AI agents (padrão existente)
- Raw SQL over ORM (padrão existente)
- Env-based mode switching (padrão existente)
- Repository pattern for DB access (padrão existente)
