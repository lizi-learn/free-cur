"""Prepare a verified static-site directory; no production credentials or remote writes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
ROOT_FILES = {'index.html', 'app.js', 'style.css', 'pixel.css', 'site.css', 'favicon.svg',
              'catalog.json', 'verification.json', 'privacy.html', 'terms.html', 'about.html',
              'install-linux.sh', 'windows-feed.xml'}


def public_files():
    dist = ROOT / 'dist'
    assert (dist / 'verification.json').is_file(), 'Run verify.py first.'
    catalog = json.loads((dist / 'catalog.json').read_text())
    allowed = set(json.loads((ROOT / 'release-policy.json').read_text())['active_groups'])
    assert all(theme['group'] in allowed for theme in catalog['themes'])
    active = {theme['id'] for theme in catalog['themes']}
    downloads = [package for theme in catalog['themes'] for package in theme['packages'].values()]
    downloads.extend(catalog['managers'].values())
    paths = set(ROOT_FILES)
    for package in downloads:
        relative = Path(package['url'].removeprefix('/'))
        assert relative.parts[0] == 'downloads' and '..' not in relative.parts and not relative.is_absolute()
        payload = dist / relative
        assert payload.is_file() and not payload.is_symlink()
        assert payload.stat().st_size == package['bytes']
        assert hashlib.sha256(payload.read_bytes()).hexdigest() == package['sha256']
        paths.add(relative.as_posix())
    paths.add('downloads/FreeCur-Setup-x64.exe')
    latest = dist / 'downloads/FreeCur-Setup-x64.exe'
    assert hashlib.sha256(latest.read_bytes()).hexdigest() == catalog['managers']['windows_exe']['sha256']
    paths.update('client-preview/' + name for name in ['setup.png', 'manager.png'] if (dist / 'client-preview' / name).is_file())
    for theme in active:
        paths.update(path.relative_to(dist).as_posix() for path in (dist / 'previews' / theme).iterdir()
                     if path.suffix in {'.png', '.gif', '.webp'} and path.is_file() and not path.is_symlink())
    assert all((dist / name).is_file() and not (dist / name).is_symlink() for name in paths)
    return sorted(paths)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    names = public_files()
    args.output.mkdir(parents=True, exist_ok=False)
    for name in names:
        path = args.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'dist' / name, path)
    print(json.dumps({'files': len(names), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
