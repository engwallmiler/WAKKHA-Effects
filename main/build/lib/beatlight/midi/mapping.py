"""Perfis pequenos, Learn explícito e decisões MIDI sem acesso a widgets/drivers."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

ACTIONS={'drop':'Drop agora','breakdown':'Breakdown manual','groove':'Groove manual','buildup':'Build-up manual',
         'peak_level':'Intensidade do pico','sync_1_8':'Sincronizar beat 1/8','next_combo':'Próxima combinação · no compasso',
         'auto':'Auto Show','organic':'Orgânico','continuous':'Contínuo','cue_sync':'Marcar compasso 1 · trocas'}
MODES=('absolute','relative_twos','relative_binary','relative_sign')


def default_profile():
    return {'version':2,'input_port':'','output_port':'','detected_feedback':False,
            'mappings':{action:{'input':None,'output':None} for action in ACTIONS}}


def address(data,output=False):
    if not isinstance(data,dict) or data.get('kind') not in ('note','cc') or type(data.get('channel')) is not int or not 1<=data['channel']<=16 or type(data.get('number')) is not int or not 0<=data['number']<=127:
        raise ValueError('Use Note ou CC, canal 1 a 16 e número 0 a 127.')
    if output:
        if any(type(data.get(key)) is not int or not 0<=data[key]<=127 for key in ('on','off')):raise ValueError('Valores de LED devem estar entre 0 e 127.')
    elif data.get('mode') not in MODES or data['kind']=='note' and data['mode']!='absolute':raise ValueError('Modo de controle MIDI inválido.')
    return data['kind'],data['channel'],data['number']


def validate_profile(profile):
    if not isinstance(profile,dict) or type(profile.get('version')) is not int or profile['version'] not in (1,2):raise ValueError('Perfil MIDI inválido.')
    profile=deepcopy(profile)
    if any(not isinstance(profile.get(key),str) or len(profile[key])>128 for key in ('input_port','output_port')) or type(profile.get('detected_feedback')) is not bool:raise ValueError('Portas ou opção de retorno MIDI inválidas.')
    rows=profile.get('mappings')
    if profile['version']==1 and isinstance(rows,dict) and set(rows)==set(ACTIONS)-{'cue_sync'}:
        rows['cue_sync']={'input':None,'output':None};profile['version']=2
    if profile['version']!=2 or not isinstance(rows,dict) or set(rows)!=set(ACTIONS):raise ValueError('O perfil deve conter as funções MIDI conhecidas.')
    inputs=set();outputs=set()
    for action,row in rows.items():
        if not isinstance(row,dict) or set(row)!=set(('input','output')):raise ValueError('Mapeamento MIDI inválido.')
        for key,used in (('input',inputs),('output',outputs)):
            if row[key] is None:continue
            identity=address(row[key],key=='output')
            if identity in used:raise ValueError('Esse endereço MIDI já está associado a outra função. Limpe ou altere a associação anterior.')
            used.add(identity)
        if action!='peak_level' and row['input'] and row['input']['mode']!='absolute':raise ValueError('Encoders relativos são usados somente para intensidade do pico.')
    return deepcopy(profile)


def read_profile(path):
    path=Path(path)
    if not path.exists():return default_profile()
    if path.stat().st_size>32768:raise ValueError('Perfil MIDI excede 32 KB.')
    return validate_profile(json.loads(path.read_text(encoding='utf-8')))


def save_profile(path,profile):
    data=validate_profile(profile);path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name);json.dump(data,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:
        if temporary and temporary.exists():temporary.unlink()


def decode(word):
    if type(word) is not int or not 0<=word<=0xffffffff:return None
    status=word&255;kind=status&0xf0;number=(word>>8)&255;value=(word>>16)&255
    if kind not in (0x80,0x90,0xb0) or number>127 or value>127:return None
    return ('cc' if kind==0xb0 else 'note',(status&15)+1,number,0 if kind==0x80 else value)


def wire(binding,value):
    return ((0x90 if binding['kind']=='note' else 0xb0)|(binding['channel']-1))|(binding['number']<<8)|(value<<16)


class MidiMapper:
    def __init__(self,profile=None):
        self.profile=validate_profile(profile or default_profile());self.learning=None;self.candidate=None;self.pressed={};self.peak=.75
        self._index={}
        self.configure(self.profile)

    def configure(self,profile):
        self.profile=validate_profile(profile);self.pressed.clear()
        self._index={address(row['input']):action for action,row in self.profile['mappings'].items() if row['input']}

    def start_learn(self,action,mode='absolute'):
        if action not in ACTIONS or mode not in MODES:raise ValueError('Função ou modo de Learn inválido.')
        self.learning=action;self.learning_mode=mode if action=='peak_level' else 'absolute';self.candidate=None;self.pressed.clear()

    def stop_learn(self):
        action=self.learning;candidate=self.candidate;self.learning=None;self.candidate=None;self.pressed.clear()
        if action and candidate:
            profile=deepcopy(self.profile);profile['mappings'][action]['input']=candidate;self.configure(profile)
            return True
        return False

    def accept(self,word):
        message=decode(word)
        if message is None:return None
        kind,channel,number,value=message;identity=message[:3]
        if self.learning:
            if kind=='note' and not value:return None
            if self.candidate is None:self.candidate={'kind':kind,'channel':channel,'number':number,'mode':self.learning_mode if kind=='cc' else 'absolute'}
            return None
        action=self._index.get(identity)
        if not action:return None
        binding=self.profile['mappings'][action]['input']
        if action=='peak_level':
            if kind=='note' and value==0:return None
            mode=binding['mode']
            if mode=='absolute':self.peak=value/127
            else:
                delta=(value if value<64 else value-128) if mode=='relative_twos' else value-64 if mode=='relative_binary' else value if value<64 else -(value-64)
                if mode=='relative_sign' and value in (0,64):delta=0
                if not delta:return None
                self.peak=max(0,min(1,self.peak+delta/127))
            return action,self.peak
        down=value>0 if kind=='note' else value>=64;previous=self.pressed.get(identity,False);self.pressed[identity]=down
        return (action,None) if down and not previous else None

    def feedback(self,state):
        result={}
        for action,row in self.profile['mappings'].items():
            binding=row['output']
            if not binding:continue
            if action in ('groove','breakdown','buildup'):
                active=state.get('structure')==action if self.profile['detected_feedback'] else state.get('manual_structure')==action
            elif action=='drop':active=state.get('drop',False)
            elif action=='auto':active=state.get('mode')=='auto' and not state.get('continuous',False)
            elif action=='organic':active=state.get('mode')=='organic' and not state.get('continuous',False)
            elif action=='continuous':active=state.get('continuous',False)
            elif action=='sync_1_8':active=state.get('sync',False)
            elif action=='cue_sync':active=state.get('cue_sync',False)
            elif action=='next_combo':active=state.get('queued',False)
            else:active=state.get('peak_level',0)
            level=round(binding['off']+(binding['on']-binding['off'])*max(0,min(1,active)))
            identity=address(binding,True);result[identity]=(wire(binding,level),wire(binding,binding['off']))
        return result
