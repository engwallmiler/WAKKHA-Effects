# ESP32 USB — quatro saídas WS2812 · versão 0.37

Aplicativo e firmware para **ESP32 DevKit / ESP32-WROOM-32**, fitas **WS2812/WS2812B RGB de 5 V**, ordem **GRB**. Uma única conexão USB controla quatro sinais independentes:

| Saída | GPIO | LEDs configuráveis |
|---|---|---|
| 1 | 18 | 1 a 300 |
| 2 | 19 | 1 a 300 |
| 3 | 25 | 1 a 300 |
| 4 | 26 | 1 a 300 |

São até **1.200 LEDs individuais no total**. Cada saída pode usar uma fita lógica diferente, inclusive um cabo dividido em barras. Escolher a mesma fita lógica em duas saídas faz ambas receberem cópias exatas no mesmo quadro. Saídas desmarcadas permanecem apagadas. O relógio musical, as cores, o áudio e o Link continuam no computador.

## Atualizar o firmware

**Para usar GPIO 19, 25 e 26, grave o firmware 0.37 uma vez.** O firmware 0.22 continua aceito pelo aplicativo somente para a saída GPIO 18. Tentar habilitar outras saídas com ele apresenta uma mensagem e não inicia o envio.

O código está em [beatlight_esp32.ino](../firmware/beatlight_esp32/beatlight_esp32.ino), acompanhado de [protocol.h](../firmware/beatlight_esp32/protocol.h) e [platformio.ini](../firmware/beatlight_esp32/platformio.ini). Mantenha os arquivos juntos. Referência fixada: **Arduino-ESP32 2.0.17 / Espressif32 6.12.0 / FastLED 3.10.3**.

### Imagem pronta

Use [beatlight-wroom32-ws2812-4x300-v0.37.0.bin](../firmware/beatlight_esp32/dist/beatlight-wroom32-ws2812-4x300-v0.37.0.bin), imagem única para WROOM-32 com **4 MB**, no endereço **0x0**. Ela inclui bootloader, partições e aplicação. Feche o Monitor Serial e desconecte a COM no BEATLIGHT antes de gravar.

Na pasta `main`, com Python e esptool 4.9.0 instalados:

```powershell
python -m esptool --chip esp32 --port COM5 --baud 460800 write_flash 0x0 firmware/beatlight_esp32/dist/beatlight-wroom32-ws2812-4x300-v0.37.0.bin
```

Troque **COM5** pela porta da sua placa. Se a gravação aguardar conexão, mantenha BOOT pressionado até começar; depois solte. Ao concluir, reinicie pelo botão EN/RESET e reabra o aplicativo. Os projetos salvos no computador são mantidos. [Registro de compilação e hash](resultado-esp32-v0.37.json).

### Compilar o código

Na Arduino IDE, selecione **ESP32 Dev Module**, Flash **4 MB**, PSRAM desativada, instale as versões de referência acima, abra o `.ino` e use Verificar/Carregar. O arquivo reserva oito slots RMT, com dois blocos de memória por fita, para quatro transmissores paralelos nos canais 0/2/4/6. O PlatformIO também fixa essas opções para os arquivos da biblioteca. Não altere os pinos do código sem atualizar também o mapeamento/protocolo do aplicativo.

Com PlatformIO, na pasta do firmware:

```powershell
pio run -e esp32dev
pio run -e esp32dev -t upload --upload-port COM5
```

No Windows, use um caminho curto e sem acentos para a compilação, por exemplo uma cópia dos três arquivos em `C:\Temp\beatlight-esp32`. Os programas antigos do toolchain ESP32 podem falhar com acentos ou comandos muito longos. Gravar exige a saída do BEATLIGHT desconectada da COM.

## Ligações das quatro fitas

Cada GPIO liga ao **seu próprio DIN**, através de um conversor de nível **3,3 → 5 V** e resistor de dados. Não una os quatro sinais de dados. Uma única **74AHCT125 de 14 pinos** oferece os quatro canais:

| Saída | ESP32 → entrada A do CI | Saída Y do CI → resistor 330 Ω → DIN |
|---|---|---|
| GPIO 18 | Pino 2 / 1A | Pino 3 / 1Y → fita 1 |
| GPIO 19 | Pino 5 / 2A | Pino 6 / 2Y → fita 2 |
| GPIO 25 | Pino 9 / 3A | Pino 8 / 3Y → fita 3 |
| GPIO 26 | Pino 12 / 4A | Pino 11 / 4Y → fita 4 |

No CI: **pino 14 em +5 V**, **pino 7 em GND** e enables **1, 4, 10 e 13 em GND**. Use capacitor de 100 nF junto ao CI e um resistor de 10 kΩ de cada entrada A para GND para manter nível baixo com o ESP32 desligado. A tabela considera o CI visto de cima, pela marca do pino 1; módulos prontos podem usar outros rótulos. Confira o [datasheet da Texas Instruments](https://www.ti.com/lit/ds/symlink/sn74ahct125.pdf).

**As fitas recebem alimentação externa de 5 V, nunca pelo USB/VIN/regulador do ESP32.** Una os GNDs do ESP32, conversor e fontes das fitas. O ESP32 continua alimentado pelo USB; não conecte o positivo externo ao 5V/VIN da placa nessa montagem. Fontes distintas não devem ter suas saídas positivas unidas entre si.

Use proteção e distribuição dimensionadas para cada ramal, resistor junto a cada DIN e capacitor de 500–1.000 µF na entrada de alimentação de cada fita, respeitando a polaridade. Cabos de sinal devem ser curtos e acompanhados de GND. A orientação segue as [boas práticas da Adafruit](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices). Desligue USB e fontes para montar a fiação.

O **limite total estimado** do aplicativo é compartilhado pelas quatro saídas. Continua iniciando em 2.000 mA e brilho de 25%; com várias fitas isso pode reduzir bastante o brilho. Ajuste conforme as fontes e a distribuição realmente instaladas. Esse limite é uma estimativa da FastLED, não uma medição nem uma proteção individual por ramal.

## Configurar no Pixel Studio

1. Reabra pelo **iniciar.cmd** e confira **v0.37**.
2. Escolha **Saída física · ESP32 USB** e expanda **configurar 4 saídas**.
3. Marque somente os GPIOs usados. Em cada linha, escolha a fita lógica do projeto, confira o total de LEDs e clique **Preparar fita WS2812**. Sua fita de 120 LEDs continua com 120. Quando o total já corresponde ao projeto, as quantidades por trecho são conservadas.
4. Configure o teto de brilho e o **limite total estimado**. Escolha a COM e clique **Conectar ESP32**. A conexão começa apagada.
5. Clique **Ativar saídas físicas**. Para testar sem música, escolha **Demonstração · sem áudio** na prévia. Para Traktor, use áudio ativo e o relógio escolhido, incluindo Ableton Link.
6. Recolha a configuração USB para dar espaço ao palco. Minimizar ou usar Apresentação leve mantém o cálculo e a transmissão.
7. **APAGAR TODAS** interrompe as quatro saídas. **BLACKOUT** também afeta todas. Para alterar fitas/saídas, apague primeiro; mudar o mapeamento ou a quantidade desconecta a sessão e exige **Conectar ESP32** novamente.

Os mapeamentos e limites são salvos em `pixel-usb.json`, separados do projeto visual. Preferências antigas migram para GPIO 18 e deixam as três novas saídas desativadas. A ativação física nunca é restaurada automaticamente.

O [projeto de exemplo](../examples/quatro-saidas-ws2812.json) contém quatro fitas de 120 LEDs. Importe-o pela biblioteca e associe cada fita ao GPIO correspondente no painel. Para copiar a fita 1 na saída 4, selecione a mesma fita nas duas linhas; não é necessário duplicar a geometria.

## Otimizações e limites

- Um único pedido ao motor avança o relógio e amostra todas as saídas; cópias reutilizam o quadro e o cache de pixels.
- Um pacote CRC contém todas as saídas habilitadas, na ordem 18 → 19 → 25 → 26. Um único `FastLED.show()` atualiza os quatro controladores RMT; o ACK vem ao final.
- O firmware usa o comprimento real de cada saída. Quatro fitas de 120 LEDs enviam **1.440 bytes RGB**, em vez de 3.600. Saídas desativadas não ocupam dados RGB.
- CRC por tabela de 16 entradas, buffers fixos e recepção de 8 KB evitam alocação de quadros no loop do ESP32. No computador há uma confirmação pendente e somente o quadro mais recente aguardando envio.
- USB continua em **921.600 baud**; 30 fps é teto, não uma promessa. Com quatro fitas de 300 LEDs, apenas os dados e o sinal dos LEDs já ocupam aproximadamente 48 ms por quadro, sugerindo cerca de 20 fps antes de outras despesas. É uma estimativa de capacidade, não uma medição de hardware.
- Silêncio, simulação, dados inválidos/atrasados e blackout mantêm as proteções existentes. O watchdog apaga as quatro saídas após 750 ms sem quadro válido enquanto o ESP32 estiver energizado. Use APAGAR TODAS antes de retirar o USB: sem alimentação, o ESP32 não consegue enviar apagamento.

[Validação](validacao.md) · [Ensaio nativo com USB emulado](resultado-pixel-four-outputs-v0.37.0.json). A compilação e os testes não substituem a avaliação elétrica das quatro fitas reais.
