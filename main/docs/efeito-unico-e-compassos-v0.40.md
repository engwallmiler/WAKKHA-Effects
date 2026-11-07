# Efeito único e referência de compassos — 0.40.0

## Usar um efeito por vez

No palco, selecione **AUTO SHOW** e ative **EFEITO ÚNICO**. O botão fica destacado. O mesmo ajuste funciona no ORGÂNICO e no CONTÍNUO FIXO.

Entre as trocas, o show global usa um único padrão. Durante a fusão, aparecem somente o anterior e o próximo; ao terminar, o anterior é descartado. Uma mudança rápida de estrutura interrompe a fusão conservando um dos dois padrões, sem capturar uma mistura e acrescentar um terceiro. A fusão ocupa no máximo metade do intervalo, garantindo um trecho com apenas um padrão; zero faz corte direto.

Desative **EFEITO ÚNICO** para voltar às combinações em camadas. O número de camadas e a configuração anterior são preservados. Os projetos antigos continuam abrindo em camadas, sem alterar sua montagem.

As fitas com **Efeito → Seguir show global** acompanham esse modo. Uma fita configurada com efeito próprio conserva essa escolha. Os picos ativados manualmente e os flashes continuam sendo acentos separados; para uma apresentação sem esses acentos, deixe **Picos por frase → Desligados** e os flashes desligados. O modo único não acrescenta picos automáticos por composição.

O drop mantém as oito posições já utilizadas pelo sistema, com um desenho de drop por entrada e sem as camadas adicionais do modo composto. A velocidade, a luminosidade e as cores continuam respondendo ao áudio.

## Personalizar repertório e duração

Abra **Efeitos e cores → Automação → Efeito único · repertório e duração**. Habilite os padrões que deseja usar e escolha a duração de cada um. **Padrão** herda **Trocar a cada**. É preciso manter ao menos um efeito habilitado; com um único disponível, a repetição é inevitável.

Os intervalos disponíveis são **1, 2, 4, 8, 16, 32, 64 e 128 compassos**, tanto no controle geral quanto por efeito. **Compassos por cena**, na área de aparência, acompanha o mesmo valor geral. Em 4/4, 32 compassos são 128 tempos; 128 compassos são 512 tempos. A contagem usa a grade e continua sem kick.

**Fusão musical** controla a transição. Brilho, velocidade, rastro, variação, cores e resposta musical continuam nos controles existentes. No modo único, **Elementos por combinação** e **Evolução das camadas** ficam desabilitados porque não se aplicam a um padrão isolado.

A duração representa o intervalo entre os inícios das trocas, incluindo a fusão. Mudanças de estrutura e comandos manuais têm prioridade e podem antecipar uma troca. Alterar o repertório vale para as próximas escolhas; alterar a duração do padrão atual recalcula seu agendamento. **Restaurar repertório e durações** volta a permitir todos os padrões e a herdar a duração geral.

A escolha manual de um padrão ou do contínuo fixo tem prioridade sobre o repertório automático.

O modo, o repertório e as durações fazem parte do projeto salvo automaticamente e do JSON exportado.

No ensaio controlado, o Auto Show com Aurora isolada manteve 30 fps: desenho médio de **1,54 ms**, frente a **2,14 ms** da combinação Aurora + Maré + Onda Vertical na referência 0.39. A CPU do renderer passou de **19,3 para 13,5% de um núcleo**, e a memória residente de **196,4 para 167,5 MiB**. São medições curtas comparando um e três padrões, sem representar a CPU total do computador ou garantir os mesmos valores em outra máquina. [Referência](resultado-pixel-render-reference-v0.39.json) · [Efeito único](resultado-pixel-render-single-v0.40.json).

## Marcar o compasso de referência

O botão **Marcar compasso 1**, junto dos controles do palco, inicia a contagem no instante em que é pressionado. Ele conserva o efeito atual e agenda a próxima troca após sua quantidade de compassos. Se a duração atual for 32 compassos, conta 32 a partir desse momento.

Para uma troca regular, escolha **Variação automática → A cada N compassos**. **Compassos + novos elementos**, **Somente novos elementos** e **Manter padrão** continuam disponíveis com suas regras; o botão de referência não muda essa seleção.

O texto abaixo da prévia mostra o compasso contado desde a marcação e quanto falta para a próxima troca. **Desde a 0.42**, outro toque desmarca a referência e apaga o destaque/LED. Para uma nova contagem, desmarque e marque no instante desejado. A referência também funciona nas apresentações em camadas. [Comportamento atualizado](drop-bpm-e-referencia-v0.42.md).

Essa marcação é própria das trocas: **não muda BPM, grade do áudio/Link, Sincronizar 1/8 nem Sincronizar pico**. Mudanças de estrutura têm prioridade, preservando a referência do ciclo de trocas. Correções de relógio deslocam origem e prazos juntos; períodos perdidos durante uma interrupção são descartados, sem executar uma sequência de efeitos atrasados.

A referência vale para a sessão. Parar a captura, trocar a fonte de simulação ou carregar um projeto limpa a marcação. No áudio ao vivo, o botão exige uma grade recente; na demonstração, usa o relógio interno.

## Mapear na X1 MK1

Em **Controladora MIDI**, selecione a nova função **Marcar compasso 1 · trocas**. Use **Ativar Learn → pressionar o botão da X1 → Encerrar Learn → Salvar perfil**. Esse comando também funciona com o aplicativo minimizado.

O retorno LED é opcional e usa o mesmo editor das demais funções. Ele fica aceso enquanto existe uma referência marcada e apaga quando ela é limpa. Os perfis MIDI anteriores são migrados em memória, preservando as dez associações anteriores e deixando a nova função sem associação. O próximo **Salvar perfil** grava o formato 2, agora com onze funções. Não há conexão automática com a controladora.

[Guia da X1 MK1](midi-x1-mk1.md) · [Auditoria de buffers](auditoria-buffers-v0.40.md) · [Validação](validacao.md).
