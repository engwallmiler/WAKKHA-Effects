# BEATLIGHT DMX
## Especificação técnica e arquitetural do sistema

### 1. Objetivo geral

Desenvolver uma aplicação desktop para Windows 11 destinada ao controle inteligente e automatizado de iluminação profissional, especialmente para festas e apresentações de música eletrônica.

O sistema deverá capturar, analisar e interpretar o áudio reproduzido por softwares de DJ, como Traktor Pro 3 e, futuramente, Serato DJ, identificando características rítmicas e estruturais da música para gerar efeitos de iluminação sincronizados.

O software não deverá se limitar à simples reação à intensidade sonora. Seu objetivo é interpretar aspectos musicais como kicks, BPM, compassos, repetições rítmicas, energia espectral, pausas, transições, breakdowns, build-ups e drops.

O sistema deverá possuir uma interface gráfica moderna e um simulador visual de iluminação capaz de representar os efeitos em tempo real, mesmo sem equipamentos DMX conectados.

A arquitetura deverá permitir a integração futura com luminárias reais por meio de Art-Net, sACN e interfaces USB-DMX, sem alterar os algoritmos responsáveis pela interpretação musical.

O desenvolvimento deverá ser incremental, com módulos independentes, bem documentados e testáveis.

---

### 2. Ambiente tecnológico

O sistema será desenvolvido inicialmente em Python 3.12, com arquitetura orientada a componentes e separação explícita entre processamento, lógica de negócio, interface e comunicação com hardware.

Tecnologias preferenciais:

- **Python:** linguagem principal e integração dos módulos.
- **PySide6 / Qt:** interface gráfica desktop e gerenciamento das interações.
- **PyAudioWPatch:** implementação inicial da captura WASAPI Loopback no Windows.
- **NumPy:** operações vetoriais, tratamento de amostras e cálculos numéricos.
- **SciPy:** filtros digitais, análise espectral e processamento de sinais.
- **Pytest:** testes automatizados.
- **JSON:** persistência inicial de configurações, perfis e projetos.

A utilização dessas tecnologias não deverá provocar dependência rígida entre módulos. Bibliotecas deverão ser encapsuladas atrás de interfaces próprias sempre que representarem funcionalidades que poderão ser substituídas futuramente.

O sistema deverá permanecer preparado para receber componentes escritos em C++, Rust ou outras tecnologias caso determinados algoritmos exijam maior desempenho.

A aplicação deverá funcionar localmente, sem internet, contas de usuário ou serviços externos obrigatórios.

---

### 3. Princípios obrigatórios da arquitetura

**3.1. Modularidade**

O software deverá ser dividido em subsistemas independentes, cada um responsável por uma função claramente delimitada.

Nenhum componente deverá acessar diretamente detalhes internos de outro componente. Toda comunicação deverá ocorrer por interfaces documentadas, eventos ou estruturas de dados padronizadas.

**3.2. Baixo acoplamento**

O módulo responsável por detectar kicks, por exemplo, não deverá conhecer luminárias, DMX, Qt ou qualquer componente de apresentação visual.

Da mesma forma, o simulador de iluminação não deverá realizar processamento musical. Ele deverá receber somente os estados de iluminação produzidos pelo motor responsável.

**3.3. Inversão de dependências**

Os componentes centrais do sistema não deverão depender de implementações específicas de captura de áudio, interfaces DMX ou mecanismos gráficos.

Essas tecnologias deverão ser conectadas ao sistema por adaptadores.

**3.4. Processamento concorrente**

A captura de áudio, a análise DSP, a atualização gráfica e a comunicação DMX deverão trabalhar de maneira desacoplada, com mecanismos apropriados de sincronização.

Nenhuma operação demorada da interface poderá bloquear a captura de áudio.

**3.5. Testabilidade**

Cada módulo deverá ser testável de forma isolada, inclusive utilizando arquivos de áudio ou sinais sintéticos.

Não deverá ser obrigatório abrir o Traktor para testar algoritmos musicais.

**3.6. Extensibilidade**

Novos algoritmos, padrões de iluminação, tipos de luminárias e fontes de áudio deverão ser acrescentados sem alterações extensas nos componentes existentes.

**3.7. Observabilidade**

O software deverá informar seu estado operacional, erros, tempos de processamento, perdas de amostras, atrasos e níveis de confiança das detecções musicais.

---

### 4. Organização dos subsistemas

Organizar a aplicação nos seguintes subsistemas principais, com submódulos específicos para cada responsabilidade.

**4.1. Application Core**

Responsável por inicialização, encerramento, gerenciamento do ciclo de vida da aplicação e integração dos demais subsistemas.

Deverá centralizar a configuração das dependências e controlar quais módulos estarão ativos, sem incorporar algoritmos de áudio ou iluminação.

**4.2. Audio Input Engine**

Responsável exclusivamente pela obtenção de amostras de áudio.

Deverá conter implementações intercambiáveis de captura, incluindo inicialmente WASAPI Loopback.

**4.3. Digital Signal Processing Engine**

Responsável pelos cálculos e transformações digitais aplicados ao sinal recebido.

Deverá oferecer filtros, análise espectral, extração de características e detecção de transientes.

**4.4. Music Intelligence Engine**

Responsável por interpretar os resultados do processamento digital e construir uma representação temporal e estrutural da música.

Deverá incluir detecção de batidas, BPM, fase, compassos, padrões repetitivos e eventos musicais.

**4.5. Lighting Automation Engine**

Responsável pela transformação das informações musicais em decisões e comandos abstratos de iluminação.

Deverá trabalhar com cenas, sequências, regras, prioridades e transições.

**4.6. Fixture Management Engine**

Responsável pela representação lógica dos equipamentos de iluminação, suas características, capacidades, parâmetros e agrupamentos.

**4.7. Visual Simulation Engine**

Responsável pela simulação visual dos aparelhos e dos efeitos de iluminação.

Deverá funcionar independentemente da existência de hardware DMX.

**4.8. Lighting Output Engine**

Responsável pela transmissão dos estados de iluminação para interfaces físicas.

Inicialmente poderá ser uma implementação simulada, permitindo futuramente adaptadores Art-Net, sACN e USB-DMX.

**4.9. User Interface Engine**

Responsável exclusivamente pela apresentação de informações, recebimento de comandos do usuário e atualização dos elementos gráficos.

**4.10. Configuration and Project Management**

Responsável pela persistência de preferências, dispositivos, projetos, cenas, perfis de equipamentos e calibrações.

**4.11. Diagnostics and Testing**

Responsável por registros de eventos, métricas operacionais, testes e ferramentas de depuração.

Cada subsistema deverá possuir seus próprios componentes internos e testes. A organização do projeto deverá distinguir claramente contratos públicos, implementações, modelos de domínio e adaptadores.

---

### 5. Módulo de captura de áudio — WASAPI Loopback

Este será o primeiro módulo funcional a ser desenvolvido.

#### 5.1. Objetivo

Capturar digitalmente o áudio reproduzido em um dispositivo de saída do Windows, sem interferir na reprodução sonora.

O cenário inicial será o Traktor Pro 3 utilizando o mixer interno e a saída Realtek em modo WASAPI compartilhado.

A aplicação deverá capturar o áudio diretamente da saída escolhida, sem necessidade de microfones, cabos analógicos ou uma controladora DJ.

#### 5.2. Requisitos funcionais

O módulo deverá:

- Identificar os dispositivos de reprodução disponíveis no Windows.
- Exibir o nome de cada dispositivo e suas características relevantes.
- Permitir ao usuário selecionar o dispositivo que será monitorado.
- Identificar automaticamente o dispositivo padrão quando apropriado.
- Iniciar, interromper e reiniciar a captura.
- Capturar áudio estéreo e fornecer os dados em formato padronizado.
- Informar taxa de amostragem, quantidade de canais e formato efetivamente utilizado.
- Detectar ausência de sinal, desconexões e alterações no dispositivo.
- Tratar erros de inicialização e recuperação da captura.
- Disponibilizar medidores de nível em tempo real.

A captura deverá utilizar inicialmente PyAudioWPatch, encapsulado em um adaptador próprio.

#### 5.3. Requisitos de funcionamento

O sistema deverá suportar inicialmente áudio em 44,1 kHz e 48 kHz, respeitando o formato efetivo oferecido pelo dispositivo.

O formato interno preferencial para processamento será ponto flutuante de 32 bits.

Quando necessário, deverão existir operações explícitas de conversão de formato, quantidade de canais ou taxa de amostragem.

Essas conversões não deverão ocorrer desnecessariamente.

Os blocos de captura deverão possuir tamanho configurável. O projeto poderá começar com blocos de 512 ou 1024 amostras, avaliando posteriormente o equilíbrio entre latência, estabilidade e utilização de CPU.

#### 5.4. Tratamento dos dados

Cada bloco capturado deverá conter:

- Identificação da fonte de áudio.
- Amostras capturadas.
- Taxa de amostragem.
- Quantidade de canais.
- Número sequencial.
- Quantidade de quadros.
- Referência temporal de captura.
- Informações de continuidade e integridade.

Os dados deverão ser encaminhados a outros módulos sem vinculação direta à biblioteca utilizada para capturá-los.

#### 5.5. Limitações previstas

A captura WASAPI Loopback convencional poderá incluir sons de outros aplicativos que utilizem o mesmo dispositivo de reprodução.

Deverá existir um aviso na interface indicando que a origem selecionada representa a mixagem daquele dispositivo, não exclusivamente o Traktor.

A implementação inicial não deverá assumir compatibilidade com o driver ASIO nativo da Traktor Kontrol S4 MK2.

O projeto deverá prever futuros adaptadores para roteamento virtual, captura de entradas físicas, áudio por rede e outras formas de aquisição.

---

### 6. Gerenciamento dos fluxos de áudio

Criar uma camada intermediária entre as fontes de áudio e os algoritmos DSP.

Essa camada deverá padronizar os blocos, controlar buffers e administrar a entrega de dados aos consumidores.

O sistema deverá utilizar buffers circulares ou filas limitadas, adequados ao processamento contínuo.

Em situações de sobrecarga, o comportamento deverá ser explicitamente definido. Para análise em tempo real, normalmente será preferível descartar dados antigos de uma fila congestionada a acumular vários segundos de atraso.

Qualquer descarte deverá ser registrado nas métricas de diagnóstico.

O fluxo de áudio destinado ao DSP deverá ser independente dos dados reduzidos ou agregados enviados à interface gráfica.

Os módulos deverão utilizar uma referência temporal monotônica comum. O sistema deverá distinguir o instante estimado de aquisição da amostra do instante em que ela foi processada.

Essa separação será essencial para medir latência, estimar a fase musical e sincronizar os efeitos de iluminação.

---

### 7. Módulo de processamento digital de sinais

O DSP deverá atuar como uma biblioteca interna de processamento musical, sem qualquer dependência da interface gráfica ou de DMX.

Organizar suas funções em componentes especializados.

#### 7.1. Pré-processamento

Implementar:

- Conversão de estéreo para mono quando necessária à análise.
- Remoção opcional de componente DC.
- Normalização controlada para análise.
- Cálculo de amplitude RMS.
- Cálculo de picos.
- Detecção de silêncio.
- Janelamento temporal.
- Estimativa de níveis energéticos.

Os algoritmos deverão preservar informações importantes da dinâmica musical e evitar normalizações que prejudiquem a interpretação de transientes.

#### 7.2. Banco de filtros digitais

Criar um componente capaz de implementar filtros passa-baixa, passa-alta e passa-banda.

As frequências de corte e outros parâmetros deverão ser configuráveis.

Deverá ser possível criar diversas bandas de análise simultaneamente, sem repetir desnecessariamente operações computacionais.

#### 7.3. Análise espectral

Implementar análise baseada em FFT e outras técnicas adequadas para identificar a distribuição de energia nas diferentes regiões do espectro.

Deverá produzir informações sobre graves, médios, agudos, variações espectrais e transientes.

O componente deverá permitir diferentes tamanhos de janela e sobreposição, pois os requisitos de resolução temporal e de frequência variam conforme o algoritmo.

#### 7.4. Detecção de transientes

Implementar um detector genérico de eventos sonoros abruptos, baseado em energia, variação espectral ou combinação de diferentes características.

O detector deverá ser reutilizável por algoritmos específicos, como identificação de kicks, snares e outros elementos percussivos.

Cada evento deverá possuir referência temporal, intensidade estimada e indicador de confiança.

---

### 8. Módulo de detecção de kicks

Este será um dos componentes mais importantes do sistema.

O detector deverá identificar os bumbos característicos da música eletrônica, principalmente em gêneros como techno, house e progressive house.

A solução não deverá se basear exclusivamente em um filtro passa-baixa seguido de um comparador de amplitude.

É necessário distinguir, na medida do possível, os transientes dos kicks de linhas de baixo contínuas, subgraves e outros sons com energia nas baixas frequências.

O detector deverá combinar características como:

- Energia em bandas de baixas frequências.
- Variação temporal da energia.
- Ataque do transiente.
- Comparação com o histórico recente.
- Intervalo entre eventos.
- Regularidade rítmica.
- Coerência com o relógio musical estimado.

Deverá utilizar limiares adaptativos para funcionar com músicas de diferentes níveis e masterizações.

A faixa inicial de interesse poderá ser configurada aproximadamente entre 40 e 150 Hz, sem tratá-la como limite fixo ou suficiente para todos os kicks.

O módulo deverá fornecer, para cada evento detectado, o instante estimado, a intensidade relativa e um nível de confiança.

Também deverá permitir inspeção visual dos sinais intermediários para facilitar o ajuste dos algoritmos.

---

### 9. Módulo de BPM e sincronismo musical

Desenvolver um motor de acompanhamento rítmico que utilize os eventos detectados para estimar o tempo musical.

O sistema deverá:

- Estimar automaticamente o BPM.
- Calcular intervalos entre batidas.
- Identificar regularidade temporal.
- Detectar mudanças graduais de BPM.
- Diferenciar hipóteses de tempo normal, metade e dobro do BPM.
- Estimar a fase das batidas.
- Prever os instantes das próximas batidas.
- Manter o sincronismo durante pequenas interrupções dos kicks.
- Informar a confiança da sincronização.

Deverá possuir um relógio interno musical que avance continuamente enquanto existir referência confiável.

O relógio não deverá ser reiniciado a cada novo kick. Em vez disso, deverá ajustar progressivamente sua fase e período com base nos eventos recebidos.

Poderá ser utilizada uma abordagem semelhante a um PLL digital ou outro mecanismo de acompanhamento temporal.

O sistema deverá apresentar estados distintos de operação, como não sincronizado, adquirindo sincronismo, sincronizado e sincronismo estimado.

Inicialmente, a aplicação poderá priorizar músicas eletrônicas entre aproximadamente 90 e 160 BPM, com limites configuráveis.

---

### 10. Módulo de compassos e padrões rítmicos

O sistema deverá evoluir da simples detecção de batidas para a interpretação da organização temporal da música.

A estrutura inicial deverá priorizar músicas em compasso 4/4, comuns em música eletrônica, sem impedir futuras extensões para outras métricas.

O motor deverá manter referências para:

- Batidas individuais.
- Subdivisões rítmicas.
- Posição no compasso.
- Grupos de compassos.
- Ciclos de 4, 8, 16 e 32 compassos.
- Repetições e variações de padrões.

É importante diferenciar a detecção das batidas da identificação do primeiro tempo do compasso.

O software não deverá afirmar que identificou um início de compasso quando possuir apenas uma hipótese baseada em contagem.

Deverá existir uma medida de confiança para a posição do compasso e para a interpretação de ciclos mais longos.

O usuário poderá corrigir manualmente a fase, o primeiro tempo e a contagem quando necessário.

---

### 11. Módulo de interpretação estrutural da música

Desenvolver um subsistema especializado em identificar alterações relevantes na estrutura musical.

O objetivo será reconhecer situações como:

**Groove estável:** presença de padrões rítmicos regulares e relativamente constantes.

**Breakdown:** redução significativa de determinados elementos musicais, especialmente quando acompanhada por mudanças na energia, no espectro e na organização rítmica.

**Build-up:** aumento progressivo de energia, densidade rítmica ou atividade espectral.

**Drop:** entrada ou retorno expressivo de elementos rítmicos e energéticos após uma transição.

**Transição:** alteração significativa na instrumentação, distribuição espectral ou padrão musical.

Esses eventos deverão ser classificados probabilisticamente ou por regras graduais, evitando decisões baseadas exclusivamente em um único limiar.

O módulo deverá utilizar históricos temporais, histerese e confirmações para reduzir falsos positivos.

A interpretação deverá funcionar sem inteligência artificial na versão inicial, utilizando DSP e algoritmos determinísticos.

A arquitetura, entretanto, deverá permitir futura integração com modelos de aprendizado de máquina.

É fundamental reconhecer a limitação da análise causal: eventos musicais futuros não poderão ser conhecidos com precisão apenas a partir do áudio já recebido. Funcionalidades preditivas mais sofisticadas poderão utilizar posteriormente análise prévia de faixas ou informações de softwares de DJ.

---

### 12. Motor de iluminação

O Lighting Engine será responsável por transformar eventos musicais em efeitos visuais.

Esse módulo não deverá conhecer detalhes do protocolo DMX, do hardware utilizado ou da tecnologia de renderização gráfica.

Ele deverá trabalhar com abstrações como intensidade, cor, movimento, posição, velocidade, transição, cena e grupo de equipamentos.

O motor deverá possuir um sistema de regras configuráveis.

Exemplos de comportamentos desejados:

- Executar um pulso luminoso a cada kick.
- Alternar grupos de PAR LEDs em compassos sucessivos.
- Mudar uma sequência a cada 8 ou 16 compassos.
- Executar movimentos graduais dos moving heads durante grooves estáveis.
- Reduzir a intensidade e a velocidade das transições durante breakdowns.
- Aumentar progressivamente a dinâmica visual durante build-ups.
- Executar mudanças de cena em drops detectados com confiança suficiente.

As regras deverão possuir prioridades, condições de ativação e mecanismos para evitar conflitos.

O sistema deverá distinguir automações musicais, comandos manuais e operações de segurança.

Os efeitos deverão ser parametrizáveis e reutilizáveis em diferentes projetos.

---

### 13. Sequenciador de iluminação

Criar um subsistema próprio para sequências temporais.

O sequenciador deverá operar preferencialmente utilizando o relógio musical, e não temporizadores independentes sem sincronização.

Deverá oferecer divisões por batidas, subdivisões e compassos.

Cada sequência deverá permitir definir duração, repetição, parâmetros de iluminação, transições e condições de interrupção.

O motor deverá permitir que diferentes sequências atuem sobre grupos distintos de luminárias, desde que exista resolução explícita de prioridades e conflitos.

Também deverá ser possível criar sequências não vinculadas ao BPM, como movimentos ambientais lentos.

---

### 14. Sistema de cenas e perfis musicais

Implementar um mecanismo de cenas capaz de armazenar comportamentos completos de iluminação.

As cenas deverão ser independentes do modelo exato de luminária sempre que possível.

Criar também perfis musicais, permitindo que uma mesma música seja interpretada visualmente de formas diferentes.

Perfis iniciais sugeridos:

**Techno hipnótico:** transições longas, efeitos geométricos, movimentos sutis, repetições e mudanças graduais.

**Techno energético:** maior intensidade, movimentos dinâmicos e respostas mais marcadas aos transientes.

**House:** iluminação com maior variação rítmica, alternância de cores e respostas às diferentes camadas percussivas.

**Progressive house:** valorização de construções musicais, atmosferas e transições estruturais.

**Modo manual:** efeitos executados diretamente pelo operador, sem dependência da interpretação musical.

Esses perfis deverão ser configuráveis e não deverão alterar os algoritmos básicos de detecção.

---

### 15. Representação lógica das luminárias

Criar uma abstração genérica para equipamentos de iluminação.

Cada dispositivo deverá possuir identificação, nome, tipo, capacidades, estado atual e parâmetros operacionais.

Inicialmente, considerar:

- PAR LEDs RGB e RGBW.
- Moving heads.
- Strobes.
- Barras de LED.
- Equipamentos com dimmer.

As propriedades abstratas poderão incluir intensidade, cor, pan, tilt, velocidade, frequência de efeitos e outros parâmetros.

Nem todas as luminárias suportarão todos os recursos. O modelo deverá representar explicitamente essas capacidades.

Criar um sistema de agrupamentos, permitindo comandar dispositivos individualmente ou por grupos.

O mesmo conjunto de dispositivos lógicos deverá alimentar tanto o simulador quanto as futuras interfaces físicas.

---

### 16. Simulador visual de iluminação

Este será um componente central da experiência do usuário.

Desenvolver inicialmente um simulador bidimensional de palco, com possibilidade de evolução para uma visualização tridimensional.

A primeira versão deverá representar aproximadamente seis PAR LEDs, dois moving heads e um equipamento de strobe.

O simulador deverá exibir:

- Cor de cada luminária.
- Intensidade luminosa.
- Pulsos sincronizados.
- Movimentos dos moving heads.
- Cones ou feixes de luz.
- Transições entre cenas.
- Estado dos equipamentos.
- Disposição espacial simplificada.

A renderização deverá utilizar o estado fornecido pelo motor de iluminação, nunca executar algoritmos musicais próprios.

O usuário deverá poder alterar a distribuição dos dispositivos no palco virtual.

O simulador deverá funcionar sem Traktor, áudio ou equipamentos DMX, utilizando cenas manuais e um relógio musical simulado.

A primeira implementação poderá utilizar os recursos gráficos do Qt. Posteriormente, deverá ser possível integrar um motor 3D, como Three.js, por meio de um adaptador visual independente.

A atualização visual deverá buscar fluidez entre aproximadamente 30 e 60 FPS, sem impor essa frequência aos cálculos DSP ou à transmissão DMX.

---

### 17. Saída DMX e protocolos futuros

Desenvolver desde o início uma interface abstrata de saída de iluminação.

A primeira implementação deverá ser uma saída simulada, sem comunicação física.

Posteriormente, adicionar:

**Art-Net:** transmissão de universos DMX por rede Ethernet.

**sACN:** transmissão por protocolo de iluminação baseado em rede.

**USB-DMX:** comunicação direta com interfaces compatíveis.

O módulo deverá receber estados lógicos dos dispositivos e convertê-los em valores de canais específicos, usando perfis de luminárias.

Deverá permitir configuração de endereços DMX, universos e personalidades dos equipamentos.

Deverá prever canais de 8 e 16 bits, conforme as capacidades da luminária.

O controle de atualização dos quadros DMX deverá ser independente da frequência de atualização gráfica.

Criar mecanismos de tratamento de perda de comunicação, encerramento seguro e desativação manual das saídas.

Efeitos estroboscópicos deverão possuir limites configuráveis e proteções contra acionamentos involuntários, considerando os riscos associados a flashes intensos.

---

### 18. Arquitetura de comunicação interna

Adotar uma abordagem baseada em eventos e contratos padronizados.

O sistema deverá possuir modelos explícitos para informações como:

- Bloco de áudio capturado.
- Características espectrais.
- Evento de kick.
- Evento de transiente.
- Estimativa de BPM.
- Estado do relógio musical.
- Evento estrutural.
- Comando abstrato de iluminação.
- Estado de luminária.
- Estado operacional de módulo.

As comunicações contínuas de alta frequência não deverão depender de mecanismos inadequados para grandes volumes de dados.

Utilizar buffers e filas limitadas para áudio e sinais DSP.

Eventos discretos, como detecção de kick ou mudança de cena, poderão ser distribuídos por um mecanismo específico de eventos.

Estados destinados à interface poderão utilizar snapshots imutáveis ou estruturas equivalentes.

A interface não deverá precisar receber cada amostra de áudio capturada.

Evitar a criação de um barramento universal excessivamente complexo. Cada contrato deverá existir para atender a uma necessidade concreta de comunicação.

---

### 19. Sincronização temporal e latência

O sistema deverá utilizar uma referência temporal monotônica comum para as operações críticas.

Cada módulo deverá distinguir os tempos de aquisição, detecção, processamento e apresentação dos eventos.

O objetivo é reduzir atrasos e permitir sua medição e compensação.

A aplicação deverá apresentar métricas como:

- Latência estimada da captura.
- Tempo de processamento DSP.
- Atraso de distribuição dos eventos.
- Atraso de atualização visual.
- Latência total estimada.
- Perdas de blocos ou eventos.

O processamento deverá priorizar informações recentes, evitando que uma sobrecarga provoque uma fila crescente de eventos atrasados.

O relógio musical deverá permitir agendamento de efeitos baseado em instantes previstos de batida.

Deverá existir uma função de calibração de deslocamento temporal para ajustar a resposta visual ou física em relação ao áudio percebido.

Essa calibração não deverá ser confundida com a capacidade de prever alterações musicais ainda não observadas.

---

### 20. Interface gráfica

Criar uma interface desktop moderna, com tema escuro e organização semelhante a ferramentas profissionais de áudio e iluminação.

A aplicação deverá possuir áreas funcionais independentes.

**Painel principal:** estado geral, dispositivo de áudio selecionado, indicadores de conexão e informações operacionais.

**Audio Monitor:** medidores de nível, forma de onda, espectro e informações sobre a captura.

**Rhythm Monitor:** BPM estimado, confiança, eventos de kick, fase, posição no compasso e estado do sincronismo.

**Music Analysis:** energia por banda, transientes, eventos estruturais e indicadores de padrões musicais.

**Lighting Studio:** criação de cenas, grupos de luminárias, regras e sequências.

**Stage Preview:** simulador visual de iluminação.

**Fixture Manager:** cadastro e parametrização dos dispositivos.

**Settings:** preferências, configuração de captura, desempenho, calibração e diagnósticos.

Os componentes visuais deverão ser separados da lógica que fornece seus dados.

A interface deverá permitir reorganizar painéis e futuramente utilizar um segundo monitor para apresentar o simulador em tela cheia.

---

### 21. Gerenciamento de projetos e configurações

Implementar um sistema de persistência que permita salvar e recuperar o ambiente de trabalho.

O sistema deverá armazenar separadamente:

- Preferências globais da aplicação.
- Configurações das fontes de áudio.
- Parâmetros dos algoritmos DSP.
- Perfis musicais.
- Cenas e sequências.
- Equipamentos cadastrados.
- Organização do palco virtual.
- Endereçamento DMX.
- Calibrações temporais.

As configurações deverão possuir controle de versão de formato para possibilitar migrações futuras.

O usuário deverá poder exportar e importar projetos.

Configurações inválidas deverão ser tratadas sem impedir desnecessariamente a inicialização da aplicação.

---

### 22. Diagnóstico e tratamento de falhas

Implementar registros de eventos estruturados e ferramentas para identificar falhas.

A aplicação deverá conseguir informar claramente problemas de áudio, processamento, interface ou comunicação.

Deverão existir métricas de:

- Utilização de CPU por subsistema, quando mensurável.
- Frequência efetiva de atualização.
- Tempo de execução dos algoritmos.
- Quantidade de eventos detectados.
- Continuidade da captura.
- Perda de blocos.
- Estado das filas.
- Erros de dispositivos.

O sistema deverá tratar especialmente desconexões de dispositivos, alterações na saída padrão, silêncio prolongado e falhas em módulos opcionais.

Uma falha no simulador não deverá interromper desnecessariamente a captura de áudio.

Uma falha em uma interface de iluminação não deverá encerrar toda a aplicação.

O módulo de saída física deverá possuir política configurável de segurança para falhas e encerramento.

---

### 23. Testes automatizados e validação

Criar testes independentes para cada subsistema.

Os módulos DSP deverão ser testados com sinais sintéticos de frequência, amplitude e comportamento conhecidos.

O detector de kicks deverá ser validado utilizando sequências sintéticas de kicks em diferentes BPMs, amplitudes e relações sinal-ruído.

O Beat Tracker deverá ser testado com alterações graduais de andamento, ausência temporária de batidas e padrões capazes de provocar ambiguidades entre BPM normal, metade e dobro.

O módulo de interpretação estrutural deverá ser testado com exemplos de transições, pausas e mudanças de energia.

O simulador deverá ser testado com estados de iluminação produzidos artificialmente.

A comunicação DMX deverá permitir testes de conversão de canais sem hardware conectado.

Também deverão existir testes de integração, verificando a propagação de eventos desde a fonte de áudio até o estado das luminárias.

Não utilizar resultados de simulação como comprovação automática de desempenho com áudio real.

---

### 24. Requisitos de desempenho

O software deverá buscar funcionamento fluido em um notebook Windows 11 equipado com processador Intel Core i5 de 12ª geração, 16 GB de RAM e GPU dedicada, mantendo recursos disponíveis para a execução simultânea do Traktor.

A captura deverá ser contínua, com processamento compatível com tempo real.

A interface gráfica deverá permanecer responsiva mesmo durante operações intensivas de análise.

Utilizar inicialmente blocos de áudio pequenos o suficiente para permitir boa resolução temporal, sem gerar sobrecarga excessiva por chamadas frequentes.

O objetivo preliminar será manter a reação do analisador e do simulador aos eventos musicais em uma faixa de latência perceptualmente adequada para iluminação rítmica, buscando tempos inferiores a aproximadamente 100 ms nas condições favoráveis da primeira implementação.

Esse valor será uma meta de engenharia, não uma garantia, e deverá ser verificado experimentalmente.

Evitar cópias desnecessárias de grandes buffers, operações bloqueantes e cálculos repetidos.

Utilizar processamento vetorizado sempre que apropriado.

---

### 25. Estratégia de desenvolvimento incremental

O desenvolvimento deverá ser organizado em fases independentes e verificáveis.

**Fase 1 — Fundação da aplicação**

Criar a estrutura modular do projeto, os contratos principais, a inicialização, o gerenciamento de configuração, os testes e uma interface gráfica básica.

Nenhum componente deverá depender de implementações ainda inexistentes.

**Fase 2 — Captura WASAPI Loopback**

Implementar a descoberta de dispositivos, seleção da saída Realtek, captura contínua e monitoramento visual do sinal.

Validar com áudio reproduzido pelo Windows e posteriormente com o Traktor Pro 3.

**Fase 3 — Processamento DSP básico**

Implementar pré-processamento, medidores, filtros digitais, FFT e visualização espectral.

**Fase 4 — Detecção de kicks**

Implementar, testar e ajustar a identificação dos kicks em música eletrônica.

**Fase 5 — Beat Tracker**

Desenvolver estimativa de BPM, sincronização temporal e previsão das batidas.

**Fase 6 — Motor de iluminação inicial**

Criar luminárias abstratas e os primeiros efeitos sincronizados aos kicks e ao relógio musical.

**Fase 7 — Simulador visual**

Implementar o palco virtual e a representação dinâmica dos dispositivos.

**Fase 8 — Interpretação musical avançada**

Acrescentar compassos, padrões rítmicos, transições, breakdowns, build-ups e drops.

**Fase 9 — Automação configurável**

Desenvolver cenas, sequências, regras, perfis musicais e ferramentas de edição.

**Fase 10 — Comunicação DMX**

Implementar Art-Net inicialmente, seguido dos demais protocolos conforme a necessidade.

**Fase 11 — Fontes e sincronismos adicionais**

Integrar outras fontes de áudio, incluindo áudio de arquivos, roteamento virtual, áudio por rede e, futuramente, sincronização Ableton Link.

Cada fase deverá possuir critérios próprios de conclusão e testes antes do desenvolvimento da próxima.

---

### 26. Requisitos específicos para o primeiro protótipo

O primeiro protótipo funcional deverá concentrar-se exclusivamente na captura e monitoramento de áudio.

Seu objetivo será comprovar a estabilidade da arquitetura e da captura WASAPI Loopback.

Deverá apresentar:

1. Interface desktop inicial em PySide6.
2. Identificação e seleção dos dispositivos de saída Windows.
3. Captura WASAPI Loopback do dispositivo selecionado.
4. Indicadores de funcionamento e nível de áudio.
5. Visualização da forma de onda em tempo real.
6. Medição de RMS e pico.
7. Início e interrupção segura da captura.
8. Informações de formato, taxa de amostragem e tamanho dos blocos.
9. Indicadores básicos de desempenho e erros.
10. Estrutura preparada para conectar os algoritmos DSP posteriores.

Esse protótipo não deverá implementar prematuramente o motor completo de iluminação, interpretação estrutural, controle DMX ou simulador 3D.

Entretanto, todos esses componentes deverão estar previstos na arquitetura e em seus contratos conceituais.

A entrega será considerada satisfatória quando a aplicação conseguir capturar continuamente o áudio da saída Realtek utilizada pelo Traktor Pro 3, apresentar os níveis e a forma de onda sem interrupções perceptíveis e encerrar a captura corretamente.

Também deverão ser realizados testes de troca de dispositivo, ausência de sinal e repetidas operações de iniciar e parar.

---

### 27. Diretrizes para o desenvolvimento no VS Code

Desenvolver a aplicação progressivamente, preservando a separação dos módulos definida nesta especificação.

Antes de implementar cada funcionalidade, identificar qual subsistema será responsável por ela, quais dados receberá e quais resultados fornecerá.

Evitar arquivos excessivamente grandes e classes que acumulem responsabilidades não relacionadas.

Não inserir algoritmos DSP diretamente nos componentes gráficos.

Não incorporar lógica específica do Traktor ao núcleo da aplicação. O software deverá interpretar fontes de áudio genéricas.

Não acoplar os efeitos de iluminação à representação visual dos aparelhos.

Cada novo módulo deverá apresentar responsabilidades claras, interfaces documentadas, tratamento de erros e testes apropriados.

Manter uma documentação de arquitetura atualizada conforme decisões forem implementadas.

Caso uma funcionalidade exija alterar contratos de módulos existentes, avaliar primeiro o impacto sobre os demais componentes.

Evitar abstrações desnecessárias e generalizações prematuras. A arquitetura deverá ser extensível, mas cada componente criado deverá possuir uma responsabilidade real.

Não desenvolver todas as fases simultaneamente.

**A implementação deverá começar exclusivamente pela Fase 1, seguida da Fase 2, priorizando a qualidade da fundação arquitetural e a confiabilidade da captura WASAPI Loopback.**

O resultado esperado é uma plataforma de iluminação musical moderna, modular e expansível, capaz de evoluir progressivamente de um simples analisador de áudio para um sistema profissional de interpretação musical e controle inteligente de iluminação DMX.