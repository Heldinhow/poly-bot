# Spec: Execution Live Tracking

## Overview
Substituir os `ExecutionCard` estáticos da ExecutionsPage por `LiveExecutionCard` com streaming WebSocket em tempo real, timeline colorida por tipo de step, auto-scroll e output final.

## User Stories

### STORY-1: Ver steps do agent em tempo real
**As** operador do bot  
**Quero** ver tool calls, thinking, e outputs do agent aparecendo em tempo real no card de execução  
**Para que** eu possa acompanhar o raciocínio do agent conforme ele analisa um mercado

**Acceptance Criteria:**
- Quando uma execução está `running`, o card conecta ao WebSocket `/api/executions/{id}/stream`
- Steps aparecem no card em <500ms após serem produzidos pelo agent
- Cada step mostra: número de sequência (#1, #2...), tipo com badge colorido, preview do conteúdo
- Tool calls mostram nome da tool + input resumido (ex: "bash: curl polymarket.com/...")
- Tool results mostram preview do output (truncado)
- Thinking steps mostram texto em itálico
- Error steps mostram mensagem em vermelho
- Steps são expansíveis para ver conteúdo completo
- Timeline rola automaticamente para o step mais recente
- Se usuário scrollar para cima, botão "↓ Latest" aparece para voltar ao final

### STORY-2: Barra de progresso colorida
**As** operador do bot  
**Quero** ver uma barra de progresso que mostra a composição da execução por tipo de step  
**Para que** eu entenda rapidamente se o agent passou mais tempo pensando, usando tools, ou produzindo texto

**Acceptance Criteria:**
- Barra horizontal com segmentos proporcionais à contagem de cada tipo
- Cores: text=emerald, thinking=violet, tool_use=blue, tool_result=slate, error=red
- Hover em cada segmento mostra tooltip: "{tipo}: {contagem} steps"
- Barra atualiza em tempo real conforme novos steps chegam
- Quando completado, barra mostra composição final

### STORY-3: Output final ao completar
**As** operador do bot  
**Quero** ver um resumo claro do resultado quando a execução termina  
**Para que** eu saiba imediatamente qual foi a decisão do agent sem precisar expandir nada

**Acceptance Criteria:**
- Card mostra grid com: Probability (%), Confidence, Edge, Decision badge (ACCEPT/REJECT/SKIP)
- Reasoning text visível inline
- Se FAILED, mostra mensagem de erro
- Se COMPLETED com sucesso, mostra valores em destaque
- Ações: copiar output, ver steps completos

### STORY-4: Card colapsado informativo
**As** operador do bot  
**Quero** ver informações relevantes mesmo com o card fechado  
**Para que** eu possa escanear rapidamente a lista de execuções

**Acceptance Criteria:**
- Header mostra: status badge + agent name + elapsed time + tool count
- Para execuções running: spinner animado + tempo decorrido ao vivo
- Para execuções completed: status verde + prob/conf resumidos
- Clique expande para ver timeline + output

## Non-functional Requirements
- WebSocket deve reconectar automaticamente com backoff exponencial (1s → 15s)
- Buffer máximo de 1000 steps por execução no frontend
- Steps já salvos no DB devem ser carregados via REST antes de iniciar streaming (para steps anteriores à conexão WS)
- Layout responsivo: timeline ocupa altura máxima de 300px com scroll interno
