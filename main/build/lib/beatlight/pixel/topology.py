"""Conexões lógicas de barras: continuidade ordenada e cópias simultâneas."""


def validate_patch(patch, strip_ids):
    if not isinstance(patch,dict) or type(patch.get('version')) is not int or patch['version']!=1:
        raise ValueError('Conexões de fitas inválidas.')
    runs,mirrors=patch.get('runs'),patch.get('mirrors')
    if not isinstance(runs,list) or len(runs)>32 or not isinstance(mirrors,list) or len(mirrors)>32:
        raise ValueError('Use até 32 conexões de cada tipo.')
    roots=set(strip_ids);used=set();run_ids=set()
    for run in runs:
        if not isinstance(run,dict):raise ValueError('Fita lógica inválida.')
        rid,name,segments=run.get('id'),run.get('name'),run.get('segments')
        if not isinstance(rid,str) or not 1<=len(rid)<=64 or rid in roots or rid in run_ids:
            raise ValueError('Identificador de fita lógica repetido ou inválido.')
        if not isinstance(name,str) or not name.strip() or len(name)>48:
            raise ValueError('Informe um nome para a fita lógica.')
        if not isinstance(segments,list) or not 1<=len(segments)<=32:
            raise ValueError('Escolha ao menos uma barra para a continuidade.')
        run_ids.add(rid)
        for segment in segments:
            if not isinstance(segment,dict) or not isinstance(segment.get('strip_id'),str) or segment['strip_id'] not in roots or type(segment.get('reverse')) is not bool:
                raise ValueError('Trecho de fita desconhecido ou sentido inválido.')
            sid=segment['strip_id']
            if sid in used:raise ValueError('Uma barra só pode pertencer a uma fita lógica.')
            used.add(sid)
    run_members={run['id']:{part['strip_id'] for part in run['segments']} for run in runs}
    roots=roots|run_ids
    sources=set();source_bars=set();targets=set()
    for mirror in mirrors:
        if not isinstance(mirror,dict) or not isinstance(mirror.get('source'),str) or mirror['source'] not in roots or mirror['source'] in sources:
            raise ValueError('Referência de simetria desconhecida ou repetida.')
        source=mirror['source'];members=mirror.get('targets')
        if mirror.get('mode','fit') not in ('exact','fit'):
            raise ValueError('Modo de cópia inválido.')
        if not isinstance(members,list) or not 1<=len(members)<=31:
            raise ValueError('Escolha os destinos do grupo de simetria.')
        sources.add(source)
        source_bars.update(run_members.get(source,{source}))
        for target in members:
            if not isinstance(target,dict) or not isinstance(target.get('id'),str) or target['id'] not in roots or type(target.get('reverse')) is not bool:
                raise ValueError('Destino de simetria desconhecido ou sentido inválido.')
            tid=target['id']
            bars=run_members.get(tid,{tid})
            if bars & targets:raise ValueError('Cada barra de destino só pode seguir uma referência.')
            targets.update(bars)
    if source_bars & targets:raise ValueError('Uma referência não pode ser destino de outro grupo; reúna as cópias no mesmo grupo.')
    return patch


def validate_exact_copies(patch,lines,strips):
    bars={strip['id']:(line['pixels'],strip['profile']) for strip,line in zip(strips,lines)}
    runs={run['id']:run['segments'] for run in patch['runs']}
    def signature(identity):
        result=[]
        for part in runs.get(identity,[{'strip_id':identity}]):
            pixels,profile=bars[part['strip_id']]
            result.extend(['rgb' if profile in ('ws2811','ws2812') else profile]*pixels)
        return result
    for group in patch['mirrors']:
        if group.get('mode')!='exact':continue
        source=signature(group['source'])
        for target in group['targets']:
            dest=signature(target['id'])
            if target['reverse']:dest.reverse()
            if source!=dest:
                raise ValueError('Cópia exata exige a mesma quantidade de pixels e formato RGB/RGBW.')
