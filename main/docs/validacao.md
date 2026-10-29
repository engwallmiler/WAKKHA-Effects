# Validação — versão 0.26.0

Registro: **2026-10-28 (UTC)**. Grupos visíveis, cópia exata/proporcional, simulação do projeto atual sem USB, abas e operação minimizada/apresentação leve. Nenhum ESP32, captura de áudio física ou sessão Link nativa foi usado nos ensaios desta entrega.

## Regressão

**744 testes Python**: DSP/estrutura, captura, Link, projetos, topologia, persistência, transporte, worker e ponte Qt. Inclui validação exata de pixels/perfis, preservação do projeto em falha, suspensão/retomada do worker PAR e distinção entre uma solicitação explícita de prévia e um snapshot antigo. [Saída completa](resultado-pytest-v0.26.txt).

**78 testes JavaScript**, sem falhas: evolução/ritmo e amostragem dos 26 efeitos, grupos, ordem dos fios, cópia exata, inversão, proporcionalidade, ajuste atômico de destino e conservação das posições. Verificam prévia do projeto atual sem alterar a montagem, bloqueio de quadros físicos, parada/retomada do agendamento visual e avanço dos efeitos sem pintar. [Saída completa](resultado-pixel-js-v0.26.txt).

## Qt nativo: apresentação, páginas ocultas e USB

[validate_pixel_presentation.py](../scripts/validate_pixel_presentation.py) passou em Qt WebEngine por software, com configuração isolada em `.runtime/pixel-presentation-qa`. Sete fases de aproximadamente oito segundos: palco, controles, modo leve, minimização, espectro visível, palco PAR e retorno aos pixels.

- Pixels continuam mudando e os três pares permanecem iguais em todas as fases.
- Áudio e quadros USB emulados continuam, com **zero descartes de áudio**.
- **Zero desenhos Canvas** nos controles, no modo leve, minimizado e fora da página de pixels.
- Espectro recebe atualizações somente em sua página visível. Worker/tabela PAR são atualizados somente no palco anterior.
- Restauração retoma o desenho; simular o projeto atual preserva geometria/grupos, apaga e desconecta a saída emulada.
- Ausência de erros JavaScript; fechamento conclui e apaga a saída.

[JSON com CPU e contadores](resultado-pixel-presentation-v0.26.0.json) · [Log nativo](resultado-pixel-presentation-native-v0.26.txt) · [Cartões de grupos](../preview-pixel-groups-v0.26.png) · [Apresentação leve](../preview-pixel-presentation-v0.26.png).

A CPU registrada separa processo principal e renderer e usa um núcleo lógico como 100%. Os padrões evoluem entre fases; o ensaio não mede isoladamente a FFT nem certifica a carga do Traktor. A medição final foi executada sem pytest simultâneo. As mensagens de inicialização gráfica do Qt offscreen permanecem no log; as verificações de desenho/canais passaram e as capturas foram inspecionadas.

O [ensaio USB pelos controles reais da interface](../scripts/validate_pixel_usb.py) também passou para **26 efeitos**, configuração de limites, ativação, blackout, continuidade fora da página e encerramento. Usa exclusivamente uma porta emulada. [JSON USB](resultado-pixel-usb-v0.26.0.json) · [Log](resultado-pixel-usb-native-v0.26.txt). Corrigida a disputa entre escolha física e mensagens antigas de operador; botões de conexão refletem imediatamente a troca de modo.

## Distribuição e limites

O HTML, guias, exemplos e módulos integram o wheel 0.26.0. Compilação, iniciar.cmd --help, instalação editável, identidade dos arquivos e hash do firmware são conferidos em [resultado-package-v0.26.json](resultado-package-v0.26.json). O firmware **0.22 permanece idêntico** e não requer regravação.

Não houve ensaio de seis/oito horas reais. O relógio acelerado de oito horas e os buffers limitados foram verificados na 0.25; os novos testes verificam a continuidade sem pintura. [Histórico 0.25](validacao-v0.25.md) · [Auditoria e comando de oito horas reais](confiabilidade.md). Ainda precisam de ensaio prolongado a memória do Chromium, o conjunto real Traktor/Link e o transporte físico. O motor permanece no processo WebEngine; modo leve não o torna independente de falhas desse processo.

Operação: [apresentacao-leve.md](apresentacao-leve.md) · [conexoes-fitas.md](conexoes-fitas.md) · [esp32-ws2812-usb.md](esp32-ws2812-usb.md).
