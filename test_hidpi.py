"""Real C# selection and recommendation tests, no desktop/cursor/display setters."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

import windows_build
from build import WINDOWS_SIZES
from verify import check_ani

ROOT=Path(__file__).parent


def chunks(data):
    result=[];at=12
    while at<len(data):
        n=struct.unpack_from('<I',data,at+4)[0]
        result.append((data[at:at+4],data[at+8:at+8+n]));at+=8+n+n%2
    return result


def frames(data):
    for tag,content in chunks(data):
        if tag!=b'LIST':continue
        assert content[:4]==b'fram'
        at=4
        while at<len(content):
            n=struct.unpack_from('<I',content,at+4)[0]
            yield content[at+8:at+8+n];at+=8+n+n%2


def cursor_image(data,size):
    count=struct.unpack_from('<H',data,4)[0]
    for i in range(count):
        at=6+i*16;w,h=data[at] or 256,data[at+1] or 256
        if (w,h)!=(size,size):continue
        hx,hy,n,offset=struct.unpack_from('<HHII',data,at+4)
        return (hx,hy),data[offset:offset+n]
    raise AssertionError('Native size missing: '+str(size))


class HiDpiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='free-cur-hidpi-');cls.folder=Path(cls.temp.name)
        cls.native=cls.folder/'native';cls.native.mkdir()
        cls.catalog=json.loads((ROOT/'dist/catalog.json').read_text())
        with zipfile.ZipFile(ROOT/'dist'/cls.catalog['managers']['windows']['url'].lstrip('/')) as archive:archive.extractall(cls.native)
        cls.environment=windows_build.mono_environment()

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def run_native(self,*args):
        return subprocess.run(['mono',str(self.native/'FreeCur.exe'),*map(str,args)],env=self.environment,capture_output=True,text=True,timeout=60)

    def test_resolution_and_dpi_matrix_without_double_scaling(self):
        cases=[(1920,1080,96,64),(2560,1440,96,96),(2560,1440,120,96),
               (2560,1440,144,96),(3840,2160,192,128),(1920,1080,144,96),
               (1920,1080,240,128),(1440,2560,120,96),(3440,1440,96,96),
               (2560,1080,96,64),(1366,768,96,48),(7680,4320,384,128)]
        for width,height,dpi,expected in cases:
            result=self.run_native('--recommend-size',width,height,dpi)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(int(result.stdout.strip()),expected)

    def test_invalid_display_inputs_and_manual_sizes_rejected(self):
        for args in ((0,1080,96),(1920,0,96),(1920,1080,0),(999999,1080,96),(1920,1080,999999)):
            self.assertNotEqual(self.run_native('--recommend-size',*args).returncode,0)
        for size in (31,65,97,129,100000):self.assertNotEqual(self.run_native('--check-size',size).returncode,0)

    def test_every_source_frame_contains_all_six_sizes_and_binary_alpha(self):
        roles=0
        for theme in self.catalog['themes']:
            with zipfile.ZipFile(self.native/'packs'/(theme['id']+'-windows.zip')) as archive:
                for role in theme['animated_roles']:
                    data=archive.read(role+'.ani');check_ani(data,expected_sizes=WINDOWS_SIZES)
                    for frame in frames(data):
                        for size in (96,128):
                            hotspot,dib=cursor_image(frame,size)
                            alpha=dib[43:40+size*size*4:4]
                            self.assertLessEqual(set(alpha),{0,255});self.assertNotEqual(set(alpha),{0})
                            self.assertTrue(all(0<=v<size for v in hotspot))
                    roles+=1
        self.assertEqual(roles,285)

    def test_exact_large_frames_preserve_pixels_hotspots_and_animation(self):
        for size in (96,128):
            output=self.folder/('native-'+str(size))
            result=self.run_native('--export-sized-packages',self.native,size,0,output)
            self.assertEqual(result.returncode,0,result.stderr)
            for theme in self.catalog['themes']:
                pack=self.native/'packs'/(theme['id']+'-windows.zip')
                self.assertEqual(hashlib.sha256(pack.read_bytes()).hexdigest(),theme['packages']['windows']['sha256'])
                with zipfile.ZipFile(pack) as archive:
                    for role in theme['animated_roles']:
                        name=role+'.ani';source=archive.read(name);derived=(output/theme['id']/name).read_bytes()
                        check_ani(derived,expected_sizes=(size,))
                        source_chunks=chunks(source);derived_chunks=chunks(derived)
                        self.assertEqual([t for t,c in source_chunks],[t for t,c in derived_chunks])
                        for (tag,a),(_,b) in zip(source_chunks,derived_chunks):
                            if tag==b'anih':
                                wanted=bytearray(a);struct.pack_into('<II',wanted,12,size,size);self.assertEqual(bytes(wanted),b)
                            elif tag!=b'LIST':self.assertEqual(a,b)
                        for a,b in zip(frames(source),frames(derived)):
                            self.assertEqual(cursor_image(a,size),cursor_image(b,size))

    def test_size_selection_composes_with_hdr_without_resampling(self):
        source=self.folder/'source.ani'
        with zipfile.ZipFile(self.native/'packs/taffy-windows.zip') as archive:source.write_bytes(archive.read('Arrow.ani'))
        tinted=self.folder/'hdr.ani';selected=self.folder/'hdr-selected.ani'
        self.assertEqual(self.run_native('--convert-hdr',source,tinted,100,'file-only').returncode,0)
        self.assertEqual(self.run_native('--convert-size',tinted,selected,128,'file-only').returncode,0)
        check_ani(selected.read_bytes(),expected_sizes=(128,))
        for a,b in zip(frames(tinted.read_bytes()),frames(selected.read_bytes())):
            self.assertEqual(cursor_image(a,128),cursor_image(b,128))
        self.assertNotEqual(self.run_native('--convert-size',source,selected,96,'file-only').returncode,0)

    def test_old_pack_missing_large_size_fails_without_creating_output(self):
        source=self.folder/'one-size.ani';target=self.folder/'missing.ani'
        with zipfile.ZipFile(self.native/'packs/diana-windows.zip') as archive:source.write_bytes(archive.read('Arrow.ani'))
        narrow=self.folder/'small.ani'
        self.assertEqual(self.run_native('--convert-size',source,narrow,32,'file-only').returncode,0)
        result=self.run_native('--convert-size',narrow,target,128,'file-only')
        self.assertNotEqual(result.returncode,0);self.assertIn('缺少原生',result.stderr);self.assertFalse(target.exists())

    def test_per_monitor_manifest_config_and_current_user_preferences(self):
        self.assertEqual(WINDOWS_SIZES,(24,32,48,64,96,128))
        config=ET.parse(self.native/'FreeCur.exe.config').getroot()
        self.assertEqual(config.find('./System.Windows.Forms.ApplicationConfigurationSection/add').attrib['value'],'PerMonitorV2')
        manifest=ET.parse(ROOT/'windows/app.manifest').getroot()
        self.assertEqual(manifest.find('.//{http://schemas.microsoft.com/SMI/2016/WindowsSettings}dpiAwareness').text,'PerMonitorV2,PerMonitor')
        form=(ROOT/'windows/LibraryForm.cs').read_text();core=(ROOT/'windows/FreeCur.cs').read_text();probe=(ROOT/'windows/ScreenSizing.cs').read_text()
        for token in ('WM_DPICHANGED','WM_DISPLAYCHANGE','PreferredAutomaticSize','ScreenSizing.Read(Handle)','原生帧'):
            self.assertIn(token,form)
        self.assertIn('<size-mode>',core);self.assertIn('CursorSizing.Exact(x.Value,size)',core)
        for forbidden in ('ChangeDisplaySettings','SetDisplayConfig','SetProcessDPIAware','SetCursorPos','SetWindowsHookEx'):
            self.assertNotIn(forbidden,probe+core+form)

    def test_old_cache_uses_new_offline_bitmaps_without_reviving_hidden_themes(self):
        document=ET.parse(self.native/'themes.xml');document.getroot().set('version','2.4.0')
        for element in list(document.getroot()):
            if element.attrib['id']=='taffy':document.getroot().remove(element)
            else:element.set('sha256','0'*64)
        cache=self.folder/'old-cache.xml';document.write(cache,encoding='utf-8')
        result=self.run_native('--check-offline-catalog',self.native,cache)
        self.assertEqual(result.returncode,0,result.stderr)
        listed=dict(line.split(':') for line in result.stdout.strip().splitlines())
        self.assertEqual(set(listed),{t['id'] for t in self.catalog['themes']}-{'taffy'})
        self.assertEqual(listed['diana'],next(t['packages']['windows']['sha256'] for t in self.catalog['themes'] if t['id']=='diana'))

    def test_empty_or_current_cloud_catalogue_is_preserved(self):
        for version in ('2.4.0','2.5.0','2.6.0'):
            cache=self.folder/('empty-'+version+'.xml');cache.write_text('<free-cur version="'+version+'"/>')
            result=self.run_native('--check-offline-catalog',self.native,cache)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),'')
        document=ET.parse(self.native/'themes.xml');document.getroot().set('version','2.6.0')
        document.getroot()[0].set('sha256','0'*64);cache=self.folder/'future-cache.xml';document.write(cache,encoding='utf-8')
        result=self.run_native('--check-offline-catalog',self.native,cache)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn(document.getroot()[0].attrib['id']+':'+'0'*64,result.stdout)


if __name__=='__main__':unittest.main()
