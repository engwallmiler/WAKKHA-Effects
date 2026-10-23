# Baixo, densidade sonora e automação — versão 0.9

## Descritores independentes do kick

O extrator do áudio original conserva a FFT de 2048 amostras, 75% de sobreposição e potências por canal. Acrescenta energia em 30–250 Hz, energia harmônica em 250–1500 Hz e doze bandas logarítmicas entre 30 Hz e 16 kHz (ou Nyquist). Alterar o filtro de inspeção não altera esses descritores. Não há gravação nem separação de stems.

TextureTracker recebe somente StructureFeatures e publica TextureSnapshot. Não exige KickEvent, BPM, grid ou uma estrutura aprendida.

| Medida | Cálculo e interpretação |
|---|---|
| Graves | Energia de 30–250 Hz em dBFS. Inclui baixo, kick e outras fontes nessa região. |
| Envelope grave | Mapeamento de −65 a −15 dBFS para 0–1, ataque de 60 ms e soltura de 250 ms. |
| Atividade grave | Crescimento da potência frente a uma referência de 180 ms, suavizado em 80 ms. |
| Ocupação | Fração das 12 bandas acima de −65 dBFS e a menos de 28 dB da banda mais forte. |
| Densidade sonora | 80% ocupação e 20% taxa de ataques, limitada em 10 ataques/s, suavizada em 300 ms. |
| Brilho | Descritor espectral existente, usado nas cores automáticas. |

Densidade é um indicador de preenchimento sonoro. Ruído e distorção também podem elevá-la; ela não conta instrumentos. O envelope de baixo depende do ganho da mixagem. Ocupação é relativamente robusta ao ganho acima do piso de silêncio. Em silêncio o efeito escurece imediatamente, mesmo com envelopes ainda decaindo.

## Efeitos e pesos

- **Linha de baixo · envelope dos graves**: intensidade segue 80% envelope e 20% atividade grave, multiplicada pelo peso do baixo. Moving heads acompanham densidade/atividade com movimento contínuo.
- **Densidade sonora · distribuição dos fachos**: densidade abre as luminárias gradualmente e aumenta intensidade e velocidade; o peso de densidade regula a contribuição.
- **Automação musical · baixo, densidade e kicks**: em aprendizagem/groove, mistura uma base contínua de graves/densidade com acentos de kicks confirmados. O breakdown conserva espaço para tensão; build-up/drop mantêm seus perfis estruturais e a janela de oito kicks. Esses perfis não são desligados ao zerar os pesos das camadas.

Pesos padrão: kicks **70%**, baixo **65%**, densidade **50%**. São controles de 0–100% no Lighting Studio. O peso de kicks regula os acentos da automação musical; duração do pulso e master também regulam o efeito dedicado Pulso por kick. Master multiplica todas as intensidades. Movimento zero congela a pose nos modos musical/baixo/densidade. Frequências são suavizadas e integradas para preservar a continuidade da fase.

Cores automáticas conservam prioridade para breakdown/build-up/drop. Em aprendizagem/groove ou sem estrutura disponível, áudio denso usa âmbar/violeta; graves fortes com pouco brilho usam vermelho/azul; textura leve usa menta/azul. Fixo e manual usam a paleta selecionada. Os pesos são salvos em preferências v7; v1–v6 recebem os padrões e preservam seus parâmetros conhecidos.

## Pipeline e falhas

O extrator é compartilhado pelas camadas estrutural, textura e confirmação, evitando outra FFT. TextureTracker, StructureTracker e KickAudit têm erros separados no MonitorSnapshot. Falha da estrutura ou do BPM não interrompe os efeitos dedicados de textura. Falha do extrator compartilhado invalida todas as camadas que dependem dele; cada falha é registrada uma vez por fonte/formato. Troca de fonte, formato ou descontinuidade reinicia as referências. Medidores, espectro e detector bruto continuam independentes.

LightingInput transporta TextureSnapshot, eventos confirmados e instante da confirmação. LightingRuntime passa explicitamente uma sequência vazia quando a confirmação não está disponível; o motor em execução não substitui esses eventos por candidatos brutos. A interface apenas apresenta os resultados. Stage Preview acrescenta dois medidores com altura fixa para conservar a estabilidade do layout.

## Testar

Reabrir iniciar.cmd. No Lighting Studio, selecionar um dos três efeitos e ativar o motor. Começar no groove para aprender o kick e depois comparar trechos com baixo, hats/melodia e ausência de kick. No Kick Monitor, candidatos graves podem continuar aparecendo; kicks confirmados e tempos previstos são apresentados separadamente.

**Teste • baixo e densidade** é uma composição sintética de 24 s: groove até 6 s; bassline agressiva no contratempo sem kick até 18 s; camadas médias/agudas entram em 12 s; kicks retornam em 18 s. Não reproduz som. scripts/validate_texture.py verifica as cenas em tempo real, a ausência de confirmações falsas na seção sem kick, crescimento da densidade, geometria constante, continuidade e encerramento.

Não existe saída física DMX nesta versão. Os resultados sintéticos não fornecem uma taxa de acerto em músicas reais.
