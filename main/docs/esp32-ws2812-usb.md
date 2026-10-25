# ESP32 USB + WS2812: uma fita com 300 LEDs individuais

Aplicativo 0.24, compatível com o firmware USB 0.22 já fornecido; não é necessário regravá-lo para os efeitos novos. Placa confirmada: **ESP32 DevKit / ESP32-WROOM-32**. Fita RGB WS2812/WS2812B de **5 V**, 300 LEDs. Saída de dados: **GPIO 18**, ordem física **GRB**. Este firmware não é destinado a ESP32-S3/C3 nem a fitas RGBW/12 V.

O computador executa o mesmo motor do Pixel Studio: 26 efeitos, Orgânico, Auto Show, transições por compassos, cores, baixo/densidade, estrutura musical e DROP AGORA. Envia 300 triplos RGB por USB. O ESP32 recebe cada quadro completo e gera o sinal da fita. **Um pixel corresponde a um LED**, sem agrupamentos de três.

## Materiais e alimentação

- ESP32 DevKit/WROOM-32 e cabo USB **de dados**.
- Fita WS2812/WS2812B RGB, 300 LEDs, e fonte externa regulada de **5 V**.
- Conversor de nível **74AHCT125** (ou módulo equivalente adequado para esse sinal), resistor de **330 Ω**, resistor de **10 kΩ**, capacitor eletrolítico de **1.000 µF / 10 V** e cerâmico de **100 nF**.
- Cabos, terminais e fusíveis dimensionados para a distribuição de alimentação.

**A fita não deve ser alimentada pelo USB, pelo pino 5V/VIN ou pelo regulador do ESP32.** Nesta montagem, o ESP32 recebe energia pelo USB; a fonte externa alimenta somente a fita e o conversor. Una os GNDs. Não ligue o positivo externo ao 5V/VIN da placa enquanto ela estiver alimentada pelo USB.

Como referência conservadora de dimensionamento, 300 × 60 mA = **18 A / 90 W** em branco máximo; uma fonte de 5 V / 20 A cobre essa estimativa. O consumo depende da revisão da fita e deve ser conferido em sua especificação. Distribua alimentação pelos extremos e, conforme a queda de tensão, por pontos intermediários, com proteção e cabos adequados por ramal. Não conduza a corrente da fita por uma protoboard. Essa conta usa a referência de consumo do [guia de alimentação da Adafruit](https://learn.adafruit.com/adafruit-neopixel-uberguide/powering-neopixels).

O aplicativo começa com **teto de brilho de 25% e limite estimado de 2.000 mA**. A biblioteca reduz a luminosidade quando necessário. O limite é uma estimativa por software, não uma medição de corrente nem substituto de fusíveis/fiação. Configure-o conforme a fonte e a distribuição que você montou; desconecte a saída USB no aplicativo para alterar esses limites.

## Ligações

Monte com USB e fonte desligados. Entre primeiro em **DIN/DI** da fita, seguindo o sentido das setas; DOUT/DO fica na outra ponta.

```text
Computador ── cabo USB de dados ── ESP32 DevKit/WROOM-32
                                      GPIO 18
                                         │ 3,3 V
                                    74AHCT125
                                         │ 5 V
                                       330 Ω
                                         │
                                         └────────── DIN da WS2812

Fonte externa +5 V ─────────────── +5 V da fita e VCC do 74AHCT125
Fonte externa GND ──┬───────────── GND da fita
                   ├───────────── GND do 74AHCT125
                   └───────────── GND do ESP32
```

Para o **74AHCT125 em encapsulamento DIP de 14 pinos**, use o primeiro canal:

| Ligação | Destino |
|---|---|
| Fonte +5 V | Pino 14 / VCC |
| GND comum | Pino 7 / GND e pino 1 / 1OE |
| GPIO 18 do ESP32 | Pino 2 / 1A |
| Resistor 10 kΩ | Entre pino 2 / 1A e GND |
| Pino 3 / 1Y | Resistor 330 Ω → DIN do primeiro LED |
| Capacitor cerâmico 100 nF | Entre pinos 14 e 7, junto ao CI |
| Canais não usados | Pinos 4, 10 e 13 em +5 V; entradas 5, 9 e 12 em GND; saídas 6, 8 e 11 livres |

A numeração acima considera o CI visto de cima, pela marca de pino 1. Um módulo pronto pode ter outra disposição de terminais. Confira a [pinagem oficial da Texas Instruments](https://www.ti.com/lit/ds/symlink/sn74ahct125.pdf).

Coloque o eletrolítico entre +5 V e GND junto à entrada de energia da fita, respeitando a polaridade. O resistor de dados deve ficar perto de DIN. Mantenha o trecho entre o conversor e o primeiro LED curto e acompanhe o sinal com GND. O uso de conversor 3,3 → 5 V, resistor e capacitor segue as [boas práticas da Adafruit](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices).

Depois de conferir a montagem, ligue primeiro a alimentação da fita/conversor e depois o USB. Para desligar, apague a saída, retire o USB e desligue a fonte.

## Gravar o firmware pela Arduino IDE

Os arquivos estão em [firmware/beatlight_esp32](../firmware/beatlight_esp32/beatlight_esp32.ino). **beatlight_esp32.ino e protocol.h precisam permanecer juntos nessa pasta.**

1. Instale a Arduino IDE. Em Preferências → URLs adicionais para gerenciadores de placas, adicione:

   ```text
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```

2. No Gerenciador de Placas, instale **esp32 by Espressif Systems**. O projeto PlatformIO fixa o Arduino-ESP32 **2.0.17**, e essa também é a versão de referência para reproduzir a compilação na IDE. A [documentação da Espressif](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html) explica a instalação do suporte.
3. No Gerenciador de Bibliotecas, instale **FastLED 3.10.3**.
4. Abra **beatlight_esp32.ino**, selecione **ESP32 Dev Module**, Flash Size **4 MB**, PSRAM **Disabled** e a porta COM da sua placa.
5. Clique em **Verificar** e depois **Carregar**. Se ficar em “Connecting…”, mantenha BOOT pressionado até começar a gravação; solte em seguida. Aperte EN/RESET ao terminar, se necessário.
6. **Feche o Monitor Serial e qualquer outro programa que esteja usando essa COM** antes de conectar pelo BEATLIGHT.

A comunicação do aplicativo é binária a **921.600 baud, 8N1**. O Monitor Serial não mostra os efeitos em texto. Não é necessário mudar o firmware para cada efeito nem ativar Wi-Fi/Bluetooth. Ao inicializar, a fita fica apagada.

Alternativa para quem usa PlatformIO: abra a pasta do firmware e execute:

```powershell
pio run -e esp32dev
pio run -e esp32dev -t upload --upload-port COM5
```

Troque COM5 pela porta real e feche a conexão do BEATLIGHT antes de gravar. O arquivo platformio.ini fixa plataforma e biblioteca; instalar/compilar exige internet na primeira vez. Esses comandos só gravam a placa quando você usa o alvo upload.

### Binário pré-compilado (alternativo)

A imagem única [beatlight-wroom32-ws2812-300-v0.22.0.bin](../firmware/beatlight_esp32/dist/beatlight-wroom32-ws2812-300-v0.22.0.bin) já contém bootloader, partições e aplicação para **ESP32-WROOM-32 de 4 MB**. Ela é gravada no endereço **0x0**, não em 0x10000. Substitui o firmware e reinicializa a região de configuração/NVS incluída nessa imagem; os projetos do computador ficam separados.

Em um terminal com Python, a partir da pasta main, a alternativa sem Arduino IDE é:

```powershell
python -m pip install esptool==4.9.0
python -m esptool --chip esp32 --port COM5 --baud 460800 write_flash 0x0 firmware/beatlight_esp32/dist/beatlight-wroom32-ws2812-300-v0.22.0.bin
```

Troque COM5 pela porta da placa e mantenha o BEATLIGHT desconectado dessa porta durante a gravação. A imagem foi gerada pelo esptool a partir da compilação do código entregue; hashes e versões estão em [resultado-esp32-v0.22.json](resultado-esp32-v0.22.json).

## Operar no BEATLIGHT

1. Abra **iniciar.cmd**. Na página Pixel Studio, expanda **ESP32 USB · configuração da fita** acima da prévia.
2. Escolha a **fita do projeto** que deseja enviar. Clique **Preparar 300 WS2812**: apenas essa linha passa a ter 300 LEDs, 300 pixels e perfil WS2812; as demais são preservadas. O projeto é salvo normalmente. Se preferir começar com uma única linha, importe [examples/ws2812-300.json](../examples/ws2812-300.json) em **Importar projeto de fitas**; exporte antes seu projeto atual se quiser guardá-lo.
3. Com o firmware já gravado, selecione a porta **COM** e clique **Conectar ESP32**. O aplicativo confere a identificação e envia os limites de brilho/corrente. A conexão começa com a saída apagada.
4. Clique **Ativar saída física**. Isso também ativa as fitas no motor de efeitos. **Conectar não equivale a acender**; a ativação física é sempre manual e não é restaurada ao abrir o aplicativo.
5. Para música real, use **BEATLIGHT · áudio / Ableton Link**, inicie a captura e conecte o Link como de costume. Para conferir a montagem sem música, selecione **Demonstração · BPM interno**. O modo ao vivo permanece apagado quando não há áudio recente/audível.
6. Escolha efeitos, Orgânico/Auto Show, cores e transições normalmente. Só a fita selecionada é transmitida nesta versão. **DROP AGORA**, sincronismo 1/8, blackout, sentido, brilho, velocidade e defasagem também se aplicam a ela.
7. **APAGAR SAÍDA** interrompe a emissão física e mantém a COM conectada. Para retomar, clique **Ativar saída física** novamente. **BLACKOUT** do Pixel Studio apaga mantendo a automação armada; liberar o blackout permite a retomada. **Desconectar** apaga e libera a COM.

É possível continuar transmitindo ao rolar a página ou abrir outro painel do aplicativo. O cálculo RGB da saída não depende de o Canvas estar visível. Brilho, potência estimada e aparência do difusor virtual podem fazer a luminosidade física diferir da ilustração; o padrão e os valores RGB do motor são compartilhados.

## Primeiro teste

Comece com os limites padrão. Em demonstração, selecione **Atmosfera**, resposta **Sustentação**, uma cor fixa vermelha, depois verde e azul. Confirme que as três cores estão corretas e que **APAGAR SAÍDA** funciona. Depois experimente Scanner, Arco-íris, Cometa, Orgânico e DROP AGORA com música.

Se as cores estiverem trocadas, confira se a fita é RGB WS2812B com ordem GRB. O firmware desta versão usa GRB; fitas de outra ordem precisam de uma variante de firmware, não de inverter os fios de alimentação.

| Sintoma | Verificação |
|---|---|
| Sem COM | Cabo de dados, driver USB-UART da placa (CP210x/CH340) e botão Atualizar portas |
| Sem identificação BEATLIGHT | Firmware certo, ESP32 fora do bootloader, COM correta e Monitor Serial fechado |
| COM ocupada | Fechar outros programas e desconectar na IDE/aplicativo antes de trocar |
| Conectado, LEDs apagados | Ativar saída física; conferir alimentação, GND comum, DIN, GPIO 18, brilho, fita habilitada e blackout |
| Modo ao vivo apagado | Iniciar áudio e conferir sinal; Link sozinho fornece relógio, não áudio |
| Últimos LEDs fracos ou cor instável | Queda de tensão, distribuição de energia, terminais, GND e nível de dados |
| Saída parou com aviso de atraso | O aplicativo apaga por segurança; corrija a sobrecarga/comunicação e ative novamente |

## Transporte e comportamento em falhas

O protocolo BLP1 envia cabeçalho, sequência, **900 bytes RGB** e CRC32. O ESP32 confirma o quadro depois de atualizar a fita. O emissor tem alvo máximo de **30 quadros/s**, uma confirmação pendente e uma posição para o próximo quadro; quadros novos substituem os antigos. Blackout tem prioridade. A taxa obtida depende da USB, driver e processamento.

O computador descarta quadros com mais de 250 ms e apaga se o motor parar de fornecer dados. Silêncio, captura parada, fitas desativadas e blackout produzem zeros. Com o ESP32 energizado, o firmware apaga após **750 ms sem quadro válido**, inclusive se o aplicativo travar ou só chegarem pacotes incompletos/corrompidos. Reiniciar o programa ou conectar o USB não reativa a saída física automaticamente.

**O watchdog precisa de energia no ESP32.** Nesta montagem ele é alimentado pelo USB: retirar fisicamente o cabo desliga a placa, e a fita, ainda alimentada pela fonte externa, pode conservar a última cor. Use APAGAR SAÍDA antes de retirar o USB e depois desligue a fonte. Apagamento garantido ao perder também a alimentação do controlador requer uma solução elétrica adicional; o firmware sozinho não consegue transmitir um quadro apagado enquanto a placa está sem energia.

O limite de potência utiliza a implementação da [FastLED](https://raw.githubusercontent.com/FastLED/FastLED/3.10.3/src/power_mgt.h). Há somente um canal físico de 300 LEDs nesta versão; outras fitas do projeto continuam disponíveis na simulação. Não há saída DMX física. Não há análise musical no ESP32: BPM, estrutura e efeitos continuam no computador.

## Validação disponível

Os testes de protocolo/firmware e o ensaio nativo usam periféricos emulados. Não havia ESP32/fita conectados no ambiente de desenvolvimento; brilho real, alimentação, integridade elétrica e latência física precisam ser conferidos na montagem. Os resultados de compilação e regressão estão em [validacao.md](validacao.md).
