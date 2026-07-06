# Roteiro do Vídeo (slide a slide, 10 a 11,5 min)

**Trabalho:** Roteamento Inteligente com Agente Q-Learning. MATA59 (UFBA).
**Dupla:** _(Integrante 1)_ e _(Integrante 2)_
**Deck:** apresentação no Canva (9 slides) + gravação de tela da simulação.

> As falas estão prontas para leitura, mas soam melhor ditas com suas palavras.
> O símbolo 🎬 marca os momentos de trocar entre slides e simulação.

**Preparação antes de gravar**
1. `pip install -r requirements.txt` e rodar `python experiments/run_experiments.py` uma vez (gera os gráficos usados nos slides 7/8, se você os inserir).
2. Deixar o dashboard rodando em segundo plano: `python src/app.py` e abrir `http://localhost:5000`. Clicar em **Reset** para partir do estado limpo.
3. Abrir a apresentação do Canva em modo de exibição.
4. Testar o microfone e o software de captura (OBS, Xbox Game Bar com Win+G, ou similar) gravando 10 segundos de teste.

---

## Slide 1 | Capa (0:00 a 0:40) | Integrante 1

**Falar:**
> "Olá, professor. Somos _(nome 1)_ e _(nome 2)_ e este é o nosso trabalho final de Redes de Computadores. O tema é roteamento inteligente: nós construímos um agente de aprendizado por reforço, com Q-Learning, que decide as rotas de uma rede em tempo real, e o comparamos com o roteamento clássico por Dijkstra, que é a base do protocolo OSPF."

**Na tela:** slide 1 parado. Se possível, as câmeras dos dois integrantes visíveis (atende à regra de "mostrar os integrantes explicando").

---

## Slide 2 | Introdução (0:40 a 1:30) | Integrante 1

**Falar:**
> "O roteamento é o serviço da camada de rede que decide por qual caminho os dados vão da origem ao destino. Hoje isso é resolvido por algoritmos de caminho mais curto, que funcionam muito bem, mas têm um ponto cego: o custo de cada enlace é um número fixo. Isso significa que o roteamento clássico não percebe congestionamento. Se a rota mais curta ficar sobrecarregada, ele continua usando ela.
>
> Nosso objetivo foi atacar exatamente esse ponto: criar um agente que observa o estado real da rede e reroteia o tráfego sozinho, e medir o quanto ele ganha do Dijkstra em cenários de congestão e de falha."

**Na tela:** slide 2 (cards "Protocolo e Problema" e "Objetivo do Trabalho").

---

## Slide 3 | Como funciona o roteamento clássico (1:30 a 3:00) | Integrante 2

Esta é a parte que o PDF pede para explicar o protocolo. Falar com calma.

**Falar:**
> "Primeiro, como o roteamento clássico funciona. Em protocolos de estado de enlace, como o OSPF, cada roteador conhece o mapa completo da rede: quais roteadores existem e como estão conectados. Cada enlace desse mapa recebe um custo, que é a métrica de roteamento, normalmente ligada à latência ou à largura de banda do enlace. Quanto melhor o enlace, menor o custo.
>
> Com esse mapa, cada roteador roda o algoritmo de Dijkstra, que calcula a árvore de caminhos mais curtos: para cada destino, o caminho cuja soma dos custos é a menor possível. O tráfego então segue por esse caminho.
>
> E aqui está o detalhe central: essas rotas só são recalculadas quando a topologia muda, ou seja, quando um enlace cai ou volta a operar. Nesse momento os roteadores trocam mensagens de estado de enlace, as LSAs, atualizam o mapa e refazem o cálculo. Fora isso, o custo é fixo e a rota não muda."

**Na tela:** slide 3.

---

## Slide 4 | Limitações e onde entra a IA (3:00 a 4:15) | Integrante 2

**Falar:**
> "O problema é consequência direta desse custo fixo. O Dijkstra não enxerga congestionamento. Se vários fluxos escolhem o mesmo caminho mais curto, esse caminho satura: a fila cresce, a latência dispara e começa a haver perda de pacotes. Mas, para o algoritmo, o custo daquele enlace continua o mesmo, então ele continua mandando tráfego para lá. Ele fica cego para a congestão que ele mesmo criou.
>
> É aí que entra a inteligência artificial. Em vez de um custo fixo, usamos um agente de aprendizado por reforço cuja recompensa depende da latência real do enlace, aquela que cresce quando o enlace enche. Como o agente é punido toda vez que usa um enlace carregado, ele aprende sozinho a desviar do congestionamento, sem ninguém programar as rotas manualmente."

**Na tela:** slide 4 (duas colunas: limitações e IA).

---

## Slide 5 | Arquitetura da solução (4:15 a 5:00) | Integrante 1

**Falar:**
> "A implementação foi feita em Python, organizada em módulos. O módulo network monta a topologia com NetworkX, com nove roteadores e caminhos redundantes, e implementa o modelo de congestão, em que a latência de cada enlace cresce com a utilização. O módulo traffic gera os fluxos de demanda. Em routers estão os dois competidores: o Dijkstra estático e o agente Q-Learning. O simulador executa os dois nas mesmas condições, ao mesmo tempo, para a comparação ser justa. E um dashboard web mostra tudo em tempo real, que é o que vocês vão ver na demonstração."

**Na tela:** slide 5.

---

## Slide 6 | Lógica de decisão do agente (5:00 a 6:15) | Integrante 1

**Falar:**
> "Como o agente decide? Modelamos o roteamento como aprendizado por reforço. O estado é o nó em que o pacote está. A ação é escolher para qual vizinho enviar, ou seja, o próximo salto. E a recompensa é o que ensina: ela é a latência efetiva do enlace com sinal negativo, tem uma penalidade grande se o enlace estiver congestionado e um bônus quando chega ao destino.
>
> O agente guarda o que aprendeu em uma tabela Q, uma por destino, com o valor estimado de cada próximo salto possível. A cada experiência, ele ajusta essa tabela na direção da recompensa que observou. E como ele treina continuamente sobre o estado atual da rede, quando algo muda, uma congestão ou uma queda de enlace, as recompensas mudam e a política dele muda junto. É isso que faz a rota se redesenhar sozinha."

**Na tela:** slide 6 (cards Estado, Ação, Recompensa).

---

## Slide 7 | Demonstração prática (6:15 a 6:40) | Integrante 2

**Falar (curto, é só a ponte):**
> "Agora a parte mais importante: o sistema rodando de verdade. Vamos executar três cenários ao vivo: a rede em estado normal, uma injeção de congestão no enlace B-C e a queda do enlace C-D com um gargalo. Reparem no comportamento dos dois roteadores em cada caso."

**Na tela:** slide 7.

---

## 🎬 SIMULAÇÃO (6:40 a 9:30) | ambos, revezando | ponto obrigatório do PDF

**Trocar do Canva para a tela do dashboard** (`http://localhost:5000`). É esta gravação de tela que cumpre a exigência de "mostrar o sistema funcionando" e "demonstração prática". Falar enquanto clica, sem pressa.

**Cenário 1: estado normal (~40 s)**
- Mostrar a topologia e a rota destacada A até D (A-B-C-D).
- Alternar os botões Q-Learning / Dijkstra.

> "Este é o dashboard. Cada bolinha é um roteador e as cores dos enlaces mostram a utilização: verde é livre, vermelho é congestionado. A rota destacada é do fluxo de A até D. Sem congestão, os dois roteadores escolhem o mesmo caminho curto e as métricas empatam."

**Cenário 2: congestão em B-C (~60 s)**
- Selecionar o enlace B-C na lista e clicar em Injetar congestão (ou usar o atalho Congestionar B-C).
- Mostrar primeiro a visão Dijkstra, depois alternar para Q-Learning.
- Apontar a tabela de métricas e o gráfico de latência.

> "Agora eu injeto congestão no enlace B-C, que está na rota principal. Ele fica vermelho. Na visão do Dijkstra, a rota não muda: ele continua passando por B-C, o enlace satura e a tabela mostra fluxos descartados. Agora, na visão do Q-Learning: em poucos segundos o agente aprende a desviar, a rota se redesenha por baixo e os descartes voltam a zero. No gráfico, a linha do Dijkstra fica presa lá em cima, e a do agente cai depois de um pico rápido. Esse pico é o aprendizado acontecendo."

**Cenário 3: falha de C-D com gargalo (~60 s)**
- Clicar em Restaurar tudo. Depois usar o atalho Falha C-D + gargalo.

> "Cenário mais difícil: derrubo o enlace C-D e ainda crio um gargalo em G-H. O Dijkstra até reage à falha e recalcula a rota, mas empurra todo o tráfego para o gargalo e descarta os três fluxos. O agente percebe o gargalo e contorna por um caminho mais longo, pelo nó I, e continua entregando tudo. Três descartes contra zero."

**Fechamento da demo (~10 s)**
- Clicar em Restaurar tudo e mostrar a rede normalizando.

> "Restaurando a rede, tudo volta ao normal. Vamos aos números consolidados."

🎬 **Voltar do dashboard para o Canva, slide 8.**

---

## Slide 8 | Resultados (9:30 a 10:30) | Integrante 2

**Falar:**
> "Resumindo os experimentos, que rodamos de forma controlada com um script à parte. Sem congestão, empate técnico: latências entre 32 e 35 milissegundos e todos os fluxos entregues, o que mostra que o agente não perde nada quando a rede está tranquila. Com congestão em B-C, o Dijkstra vai a 341 milissegundos e descarta dois dos três fluxos, enquanto o agente entrega tudo com 66. E na falha com gargalo, o Dijkstra perde os três fluxos e o agente entrega os três com cerca de 60 milissegundos."

**Na tela:** slide 8 (três cards de cenário). Se tiver inserido os gráficos de `results/`, apontar a curva do cenário 2.

---

## Slide 9 | Conclusão (10:30 a 11:30) | Integrante 1

**Falar:**
> "Concluindo. O agente mostrou comportamento adaptativo real: resiliência a congestão e a falhas, mantendo a entrega onde o roteamento estático perde tráfego, e sem custo quando a rede está livre. As limitações que identificamos: a tabela Q não escala para redes muito grandes, existe um tempo curto de convergência depois de cada evento e o nosso modelo de congestão é uma aproximação analítica. Como melhorias futuras, apontamos trocar a tabela por uma Deep Q-Network, colocar a utilização dos enlaces no estado do agente e validar em um emulador real como o Mininet.
>
> No fim, o resultado confirma a ideia do trabalho: aprendizado por reforço traz para o roteamento uma resiliência que o custo fixo do roteamento clássico não consegue oferecer. Obrigado."

**Na tela:** slide 9.

---

### Checklist final antes de enviar
- [ ] Os dois integrantes aparecem e explicam (câmera ou voz identificada).
- [ ] A simulação foi mostrada rodando de verdade (bloco 🎬, entre os slides 7 e 8).
- [ ] Congestão e queda de enlace foram feitas ao vivo, com o reroteamento visível.
- [ ] Áudio compreensível e duração entre 8 e 12 minutos.
- [ ] Nomes da dupla preenchidos no slide 1.
