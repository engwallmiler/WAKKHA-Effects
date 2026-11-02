# Validação — versão 0.37.0

Registro: **2026-11-02**. Quatro saídas WS2812 no ESP32-WROOM-32, GPIOs **18, 19, 25 e 26**, de 1 a 300 LEDs por saída, até 1.200 no total.

## Regressão

**160 testes JavaScript passaram**. Os novos casos verificam que quatro saídas compartilham um avanço de relógio e uma geração de amostragem, que fontes duplicadas reutilizam o mesmo quadro, que saídas desativadas retornam vazio e que erros/simulação não liberam sinal físico. A suíte conserva os 33 efeitos, cores, estruturas, picos, continuidade, cópias, blackout e verificações de memória limitada. [Log](resultado-pixel-js-v0.37.txt).

**164 testes Python passaram**, sem skips. Incluem projetos, topologia, confiabilidade, USB, interface e execução do sketch real com periféricos simulados. Novos casos cobrem configurações de quatro comprimentos, payload sem preenchimento, validação de dispositivo/pinos, fila de quadro mais recente, impedimento das saídas extras com firmware antigo, persistência/migração dos mapeamentos e conservação da identidade ao remover fitas. [Log](resultado-pytest-v0.37.txt).

A análise musical não foi alterada; a suíte DSP completa não foi repetida. DSP, música e contratos são comparados byte a byte ao pacote 0.36. [Registro anterior](validacao-v0.36.md) · [Verificação do pacote](resultado-package-v0.37.json).

## Sketch e compilação

O teste C++ compila e executa o arquivo .ino verdadeiro com serial/LEDs simulados. Os vetores binários vêm do Python. Verifica os quatro GPIOs, 1.200 pixels, um único show por pacote, comprimentos distintos, saída desativada, CRC corrompido, pacote truncado, duplicatas, sequência antiga, watchdog de 750 ms e wraparound de sequência/relógio.

A conferência do driver FastLED 3.10.3 confirmou que cada transmissor reserva dois blocos RMT. O build fixa oito slots e dois blocos para iniciar quatro transmissores nos canais 0/2/4/6; a razão também é exigida por assert de compilação no ensaio host. [Ensaio host](resultado-firmware-host-v0.37.txt).

O firmware foi compilado para **ESP32 Dev Module / WROOM-32 de 4 MB**, Espressif32 **6.12.0**, Arduino **2.0.17**, FastLED **3.10.3**. O resultado usa **29.920 bytes de RAM estática** e **293.561 bytes de programa**. RAM estática não representa o pico de heap do driver. A compilação foi feita em caminho temporário curto e sem acentos para contornar limitações das ferramentas Windows; os três arquivos de origem são conferidos por hash contra o projeto.

A imagem única tem **359.456 bytes**, gravação em **0x0**, flash DIO/40 MHz/4 MB. O binário legado 0.22 permanece disponível e idêntico. [Registro e hashes](resultado-esp32-v0.37.json) · [Log de compilação](resultado-esp32-build-v0.37.txt) · [Código](../firmware/beatlight_esp32/beatlight_esp32.ino) · [Imagem gravável](../firmware/beatlight_esp32/dist/beatlight-wroom32-ws2812-4x300-v0.37.0.bin).

## Interface nativa e USB emulado

[validate_pixel_four_outputs.py](../scripts/validate_pixel_four_outputs.py) abre Qt/WebEngine e serial emulada, sem acessar uma COM real. Usa uma montagem com comprimentos **120/300/90/120**, copiando a fonte do GPIO 18 no GPIO 26. Confirmou:

- mapeamento independente e preparação de cada fita, mantendo a geometria;
- pacote RGB conjunto de **1.890 bytes**, sem preencher endereços até 1.200;
- cópia física com bytes exatamente iguais dentro do mesmo quadro;
- texturas e buffers reutilizados durante o envio;
- continuidade com configuração recolhida e aplicativo minimizado;
- blackout nas quatro saídas e fechamento com apagamento;
- saída desativada omitida após reconexão, com pacote reduzido para 1.620 bytes;
- reabertura da prévia, persistência de mapeamentos e ativação manual.

[Relatório](resultado-pixel-four-outputs-v0.37.0.json) · [Log](resultado-pixel-four-outputs-v0.37.txt) · [Painel](../preview-quatro-saidas-v0.37.png) · [Palco com painel recolhido](../preview-quatro-saidas-palco-v0.37.png).

O emulador verifica dados e comandos, sem reproduzir temporização elétrica, alimentação ou potência. As medidas de fps incluem interação/recarga e não são um benchmark do ESP32. Não houve ensaio com quatro fitas reais nem teste de seis horas nesta entrega.

Um segundo [ensaio nativo de compatibilidade](resultado-pixel-strip-size-v0.37.0.json) confirmou o firmware emulado 0.22 no GPIO 18 com 120 LEDs, preenchimento apagado até 300, troca 300 → 120 com reconexão, minimização, recarga e persistência. [Log](resultado-legacy-usb-v0.37.txt).

## Compatibilidade e distribuição

A UI migra preferências antigas para GPIO 18 e deixa as três novas saídas desativadas. O protocolo usa o mesmo envelope com CRC32, mas negocia versão 2 no INFO. CONFIG v2 carrega quatro contagens uint16, brilho uint8 e corrente total uint16; FRAME concatena somente os LEDs habilitados, na ordem 18/19/25/26. Um ACK confirma o conjunto após um show dos quatro controladores RMT4. BLP1 legado mantém 900 bytes no GPIO 18; habilitar saídas extras exige firmware 0.37.

Mudanças de mapeamento/comprimento exigem reconexão, evitando interpretar um quadro com comprimentos antigos. A fila continua limitada ao quadro mais recente; não há thread, timer ou pedido WebEngine separado por fita. O watchdog e o orçamento de corrente abrangem as quatro saídas.

Instalação editável e wheel são **0.37.0**. A verificação compara todas as fontes/recursos ao pacote, confere o binário novo e seus arquivos de origem por hash e preserva o hash do binário legado. [Verificação](resultado-package-v0.37.json) · [Guia de atualização e ligações](esp32-quatro-saidas.md).
