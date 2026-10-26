from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).parent


class Document(HTMLParser):
    def __init__(self,text):
        super().__init__();self.tags=[];self.feed(text)
    def handle_starttag(self,tag,attrs):self.tags.append((tag,dict(attrs)))


class ThreePageUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/'web/index.html').read_text()
        cls.doc=Document(cls.html)
        cls.js=(ROOT/'web/app.js').read_text()

    def test_ids_unique_and_script_targets_exist(self):
        ids=[a['id'] for _,a in self.doc.tags if 'id' in a]
        self.assertEqual(len(ids),len(set(ids)))
        used=set(re.findall(r'''\$\(['"]#([\w-]+)['"]\)''',self.js))
        dynamic=set(re.findall(r'''\.id=['"]([\w-]+)['"]''',self.js))
        self.assertFalse(used-set(ids)-dynamic,used-set(ids)-dynamic)

    def test_three_separate_views_and_home_is_default(self):
        views={a['id']:a for tag,a in self.doc.tags if tag=='section' and 'page-view' in a.get('class','').split()}
        self.assertEqual(set(views),{'home','library','install'})
        self.assertNotIn('hidden',views['home'])
        self.assertIn('hidden',views['library']);self.assertIn('hidden',views['install'])
        self.assertIn('[hidden]{display:none!important}',(ROOT/'web/site.css').read_text())

    def test_paginated_library_and_accessible_navigation(self):
        per_page=int(re.search(r'size:(\d+)',self.js).group(1))
        count=len(json.loads((ROOT/'dist/catalog.json').read_text())['themes'])
        self.assertEqual(per_page,6);self.assertEqual(math.ceil(count/per_page),4)
        links={a.get('href') for tag,a in self.doc.tags if tag=='a' and 'data-view-link' in a}
        self.assertEqual(links,{'#home','#library','#install'})
        self.assertIn("window.addEventListener('hashchange',route)",self.js)

    def test_every_public_ui_asset_is_publishable(self):
        deploy=(ROOT/'deploy.py').read_text()
        for tag,attrs in self.doc.tags:
            url=attrs.get('src') if tag=='script' else attrs.get('href') if tag=='link' else None
            if url and url.startswith('/'):
                name=url.split('?')[0][1:]
                self.assertTrue((ROOT/'web'/name).exists(),name)
                self.assertIn(repr(name),deploy)

    def test_motion_is_optional_not_an_always_running_render_loop(self):
        self.assertIn('@media(prefers-reduced-motion:reduce)',(ROOT/'web/site.css').read_text())
        self.assertIn("event.pointerType!=='mouse'",self.js)
        self.assertIn("document.body.dataset.view!=='home'",self.js)
        self.assertNotIn('WebGLRenderer',self.js)


if __name__=='__main__':unittest.main()
