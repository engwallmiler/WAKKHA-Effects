from pathlib import Path
import json
import os
import shutil
import subprocess
import pytest
from beatlight.pixel.usb_protocol import encode,HELLO,CONFIG,FRAME,INFO,ACK,Decoder,OutputConfig


def test_actual_esp32_sketch_with_python_wire_vectors_and_mock_peripherals(tmp_path):
    compiler=shutil.which('g++')
    if not compiler:pytest.skip('Compilador C++ não instalado para ensaio host do firmware')
    root=Path(__file__).resolve().parents[1]
    executable=tmp_path/('esp32-firmware-test.exe' if os.name=='nt' else 'esp32-firmware-test')
    built=subprocess.run([compiler,'-std=c++11','-Wall','-Wextra','-static-libgcc','-static-libstdc++',
        '-I',str(root/'tests/esp32_stubs'),str(root/'tests/esp32_firmware_test.cpp'),'-o',str(executable)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
    assert built.returncode==0,built.stderr
    rgb=bytes(channel for pixel in range(300) for channel in (pixel%256,255-pixel%256,pixel//256))
    input_path=tmp_path/'wire-input.bin';output_path=tmp_path/'wire-output.bin'
    input_path.write_bytes(b'boot log\r\n'+encode(CONFIG,10,OutputConfig().payload())+encode(FRAME,11,rgb))
    result=subprocess.run([str(executable),str(input_path),str(output_path)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=10)
    assert result.returncode==0,result.stdout+result.stderr
    replies=Decoder().feed(output_path.read_bytes())
    assert any(r.kind==INFO and json.loads(r.payload)['device']=='BEATLIGHT-ESP32' for r in replies)
    assert any(r.kind==ACK and r.sequence==11 and r.payload[:2]==bytes((FRAME,0)) for r in replies)
