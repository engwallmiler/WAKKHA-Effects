# Validação — versão 0.7

Registro: 2026-10-12. Windows x64, Python 3.12.10, NumPy 2.5.4, SciPy 1.18.1, PySide6 6.12.0 e PyAudioWPatch 0.2.12.9. Nenhuma dependência nova. Pacote e metadata locais atualizados para 0.7.0.

## Regressão automatizada

**229 testes passaram em 36,82 s**, incluindo os 212 casos anteriores. Evidência: resultado-pytest.txt. Após o ajuste final da largura dos botões, os **15 testes de interface passaram em 9,83 s**; evidência: resultado-pytest-ui-v0.7.txt. Histórico preservado em validacao-v0.6.md e resultado-pytest-v0.6.txt.

Os 17 casos acrescentados cobrem:

- Geometria do palco constante em todas as estruturas e motivos longos, nas janelas 1440 × 960, 1280 × 800 e 1100 × 760. O teste reproduziu o problema anterior: a altura oscilava entre 432, 364 e 392 px na maior janela.
- Rolls rápidos já presentes na entrada do breakdown; build-up sobre kicks contínuos; redução de graves; rejeição de virada curta e de percussão rápida que já integra o groove.
- Extração de ataques em 8 e 16 Hz, intervalo mínimo entre eventos e rejeição de hats agudos no detector de corpo percussivo.
- Pipeline completo com roll de médios misturado ao groove, sem exigir breakdown prévio e sem criar falso drop durante os kicks contínuos.
- Aceleração, branco progressivo, luminosidade e limite do master; movimento contínuo durante mudanças de estado e passagem da fase pelo ciclo completo; velocidade zero preservando a pose; troca de paleta após quatro kicks; metadados zerados fora do modo musical.

A bateria existente continua cobrindo perdas/reset, silêncio, aprovação causal do drop, oito kicks deduplicados, independência dos filtros, estéreo em oposição de fase, ganho reduzido, isolamento de falhas, manual/blackout/master, persistência e encerramento.

## Sessão em tempo real, palco aberto

validate_stage.py executou a aplicação Qt com modo musical, fonte sintética e palco visível durante 26 s. Capturas são mantidas em memória e codificadas em PNG após o encerramento: comprimir arquivos durante a sessão de QA havia provocado disputa com o processamento de áudio.

| Medida | Resultado |
|---|---|
| Áudio | 48 kHz, estéreo, blocos de 512 |
| Blocos recebidos | 2.436 |
| Descartes / falhas de continuidade | 0 / 0 |
| Groove aprendido | 4,031 s |
| Breakdown | 8,640 s |
| Build-up | 12,922 s |
| Drop | 20,031 s |
| Retorno ao groove no nono kick | 24,031 s |
| Contagem observada no drop | 1, 2, 3, 4, 5, 6, 7, 8 |
| Geometria do palco | Um único retângulo: x=0, y=194, largura=1157, altura=355 |
| Pico de branco do perfil na subida | 97% |
| Pico de intensidade antes do drop | 63,35%, com master em 80% |
| Pico de frequência de movimento na subida | 0,325 ciclos/s |
| Motor de iluminação | Aproximadamente 60 Hz; última janela 61 Hz |
| Processamento do último quadro de luz | 0,1585 ms |
| Erros de subsistemas | Nenhum |
| Encerramento | Workers encerrados, intensidades finais zero |

Evidência: resultado-palco-v0.7.json. Imagens inspecionadas: preview-breakdown.png, preview-buildup.png e preview-drop.png; preview-palco.png acompanha o drop. O script exige ausência de descartes e falhas de continuidade, sequência completa, oito kicks, geometria única, perfil branco acima de 85% e encerramento limpo.

## Composição offline

validate_structure.py analisou 28 s de sinal em aproximadamente **6,63 s** neste computador. Média: **2,28 ms/bloco**; percentil 99: **3,39 ms**. O caminho completo identificou drop em 20 s, contou oito kicks e voltou ao groove em 24 s. Tensão máxima na subida: aproximadamente 95%; pico de intensidade ao entrar no drop: 0,753, limitado pelo master de 0,8. Nenhuma falha de análise ou continuidade.

Evidência: resultado-estrutura-v0.7.json. O teste de regressão também repete a composição em ganho 25%. Esses números não garantem latência ou desempenho prolongado. Não houve reprodução sonora, gravação de áudio ou transmissão DMX.

## Avaliação com música real

O usuário aprovou captura/DSP, kicks, BPM/PLL e o motor inicial com Traktor e saída do notebook. Avaliou a primeira estrutura como relativamente satisfatória, relatando tremor do palco e um trecho de snares rápidos não promovido a build-up. A correção visual e os refinamentos musicais 0.7 têm os registros sintéticos acima; a faixa original desse relato não foi disponibilizada nem testada nesta sessão.

1. Fechar a janela antiga e reabrir iniciar.cmd. Capturar a saída do Traktor e começar por um groove com kicks regulares.
2. Abrir Stage Preview, clicar em Usar automação musical e Ativar motor.
3. Conferir que as mudanças de estrutura e os textos de motivo não redimensionam o palco. O redimensionamento manual da janela continua funcionando.
4. Repetir o trecho de snares rápidos, observando ataques, roll em médios, estado e tensão. Comparar também com hats e viradas curtas.
5. Observar velocidade crescente, maior luminosidade e clareamento antes do drop; depois, retorno à paleta, movimento amplo e contador 1/8 a 8/8.
6. Em Lighting Studio, alterar Movimento: ele limita a velocidade automática; zero congela a pose. Testar master, paleta, manual e blackout.
7. Se desejar repetir sem Traktor, selecionar Teste • breakdown e drop. O sinal de teste não é reproduzido nos alto-falantes.

A análise continua heurística: não classifica snares/upfilters individualmente e não detecta downbeat real. Um build-up sobre kicks contínuos é possível; confirmar drop ainda exige lacuna de kicks e retorno dos graves. Não foi implementada saída física DMX.
