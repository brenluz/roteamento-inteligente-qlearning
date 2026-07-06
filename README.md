# Roteamento Inteligente com Agente Q-Learning

Trabalho final de **Redes de Computadores (MATA59, UFBA)**. Protocolos de Rede
Inteligentes usando IA e Agentes.

Tema: **Roteamento Inteligente** (Camada de Rede). Um agente de **Q-Learning**
(aprendizado por reforço) monitora a utilização e a latência dos enlaces e
**reroteia fluxos em tempo real** para evitar congestionamento e reagir a falhas,
comparado diretamente com o **Dijkstra estático** (comportamento clássico estilo
OSPF).

---

## O que este projeto demonstra

O roteamento clássico (Dijkstra/OSPF) calcula o caminho mais curto de forma
**estática**: o custo do enlace é fixo e só muda quando a topologia muda. Ele
reconverge após uma falha, mas **ignora o congestionamento**: continua enviando
tráfego por um enlace saturado.

O agente Q-Learning aprende uma política de roteamento cuja recompensa é a
**latência efetiva** (que cresce com a carga). Quando um enlace congestiona ou
cai, as recompensas mudam e, após alguns episódios de treino, a política **desvia
o tráfego**, e o reroteamento acontece ao vivo, na frente do avaliador.

| Cenário | Dijkstra estático | Agente Q-Learning |
|---|---|---|
| Rede sem congestão | ~35 ms, 3 fluxos entregues | ~32 ms, 3 fluxos entregues |
| Congestão no enlace B-C | **341 ms, 2 fluxos descartados** | 66 ms, 3 entregues |
| Falha de C-D + gargalo G-H | **3 fluxos descartados** | 60 ms, 3 entregues |

*(valores do `experiments/run_experiments.py`; latência penalizada, em que descarte conta como penalidade.)*

---

## Requisitos

- Python 3.10+
- Dependências em `requirements.txt`: `networkx`, `flask`, `matplotlib`, `numpy`

## Instalação

```bash
# (opcional) ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

## Execução

### 1. Dashboard interativo (demonstração ao vivo)

```bash
python src/app.py
```

Abra **http://localhost:5000**. No painel você pode:

- alternar a visualização da carga entre **Q-Learning** e **Dijkstra**;
- escolher o **fluxo destacado** (a rota é realçada no grafo);
- **clicar em um enlace** e então **Injetar congestão**, **Derrubar** ou
  **Restaurar** esse enlace;
- usar os **atalhos de demo**: *Congestionar B-C* e *Falha C-D + gargalo*;
- acompanhar a **tabela de métricas** comparativa e o **gráfico de latência**
  em tempo real.

A simulação roda numa thread de fundo; o agente treina continuamente e a rota
se redesenha alguns segundos após cada evento.

### 2. Experimentos headless (gera gráficos e CSV do relatório)

```bash
python experiments/run_experiments.py
```

Gera em `results/`:

- `cenario2_congestao.png`, `cenario3_falha.png`: latência ao longo do tempo;
- `comparacao_barras.png`: resumo dos três cenários;
- `resultados.csv`: tabela consolidada.

---

## Estrutura do projeto

```
src/
  network.py            # topologia (NetworkX) + modelo de latência/congestão
  traffic.py            # fluxos de demanda e aplicação de carga nos enlaces
  metrics.py            # métricas (latência, utilização, descartes)
  simulator.py          # motor de simulação por passos + eventos ao vivo
  app.py                # servidor Flask do dashboard
  routers/
    base.py             # interface comum dos roteadores
    dijkstra_router.py  # baseline estático (peso = latência base)
    qlearning_router.py # agente Q-Learning adaptativo
static/                 # dashboard web (vis-network + Chart.js via CDN)
experiments/            # comparação headless e geração de gráficos
results/                # saídas dos experimentos (gráficos + CSV)
relatorio/RELATORIO.md  # relatório técnico
roteiro_video.md        # roteiro do vídeo de apresentação
```

## Como o agente funciona (resumo)

- **Estado**: nó atual da rede (uma tabela Q por destino).
- **Ação**: escolher um vizinho como próximo salto.
- **Recompensa**: `-latência_efetiva` do enlace, com penalidade extra para
  enlaces congestionados e bônus ao chegar ao destino.
- **Atualização**: Q-learning off-policy, `Q(s,a) = Q(s,a) + α·(r + γ·maxₐ' Q(s',a') - Q(s,a))`,
  exploração ε-gulosa.
- Como a recompensa usa a latência **efetiva** (que depende da carga), o agente
  aprende a evitar enlaces congestionados. Há salvaguardas contra laços e
  *fallback* para o caminho mais curto enquanto a política não converge.

Detalhes e hiperparâmetros em `src/routers/qlearning_router.py`.
