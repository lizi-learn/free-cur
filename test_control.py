import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from http.server import HTTPServer

import control


class CatalogueTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='free-cur-control-')
        self.database=Path(self.temporary.name)/'state.db'
        self.seed=Path(__file__).parent/'dist/windows-feed.xml'
        self.store=control.Store(self.database,self.seed)

    def tearDown(self):
        self.temporary.cleanup()

    def change(self, ident, published, revision=None):
        return self.store.update(dict(id=ident,published=published,revision=revision or self.store.admin()['revision']))

    def test_hide_and_republish_data_only(self):
        self.assertEqual(len(ET.fromstring(self.store.public_feed()[0])),19)
        self.assertEqual(self.change('diana',False)[0],200)
        self.assertNotIn('diana',{x.attrib['id'] for x in ET.fromstring(self.store.public_feed()[0])})
        self.assertEqual(self.change('diana',True)[0],200)
        self.assertEqual(len(ET.fromstring(self.store.public_feed()[0])),19)

    def test_changes_persist(self):
        self.change('diana',False)
        other=control.Store(self.database,self.seed)
        self.assertFalse(next(x for x in other.admin()['themes'] if x['id']=='diana')['published'])

    def test_concurrent_update_conflict(self):
        revision=self.store.admin()['revision']
        self.change('diana',False,revision)
        self.assertEqual(self.change('ava',False,revision)[0],409)

    def test_unknown_theme_and_remote_command_rejected(self):
        with self.assertRaises(ValueError):self.change('../run.exe',True)
        with self.assertRaises(ValueError):self.store.update(dict(id='diana',published=True,revision='x',command='run'))

    def test_empty_remote_feed_valid_for_all_hidden(self):
        for theme in self.store.admin()['themes']:self.change(theme['id'],False)
        self.assertEqual(len(ET.fromstring(self.store.public_feed()[0])),0)

    def test_http_csrf_and_write_restrictions(self):
        server=HTTPServer(('127.0.0.1',0),control.handler(self.store,Path(__file__).parent))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base='http://127.0.0.1:'+str(server.server_port)
        try:
            data=json.dumps(dict(id='diana',published=False,revision=self.store.admin()['revision'])).encode()
            def post(path,headers):
                request=urllib.request.Request(base+path,data=data,headers=dict({'Content-Type':'application/json'},**headers))
                try:
                    with urllib.request.urlopen(request) as response:return response.status
                except urllib.error.HTTPError as error:return error.code
            self.assertEqual(post('/api/admin/catalog',{}),403)
            self.assertEqual(post('/api/admin/catalog',{'Origin':'https://evil.test','X-CSRF-Token':self.store.csrf}),403)
            self.assertEqual(post('/api/admin/catalog',{'Origin':control.ORIGIN,'X-CSRF-Token':self.store.csrf}),200)
            self.assertEqual(post('/api/windows/catalog.xml',{}),405)
        finally:
            server.shutdown();server.server_close();thread.join()
