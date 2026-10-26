import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import manager_linux as manager


class ManagerSecurity(unittest.TestCase):
    def test_parent_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);pack=base/'bad.zip';target=base/'out';target.mkdir()
            with zipfile.ZipFile(pack,'w') as z:z.writestr('../escape.txt','not allowed')
            with self.assertRaises(ValueError):manager.extract_theme(pack,target)
            self.assertFalse((base/'escape.txt').exists())

    def test_absolute_path_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);pack=base/'bad.zip';target=base/'out';target.mkdir()
            with zipfile.ZipFile(pack,'w') as z:z.writestr('/absolute.txt','not allowed')
            with self.assertRaises(ValueError):manager.extract_theme(pack,target)

    def test_regular_theme_extracts(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);pack=base/'good.zip';target=base/'out';target.mkdir()
            with zipfile.ZipFile(pack,'w') as z:z.writestr('cursors/default',b'Xcur')
            manager.extract_theme(pack,target)
            self.assertEqual((target/'cursors/default').read_bytes(),b'Xcur')

    def test_gnome_only_modifies_current_user_after_backup(self):
        with tempfile.TemporaryDirectory() as d,patch.object(manager,'STATE',Path(d)),patch.dict(manager.os.environ,{'XDG_CURRENT_DESKTOP':'GNOME'}),patch.object(manager,'gnome_theme',return_value='Yaru'),patch.object(manager.subprocess,'check_output',return_value='24'),patch.object(manager.subprocess,'run') as run:
            manager.apply_theme('FreeCur-diana')
            self.assertEqual(json.loads((Path(d)/'previous.json').read_text())['theme'],'Yaru')
            self.assertEqual(run.call_args.args[0],['gsettings','set','org.gnome.desktop.interface','cursor-theme','FreeCur-diana'])
            self.assertEqual(json.loads((Path(d)/'previous.json').read_text())['size'],24)
            self.assertIn(['gsettings','set','org.gnome.desktop.interface','cursor-size','48'],[c.args[0] for c in run.call_args_list])
            manager.apply_theme('FreeCur-ava')
            self.assertEqual(json.loads((Path(d)/'previous.json').read_text())['theme'],'Yaru')

    def test_size_failure_rolls_back_without_overwriting_backup(self):
        with tempfile.TemporaryDirectory() as d,patch.object(manager,'STATE',Path(d)),patch.dict(manager.os.environ,{'XDG_CURRENT_DESKTOP':'GNOME'}),patch.object(manager,'gnome_theme',return_value='Yaru'),patch.object(manager.subprocess,'check_output',return_value='24'),patch.object(manager.subprocess,'run',side_effect=[RuntimeError('failed'),None,None]) as run:
            with self.assertRaises(RuntimeError):manager.apply_theme('FreeCur-diana',64)
            self.assertEqual(run.call_args_list[-2].args[0][-1],'24')
            self.assertEqual(run.call_args_list[-1].args[0][-1],'Yaru')

    def test_invalid_size_rejected_before_system_commands(self):
        with patch.object(manager.subprocess,'run') as run:
            with self.assertRaises(ValueError):manager.apply_theme('FreeCur-diana',999)
            run.assert_not_called()

    def test_restore_can_keep_nonpreset_original_size(self):
        with tempfile.TemporaryDirectory() as d,patch.object(manager,'STATE',Path(d)),patch.dict(manager.os.environ,{'XDG_CURRENT_DESKTOP':'GNOME'}),patch.object(manager,'gnome_theme',return_value='Yaru'),patch.object(manager.subprocess,'check_output',return_value='36'),patch.object(manager.subprocess,'run') as run:
            manager.apply_theme('FreeCur-diana',48)
            previous=json.loads((Path(d)/'previous.json').read_text())
            manager.apply_theme(previous['theme'],previous['size'])
            self.assertIn(['gsettings','set','org.gnome.desktop.interface','cursor-size','36'],[c.args[0] for c in run.call_args_list])


if __name__=='__main__':unittest.main()
