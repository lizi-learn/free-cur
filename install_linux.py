"""Embedded user-only installer. Standard library only; never applies a theme."""
import hashlib
import io
import json
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

BASE = 'https://free-cur.bismih.cn'
MARKER = '# Free Cur user installer (managed)'
MAX_PACKAGE = 64 * 1024 * 1024


def owned_url(path):
    url = urllib.parse.urljoin(BASE + '/', path)
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme, parsed.netloc) != ('https', 'free-cur.bismih.cn') or parsed.query or parsed.fragment:
        raise ValueError('拒绝下载非本站 HTTPS 资源')
    return url


class SameOriginRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        owned_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(path, limit):
    request = urllib.request.Request(owned_url(path), headers={'User-Agent': 'FreeCur-LinuxInstaller/1.0'})
    with urllib.request.build_opener(SameOriginRedirect).open(request, timeout=60) as response:
        owned_url(response.geturl())
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('下载文件超过允许大小')
        return data


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def unpack(data, destination):
    """Reject traversal, symlinks, duplicate names and decompression bombs."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > 500 or sum(x.file_size for x in entries) > 100 * 1024 * 1024:
            raise ValueError('安装包解压大小异常')
        seen = set()
        for entry in entries:
            name = entry.filename
            parts = PurePosixPath(name)
            mode = stat.S_IFMT(entry.external_attr >> 16)
            if (name in seen or not name or '\\' in name or parts.is_absolute()
                    or any(x in ('', '.', '..') for x in name.rstrip('/').split('/'))
                    or mode not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError('安装包包含不安全路径或链接')
            seen.add(name)
        for entry in entries:
            target = destination / entry.filename
            if entry.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(entry))
                target.chmod(0o644)
    return {x for x in seen if not x.endswith('/')}


def verify_contents(directory, files):
    catalog = json.loads((directory / 'catalog.json').read_text())
    themes = catalog.get('themes', [])
    if not 1 <= len(themes) <= 100:
        raise ValueError('主题索引数量异常')
    expected = {'catalog.json', 'manager.py', 'start.sh', 'README.txt'}
    identifiers = set()
    for item in themes:
        ident = item['id']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', ident) or ident in identifiers:
            raise ValueError('主题标识异常')
        identifiers.add(ident)
        name = 'packs/' + ident + '-linux.zip'
        expected.add(name)
        metadata = item['packages']['linux']
        content = (directory / name).read_bytes()
        if len(content) != metadata['bytes'] or sha256(content) != metadata['sha256']:
            raise ValueError('主题包校验失败：' + ident)
    if files != expected:
        raise ValueError('安装包文件列表与索引不符')
    compile((directory / 'manager.py').read_text(), 'manager.py', 'exec')
    return len(themes)


def check_owned_file(path):
    if path.is_symlink() or (path.exists() and (not path.is_file() or MARKER not in path.read_text())):
        raise ValueError('保留已有的非本安装器文件：' + str(path))


def atomic_write(path, text, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix='.free-cur-', delete=False) as stream:
        pending = Path(stream.name)
        stream.write(text)
    try:
        pending.chmod(mode)
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)


def desktop_quote(value):
    # Desktop Entry Exec quoting differs from shell quoting.
    return '"' + ''.join(('\\' + c) if c in '\\"`$' else ('%%' if c == '%' else c) for c in value) + '"'


def install(user_directory, launch=True, downloader=fetch):
    user_directory = Path(user_directory)
    base = user_directory / '.local/share/free-cur'
    releases = base / 'releases'
    current = base / 'current'
    launcher = user_directory / '.local/bin/free-cur'
    desktop = user_directory / '.local/share/applications/free-cur.desktop'
    check_owned_file(launcher)
    check_owned_file(desktop)
    if current.is_symlink():
        if current.resolve().parent != releases.resolve():
            raise ValueError('保留已有的非本安装器 current 链接')
    elif current.exists():
        raise ValueError('保留已有的非本安装器 current 目录')

    print('读取最新主题索引…', flush=True)
    catalog = json.loads(downloader('/catalog.json', 2 * 1024 * 1024))
    metadata = catalog['managers']['linux']
    if (not re.fullmatch(r'/downloads/[a-z0-9-]+\.zip', metadata['url'])
            or not re.fullmatch(r'[0-9a-f]{64}', metadata['sha256'])
            or not 0 < metadata['bytes'] <= MAX_PACKAGE):
        raise ValueError('下载索引不合法')
    print('下载 Linux 光标合集并进行 SHA-256 校验…', flush=True)
    data = downloader(metadata['url'], MAX_PACKAGE)
    if len(data) != metadata['bytes'] or sha256(data) != metadata['sha256']:
        raise ValueError('下载校验失败，未启动任何程序。请重新执行以获取同一版本')

    releases.mkdir(parents=True, exist_ok=True)
    release = releases / metadata['sha256']
    with tempfile.TemporaryDirectory(prefix='.stage-', dir=releases) as temporary:
        staging = Path(temporary) / 'app'
        staging.mkdir()
        files = unpack(data, staging)
        theme_count = verify_contents(staging, files)
        if release.is_symlink():
            raise ValueError('版本目录不能是符号链接')
        if release.exists():
            installed = {p.relative_to(release).as_posix() for p in release.rglob('*') if p.is_file()}
            if installed != files or any((release / name).is_symlink() or
                    (release / name).read_bytes() != (staging / name).read_bytes() for name in files):
                raise ValueError('已安装版本被本地修改，保留原文件；请先自行检查版本目录')
        else:
            staging.rename(release)

    # Preflight passed. A single atomic symlink chooses the verified offline release.
    pending = base / 'current.new'
    if pending.exists() or pending.is_symlink():
        raise ValueError('发现未完成的 current.new，请先检查；不会覆盖')
    pending.symlink_to(release)
    pending.replace(current)
    atomic_write(launcher, '#!/bin/sh\n' + MARKER + '\nexec ' + shlex.quote(sys.executable)
                 + ' ' + shlex.quote(str(current / 'manager.py')) + ' "$@"\n', 0o755)
    atomic_write(desktop, '[Desktop Entry]\n' + MARKER + '\nType=Application\n'
                 'Name=Free Cur 光标切换器\nComment=当前用户光标主题：安装、切换和恢复\nExec='
                 + desktop_quote(str(launcher)) + '\nIcon=input-mouse\nTerminal=false\n'
                 'Categories=Settings;DesktopSettings;\nStartupNotify=false\n', 0o644)
    print(f'安装完成：{theme_count} 套主题。应用菜单中搜索 Free Cur，或执行：\n{launcher}', flush=True)
    print('尚未修改你的光标。点击「安装并应用」才切换；「恢复原主题」可以撤回。', flush=True)
    if launch and (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        with (base / 'manager.log').open('a') as log:
            process = subprocess.Popen([str(launcher)], stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log, start_new_session=True)
        try:
            result = process.wait(timeout=2)
            if result:
                print('切换器未能打开。请在桌面终端运行上面的命令；日志：' + str(base / 'manager.log'))
        except subprocess.TimeoutExpired:
            print('已打开切换器。')
    elif launch:
        print('当前没有图形会话，已完成安装；请在桌面会话启动切换器。')
    return release


if __name__ == '__main__':
    try:
        install(Path.home(), launch=len(sys.argv) < 2 or sys.argv[1] != '0')
    except Exception as error:
        print('安装未完成：' + str(error), file=sys.stderr)
        sys.exit(1)
