"""Exercise the real compiled C# validator under Mono, without a desktop or registry writes."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

import windows_build

DIST = Path(__file__).resolve().parent / 'dist'


class WindowsNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        catalog = json.loads((DIST / 'catalog.json').read_text())
        cls.package = DIST / catalog['managers']['windows']['url'].lstrip('/')
        cls.environment = windows_build.mono_environment()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='free-cur-win-test-')
        self.root = Path(self.temporary.name)
        with zipfile.ZipFile(self.package) as archive:
            for name in ('FreeCur.exe', 'themes.xml', 'packs/diana-windows.zip'):
                archive.extract(name, self.root)
        tree = ET.parse(self.root / 'themes.xml')
        for theme in list(tree.getroot()):
            if theme.attrib['id'] != 'diana':
                tree.getroot().remove(theme)
        tree.write(self.root / 'themes.xml', encoding='utf-8', xml_declaration=True)

    def tearDown(self):
        self.temporary.cleanup()

    def run_validator(self):
        return subprocess.run(['mono', str(self.root / 'FreeCur.exe'), '--verify-packages', str(self.root)],
                              env=self.environment, capture_output=True, text=True, timeout=20)

    def test_real_native_validator_accepts_diana(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('1 offline themes / 15 cursor roles', result.stdout)

    def test_corrupted_package_rejected(self):
        with (self.root / 'packs/diana-windows.zip').open('ab') as stream:
            stream.write(b'corrupt')
        self.assertNotEqual(self.run_validator().returncode, 0)

    def test_hash_mismatch_rejected(self):
        tree = ET.parse(self.root / 'themes.xml')
        tree.getroot()[0].set('sha256', '0' * 64)
        tree.write(self.root / 'themes.xml', encoding='utf-8')
        self.assertNotEqual(self.run_validator().returncode, 0)

    def test_role_path_escape_rejected(self):
        tree = ET.parse(self.root / 'themes.xml')
        tree.getroot()[0][0].set('file', '../outside.ani')
        tree.write(self.root / 'themes.xml', encoding='utf-8')
        self.assertNotEqual(self.run_validator().returncode, 0)

    def test_valid_hash_does_not_allow_traversal_inside_zip(self):
        pack = self.root / 'packs/diana-windows.zip'
        with zipfile.ZipFile(pack, 'a') as archive:
            archive.writestr('../outside.txt', b'unsafe')
        tree = ET.parse(self.root / 'themes.xml')
        tree.getroot()[0].set('sha256', hashlib.sha256(pack.read_bytes()).hexdigest())
        tree.getroot()[0].set('bytes', str(pack.stat().st_size))
        tree.write(self.root / 'themes.xml', encoding='utf-8')
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('不安全路径', result.stderr)
        self.assertFalse((self.root.parent / 'outside.txt').exists())

    def test_xml_external_entities_are_rejected(self):
        (self.root / 'themes.xml').write_text('<!DOCTYPE x [<!ENTITY injected SYSTEM "file:///etc/hostname">]><free-cur>&injected;</free-cur>')
        self.assertNotEqual(self.run_validator().returncode, 0)

    def test_uninstaller_never_uses_recursive_directory_delete(self):
        script = (DIST.parent / 'windows/setup.nsi').read_text()
        self.assertIn('RequestExecutionLevel user', script)
        self.assertIn('SetShellVarContext current', script)
        self.assertIn('--prepare-uninstall', script)
        self.assertNotIn('RMDir /r', script)
        self.assertNotIn('WriteRegStr HKLM', script)

    def test_remote_feed_accepts_empty_catalogue(self):
        feed=self.root/'empty.xml';feed.write_text('<free-cur version="2.0.0"/>')
        result=subprocess.run(['mono',str(self.root/'FreeCur.exe'),'--check-feed',str(feed)],env=self.environment,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_cloud_package_cannot_point_to_executable(self):
        tree=ET.parse(self.root/'themes.xml');tree.getroot()[0].set('url','https://evil.test/run.exe')
        tree.write(self.root/'themes.xml',encoding='utf-8')
        self.assertNotEqual(self.run_validator().returncode,0)

    def test_microsoft_framework_reference_compile_is_enforced(self):
        source=(DIST.parent/'windows_build.py').read_text()
        self.assertIn("'-nostdlib'",source)
        self.assertIn("'-noconfig'",source)
        self.assertIn('toolchain/net48/build/.NETFramework/v4.8',source)
        manager=(DIST.parent/'windows/FreeCur.cs').read_text()
        self.assertIn("TrimEnd(new char[] { '/' })",manager)

    def test_real_size_validation_does_not_touch_registry(self):
        for size,expected in [('32',0),('48',0),('64',0),('96',0),('128',0),('0',1),('999',1)]:
            result=subprocess.run(['mono',str(self.root/'FreeCur.exe'),'--check-size',size],env=self.environment,capture_output=True,text=True)
            self.assertEqual(result.returncode,expected,result.stderr)

    def test_size_has_persistence_restore_and_explicit_windows_api(self):
        source=(DIST.parent/'windows/FreeCur.cs').read_text()
        self.assertIn('LoadImage(IntPtr.Zero,Path.Combine(target,theme.Files[pair.Key]),2,size,size,0x10)',source)
        self.assertIn('SetSystemCursor(handle,pair.Value)',source)
        self.assertIn('key.SetValue("CursorBaseSize",size,RegistryValueKind.DWord)',source)
        self.assertIn('key.DeleteValue("CursorBaseSize",false)',source)
        self.assertIn('original.ImportNode',source) # Preserve and upgrade 2.0 backups.


if __name__ == '__main__':
    unittest.main()
