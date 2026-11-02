# Grade virtual de picos — 0.31

Reinicie a aplicação e a captura. Em **Configurações → BPM e sincronização**, mantenha **BPM inteiro estável**, ou informe um BPM fixo. O padrão continua sendo inteiro estável; não há uma nova opção para ativar. Ableton Link continua fornecendo seu próprio período, inclusive fracionário.

## Como os kicks são procurados

O BPM fornece o intervalo esperado. Um caminho complementar procura **máximos locais reais**, usando os descritores espectrais já calculados pela análise musical. Subtrai por frequência um fundo causal curto para reduzir a influência do baixo sustentado. Não adiciona FFT, modelo de aprendizado ou dependência.

Três picos consecutivos, com intervalo compatível e espectro, forma e potência semelhantes, estabelecem uma grade ancorada nos máximos. Havendo perfil de kick aprendido, esse perfil filtra também os picos usados para escolher a fase; assim a busca não fica obrigada a reproduzir a fase da grade anterior. Sem perfil suficiente, a fase anterior limita a aquisição inicial.

A comparação da forma usa seis amostras da subida e queda em torno do máximo. O comparador considera a potência **do transiente**, não apenas a altura da mixagem. Há tolerância porque a soma de kick e bassline pode reforçar ou cancelar parte da energia medida.

Depois da aquisição, cada posição abre uma janela de ±12% do tempo: aproximadamente ±56 ms a 128 BPM. Picos fora dela são rejeitados por esse caminho. Entre os candidatos da janela, escolhe o que melhor combina espectro, forma e potência. A fase recebe pequenos ajustes; o período é fornecido pelo relógio e não é estimado novamente pelo comparador.

## Confirmação e proteção da estrutura

A recuperação atua no groove/contexto inicial, depois da confirmação normal, e exige concordância adicional com o perfil espectral/decaimento do kick aprendido. Se o ataque já foi confirmado, ele não é contado novamente. A recuperação não reaprende o perfil nem altera o BPM com uma mistura de horários de começo e de máximo do ataque.

Desvios de fase maiores continuam exigindo quatro ataques regulares e ausência de referências alinhadas, usando as proteções existentes contra mudança para o contratempo. Quando a proposta vem dos picos, essa correção altera somente a fase. O modo manual preserva sua política anterior de fase.

Retornos de breakdown/build-up e os oito kicks do drop conservam a confirmação própria de identidade, potência e cadência. Um pico recorrente isoladamente não autoriza o drop. O caminho normal de primeira resposta ao drop não ganha uma espera adicional.

Sem ataque acústico, a grade continua prevendo posições, mas **não produz kicks**. Silêncio sustentado, mudança de fonte e descontinuidade da captura descartam as referências. Os históricos e filas têm limites fixos.

## O que observar no Kick Monitor

- **Grade de tempo:** relógio musical existente.
- **Grade de picos reais**, em azul: projeção ancorada nos máximos recorrentes; continua sendo uma previsão entre ataques.
- **Kick confirmado**, em verde: evento aprovado; a tabela identifica recuperações como **Pico + BPM**.
- A linha de detalhes mostra espectro, forma, razão de potência e erro de fase do último pico compatível. Esses números não são probabilidades de reconhecimento de instrumento.

O contador de candidatos brutos pode continuar incluindo ataques de baixo. Para avaliar o resultado, use os kicks confirmados e compare com a faixa.

## Validação e limites

Os sinais de teste são sintéticos, sem clique agudo auxiliar. Nos dois cenários com baixo contínuo em 65 Hz, a confirmação passou de **20/24 para 22/24 kicks**, com **zero falsos positivos** e BPM mantido em 128. Os casos de baixo em 105 Hz conservaram 22/24 a 48 kHz e 21/24 a 44,1 kHz com blocos de 113 amostras. Não houve drops falsos nesses casos. Retirar os kicks, mantendo baixo sustentado ou ataques no contratempo, não criou recuperações ou drops.

A disponibilidade dos kicks recuperados ficou em até **178,25 ms** após o início rotulado nesses testes, incluindo espera causal, FFT e entrega por blocos. Essa é uma recuperação de ataques que antes eram perdidos; não substitui a resposta normal mais rápida quando disponível.

As medições não demonstram a mesma taxa de acerto em músicas reais. Baixos percussivos com assinatura e posição semelhantes ao kick continuam ambíguos. Para avaliar uma faixa problemática, use o [replay causal com rótulos](replay-causal.md).

[Referência 0.30](resultado-peak-grid-reference-v0.30.json) · [Resultado 0.31](resultado-peak-grid-v0.31.json) · [Inspeção nativa](resultado-peak-grid-ui-v0.31.json) · [Imagem do monitor](../preview-peak-grid-v0.31.png).
