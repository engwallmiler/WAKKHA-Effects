# Ondas orgânicas com todos os LEDs acesos — 0.34

Reinicie o programa e pressione **CONTÍNUO**. A apresentação começa por **Ondas orgânicas**, com uma base acesa em todos os pixels e regiões de cor/brilho em movimento. Os padrões também estão na biblioteca e podem ser escolhidos para cada fita.

## Três movimentos novos

- **Ondas orgânicas:** frentes coloridas se deformam e se cruzam em velocidades distintas.
- **Correntes cruzadas:** correntes de cores percorrem sentidos opostos, com contrastes de intensidade.
- **Maré cromática:** manchas largas de cor e brilho flutuam mais lentamente, como uma maré que respira.

O desenho muda ao longo da fita, em vez de apenas clarear e escurecer por inteiro. As cores se misturam suavemente; o movimento tem continuidade, sem sortear posições ou cores a cada quadro. O estilo Contínuo combina os novos movimentos com os fades da versão anterior, mantendo as frases longas e a evolução gradual.

## Controles

Em **Efeitos e cores → Automação**:

- **Profundidade das ondas, 0–100%:** controla o contraste espacial de cor e brilho. Em 0%, conserva um banho uniforme com fades; em 100%, as regiões ficam mais pronunciadas, mantendo o fundo aceso.
- **Velocidade das ondas, 25–250%:** ajusta o andamento interno das frentes. A mudança de velocidade é suavizada e não reposiciona o desenho.

Esses controles atuam nos três padrões novos, inclusive quando aparecem em combinações. **Variação orgânica**, na aparência, deforma as frentes. A velocidade geral, o controle individual de cada fita e o acompanhamento de energia continuam atuando; um breakdown com pouca energia se movimenta mais lentamente.

Para começar, experimente profundidade em **80%**, velocidade em **100%** e uma paleta como **Neon** ou **RGB**. Para ver somente o movimento contínuo, deixe **Picos por frase → Desligados**. Se os picos estiverem ligados, continuam tendo seu destaque próprio.

Para escolher exatamente uma paleta no automático, use **Cores no automático → Manter a paleta escolhida**. Com **Paletas musicais**, as cores continuam evoluindo conforme energia e estrutura.

Uma cor fixa ou paleta de uma única cor conserva essa escolha: haverá movimento de intensidade, com menos variedade de tons. Para ondas com toda a gama RGB, selecione **Espectro RGB contínuo**. As cópias exatas, inversões e continuidades da geometria continuam usando a mesma amostragem, no mesmo instante.

## Validação

O ensaio nativo usa a aplicação Qt e uma serial emulada, com uma fita de 300 pixels dividida em seis barras. Nos três padrões, todos os pixels ficaram acesos, as regiões tiveram cores/intensidades diferentes e os quadros mudaram com o tempo. Também verificou profundidade zero, velocidade sem reiniciar a fase, persistência, buffers reutilizados, movimento minimizado e zero no blackout/encerramento.

O ensaio registrou aproximadamente 21 fps e renderização média próxima de 6 ms, sem hardware físico. Não mede o brilho elétrico da fita nem certifica seis horas reais. [Relatório](resultado-pixel-flow-v0.34.0.json) · [Ondas](../preview-organico-liquid-v0.34.png) · [Correntes](../preview-organico-crossflow-v0.34.png) · [Maré](../preview-organico-chromatide-v0.34.png).

O firmware 0.22 continua compatível; não precisa regravar o ESP32.
