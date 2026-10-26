"""Collect public fictional-character artwork with traceable source records."""
import argparse
import concurrent.futures
import hashlib
import html
import json
import re
import time
from pathlib import Path
from urllib.parse import quote, urlsplit

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / '.cache'
ART = ROOT / 'artwork'
HEADERS = {'User-Agent': 'FreeCur/0.1 (noncommercial character cursor catalogue; source attribution)'}


def get(url, **kwargs):
    s = requests.Session()
    s.trust_env = False
    r = s.get(url, headers=HEADERS, timeout=(10, 30), **kwargs)
    r.raise_for_status()
    return r


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', nargs='+', help='Collect selected active characters, preserving other source records')
    args = parser.parse_args()
    CACHE.mkdir(exist_ok=True)
    ART.mkdir(exist_ok=True)
    roster = json.loads((ROOT / 'roster.json').read_text())
    allowed=set(json.loads((ROOT/'release-policy.json').read_text())['active_groups'])
    roster=[item for item in roster if item['group'] in allowed]
    if args.only:
        unknown=set(args.only)-{item['id'] for item in roster}
        if unknown:parser.error('Unknown or paused character IDs: '+', '.join(sorted(unknown)))
        roster=[item for item in roster if item['id'] in args.only]
    saved = CACHE / ('wiki-' + hashlib.sha256('|'.join(x['wiki'] for x in roster).encode()).hexdigest()[:10] + '.json')
    if not saved.exists():
        response = get('https://zh.moegirl.org.cn/api.php', params={
            'action': 'query', 'format': 'json', 'prop': 'pageimages',
            'piprop': 'name|original|thumbnail', 'pithumbsize': 640,
            'titles': '|'.join(x['wiki'] for x in roster), 'redirects': 1}).json()
        saved.write_text(json.dumps(response, ensure_ascii=False, indent=2))
    result = json.loads(saved.read_text())['query']
    redirects = {x['from']: x['to'] for x in result.get('redirects', [])}
    pages = {x['title']: x for x in result['pages'].values()}
    for item in roster:
        title = redirects.get(item['wiki'], item['wiki'])
        page = pages.get(title, {})
        item.update(source='https://zh.moegirl.org.cn/' + quote(title),
                    image_url=(page.get('original') or page.get('thumbnail') or {}).get('source'),
                    source_file=page.get('pageimage'), page_id=page.get('pageid'))
    overrides = [x for x in roster if x.get('image_file')]
    override_file = CACHE / 'image-overrides.json'
    if overrides and not override_file.exists():
        response = get('https://zh.moegirl.org.cn/api.php', params={
            'action':'query', 'format':'json', 'prop':'imageinfo', 'iiprop':'url',
            'titles':'|'.join('File:' + x['image_file'] for x in overrides)}).json()
        override_file.write_text(json.dumps(response, ensure_ascii=False))
    images = {x['title'].removeprefix('File:'): x.get('imageinfo',[{}])[0].get('url')
              for x in (json.loads(override_file.read_text()) if override_file.exists() else {}).get('query',{}).get('pages',{}).values()}
    for item in overrides:
        if images.get(item['image_file']):
            item.update(image_url=images[item['image_file']], source_file=item['image_file'])
        else:
            # Imageinfo is restricted for anonymous clients. Use only images already
            # present in the normal public article; do not retry restricted actions.
            page_file = CACHE / (item['id'] + '-article.html')
            if not page_file.exists():
                page_file.write_text(get(item['source']).text)
            expected = quote(item['image_file'])
            for match in re.finditer(r'<img\b[^>]*\bsrc="([^"]+)"', page_file.read_text()):
                url = html.unescape(match.group(1))
                if expected in url or item['image_file'] in url:
                    if url.startswith('//'):
                        url = 'https:' + url
                    item.update(image_url=url, source_file=item['image_file'])
                    break
    heroes_file = CACHE / 'heroes.json'
    if '王者荣耀' in allowed and not heroes_file.exists():
        heroes_file.write_text(json.dumps(get('https://pvp.qq.com/web201605/js/herolist.json').json(), ensure_ascii=False))
    for hero in (json.loads(heroes_file.read_text()) if '王者荣耀' in allowed else []):
        number = int(hero['ename'])
        roster.append(dict(id='hok-' + str(number), name=hero['cname'], group='王者荣耀',
            wiki=hero['cname'], color='#9a92c8', subtitle=hero.get('title', ''),
            source='https://pvp.qq.com/web201605/herodetail/' + str(number) + '.shtml',
            image_url='https://game.gtimg.cn/images/yxzj/img201606/heroimg/' + str(number) + '/' + str(number) + '.jpg',
            source_file=str(number) + '.jpg'))

    def download(item):
        name = item['id']
        path = ART / (name + '.png')
        old = CACHE / (name + '-url.txt')
        if not path.exists() or (item.get('image_file') and (not old.exists() or old.read_text() != item.get('image_url'))):
            url = item.get('image_url')
            if not url:
                return dict(item, available=False, reason='百科未返回角色图片，需要人工补充')
            allowed = {'storage.moegirl.org.cn', 'img.moegirl.org.cn', 'game.gtimg.cn', 'p.moegirl.org.cn'}
            try:
                if urlsplit(url).hostname not in allowed:
                    raise ValueError('Unexpected artwork host')
                r = get(url)
                if urlsplit(r.url).hostname not in allowed or len(r.content) > 15 * 1024 * 1024:
                    raise ValueError('Image host or size rejected')
                import io
                im = Image.open(io.BytesIO(r.content)).convert('RGBA')
                im.thumbnail((1000, 1000))
                im.save(path, optimize=True)
                old.write_text(url)
            except Exception as error:
                return dict(item, available=False, reason=type(error).__name__)
        item.update(available=True, artwork=str(path.relative_to(ROOT)),
            artwork_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            rights='角色及原图版权归原权利人；未取得独立商业或再许可授权。',
            retrieved='2026-10-19')
        return item

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        catalog = list(pool.map(download, roster))
    saved_sources=ROOT/'sources.json'
    previous=json.loads(saved_sources.read_text()) if saved_sources.exists() else []
    collected_ids={item['id'] for item in catalog}
    preserved=[item for item in previous if item['id'] not in collected_ids]
    saved_sources.write_text(json.dumps(catalog+preserved, ensure_ascii=False, indent=2))
    print(json.dumps(dict(total=len(catalog), downloaded=sum(x['available'] for x in catalog),
                         missing=[dict(name=x['name'], reason=x.get('reason')) for x in catalog if not x['available']]), ensure_ascii=False))


if __name__ == '__main__':
    main()
