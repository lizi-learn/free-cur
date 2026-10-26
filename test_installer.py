import io
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import install_linux as installer


def fixture():
    theme = b'fixture cursor archive'
    nested = {'themes': [{'id': 'diana', 'packages': {'linux': {
        'bytes': len(theme), 'sha256': installer.sha256(theme)}}}]}
    files = {'catalog.json': json.dumps(nested).encode(), 'manager.py': b'print("fixture")\n',
             'start.sh': b'#!/bin/sh\n', 'README.txt': b'fixture', 'packs/diana-linux.zip': theme}
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    data = output.getvalue()
    catalog = {'managers': {'linux': {'url': '/downloads/free-cur-linux-collection.zip',
                                    'sha256': installer.sha256(data), 'bytes': len(data)}}}
    return catalog, data


class InstallerTests(unittest.TestCase):
    def test_idempotent_user_install_without_applying_theme(self):
        catalog, data = fixture()
        def download(path, limit):
            return json.dumps(catalog).encode() if path == '/catalog.json' else data
        with tempfile.TemporaryDirectory() as folder, patch.object(installer.subprocess, 'Popen') as popen:
            base = Path(folder) / '.local/share/free-cur'
            base.mkdir(parents=True)
            (base / 'previous.json').write_text('{"theme":"original"}')
            first = installer.install(folder, launch=False, downloader=download)
            second = installer.install(folder, launch=False, downloader=download)
            self.assertEqual(first, second)
            self.assertEqual((base / 'current').resolve(), first)
            self.assertEqual((base / 'previous.json').read_text(), '{"theme":"original"}')
            self.assertFalse((Path(folder) / '.local/share/icons').exists())
            self.assertTrue((Path(folder) / '.local/bin/free-cur').stat().st_mode & stat.S_IXUSR)
            self.assertIn('Name=Free Cur', (Path(folder) / '.local/share/applications/free-cur.desktop').read_text())
            popen.assert_not_called()

    def test_corrupted_download_never_installs(self):
        catalog, data = fixture()
        with tempfile.TemporaryDirectory() as folder:
            def download(path, limit):
                return json.dumps(catalog).encode() if path == '/catalog.json' else data + b'corrupt'
            with self.assertRaisesRegex(ValueError, '校验失败'):
                installer.install(folder, False, download)
            self.assertFalse((Path(folder) / '.local/bin/free-cur').exists())

    def test_preserve_unrelated_launcher(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.local/bin/free-cur'
            path.parent.mkdir(parents=True)
            path.write_text('my own program')
            with self.assertRaisesRegex(ValueError, '保留已有'):
                installer.install(folder, False)
            self.assertEqual(path.read_text(), 'my own program')

    def test_modified_release_is_not_overwritten(self):
        catalog, data = fixture()
        def download(path, limit):
            return json.dumps(catalog).encode() if path == '/catalog.json' else data
        with tempfile.TemporaryDirectory() as folder:
            release = installer.install(folder, False, download)
            (release / 'manager.py').write_text('my local modifications')
            with self.assertRaisesRegex(ValueError, '本地修改'):
                installer.install(folder, False, download)
            self.assertEqual((release / 'manager.py').read_text(), 'my local modifications')

    def test_invalid_url(self):
        for url in ('http://free-cur.bismih.cn/x', 'https://evil.test/x', '//evil.test/x', '/x?foo=bar'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                installer.owned_url(url)

    def test_reject_archive_traversal_and_symlinks(self):
        for name, mode in (('../escape', 0), ('/escape', 0), ('a/../../escape', 0),
                           ('packs\\escape', 0), ('link', stat.S_IFLNK | 0o777)):
            output = io.BytesIO()
            with zipfile.ZipFile(output, 'w') as archive:
                info = zipfile.ZipInfo(name)
                info.external_attr = mode << 16
                archive.writestr(info, b'escape')
            with tempfile.TemporaryDirectory() as folder, self.subTest(name=name), self.assertRaises(ValueError):
                installer.unpack(output.getvalue(), Path(folder))

    def test_desktop_exec_escaping(self):
        self.assertEqual(installer.desktop_quote('/a b/50%/$x'), '"/a b/50%%/\\$x"')


if __name__ == '__main__':
    unittest.main()
