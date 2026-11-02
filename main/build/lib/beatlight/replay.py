"""Ferramenta offline: python -m beatlight.replay --help."""
import argparse
from dataclasses import replace
from html import escape
import json
from pathlib import Path
import sys
from beatlight.configuration.store import Settings,SettingsStore
from beatlight.diagnostics.replay import replay


def preview(report):
    duration = report['audio_seconds']
    rows = []
    for title, items, color in (
        ('Kicks rotulados', [{'at':t} for t in report['annotations'].get('kicks',[])], '#89b9ff'),
        ('Kicks confirmados', report['confirmed_kicks'], '#6de9c1'),
        ('Drops rotulados', [{'at':t} for t in report['annotations'].get('drops',[])], '#efc275'),
        ('Drops detectados', report['detected_drops'], '#ff8297'),
    ):
        # O JSON conserva tudo; a prévia tem um número fixo de marcas no DOM.
        stride = max(1,(len(items)+3999)//4000)
        marks = ''.join(f'<line x1="{item["at"]/duration*1000:.3f}" x2="{item["at"]/duration*1000:.3f}" y1="4" y2="32" stroke="{color}"/>' for item in items[::stride])
        rows.append(f'<label>{title} · {len(items)} eventos</label><svg viewBox="0 0 1000 36" preserveAspectRatio="none">{marks}</svg>')
    metrics = []
    for kind, title in (('kicks','Kicks'),('drops','Drops')):
        value = report['metrics'][kind]
        if value is None:
            metrics.append(f'<tr><td>{title}</td><td colspan="5">Sem rótulos; não avaliado</td></tr>')
            continue
        delay = value['available_delay_ms']
        metrics.append(f'<tr><td>{title}</td><td>{value["true"]}/{value["truth"]}</td><td>{value["false"]}</td><td>{value["missed"]}</td><td>{delay["median"]:.1f} ms</td><td>{delay["p95"]:.1f} ms</td></tr>' if delay else
            f'<tr><td>{title}</td><td>{value["true"]}/{value["truth"]}</td><td>{value["false"]}</td><td>{value["missed"]}</td><td>—</td><td>—</td></tr>')
    gates = ''.join(f'<tr><td>{escape(key)}</td><td>{value}</td></tr>' for key,value in sorted(report['decision_gates'].items()))
    changes = ''.join(f'<tr><td>{item["available_at"]:.3f} s</td><td>{escape(item["state"])}</td><td>{escape(item["reason"])}</td></tr>' for item in report['transitions'])
    audio_url = escape(Path(report['audio']).as_uri(), quote=True)
    return f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>BEATLIGHT · Replay causal</title>
<style>body{{background:#101619;color:#dfebef;font:15px system-ui;max-width:1200px;margin:32px auto;padding:0 20px}}h1,h2{{color:#6de9c1}}table{{width:100%;border-collapse:collapse;margin:20px 0}}td,th{{padding:10px;border-bottom:1px solid #30404a;text-align:left}}svg{{display:block;width:100%;height:36px;background:#1b252c;margin:8px 0 18px}}audio{{width:100%}}small,p{{color:#a5b8c4}}button{{padding:8px}}</style>
<h1>Replay causal · BEATLIGHT {escape(report['version'])}</h1><p>{escape(Path(report['audio']).name)} · {duration:.2f} s · grade {escape(report['grid_mode'])} · bloco {report['block_size']} samples</p>
<audio controls preload="metadata" src="{audio_url}"></audio><p>O áudio é reproduzido pelo navegador somente ao apertar Play. Este relatório não envia comandos de iluminação. Clique numa linha para ir àquele instante.</p>
{''.join(rows)}<small>Escala: 0 a {duration:.2f} s. Máximo de 4.000 marcas por linha; os dados completos estão no JSON.</small>
<h2>Precisão e latência</h2><table><tr><th>Evento</th><th>Corretos</th><th>Falsos</th><th>Perdidos</th><th>Atraso mediano</th><th>Atraso p95</th></tr>{''.join(metrics)}</table>
<p>Atraso medido até os samples estarem disponíveis, incluindo janela FFT e bloco. Timestamp do ataque é avaliado separadamente no JSON. Os rótulos não alimentam o detector; BPM dos rótulos só define a tolerância de avaliação de drops.</p>
<h2>Etapas de decisão</h2><p>Contagens de avaliações; um candidato pode ter mais de uma tentativa curta. Consulte o arquivo decisions.jsonl para o candidato e limiar específicos.</p><table>{gates}</table>
<h2>Estrutura entregue</h2><table><tr><th>Disponível em</th><th>Estado</th><th>Motivo</th></tr>{changes}</table>
<script>for(const row of document.querySelectorAll('svg'))row.addEventListener('click',e=>{{const r=row.getBoundingClientRect();document.querySelector('audio').currentTime=Math.max(0,Math.min({duration},(e.clientX-r.left)/r.width*{duration}));}});</script></html>'''


def main(argv=None):
    parser = argparse.ArgumentParser(description='Replay causal de WAV PCM com rótulos em segundos; não abre captura ou saídas físicas.')
    parser.add_argument('audio',type=Path)
    parser.add_argument('labels',type=Path)
    parser.add_argument('--out',type=Path,required=True,help='Diretório NOVO para report.json, report.html e decisions.jsonl')
    parser.add_argument('--block-size',type=int,default=512)
    parser.add_argument('--settings',type=Path,help='Preferências exportadas da aplicação; somente parâmetros de análise são usados')
    parser.add_argument('--grid-mode',choices=('integer','continuous'),help='Padrão inteiro, ou modo das preferências fornecidas')
    parser.add_argument('--fixed-bpm',type=int,help='BPM fixo do operador; não usa o BPM dos rótulos')
    args = parser.parse_args(argv)
    try:
        # Não sobrescreve report anterior, áudio ou rótulos por acidente.
        args.out.mkdir(parents=True,exist_ok=False)
        settings = SettingsStore.import_file(args.settings) if args.settings else Settings()
        settings = replace(settings,beat_grid_mode='manual' if args.fixed_bpm is not None else args.grid_mode or settings.beat_grid_mode,
            beat_fixed_bpm=args.fixed_bpm if args.fixed_bpm is not None else settings.beat_fixed_bpm)
        settings.beat_config()
        report = replay(args.audio,args.labels,block_size=args.block_size,settings=settings,
            trace_path=args.out/'decisions.jsonl',progress=lambda at,total:print(f'{at:.0f}/{total:.0f} s',file=sys.stderr))
        (args.out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        (args.out/'report.html').write_text(preview(report),encoding='utf-8')
        print(f'Replay concluído: {args.out.resolve()/"report.html"}')
        for kind in ('kicks','drops'):
            item = report['metrics'][kind]
            if item:
                print(f'{kind}: {item["true"]}/{item["truth"]} corretos, {item["false"]} falsos, {item["missed"]} perdidos')
        return 0
    except (OSError,ValueError,KeyError,RuntimeError) as exc:
        print(f'Replay não concluído: {exc}',file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())
