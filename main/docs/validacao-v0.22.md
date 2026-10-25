# Validação — versão 0.22

Registro: 2026-10-25 (UTC). Windows x64, Python 3.12.10. Saída física implementada para ESP32 DevKit/WROOM-32 USB e uma fita WS2812/WS2812B RGB de 300 LEDs individuais. **Não havia placa ou fita conectada no ambiente de desenvolvimento.** Os ensaios de transporte usam emulação e a compilação usa o toolchain real do ESP32.

## Regressão do aplicativo

**692 testes Python passaram em 165,79 s**, sem testes pulados. [Resultado](resultado-pytest-v0.22.txt). Permanecem aprovados captura, DSP, detecção de estrutura/drop, Link, motores anteriores, projetos, protocolo musical e interface.

Os novos casos verificam pacote binário BLP1/CRC32 com ruído, fragmentação e recuperação; configuração de brilho/corrente; identificação de dispositivo; resolução estrita de 300 LEDs/300 pixels; somente RGB; envio após ativação explícita; substituição de quadros pendentes; prioridade do blackout; timeout de ACK; cancelamento durante conexão; produtor atrasado e desconexão limpa. A regressão de interface também impede que um callback de amostragem anterior ao blackout volte a acender a saída.

**36 testes JavaScript passaram.** [Resultado](resultado-pixel-js-v0.22.txt). Os seis novos casos USB conferem preparação de uma fita sem alterar as demais, persistência do perfil WS2812, identidade dos valores RGB entre amostragem física e exportação da prévia para os vinte efeitos, avanço do relógio sem requestAnimationFrame/Canvas, respeito ao blackout/silêncio/desativação/dados antigos e rejeição de agrupamentos ou IDs removidos. Orgânico, Auto Show e drop manual usam o mesmo caminho de amostragem. A amostragem não faz operações de desenho.

## Firmware: compilação para ESP32 e teste host

O sketch entregue compilou para **esp32dev / ESP32-WROOM-32**, usando PlatformIO Espressif32 **6.12.0**, Arduino-ESP32 **2.0.17**, FastLED **3.10.3** e Xtensa GCC **8.4.0**. Resultado: **25.008 bytes de RAM (7,6%)** e **291.461 bytes de programa (22,2% da partição disponível)**. [Log de compilação](resultado-esp32-build-v0.22.txt).

O esptool 4.9.0 reuniu bootloader, tabela de partições, boot_app0 e aplicação numa imagem única de **357.360 bytes**, para gravação em **0x0** numa placa de 4 MB. A comparação SHA256 confirmou que o sketch, protocol.h e platformio.ini compilados são idênticos aos entregues. [Versões, hash da imagem e metadados](resultado-esp32-v0.22.json). Nenhuma placa foi gravada durante a implementação.

Além da compilação para o chip, um teste compila e executa o **sketch real** em C++ no computador, substituindo somente os periféricos Arduino/FastLED. Vetores de bytes produzidos pelo encoder Python entram no parser do firmware. São conferidos os 300 pixels independentes, RGB, CRC inválido, pacote incompleto e expiração, ACKs, conexão sem ativação, configuração inválida, duplicatas, sequência antiga, wraparound da sequência/millis e watchdog de 750 ms. As respostas do sketch voltam ao decoder Python. Esse teste não mede o sinal elétrico RMT ou o consumo da fita.

## Ensaio desktop com porta emulada

[scripts/validate_pixel_usb.py](../scripts/validate_pixel_usb.py) passou com Qt WebEngine, Qt WebChannel e o motor real do HTML. O firmware serial foi emulado; nenhuma COM real foi aberta. O cenário importou examples/ws2812-300.json em uma pasta isolada, preparou a linha, verificou configuração inicial de 25%/2.000 mA e confirmou que conectar não transmitia quadros até a ativação.

Os **vinte efeitos** produziram quadros de **900 bytes RGB**. Foram confirmados **72 quadros** no ensaio final, continuidade ao rolar a página e ao abrir outro painel, blackout com zeros, APAGAR SAÍDA, retomada manual e apagamento/liberação da porta ao fechar. O indicador final de taxa nesse ambiente offscreen foi aproximadamente **16,3 fps**; uma execução anterior registrou cerca de 19,6 fps. O alvo do emissor é no máximo 30 fps, e não uma garantia de taxa física sustentada. [Resultado](resultado-pixel-usb-v0.22.0.json), resultado-pixel-usb-native-v0.22.txt e preview-pixel-usb.png.

O cenário usa .runtime/pixel-usb-qa; arquivos reais de AppData não foram editados diretamente. A prévia, a seleção de entrada e o Ableton Link permanecem disponíveis. O aplicativo continua usando composição por software e o sandbox normal; apenas o script de QA desativa o sandbox aninhado do Chromium neste ambiente.

## Pacote e operação

O pacote editável foi atualizado para **0.22.0**, com **pySerial 3.5** instalado no runtime portátil. O wheel inclui o motor HTML, transporte e painel USB, firmware, guia, projeto de uma fita e imagem de gravação. A conferência compara o HTML e o binário empacotados com seus arquivos fonte. Compilação de src/scripts e iniciar.cmd --help passaram.

A configuração USB fica em pixel-usb.json e guarda seleção/limites, sem conexão ou ativação automática. O projeto existente é preservado; Preparar 300 WS2812 modifica somente a fita escolhida. A transmissão usa uma thread, um quadro pendente substituível, confirmação e prazos finitos. O cálculo dos efeitos é compartilhado com a prévia e continua mesmo fora da área visível.

O firmware apaga após 750 ms sem quadro válido **se o ESP32 continuar energizado**. Nesta montagem o USB alimenta a placa; retirar esse cabo pode desligar o ESP32 antes que ele apague uma fita ainda energizada por sua fonte externa. O guia explica a limitação, a ordem de desligamento e a necessidade de solução elétrica adicional para apagamento garantido também nessa condição. O limite de corrente é estimado por software, sem medição e sem substituir a proteção da distribuição.

O comportamento elétrico, ordem real de cores da fita, alimentação, corrente e latência em LEDs físicos ainda precisam ser conferidos na montagem. Não foi aberta nova sessão Link/Traktor nativa nem modificada a análise de drops nesta rodada. Não há transporte DMX físico.

Guia: [esp32-ws2812-usb.md](esp32-ws2812-usb.md). Validação anterior: [validacao-v0.21.md](validacao-v0.21.md).