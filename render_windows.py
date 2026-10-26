"""Off-screen development renders under a private virtual display; not Windows runtime QA."""
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import zipfile
from PIL import Image

import windows_build

ROOT = Path(__file__).resolve().parent
output = ROOT / 'build/renders'
output.mkdir(parents=True,exist_ok=True)
environment = windows_build.mono_environment()
environment['FREECUR_RENDER'] = '1'
environment['PATH'] = str(windows_build.TOOLCHAIN/'bin') + os.pathsep + environment['PATH']
environment['LD_LIBRARY_PATH'] = os.pathsep.join(str(x) for x in [windows_build.TOOLCHAIN/'lib',windows_build.TOOLCHAIN/'lib/x86_64-linux-gnu'])
with tempfile.TemporaryDirectory(prefix='free-cur-render-') as folder:
    with zipfile.ZipFile(ROOT/'dist/downloads/free-cur-windows-collection.zip') as archive:
        archive.extractall(folder)
    for program,argument in [(Path(folder)/'FreeCur.exe',str(output)),(ROOT/'dist/downloads/FreeCur-Setup-x64.exe',str(output/'setup.png'))]:
        subprocess.run(['xvfb-run','-a','--server-args=-screen 0 1280x900x24 -nolisten tcp','mono',str(program),'--render-preview',argument],
                       env=environment,check=True,timeout=50)
preview=ROOT/'dist/client-preview';preview.mkdir(exist_ok=True)
for name in ['setup.png','manager.png']:
    with Image.open(output/name) as image:
        assert len(image.convert('RGB').getcolors(image.width*image.height))>100,'Blank or incomplete UI render'
    shutil.copy2(output/name,preview/name)
print(json.dumps(dict(output=str(output),scope='Off-screen Mono render, not Windows installation verification')))
