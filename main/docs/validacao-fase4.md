# Validação — fase 4, versão 0.3

Registro: **2026-10-12 (UTC)**. Windows x64, Python 3.12.10, NumPy 2.5.4, SciPy 1.18.1, PySide6 6.12.0 e PyAudioWPatch 0.2.12.9. Dependências completas: requirements-windows-py312.lock.txt.

## Resultados automatizados

**112 testes passaram em 10,96 s**, incluindo os 81 casos anteriores. Evidência: resultado-pytest.txt. O registro anterior foi preservado em validacao-fase3.md e resultado-pytest-fase3.txt.

| Área | Verificação acrescentada |
|---|---|
| Kicks conhecidos | Uma detecção por onset, erro absoluto inferior a 65 ms, em sinais com baixo contínuo, médios e chimbal no contratempo. Casos: 90/120/128/138/160 BPM; 44,1/48 kHz; ganhos 1/0,3/0,12/0,015; um caso com ruído determinístico. |
| Rejeição | Silêncio, DC, grave sustentado, grave com modulação lenta, ataques agudos e ruído sem kicks não produziram eventos nesses sinais de teste. |
| Força | Refino do pico evita medir somente o começo fraco do ataque. Um kick reduzido no meio da sequência recebe força relativa menor. |
| Intervalo mínimo | Eventos respeitam o período refratário; aumentar para 400 ms rejeita parte dos ataques separados por 375 ms. |
| Estéreo e blocos | Oposição de fase e blocos de 113/512/1024/2048 amostras preservam as decisões; estado e históricos permanecem limitados. |
| Independência | FFT visual de 8192 e passa-alta de 4 kHz mantêm a contagem de kicks da análise original. |
| Continuidade | Reset de janelas, histórico e intervalos em lacunas ou flags de driver, inclusive no detector usado diretamente. |
| Falhas opcionais | Falha de kicks mantém espectro/medidores; falha espectral mantém kicks. Erro é registrado uma vez por formato, com recuperação ao trocar para outro formato. |
| Preferências | Migração v1/v2 → v3 preserva captura e DSP conhecidos, usa padrões para novos campos e valida ajustes de kicks. |
| Interface | Iniciar/parar no Kick Monitor, eventos, origem sintética explícita, estado congelado após parar, parâmetros bloqueados durante captura, importação aplicada ao analisador e parâmetros inválidos preservando os anteriores. |

São sinais sintéticos com onsets conhecidos; esses resultados não são uma medição de precisão/recall em músicas reais.

## Sessão sintética com entrega em tempo real

Em 12 s, usando 48 kHz, estéreo e blocos de 512:

- 1.125 blocos processados, zero descartes e zero falhas de continuidade.
- 23 kicks detectados; 16 eventos retidos e 200 pontos de histórico, conforme os limites.
- Sem erros de captura, espectro ou detector.
- Em 907 snapshots observados, DSP médio de 2,31 ms, percentil 95 de 3,29 ms e máximo de 5,71 ms.

Evidência: resultado-sintetico-fase4.json. O script validate_synthetic.py permite repetir a sessão sem tocar som. A amostragem de métricas por polling não cobre obrigatoriamente todos os blocos. Não é um benchmark de Traktor, CPU total ou atraso acústico, nem teste prolongado de estabilidade.

## Interface

Renderizadas as páginas de áudio, espectro, kicks e configurações em 1440 × 960. Arquivos: preview.png, preview-espectro.png, preview-kicks.png e preview-configuracoes.png. O painel de kicks foi inspecionado visualmente; gráficos, métricas e tabela receberam dados sintéticos reais do pipeline. Páginas com mais conteúdo usam rolagem.

## Validação com Traktor

O usuário relatou que a versão anterior funcionou perfeitamente com o Traktor usando a saída de som do notebook. Isso registra a aprovação funcional de captura/DSP no cenário do usuário, sem inventar medidas de latência ou métricas dessa sessão.

**A detecção de kicks da fase 4 ainda não foi avaliada pelo usuário com faixas reais.** Os registros automáticos de WASAPI anteriores permanecem em validacao-fase3.md e validacao-fase1-2.md; resultados silenciosos ou sem blocos não são apresentados como validação de música real.

## Roteiro desta fase

1. Fechar a aplicação anterior, abrir iniciar.cmd e capturar a saída usada pelo Traktor.
2. Abrir Kick Monitor; após aproximadamente 300 ms de áudio, observar os eventos e o gráfico.
3. Comparar com trechos de kick regular, baixo contínuo, viradas e pausas. Verificar eventos perdidos e extras em faixas com masterizações diferentes.
4. Parar, alterar sensibilidade/faixa/piso/intervalo em Configurações, salvar e reiniciar. Comparar o mesmo trecho.
5. Confirmar que alterar somente FFT/pré-filtro do espectro mantém o comportamento do detector.
6. Acompanhar descartes, continuidade e tempo DSP em uma sessão prolongada. Exportar diagnóstico se houver problema; não é necessário gravar áudio.

Confiança é heurística; contagem de kicks não é BPM. A próxima fase será o rastreador BPM/PLL, depois da avaliação deste detector.
