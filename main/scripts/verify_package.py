"""Confere todas as fontes e recursos declarados contra o wheel local."""
import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import tomllib
from zipfile import ZipFile
from beatlight import __version__

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--wheel',type=Path,required=True)
parser.add_argument('--reference-wheel',type=Path)
parser.add_argument('--allow-pixel-changes',action='store_true',help='Permite uma nova versão do HTML do motor de efeitos')
parser.add_argument('--verify-music-unchanged',action='store_true',help='Confere DSP, estrutura e contratos byte a byte contra a referência')
parser.add_argument('--allow-structure-timing-changes',action='store_true',help='Exceção explícita somente para music/structure.py; registra os hashes da mudança')
parser.add_argument('--out',type=Path,required=True)
args = parser.parse_args()
if args.allow_structure_timing_changes and not args.verify_music_unchanged:parser.error('--allow-structure-timing-changes exige --verify-music-unchanged')
config = tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))
expected_version = config['project']['version']
assert __version__==version('beatlight-dmx')==expected_version
checked = []
with ZipFile(args.wheel) as archive:
    for path in sorted((root/'src').rglob('*.py')):
        member = path.relative_to(root/'src').as_posix()
        assert archive.read(member)==path.read_bytes(),member
        checked.append(member)
    data_root = f'beatlight_dmx-{expected_version}.data/data/'
    for folder,files in config['tool']['setuptools']['data-files'].items():
        for filename in files:
            path = root/filename
            member = data_root+folder+'/'+path.name
            assert archive.read(member)==path.read_bytes(),member
            checked.append(member)
    metadata = archive.read(f'beatlight_dmx-{expected_version}.dist-info/METADATA').decode()
    assert f'Version: {expected_version}' in metadata.splitlines()
    unchanged = []
    if args.reference_wheel:
        with ZipFile(args.reference_wheel) as reference:
            music_verified=[];music_changed={}
            if args.verify_music_unchanged:
                for member in archive.namelist():
                    if member.endswith('.py') and (member.startswith(('beatlight/dsp/','beatlight/music/')) or member=='beatlight/contracts.py'):
                        if args.allow_structure_timing_changes and member=='beatlight/music/structure.py':
                            assert archive.read(member)!=reference.read(member),'Exceção desnecessária: estrutura não mudou.'
                            music_changed[member]={'before':hashlib.sha256(reference.read(member)).hexdigest(),'after':hashlib.sha256(archive.read(member)).hexdigest()}
                            continue
                        assert archive.read(member)==reference.read(member),member
                        music_verified.append(member)
            for member in ('beatlight/music/tracker.py',
                           'beatlight/dsp/structure_features.py','beatlight/music/drop.py'):
                assert archive.read(member)==reference.read(member),member
            for member in archive.namelist():
                if member.startswith('beatlight/') and member in reference.namelist() and archive.read(member)==reference.read(member):
                    unchanged.append(member)
            for member in archive.namelist():
                if (member.endswith('/beatlight_pixel_studio.html') and not args.allow_pixel_changes) or member.endswith('-v0.22.0.bin'):
                    previous = next(name for name in reference.namelist() if name.endswith('/'+Path(member).name))
                    assert archive.read(member)==reference.read(previous),member
                    unchanged.append(member)
    firmware = root/'firmware/beatlight_esp32/dist/beatlight-wroom32-ws2812-300-v0.22.0.bin'
    firmware_hash = hashlib.sha256(firmware.read_bytes()).hexdigest()
    assert firmware_hash=='9b46db6cc3661fd19cc909819c064c2d8e68041c663088c98fd792a88cec4cff'
    multi=json.loads((root/'docs/resultado-esp32-v0.37.json').read_text(encoding='utf-8'))
    multi_path=root/multi['merged_file']
    assert hashlib.sha256(multi_path.read_bytes()).hexdigest()==multi['sha256']
    assert multi_path.stat().st_size==multi['bytes'] and multi['source_matches_build']
    for filename,digest in multi['source_sha256'].items():
        assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==digest,filename
report = dict(passed=True,version=expected_version,editable_version=version('beatlight-dmx'),
    files_verified=len(checked),wheel=str(args.wheel),wheel_sha256=hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
    verified=checked,unchanged_from_reference=unchanged,firmware_sha256=firmware_hash,
    music_verified=music_verified if args.reference_wheel else [],
    music_files_verified=len(music_verified) if args.reference_wheel else 0,
    music_intentionally_changed=music_changed if args.reference_wheel else {},
    firmware_bytes=firmware.stat().st_size,four_output_firmware_sha256=multi['sha256'],
    four_output_firmware_bytes=multi['bytes'],four_output_sources_verified=True,physical_device_used=False)
args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('verified','unchanged_from_reference','music_verified')},indent=2))
