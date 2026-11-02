# Kicks com linha de baixo — versão 0.27

**Correção na 0.28:** a recuperação da 0.27 foi permissiva demais fora da grade em faixas reais. Os resultados abaixo são históricos; a entrega atual separa candidatos elegíveis ao BPM, prioriza ataques reais na grade estável e acrescenta um teste com baixo antecipado. [Guia 0.28 e comparação](grade-audio-estavel.md).

## O problema reproduzido

O detector anterior comparava o aumento da energia de toda a banda grave com seu histórico, junto de fluxo, contraste e limiar adaptativo. Uma linha de baixo sustentada preenche essa banda: o kick pode continuar audível e acrescentar pouco contraste à energia total. A atividade e seu limiar também podem cair juntos; baixar apenas o limiar não recupera a informação que essa normalização perdeu.

A versão 0.27 mantém esse caminho e acrescenta um sensor de novidade espectral. A decisão sobre estrutura musical continua passando por identidade acústica e coerência temporal.

## Dois caminhos de ataque

`dsp/masked_kicks.py` reutiliza o FFT de `KickDetector`, sem outro FFT ou modelo externo. Mantém um fundo lento por frequência, comprime a razão de energia por bin e procura aumentos locais em duas regiões da banda configurada, com apoio logo acima dela. Assim, um componente sustentado pesa menos e não normaliza sozinho o ataque inteiro.

O máximo entre bins vizinhos reduz mudanças causadas por variação tonal nas frequências em que a resolução permite isso. No subgrave, um bin de cerca de 23 Hz é um salto grande: espalhar um baixo de 105 Hz para o bin de um kick de 70 Hz esconderia justamente o ataque procurado. Por isso o espalhamento fica restrito às frequências adequadas, preservando a separação no grave.

Uma proposta precisa conservar energia nova nos bins envolvidos no próximo passo de análise, aproximadamente **10 ms depois**. A confirmação verifica a permanência do componente; o fluxo não precisa continuar subindo. Piso de energia, participação grave e intervalo mínimo continuam atuando. O detector principal mantém prioridade quando os dois caminhos aprovam o mesmo ataque.

São **candidatos acústicos**, incluindo possíveis ataques de baixo. O novo sensor não separa stems nem classifica com certeza um instrumento. A coluna Sensor informa Energia ou Espectral; a confirmação estrutural decide quais eventos podem sustentar o ritmo e os efeitos de kick.

## Aquisição da grade e referência do groove

Quatro ataques regulares continuam suficientes. Antes da primeira aquisição, uma busca limitada a 16 eventos pode encontrar quatro ataques reais regulares entre outros candidatos. A previsão não acrescenta observações. O ajuste inicial usa os quatro tempos em conjunto, evitando que a mediana de três intervalos enviesados faça a grade rejeitar o quinto kick correto.

Ao adquirir a grade, o histórico confirmado e o perfil aprendido são alinhados aos eventos compatíveis. Os ataques intermediários de baixo não ficam contando como kicks retroativamente. Antes dessa aquisição, uma estimativa incerta de BPM não amplia o bloqueio entre candidatos. A grade contínua, sua manutenção sem kick e a integração Link permanecem disponíveis.

## Estrutura musical e primeiro impacto

O novo caminho ajuda o primeiro kick a chegar à confirmação de timbre, em vez de ser perdido antes dela. Os critérios de potência relativa ao groove, retorno, pausa, cadência e perfil continuam necessários para o drop.

A cauda descontada do fundo ganhou um piso de incerteza relativo ao ataque e ao leito grave. Quando a cauda fica encoberta pelo baixo, ela não é interpretada como uma queda artificial de mais de 100 dB. Isso evita aprender um decaimento impossível para comparar com o próximo retorno e preserva a invariância ao volume.

Na composição sintética de retorno com baixo forte, o relatório mede o instante da decisão sobre a linha do tempo do áudio. Esse valor não mede a latência completa Traktor → captura → USB → LED.

## Inspeção no aplicativo

1. Reabra `iniciar.cmd` e inicie a captura habitual. Não é necessário regravar o ESP32 ou refazer o projeto de fitas.
2. Em **Kick Monitor**, compare a faixa com **KICKS CONFIRMADOS** e as marcas verdes. Marcas azuis discretas são candidatos ainda sujeitos à verificação.
3. A curva verde-clara mostra o caminho anterior, com limiar amarelo. A curva roxa mostra novidade espectral, com seu limiar rosa. Uma queda do contraste global pode coexistir com um ataque espectral válido.
4. A tabela identifica o sensor de cada candidato. O total de recuperações espectrais inclui candidatos; não é uma contagem de acertos garantidos. A força relativa também inclui o contexto grave.

Os testes usam sensibilidade 1,0, banda 40–150 Hz, piso −60 dBFS e intervalo mínimo de 180 ms. Preferências anteriores são preservadas. Os filtros e o FFT da tela de espectro continuam independentes da análise de kicks. Áudio de reprodução não é modificado.

## Validação reproduzível

Os sinais são determinísticos, com onsets conhecidos, sem arquivos de tracks reais. Há baixo sustentado, notas no contratempo, linha rápida, compressão e diferentes BPMs, ganhos, blocos e fase estéreo. A associação entre evento e kick conhecido é individual, com tolerância de 75 ms; ataques adicionais são contados separadamente.

Comparação com o wheel **0.26.0**, importado separadamente, usando exatamente os mesmos sinais e sem clipping:

| Cenário | Corretos 0.26 | Falsos 0.26 | Corretos 0.27 | Falsos 0.27 |
|---|---|---|---|---|
| Kicks isolados · 120 BPM | 12/12 | 0 | 12/12 | 0 |
| Baixo sustentado · 120 BPM | 0/12 | 0 | 12/12 | 0 |
| Contratempo · 120 BPM | 0/12 | 0 | 12/12 | 0 |
| Linha rápida · 120 BPM | 9/12 | 3 | 9/12 | 1 |
| Mixagem comprimida · 120 BPM | 0/12 | 0 | 12/12 | 0 |
| Contratempo · 100 BPM | 1/10 | 10 | 10/10 | 0 |
| Contratempo · 128 BPM | 2/13 | 11 | 13/13 | 0 |
| Contratempo · 150 BPM | 1/15 | 13 | 15/15 | 0 |

Os números são **kicks confirmados pela estrutura**, não o total de candidatos graves. Os JSONs também mostram os candidatos brutos: o caminho espectral pode propor mais ataques de baixo, que continuam sujeitos à rejeição de perfil/grade.

No retorno com baixo forte, a 0.26 não detectou o drop no trecho de teste até 13 s; a 0.27 entrou em **12,064 s**, no primeiro kick conhecido em 12 s. Com baixo moderado, ambas entraram em 12,064 s. É uma medida de decisão causal no áudio sintético, sem transporte físico.

Processar os oito cenários, somando **56 s de áudio**, consumiu 5.0001 s de CPU na referência e 5.3280 s na 0.27. Isso corresponde a aproximadamente **8.93% → 9.51% de um núcleo**, ou +0.59 ponto percentual neste ensaio. São execuções consecutivas de DSP sem GUI, não um benchmark universal do computador ou do Traktor.

A validação nativa rodou oito segundos com baixo sustentado, **15 candidatos/15 confirmações**, 749 blocos e zero descartes. [Referência](resultado-kick-masking-v0.26.0.json) · [Resultado 0.27](resultado-kick-masking-v0.27.0.json) · [Ensaio nativo](resultado-kick-masking-ui-v0.27.0.json) · [Kick Monitor](../preview-kicks-baixo-v0.27.png).

O caso de linha rápida permanece uma limitação explícita. Um baixo percussivo pode ter ataque, queda e frequência próximos aos de um kick, especialmente na mesma posição da grade. Os resultados sintéticos não são uma estimativa de acurácia em todo o repertório eletrônico.

```powershell
.\.runtime\python312\python.exe -m pytest -q
.\.runtime\python312\python.exe -X utf8 scripts\validate_kick_masking.py
.\.runtime\python312\python.exe -X utf8 scripts\validate_kick_masking_ui.py
```

O ensaio opcional de referência aceita `--reference-wheel .runtime/dist-v0.26/beatlight_dmx-0.26.0-py3-none-any.whl`; o wheel anterior é importado em outro processo, sem substituir a instalação atual. Os ensaios não abrem entrada física, COM ou sessão Link nativa.

## Custo e limites de execução

O sensor conserva dois espectros anteriores, fundo e proposta de tamanho fixo, até 100 escores e 200 pontos de histórico. Só copia os bins utilizados, incluindo o vizinho necessário ao filtro. A grade usa até 16 eventos de aquisição e o perfil conserva até 16 referências. Não há rede, download de modelo ou dependência adicional.

As regras de apresentação leve e suspensão de gráficos ocultos da 0.26 permanecem. O DSP continua ativo para gerar os efeitos mesmo com a janela minimizada. Os ensaios desta rodada são curtos; não certificam seis horas reais de funcionamento nem a latência do hardware.

## Fundamentação

A escolha de observar mudanças locais no espectro segue a discussão de onsets em misturas polifônicas de [Dixon, Onset Detection Revisited, DAFx 2006](https://www.dafx.de/paper-archive/2006/papers/p_133.pdf). O uso de máximo espectral no passado foi inspirado na supressão causal de vibrato de [Böck e Widmer, Maximum Filter Vibrato Suppression for Onset Detection, DAFx 2013](https://www.dafx.de/paper-archive/2013/papers/09.dafx2013_submission_12.pdf). Esta implementação é uma adaptação própria para os candidatos graves do BEATLIGHT; não é a implementação de referência do SuperFlux nem um classificador treinado de kicks.
