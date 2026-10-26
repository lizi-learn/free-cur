"""Read every generated package, and load Linux cursors with the real Xcursor library."""
import ctypes
import ctypes.util
import hashlib
import io
import json
import plistlib
import struct
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

from build import ALIASES, DIST, MAC_ROLES, ROLES, WINDOWS_SIZES


def check_windows_exe(path, machine):
    data = path.read_bytes()
    assert data[:2] == b'MZ'
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    assert data[pe:pe+4] == b'PE\0\0'
    assert struct.unpack_from('<H', data, pe+4)[0] == machine
    assert struct.unpack_from('<H', data, pe+24+68)[0] == 2, 'GUI subsystem expected'
    assert b'asInvoker' in data and b'requireAdministrator' not in data


def check_cur(data,expected_sizes=None):
    reserved, kind, count = struct.unpack_from('<HHH', data)
    assert reserved == 0 and kind == 2 and 1<=count<=64
    sizes=[]
    for i in range(count):
        w, h, _, _, x, y, length, offset = struct.unpack_from('<BBBBHHII', data, 6+i*16)
        w, h = w or 256, h or 256
        assert w==h;sizes.append(w)
        assert 0 <= x < w and 0 <= y < h
        assert offset >= 6+count*16 and offset+length <= len(data)
        assert struct.unpack_from('<I', data, offset)[0] == 40
    if expected_sizes is not None:assert sizes==list(expected_sizes),(sizes,expected_sizes)
    image = Image.open(io.BytesIO(data))
    assert image.size == (max(sizes),max(sizes))
    image.load()


def check_ani(data,expected_ms=None,expected_sizes=None):
    assert data[:4] == b'RIFF' and data[8:12] == b'ACON'
    assert struct.unpack_from('<I',data,4)[0] == len(data)-8
    position, frames, header_frames = 12, 0, None
    while position < len(data):
        tag, length = data[position:position+4], struct.unpack_from('<I',data,position+4)[0]
        value = data[position+8:position+8+length]
        if tag == b'anih':
            header_frames = struct.unpack_from('<9I',value)[1]
            if expected_ms is not None:assert struct.unpack_from('<9I',value)[7]==round(expected_ms*60/1000)
        if tag == b'LIST':
            assert value[:4] == b'fram'
            off = 4
            while off < len(value):
                n = struct.unpack_from('<I',value,off+4)[0]
                assert value[off:off+4] == b'icon'
                check_cur(value[off+8:off+8+n],expected_sizes)
                frames += 1
                off += 8+n+(n%2)
        position += 8+length+(length%2)
    assert frames == header_frames == 8


class CursorImage(ctypes.Structure):
    _fields_=[(x,ctypes.c_uint32) for x in ('version','size','width','height','xhot','yhot','delay')]+[('pixels',ctypes.POINTER(ctypes.c_uint32))]


class CursorImages(ctypes.Structure):
    _fields_=[('nimage',ctypes.c_int),('images',ctypes.POINTER(ctypes.POINTER(CursorImage))),('name',ctypes.c_char_p)]


def main():
    lib = ctypes.CDLL(ctypes.util.find_library('Xcursor'))
    lib.XcursorFilenameLoadImages.argtypes=[ctypes.c_char_p,ctypes.c_int]
    lib.XcursorFilenameLoadImages.restype=ctypes.POINTER(CursorImages)
    lib.XcursorImagesDestroy.argtypes=[ctypes.POINTER(CursorImages)]
    catalog = json.loads((DIST/'catalog.json').read_text())
    installer = (DIST / 'install-linux.sh').read_text()
    assert '# @PAYLOAD@' not in installer
    payload = installer.split("<<'FREECUR_PY'\n", 1)[1].rsplit('\nFREECUR_PY', 1)[0]
    assert payload == (DIST.parent / 'install_linux.py').read_text()
    compile(payload, 'embedded-installer.py', 'exec')
    subprocess.run(['bash', '-n', str(DIST / 'install-linux.sh')], check=True)
    active_ids={x['id'] for x in catalog['themes']}
    allowed=set(json.loads((DIST.parent/'release-policy.json').read_text())['active_groups'])
    assert all(x['group'] in allowed for x in catalog['themes'])
    totals = dict(themes=len(catalog['themes']), windows_cur=0, windows_ani=0, xcursor_loads=0, cape_roles=0, hashes=0)
    with tempfile.TemporaryDirectory(prefix='free-cur-check-') as folder:
        target = Path(folder)/'cursor'
        for theme in catalog['themes']:
            for platform, metadata in theme['packages'].items():
                path=DIST/metadata['url'].lstrip('/')
                assert path.stat().st_size == metadata['bytes']
                assert hashlib.sha256(path.read_bytes()).hexdigest() == metadata['sha256']
                totals['hashes'] += 1
                with zipfile.ZipFile(path) as pack:
                    assert pack.testzip() is None
                    assert 'SOURCE-AND-RIGHTS.txt' in pack.namelist()
                    for name in pack.namelist():
                        assert not name.startswith('/') and '..' not in Path(name).parts
                        if name.endswith('.cur'):
                            check_cur(pack.read(name),WINDOWS_SIZES);totals['windows_cur']+=1
                        elif name.endswith('.ani'):
                            expected=theme['animation'].get('durations_ms',{}).get(Path(name).stem,theme['animation']['duration_ms']) if theme.get('pixel') else None
                            check_ani(pack.read(name),expected,WINDOWS_SIZES);totals['windows_ani']+=1
                        elif name.endswith('.cape'):
                            cape=plistlib.loads(pack.read(name))
                            assert cape['Identifier']=='cn.bismih.freecur.'+theme['id']
                            assert set(cape['Cursors'])=={identifier for group in MAC_ROLES.values() for identifier in group}
                            for role, value in cape['Cursors'].items():
                                assert role.startswith('com.apple.')
                                assert 0 <= value['HotSpotX'] < value['PointsWide']
                                assert 0 <= value['HotSpotY'] < value['PointsHigh']
                                for index, rep in enumerate(value['Representations']):
                                    image=Image.open(io.BytesIO(rep));image.load()
                                    width=32*(index+1)
                                    assert image.size==(width,width*value['FrameCount'])
                                expected=8 if role in {i for r in theme.get('animated_roles',['Wait','AppStarting']) for i in MAC_ROLES.get(r,[])} else 1
                                assert value['FrameCount']==expected
                                if theme.get('pixel'):
                                    logical=next(key for key,ids in MAC_ROLES.items() if role in ids)
                                    assert value['FrameDuration']==theme['animation']['durations_ms'][logical]/1000
                                totals['cape_roles']+=1
                    if platform=='linux':
                        for role in ROLES:
                            data=pack.read('cursors/'+role)
                            for alias in ALIASES[role]:assert pack.read('cursors/'+alias)==data
                            target.write_bytes(data)
                            for size in (24,32,48,64):
                                loaded=lib.XcursorFilenameLoadImages(str(target).encode(),size)
                                assert loaded, (theme['id'],role,size)
                                try:
                                    assert loaded.contents.nimage==(8 if role in theme.get('animated_roles',['Wait','AppStarting']) else 1)
                                    all_hotspots=set()
                                    pixels=set()
                                    for frame in range(loaded.contents.nimage):
                                        image=loaded.contents.images[frame].contents
                                        assert image.width==size and image.height==size
                                        assert image.xhot<size and image.yhot<size
                                        all_hotspots.add((image.xhot,image.yhot))
                                        pixels.add(ctypes.string_at(image.pixels,size*size*4))
                                        if theme.get('pixel'):assert image.delay==theme['animation'].get('durations_ms',{}).get(role,theme['animation']['duration_ms'])
                                    assert len(all_hotspots)==1,'Hotspot must remain fixed during animation'
                                    if theme.get('pixel'):assert len(pixels)>1,'Character must actually change pose'
                                finally:lib.XcursorImagesDestroy(loaded)
                                totals['xcursor_loads']+=1
            for role in ROLES:
                assert (DIST/'previews'/theme['id']/(role+'.png')).exists()
            if theme.get('pixel'):
                assert theme['animated_roles']==ROLES
                for role in ROLES:
                    for frame in range(8):
                        image=Image.open(DIST/'previews'/theme['id']/f'{role}-{frame}.png').convert('RGBA')
                        assert image.size==(64,64)
                        assert set(image.getchannel('A').getdata())<={0,255},'No fuzzy alpha allowed for pixel sprites'
        for metadata in catalog['managers'].values():
            path=DIST/metadata['url'].lstrip('/')
            assert hashlib.sha256(path.read_bytes()).hexdigest()==metadata['sha256']
        for platform in ('windows','linux'):
            file=DIST/catalog['managers'][platform]['url'].lstrip('/')
            with zipfile.ZipFile(file) as collection:
                nested=json.loads(collection.read('catalog.json'))
                assert {x['id'] for x in nested['themes']}==active_ids
                expected={'packs/'+x+'-'+platform+'.zip' for x in active_ids}
                assert {x for x in collection.namelist() if x.startswith('packs/')}==expected
                if platform == 'windows':
                    assert {'FreeCur.exe', 'themes.xml', 'source/FreeCur.cs', 'source/setup.nsi'} <= set(collection.namelist())
                    assert not any(name.endswith(('.ps1', '.cmd')) for name in collection.namelist())
                    native = Path(folder) / 'windows-native'
                    collection.extractall(native)
                    check_windows_exe(native / 'FreeCur.exe', 0x8664)
                    import windows_build
                    subprocess.run(['mono', str(native / 'FreeCur.exe'), '--verify-packages', str(native)],
                                   env=windows_build.mono_environment(), check=True)
        setup = DIST / catalog['managers']['windows_exe']['url'].lstrip('/')
        check_windows_exe(setup, 0x8664)
        engine = Path(folder) / 'engine.exe'
        subprocess.run(['mono',str(setup),'--extract-engine',str(engine)],env=windows_build.mono_environment(),check=True)
        check_windows_exe(engine,0x14c)
        extracted = Path(folder) / 'windows-setup'
        subprocess.run(['7z', 'x', '-y', '-o' + str(extracted), str(engine)], capture_output=True, check=True)
        with zipfile.ZipFile(DIST / catalog['managers']['windows']['url'].lstrip('/')) as collection:
            for name in collection.namelist():
                assert (extracted / name).read_bytes() == collection.read(name), 'Setup payload mismatch: ' + name
        assert {p.name for p in (extracted / 'packs').iterdir()} == {x+'-windows.zip' for x in active_ids}
        totals['windows_setup_payload_verified'] = True
        file=DIST/catalog['managers']['macos']['url'].lstrip('/')
        with zipfile.ZipFile(file) as collection:
            assert {x for x in collection.namelist() if x.endswith('.cape')}=={'FreeCur-'+x+'.cape' for x in active_ids}
        deb=DIST/catalog['managers']['deb']['url'].lstrip('/')
        result=subprocess.run(['dpkg-deb','--fsys-tarfile',str(deb)],capture_output=True,check=True)
        with tarfile.open(fileobj=io.BytesIO(result.stdout)) as package:
            names={x.name.removeprefix('./') for x in package.getmembers() if x.isfile() and '/packs/' in x.name}
            assert names=={'usr/share/free-cur/packs/'+x+'-linux.zip' for x in active_ids}
    assert set(x['name'] for x in catalog['themes'] if x['group']=='EOE')=={'露早','柚恩','莞儿','米诺','虞莫'}
    assert set(x['name'] for x in catalog['themes'] if x['group']=='四禧丸子')=={'梨安','沐霂','恬豆','又一'}
    assert {'向晚','贝拉','珈乐','嘉然','乃琳','心宜','思诺'} <= set(x['name'] for x in catalog['themes'])
    (DIST/'verification.json').write_text(json.dumps(dict(totals,windows_runtime=False,macos_runtime=False,
        linux_desktop_changed=False,scope='Native format, image, hash and Xcursor library decoding checks, not full desktop runtime certification.'),ensure_ascii=False))
    print(json.dumps(dict(totals,collection_membership_verified=True)))


if __name__=='__main__':main()
