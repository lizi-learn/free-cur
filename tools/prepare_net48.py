"""Fetch the pinned official reference pack into this checkout's ignored build tree."""
import hashlib
import io
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
URL = ('https://api.nuget.org/v3-flatcontainer/microsoft.netframework.referenceassemblies.net48/'
       '1.0.3/microsoft.netframework.referenceassemblies.net48.1.0.3.nupkg')
SHA256 = '8a7e348538e7eb91351696911689f49e3d4f63f8bab517432bbe159b8b1104a2'


def main():
    target = ROOT / 'build/toolchain/net48'
    if target.exists():
        raise SystemExit('Reference directory already exists; inspect it instead of overwriting it.')
    with urllib.request.urlopen(URL, timeout=90) as response:
        payload = response.read(32 * 1024**2 + 1)
    if len(payload) > 32 * 1024**2 or hashlib.sha256(payload).hexdigest() != SHA256:
        raise SystemExit('Reference pack checksum mismatch.')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.net48-', dir=target.parent) as folder:
        temporary = Path(folder)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for member in archive.infolist():
                name = Path(member.filename)
                if name.is_absolute() or '..' in name.parts or '\\' in member.filename:
                    raise SystemExit('Unsafe reference pack path.')
            archive.extractall(temporary)
        assert (temporary / 'build/.NETFramework/v4.8/mscorlib.dll').is_file()
        shutil.copytree(temporary, target)
    print('Verified Microsoft.NETFramework.ReferenceAssemblies.net48 1.0.3 is ready.')


if __name__ == '__main__':
    main()
