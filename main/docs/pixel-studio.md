# Pixel Studio integrado — 0.24

## Apresentação e camadas

O desktop abre em **Foco no palco**. **Mostrar controles** revela painéis recolhíveis para automação/picos, fitas/geometria, biblioteca/drops e aparência/cores. **Editar fita** abre diretamente o painel da linha escolhida. A área USB também é recolhível; ativação e APAGAR SAÍDA permanecem fora dela. As atualizações musicais não abrem/fecham painéis nem mudam a altura dos indicadores.

Existem **26 padrões**, incluindo Trama, Órbitas, Fragmentos, Maré, Mosaico e Vórtice. AUTO SHOW e ORGÂNICO escolhem composições de **duas, três ou quatro camadas**, com memória das últimas doze combinações. Um elemento pode conectar composições vizinhas; a seleção evita repetir a combinação inteira ou retornar sempre à mesma cena após breakdown.

Para receber as combinações, escolha **Efeito → Seguir show global** no controle da fita. Uma fita com efeito próprio conserva essa escolha. Mudanças sustentadas de densidade/atividade e novidade espectral podem solicitar a evolução, respeitando a duração mínima da direção visual escolhida.

**Direção visual → Hipnótica** é o novo padrão, inclusive ao abrir um projeto antigo sem esse campo. Trabalha com famílias Anéis, Corrente, Espiral, Trama, Órbitas, Túnel, Maré e Véu, selecionadas conforme a estrutura. A mesma base conecta até três composições; dentro de uma família, muda somente uma camada por troca, mantendo fase e intensidade das que continuam. As camadas usam movimentos relacionados e cores próximas, com menos deformação espacial. Padrões de pontos dispersos não são sorteados para essas famílias.

Cada composição hipnótica permanece por **pelo menos 32 tempos da grade**. Com evolução progressiva, os elementos crescem ao longo de oito tempos, com entradas distribuídas nos primeiros compassos, e permanecem sustentados. As saídas acontecem na fusão com a próxima composição; não há um esvaziamento automático a cada 16 tempos. Na grade regular de 4/4, 32 tempos correspondem a 32 kicks, mas a contagem continua sem kick. A base pode atravessar pelo menos 96 tempos quando a estrutura permanece estável e as trocas respeitam esse mínimo.

**Direção visual → Variada** conserva as combinações mais livres, mínimo de 16 tempos e entradas/saídas dentro do ciclo. Em ambas as direções, mudanças de estrutura, seleção manual e DROP AGORA podem antecipar a troca. **Manter padrão** preserva a família/composição enquanto mantém o movimento.

**Velocidade automática** suaviza a passagem entre fatores de movimento. Um breakdown com energia/tensão baixas se move devagar; build-up e drop aceleram. BPM, fase e o intervalo de quatro/oito tempos não são acelerados junto com o movimento. Desligue essa opção para usar somente a velocidade escolhida.

O protocolo físico continua BLP1/RGB/300 pixels. **O firmware 0.22 permanece compatível com todos os efeitos e camadas novos; não é necessário regravá-lo.**

## Picos por frase

**Participação automática** inclui picos em algumas composições e os deixa ausentes em outras, mantendo essa escolha durante a composição. Quando entram, repetem um motivo mais intenso a cada quatro ou oito tempos. Um breve recuo antes do acento aumenta seu contraste. Breakdown calmo utiliza um acento mais suave e longo; drops têm sua própria sequência prioritária.

O botão **Sincronizar pico · N tempos** indica a participação pela cor e marca o momento do acento ao ser pressionado. Ele conserva o intervalo indicado e passa a **Sempre ativos**; não altera o BPM, o início da composição ou a sincronização geral. Para retomar a escolha automática, selecione **Picos por frase → Participação automática**. **Sincronizar 1/8** continua sendo o controle separado do ciclo geral. Nenhum desses controles inventa eventos acústicos de kick.

A saída física inicial é **uma fita WS2812/WS2812B RGB com 300 LEDs individuais, via ESP32 DevKit/WROOM-32 USB**. No painel nativo, escolha a fita e use Preparar 300 WS2812 → Conectar ESP32 → Ativar saída física. O mesmo cálculo RGB atende a prévia e a transmissão, inclusive com o palco fora da área visível. Veja [ligação, firmware e operação](esp32-ws2812-usb.md); esse guia também abre pelo botão Instruções do painel.

O arquivo `beatlight/beatlight_pixel_studio.html` é a fonte do simulador embutido na página **Pixel Studio · LEDs**. Não é necessário abrir um navegador separado. A aplicação mantém a captura WASAPI, a análise musical e o módulo Ableton Link e passa seus resultados ao simulador.

## Sincronização e controles

No modo **BEATLIGHT · áudio / Ableton Link**, o BPM manual fica bloqueado. A grade segue o relógio selecionado no aplicativo e continua durante trechos sem kick. O acento de kick usa eventos acústicos confirmados, sem tratar uma previsão da grade como um kick real. O equalizador visual usa baixo, densidade e brilho espectral analisados; não é um separador de instrumentos.

**Ativar fitas** controla somente os pixels, independentemente do motor anterior de PARs/moves. **BLACKOUT** zera todas as fitas e flashes virtuais. Áudio parado, silêncio e perda de dados por 500 ms também deixam a emissão em zero. O aplicativo inicia com as fitas desativadas. **Demonstração · BPM interno** é um modo separado, identificado, que pode funcionar sem áudio; ele mantém as cenas e os controles do HTML original.

**Sincronizar 1/8** marca o primeiro tempo de um ciclo de oito tempos, sem alterar BPM/fase do Traktor ou do Link. Use **Variação automática** para escolher a regra de ORGÂNICO/AUTO SHOW:

- **Compassos + novos elementos**: troca a cada N compassos e permite antecipação por mudanças sustentadas, na próxima fronteira de compasso. É o padrão de projetos antigos sem esse campo.
- **A cada N compassos**: troca regularmente mesmo quando o áudio permanece estável.
- **Somente novos elementos**: conserva o padrão enquanto os elementos forem estáveis.
- **Manter padrão**: suspende a troca automática de combinações; movimentos e a automação estrutural continuam conforme a configuração.

**Trocar a cada** aceita os intervalos existentes, aplicando mínimo de 32 tempos na direção Hipnótica ou 16 na Variada. **Fusão musical** controla a passagem, separada da agenda. Em evolução progressiva, a fusão automática usa pelo menos oito tempos na Hipnótica e quatro na Variada; desligar essa evolução permite fusões curtas ou corte explícito. O relógio ao vivo usa a grade musical. **Próxima transição** informa o prazo em compassos/tempos. Para uma apresentação longa, use Hipnótica, 8 ou 16 compassos, três camadas e evolução progressiva.

Com **Acompanhar breakdown, build-up e drop**, a estrutura tem prioridade sobre os padrões individuais: o breakdown mistura sustentação calma, o build acrescenta movimento/tensão e o drop usa sua sequência de alta energia em todas as fitas habilitadas. Paletas e brilho por fita são respeitados. ORGÂNICO/AUTO usam repertórios próprios em cada trecho. A entrada automática acompanha o estado musical sem esperar o próximo compasso, e a saída segue as oito confirmações reais do detector. **Manter os efeitos escolhidos** desliga essas camadas estruturais automáticas.

## DROP AGORA

O botão laranja fica também no cabeçalho Qt, sempre acessível ao rolar o HTML. **DROP AGORA / D** começa imediatamente por oito tempos; um novo clique encerra. O disparo ativa as fitas, preservando blackout, master e linhas desabilitadas. Ele é identificado como **manual**, sem modificar a estrutura detectada ou fabricar kicks. Enquanto a grade está aprendendo, usa o último BPM como estimativa e informa isso no texto do drop.

Uma detecção automática que chega durante o disparo manual não reinicia seus oito tempos. Sincronizar 1/8 durante a cena conserva a duração restante. Parar/reiniciar a captura limpa a identificação de cenas anteriores. Na demonstração, **Armar drop** ainda agenda a entrada para o próximo compasso; **DROP AGORA** continua sendo imediato.

Cada entrada escolhe um plano diferente dos dois drops anteriores. As camadas são adicionadas progressivamente a cada dois tempos; no drop automático o avanço das camadas considera as posições acústicas confirmadas. O primeiro impacto não espera essas adições nem a confirmação posterior da continuidade. Ao terminar, AUTO/ORGÂNICO escolhem uma composição nova conectada ao contexto atual.

## Cada fita

Escolha uma linha no seletor acima do palco e clique em **Editar fita**, ou selecione no editor de geometria. Os controles individuais são aplicados imediatamente:

- efeito próprio entre os 26 padrões, ou seguir o show global;
- paleta própria, ou seguir a paleta global;
- brilho de 0–100%, velocidade de 0,1–4× e defasagem;
- início → fim ou fim → início;
- fita ligada/apagada;
- resposta combinada, grade, kick real, baixo, densidade ou sustentação.

As linhas podem ter comprimento, resolução e direção diferentes. Reverter a direção do efeito não troca a identificação da fita. Ao excluir uma linha, os controles das linhas sobreviventes acompanham suas identidades.

Os perfis **WS2811 · RGB** e **WS2812 · RGB individual** geram três canais por pixel, inclusive para branco obtido pela combinação RGB. Eles não criam um emissor W dedicado. **RGBW · simulação** é um perfil virtual separado. A escolha global RGBW da demonstração não transforma essas fitas RGB em RGBW. Para a saída USB desta versão, a linha selecionada precisa estar em WS2812, 300 LEDs e 300 pixels; o botão Preparar ajusta apenas essa linha, preservando as demais.

O modelo inicial usa seis linhas de 5 m, 600 LEDs e 200 pixels cada. Os três LEDs de cada grupo desse modelo compartilham um triplo RGB; o quadro exportado contém 200 pixels, sem duplicar 600 endereços. As resoluções do editor são configuráveis, conforme a geometria fornecida pelo usuário. Limites: 32 linhas, 32.768 LEDs físicos e 8.192 pixels no total; cada linha aceita até 4.096 LEDs e 2.048 pixels.

## Salvar, importar e exportar

`pixel-studio.json` fica no diretório das preferências/logs do BEATLIGHT. O projeto é independente do arquivo `preferences.json` v13, que continua cuidando de áudio, Link e palco anterior. As gravações são validadas e atômicas; um projeto inválido não substitui o último válido.

**Exportar projeto de fitas** inclui geometria, identificadores, controles por fita e controles globais. **Importar projeto de fitas** recupera esses dados. Ativação, blackout, pausa e seleção de entrada ao vivo/demonstração não são reativados pelo projeto. O fechamento também salva a última edição, mesmo se o usuário não aguardou o pequeno intervalo do salvamento automático.

**Exportar/importar geometria** continua aceitando o JSON versão 1 do HTML original. Esse formato guarda somente linhas. Use o projeto completo para transferir também efeitos e cores.

**Exportar quadro RGB** gera JSON com `physical_output: false` e uma lista por fita: identificação, perfil, modelo, LEDs, pixels, ordem lógica de canais e valores inteiros de 0–255. A ordem lógica exportada é **RGB** para WS2811/WS2812; o firmware converte RGB em **GRB** no fio da WS2812. O perfil virtual RGBW usa quatro canais. O arquivo exportado é um registro dos pixels calculados; o envio contínuo ao hardware acontece pelo painel USB nativo.

## Integração e limites atuais

`pixel/protocol.py` projeta snapshots musicais para um contrato pequeno e valida quadros RGB/RGBW. `pixel/project.py` valida e salva projetos. `ui/pixel.py` hospeda o HTML em Qt WebEngine, usa Qt WebChannel e bloqueia navegação/recursos remotos. O HTML continua funcionando sozinho em demonstração. O pacote inclui o HTML como recurso de dados; não há cópia divergente do motor de efeitos.

A lógica musical é processada no recebimento dos dados, sem esperar o próximo quadro de animação. A prévia embutida usa uma imagem menor e limita desenho a 30 Hz; o arquivo de quadro preserva todos os pixels configurados. Os halos usam uma camada pequena para evitar filtros caros por software. O quadro é composto fora da superfície visível e apresentado de uma só vez, por cópia de pixels em memória. O desenho pausa quando o palco sai da área visível, enquanto a grade e as cenas continuam avançando. Chromium e Qt Quick usam composição por software por padrão, com Canvas acelerado/WebGL desativados para contornar os artefatos gráficos. Essa configuração segue a alternativa de renderização por software documentada pelo [Qt WebEngine](https://doc.qt.io/qt-6.10/qtwebengine-features.html#hardware-acceleration). O sandbox do aplicativo normal permanece ativo. O motor gráfico continua sendo o simulador Canvas, não um worker de transmissão física independente da interface.

As mensagens incluem o instante de envio do host; a entrega mais rápida observada estabelece uma estimativa da diferença entre relógios. A fase considera a idade estimada da mensagem. Dados enfileirados antigos não se tornam novos kicks nem são tratados como áudio recente. A estimativa não mede a latência física do dispositivo de som. Para investigação técnica, `BEATLIGHT_PIXEL_RENDERER=gpu` mantém o backend padrão em uma sessão de teste; a configuração normal prioriza estabilidade por software.

**Saída física é uma ativação separada da prévia.** A conexão USB inicia apagada, e Ativar saída física também ativa o motor de fitas. APAGAR SAÍDA interrompe a emissão até nova ativação; o BLACKOUT global mantém o motor armado e retoma ao ser liberado. Quadros atrasados são descartados, e o firmware apaga após 750 ms sem quadro válido. A saída funciona com fonte externa de 5 V, limites físicos próprios e montagem descrita no guia. Não há DMX físico. A sincronização Traktor/Link continua somente de leitura.

Testes: `node --test beatlight/tests/geometry.test.cjs beatlight/tests/music.test.cjs beatlight/tests/usb.test.cjs beatlight/tests/evolution.test.cjs`, `python -m pytest` e os scripts `validate_pixel_studio.py`, `validate_pixel_cues.py`, `validate_pixel_usb.py` e `validate_pixel_evolution.py` da pasta scripts. O ensaio de áudio usa configuração isolada em `.runtime/pixel-qa`; cues/evolução usam cópias do projeto em pastas próprias; o ensaio USB exercita uma porta ESP32 emulada em `.runtime/pixel-usb-qa`. Nenhum abre captura de hardware ou sessão Link nativa. Somente o ambiente automatizado desativa o sandbox aninhado do Chromium; o aplicativo normal não aplica essa opção. Veja os resultados em [Validação](validacao.md).
