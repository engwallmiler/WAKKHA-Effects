# Validação — versão 0.36.0

Registro: **2026-11-01**. Saída WS2812 de 1 a 300 LEDs, incluindo a fita de 120 LEDs do usuário. Ensaios sem ESP32 físico, captura real, Traktor ou Link nativo.

## Regressão

**157 testes JavaScript passaram**. Os novos casos cobrem preparação de 120 LEDs sem substituir identidade/desenho, persistência, cabo contínuo com trechos de 30 + 90 LEDs e preservação atômica de cópias exatas incompatíveis. A suíte mantém os efeitos, continuidade, simetria, automações e verificações de memória limitada. [Log](resultado-pixel-js-v0.36.txt).

**144 testes Python passaram**, incluindo projetos, topologia, confiabilidade, USB e interface. Os novos casos verificam 1/30/120/299/300 pixels, validação estrita, preenchimento apagado, preparação com a fita selecionada, rejeição de respostas de fontes anteriores, mensagens de falha e prazo da preparação. [Log](resultado-pytest-v0.36.txt).

A análise musical não foi alterada; a suíte DSP completa não foi repetida. O pacote confere DSP, música e contratos byte a byte contra o wheel 0.35. [Registro anterior](validacao-v0.35.md) · [Verificação do pacote](resultado-package-v0.36.json).

## Interface nativa e USB emulado

[validate_pixel_strip_size.py](../scripts/validate_pixel_strip_size.py) abre a aplicação Qt com uma serial emulada e um projeto contendo fitas de 300 e 120 LEDs. O ensaio usa demonstração, sem abrir uma COM real, e confirmou:

- a fita salva de 120 LEDs é selecionada com o total correto;
- preparar mantém nome, identidade, coordenadas, metragem e as outras fitas;
- os 120 pixels produzem 360 canais RGB reais e os 180 endereços excedentes recebem zero;
- a troca 300 → 120 apaga os endereços que deixaram de ser usados;
- o envio continua minimizado;
- reabrir a prévia preserva o projeto e exige ativação física manual;
- seleção e perfil são salvos e o fechamento envia blackout.

[Relatório](resultado-pixel-strip-size-v0.36.0.json) · [Captura da interface](../preview-fita-120-v0.36.png).

O emulador registra payloads e confirma comandos; não reproduz alimentação, potência, integridade elétrica ou temporização da fita. A execução curta inclui trocas e recarga da prévia, e não constitui benchmark de fps ou teste de seis horas.

## Comportamento e distribuição

O bloqueio relatado era a exigência de exatamente 300 LEDs na amostragem e no conversor RGB; a preparação também forçava 300 no projeto. A nova UI mostra a quantidade física, utiliza o total indicado e confirma a fita preparada na mesma resposta. Consultas de fontes de uma revisão anterior são ignoradas. Preparação, conexão e ativação continuam separadas.

A saída real aceita uma fita lógica com 1 a 300 LEDs individuais, com perfil WS2812 em todos os trechos. O protocolo BLP1 continua com 300 endereços e recebe zeros depois do último LED do projeto. O firmware 0.22 permanece idêntico; não precisa ser regravado. Não há nova thread, FFT ou fila no caminho de efeitos.

Instalação editável e wheel são **0.36.0**. Fontes e recursos declarados são comparados byte a byte ao pacote. [Verificação](resultado-package-v0.36.json) · [Operação para 120 LEDs](fitas-variaveis-v0.36.md).
