"""Refresh static UI without rebuilding or replacing verified native downloads."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parent
catalog=json.loads((ROOT/'dist/catalog.json').read_text())
native=ROOT/'dist'/catalog['managers']['windows_exe']['url'].lstrip('/')
before=hashlib.sha256(native.read_bytes()).hexdigest()
for file in (ROOT/'web').iterdir():
    if file.is_dir():shutil.copytree(file,ROOT/'dist'/file.name,dirs_exist_ok=True)
    elif file.is_file():shutil.copy2(file,ROOT/'dist'/file.name)
assert hashlib.sha256(native.read_bytes()).hexdigest()==before
print('Static UI refreshed; verified native downloads unchanged.')
