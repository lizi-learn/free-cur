"""Data-only catalogue service, loopback-only behind Caddy owner authentication."""
import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import secrets
import sqlite3
import time
import xml.etree.ElementTree as ET

ORIGIN = 'https://free-cur.bismih.cn'


class Store:
    def __init__(self, database, seed):
        self.database, self.seed = str(database), Path(seed)
        self.csrf = secrets.token_urlsafe(32)
        with self.connect() as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS visibility (id TEXT PRIMARY KEY, published INTEGER NOT NULL, updated INTEGER NOT NULL)')
            connection.execute('CREATE TABLE IF NOT EXISTS audit (at INTEGER NOT NULL, id TEXT NOT NULL, published INTEGER NOT NULL)')

    def connect(self):
        return sqlite3.connect(self.database, timeout=5)

    def snapshot(self, connection=None):
        root = ET.fromstring(self.seed.read_bytes())
        if root.tag != 'free-cur' or len(root) > 100:
            raise ValueError('Invalid publisher seed')
        if connection is None:
            with self.connect() as current:
                return self._snapshot(root, current)
        return self._snapshot(root, connection)

    def _snapshot(self, root, connection):
        state = {ident: bool(published) for ident,published in connection.execute('SELECT id,published FROM visibility')}
        entries = [dict(id=item.attrib['id'], name=item.attrib['name'], group=item.attrib['group'], pixel=item.attrib.get('pixel') == 'true', published=state.get(item.attrib['id'], True)) for item in root]
        revision = hashlib.sha256(ET.tostring(root) + json.dumps(state, sort_keys=True).encode()).hexdigest()
        return root, entries, revision

    def public_feed(self):
        root, entries, revision = self.snapshot()
        published = {x['id'] for x in entries if x['published']}
        for child in list(root):
            if child.attrib['id'] not in published:
                root.remove(child)
        root.set('poll-minutes', '30')
        root.set('revision', revision)
        return ET.tostring(root, encoding='utf-8', xml_declaration=True), revision

    def admin(self):
        _, entries, revision = self.snapshot()
        with self.connect() as connection:
            history = [dict(at=at, id=ident, published=bool(published)) for at,ident,published in connection.execute('SELECT at,id,published FROM audit ORDER BY rowid DESC LIMIT 20')]
        return dict(themes=entries, revision=revision, csrf=self.csrf, history=history)

    def update(self, payload):
        if set(payload) != {'id','published','revision'} or type(payload['published']) is not bool:
            raise ValueError('Invalid change')
        with self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            _, entries, revision = self.snapshot(connection)
            if payload['revision'] != revision:
                return 409, dict(error='目录已更新，请刷新后重试')
            if payload['id'] not in {x['id'] for x in entries}:
                raise ValueError('Unknown theme')
            stamp = int(time.time())
            connection.execute('INSERT INTO visibility VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET published=excluded.published,updated=excluded.updated', (payload['id'],int(payload['published']),stamp))
            connection.execute('INSERT INTO audit VALUES(?,?,?)', (stamp,payload['id'],int(payload['published'])))
        return 200, dict(ok=True)


def handler(store, root):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'FreeCurCatalog'

        def log_message(self, *args):
            pass

        def reply(self, code, data, content_type='application/json; charset=utf-8', **headers):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            for key,value in headers.items():
                self.send_header(key.replace('_','-'),value)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(data)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            try:
                if self.path == '/health':
                    return self.reply(200,dict(ok=True))
                if self.path == '/api/windows/catalog.xml':
                    data,revision = store.public_feed()
                    return self.reply(200,data,'application/xml; charset=utf-8',ETag='"'+revision+'"')
                if self.path == '/api/admin/catalog':
                    return self.reply(200,store.admin())
                files = {'/admin/':('admin.html','text/html; charset=utf-8'),'/admin/admin.js':('admin.js','text/javascript; charset=utf-8')}
                if self.path == '/admin':
                    return self.reply(303,b'',Location='/admin/')
                if self.path in files:
                    name,content_type = files[self.path]
                    return self.reply(200,(root/name).read_bytes(),content_type)
                self.reply(404,dict(error='not found'))
            except (ValueError,OSError,ET.ParseError,sqlite3.Error):
                self.reply(503,dict(error='目录暂不可用'))

        def do_POST(self):
            if self.path != '/api/admin/catalog':
                return self.reply(405,dict(error='read only'))
            if self.headers.get('Origin') != ORIGIN or not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),store.csrf):
                return self.reply(403,dict(error='请从管理页面重新加载后操作'))
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 1 <= length <= 4096 or self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                    raise ValueError('Invalid request')
                code,data = store.update(json.loads(self.rfile.read(length)))
                self.reply(code,data)
            except (ValueError,KeyError,TypeError):
                self.reply(400,dict(error='请求不合法，仅允许修改已有主题的上架状态'))
    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database',required=True)
    parser.add_argument('--seed',required=True)
    parser.add_argument('--port',type=int,default=18467)
    arguments = parser.parse_args()
    service = Store(arguments.database,arguments.seed)
    HTTPServer(('127.0.0.1',arguments.port),handler(service,Path(__file__).parent)).serve_forever()
