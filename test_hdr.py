"""Run real compiled C# colour conversion, without calling Windows setters."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zipfile

import windows_build

ROOT=Path(__file__).parent


def spans(data):
    """Return opaque-channel positions and all alpha positions from actual ANI DIBs."""
    changed=[];alpha=[];frames=[]
    p=12
    while p<len(data):
        n=struct.unpack_from('<I',data,p+4)[0]
        if data[p:p+4]==b'LIST' and data[p+8:p+12]==b'fram':
            at=p+12
            while at<p+8+n:
                length=struct.unpack_from('<I',data,at+4)[0];frames.append(at+8);at+=8+length+length%2
        p+=8+n+n%2
    for start in frames:
        count=struct.unpack_from('<H',data,start+4)[0]
        for index in range(count):
            entry=start+6+16*index;w=data[entry] or 256;h=data[entry+1] or 256
            image=start+struct.unpack_from('<I',data,entry+12)[0]
            for at in range(image+40,image+40+w*h*4,4):
                alpha.append(at+3)
                if data[at+3]:changed.extend((at,at+1,at+2))
    return changed,alpha


class HdrCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='free-cur-hdr-')
        cls.folder=Path(cls.temporary.name);cls.native=cls.folder/'native';cls.native.mkdir()
        cls.catalog=json.loads((ROOT/'dist/catalog.json').read_text())
        pack=ROOT/'dist'/cls.catalog['managers']['windows']['url'].lstrip('/')
        with zipfile.ZipFile(pack) as archive:archive.extractall(cls.native)
        cls.program=cls.native/'FreeCur.exe';cls.environment=windows_build.mono_environment()

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def command(self,*args):
        return subprocess.run(['mono',str(self.program),*map(str,args)],env=self.environment,capture_output=True,text=True,timeout=30)

    def test_lut_identity_monotonic_and_known_srgb_value(self):
        normal=self.command('--hdr-lut','0');self.assertEqual(normal.returncode,0,normal.stderr)
        self.assertEqual(list(map(int,normal.stdout.strip().split(','))),list(range(256)))
        for strength in (25,50,75,100):
            result=self.command('--hdr-lut',strength);self.assertEqual(result.returncode,0,result.stderr)
            table=list(map(int,result.stdout.strip().split(',')))
            self.assertEqual((table[0],table[-1]),(0,255));self.assertEqual(table,sorted(table))
            self.assertTrue(all(value<=index for index,value in enumerate(table)))
            if strength==100:self.assertEqual(table[128],55)

    def test_invalid_strength_is_rejected(self):
        for strength in ('-1','101','2147483647','not-a-number'):
            self.assertNotEqual(self.command('--hdr-lut',strength).returncode,0)

    def test_hdr_and_wcg_are_not_confused_by_new_api(self):
        for flags,mode,text in ((0,'0','SDR'),(3,'1','ACM'),(51,'2','HDR 已开启'),(3,'legacy','无法区分')):
            result=self.command('--check-color-mode',flags,mode)
            self.assertEqual(result.returncode,0,result.stderr);self.assertIn(text,result.stdout)

    def test_converter_identity_and_malformed_data_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.folder) as folder:
            folder=Path(folder)
            with zipfile.ZipFile(self.native/'packs/taffy-windows.zip') as archive:original=archive.read('Arrow.ani')
            source=folder/'original.ani';source.write_bytes(original)
            target=folder/'identity.ani'
            result=self.command('--convert-hdr',source,target,0,'file-only');self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(target.read_bytes(),original)
            self.assertNotEqual(self.command('--convert-hdr',source,target,100,'file-only').returncode,0,'Never overwrite existing user files')
            broken=bytearray(original);broken[4:8]=b'\xff'*4;source.write_bytes(broken)
            self.assertNotEqual(self.command('--convert-hdr',source,folder/'bad.ani',100,'file-only').returncode,0)
            self.assertFalse((folder/'bad.ani').exists())

    def test_all_19_themes_keep_animation_alpha_hotspots_masks_and_timing(self):
        output=self.folder/'converted'
        result=self.command('--export-hdr-packages',self.native,100,output)
        self.assertEqual(result.returncode,0,result.stderr);self.assertIn('19 themes / 285 cursor roles',result.stdout)
        table=list(map(int,self.command('--hdr-lut',100).stdout.strip().split(',')))
        roles=0
        for theme in self.catalog['themes']:
            archive_path=self.native/'packs'/(theme['id']+'-windows.zip')
            digest=hashlib.sha256(archive_path.read_bytes()).hexdigest()
            self.assertEqual(digest,theme['packages']['windows']['sha256'])
            with zipfile.ZipFile(archive_path) as archive:
                for role in theme['animated_roles']:
                    name=role+'.ani';original=archive.read(name);derived=(output/theme['id']/name).read_bytes()
                    self.assertEqual(len(original),len(derived))
                    positions,alpha=spans(original)
                    expected=bytearray(original)
                    for at in positions:expected[at]=table[original[at]]
                    self.assertEqual(bytes(expected),derived,(theme['id'],role))
                    self.assertTrue(all(derived[at]==original[at] for at in alpha))
                    self.assertNotEqual(original,derived);roles+=1
        self.assertEqual(roles,285)

    def test_no_hdr_or_icc_setters_and_derived_cache_is_separate(self):
        hdr=(ROOT/'windows/HdrDisplay.cs').read_text()
        color=(ROOT/'windows/HdrColor.cs').read_text()
        core=(ROOT/'windows/FreeCur.cs').read_text()
        self.assertIn('DisplayConfigGetDeviceInfo',hdr)
        for setter in ('DisplayConfigSetDeviceInfo','SetDisplayConfig','SetDeviceGammaRamp','WcsSetDefaultColorProfile','SetICMProfile'):
            self.assertNotIn(setter,hdr+color+core)
        self.assertIn('HdrColor.CacheSuffix(hdrStrength)',core)
        self.assertIn('HdrColor.Prepare(sourceFiles,hdrStrength)',core)
        self.assertIn('cursor-preferences.xml',core)


if __name__=='__main__':unittest.main()
