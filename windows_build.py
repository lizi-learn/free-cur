"""Cross-build native .NET WinForms + per-user NSIS setup; no remote script wrappers."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / 'build'
TOOLCHAIN = BUILD / 'toolchain/nsis/root/usr'
VERSION = '2.5.0'


def windows_icon(image):
    """DIB icons with explicit XOR + 1-bit AND masks, readable by .NET Framework."""
    frames=[]
    for size in (16,32,48,64):
        frame=image.convert('RGBA').resize((size,size),Image.Resampling.NEAREST)
        xor=frame.tobytes('raw','BGRA',0,-1)
        stride=((size+31)//32)*4
        mask=bytearray(stride*size)
        for row,y in enumerate(range(size-1,-1,-1)):
            for x in range(size):
                if frame.getpixel((x,y))[3]==0:
                    mask[row*stride+x//8] |= 1 << (7-x%8)
        header=struct.pack('<IIIHHIIIIII',40,size,size*2,1,32,0,len(xor)+len(mask),0,0,0,0)
        frames.append((size,header+xor+mask))
    offset=6+16*len(frames)
    entries=[]
    for size,data in frames:
        entries.append(struct.pack('<BBBBHHII',size,size,0,0,1,32,len(data),offset));offset+=len(data)
    return struct.pack('<HHH',0,1,len(frames))+b''.join(entries)+b''.join(data for _,data in frames)


def win32_resources(icon, manifest):
    """Emit standard .res records: mcs accepts -win32manifest but does not embed it."""
    def record(kind, ident, data):
        header = struct.pack('<IIHHHHIHHII', len(data), 32, 0xffff, kind, 0xffff, ident, 0, 0x1030, 0x409, 0, 0)
        return header + data + b'\0' * (-len(data) % 4)
    output = record(0, 0, b'') + record(24, 1, manifest)
    count = struct.unpack_from('<H', icon, 4)[0]
    group = struct.pack('<HHH', 0, 1, count)
    for index in range(count):
        width, height, colors, reserved, planes, bits, size, offset = struct.unpack_from('<BBBBHHII', icon, 6 + index * 16)
        ident = index + 1
        output += record(3, ident, icon[offset:offset + size])
        group += struct.pack('<BBBBHHIH', width, height, colors, reserved, planes, bits, size, ident)
    return output + record(14, 1, group)


def references():
    directory = BUILD / 'toolchain/net48/build/.NETFramework/v4.8'
    names = ['mscorlib','System','System.Core','System.Xml','System.Windows.Forms','System.Drawing','System.IO.Compression']
    result = [directory / (name + '.dll') for name in names]
    if not all(path.exists() for path in result):
        raise RuntimeError('Microsoft.NETFramework.ReferenceAssemblies.net48 1.0.3 is required; Mono API references are deliberately not used')
    return result


def build(catalog, downloads, archive, descriptor):
    # Directory is content-addressed; no previous paused series can leak into a new installer.
    digest = hashlib.sha256(json.dumps(catalog, sort_keys=True).encode())
    digest.update(Path(__file__).read_bytes())
    for source in sorted((ROOT / 'windows').iterdir()):
        digest.update(source.name.encode() + source.read_bytes())
    payload = BUILD / ('windows-' + digest.hexdigest()[:16])
    payload.mkdir(exist_ok=True)
    files = {}
    themes = ET.Element('free-cur', version=VERSION)
    for theme in catalog['themes']:
        metadata = theme['packages']['windows']
        entry = ET.SubElement(themes, 'theme', id=theme['id'], name=theme['name'], group=theme['group'],
                              sha256=metadata['sha256'], bytes=str(metadata['bytes']), pixel=str(bool(theme.get('pixel'))).lower(), url=metadata['url'])
        preview = ROOT / 'dist/previews' / theme['id'] / 'Arrow.png'
        entry.set('preview','/previews/'+theme['id']+'/Arrow.png')
        entry.set('preview-sha256',hashlib.sha256(preview.read_bytes()).hexdigest())
        entry.set('preview-bytes',str(preview.stat().st_size))
        files['assets/'+theme['id']+'.png'] = preview
        roles = [item['id'] for item in catalog['roles']]
        animated = theme.get('animated_roles', ['AppStarting', 'Wait'])
        for role in roles:
            ET.SubElement(entry, 'role', name=role, file=role + ('.ani' if role in animated else '.cur'))
        files['packs/' + theme['id'] + '-windows.zip'] = downloads / (theme['id'] + '-windows.zip')
    files['themes.xml'] = ET.tostring(themes, encoding='utf-8', xml_declaration=True)
    (ROOT / 'dist/windows-feed.xml').write_bytes(files['themes.xml'])
    files['README.txt'] = ('Free Cur 2.5 Windows x64 · 原生 EXE / 云端主题目录 + 本地缓存\n'
        '双击 FreeCur.exe 打开切换器。默认不修改光标，点击「安装并应用」才生效；可恢复原主题。\n'
        '需要 Windows 10/11 x64 与 .NET Framework 4.8+。不要以管理员运行；不安装服务。\n'
        '2.5 默认自动推荐：读取窗口所在屏幕的物理分辨率和 Windows 缩放，不只判断 1K/2K。1080p/100% 推荐 64px、1440p 推荐 96px、4K 推荐 128px；高 DPI 取两者较大档，不重复相乘。也可手动选 32/48/64/96/128px。升级后选择档位不会立即修改系统，点击主题应用才生效。\n'
        '每帧带原生 96/128px 位图，应用时生成精确尺寸动画缓存；像素风使用最近邻，不平滑模糊边缘，不承诺凭空增加原画细节。界面启用 PerMonitorV2。多屏移动窗口会刷新推荐，程序不常驻跟踪全局鼠标；关闭后跨屏尺寸仍由 Windows 管理。检测不上传。\n'
        '2.4 新增「HDR 指针偏白补偿（实验）」：保持系统 HDR 开启，勾选后选择 25/50/75/100%，再点击主题应用。100% 为标准逆 sRGB 补偿，若明显过深请降低强度或取消勾选重新应用。默认关闭，不影响原色。\n'
        '补偿仅生成独立的本地指针缓存，不改原包、透明度、热点、动画时长、HDR 开关、ICC 或整屏颜色。它针对指针颜色传递函数不匹配，不是通用 HDR 校准；需要在发生问题的 Windows/HDR 电脑上验证。混合 HDR/SDR 多屏需逐屏核对。\n'
        '「检测显示」只读本机显示状态，不上传结果。旧版 Windows API 可能只能报告高级颜色开启，不能区分 HDR 和 ACM。\n'
        '打开后自动同步本站主题目录，之后约每30分钟静默检查；下架不强制更换已应用的光标。关闭后不常驻；自启动默认关闭，可以在软件内选择启动到托盘。\n'
        '只访问 free-cur.bismih.cn 的目录、PNG预览和主题包，不上传设备身份、鼠标、屏幕或用户文件，不远程执行代码，不自动更新EXE。\n'
        '应用后可关闭程序，不需要常驻。正式安装请使用网站的 FreeCur-Setup-x64.exe。\n'
        '免费、非商业、非官方。角色与素材权利归原权利人，逐主题来源见 packs 内 SOURCE-AND-RIGHTS.txt。\n'
        '当前为未签名软件，可能出现未知发布者提示；没有 Windows 真机时不得宣称实机验收通过。\n'
        'C# 与安装器源码位于 source。卸载会恢复仍在使用的 Free Cur 指针，保留原主题备份与缓存。\n').encode('utf-8-sig')
    files['free-cur-managed.txt'] = b'Free Cur managed installation v1\n'
    icon = payload / 'free-cur.ico'
    icon.write_bytes(windows_icon(Image.open(ROOT / 'dist/previews/diana/Arrow.png')))
    files['free-cur.ico'] = icon
    resources = payload / 'native.res'
    resources.write_bytes(win32_resources(icon.read_bytes(), (ROOT / 'windows/app.manifest').read_bytes()))
    executable = payload / 'FreeCur.exe'
    command = ['mcs', '-nologo', '-noconfig', '-nostdlib', '-target:winexe', '-platform:x64', '-optimize+', '-main:Program',
               '-out:' + str(executable), '-win32res:' + str(resources),
               '-resource:' + str(ROOT / 'dist/previews/diana/Character-Hand.gif') + ',FreeCur.Diana']
    command.extend('-r:' + str(path) for path in references())
    command.extend(str(ROOT / 'windows' / name) for name in ['FreeCur.cs','Design.cs','Cloud.cs','LibraryForm.cs','HdrColor.cs','HdrDisplay.cs','ScreenSizing.cs','CursorSizing.cs'])
    subprocess.run(command, check=True)
    files['FreeCur.exe'] = executable
    files['FreeCur.exe.config'] = ROOT/'windows/FreeCur.exe.config'
    for source in (ROOT / 'windows').iterdir():
        files['source/' + source.name] = source
    # Preserve JSON for catalog/rights inspection; native runtime uses validated themes.xml.
    files['catalog.json'] = json.dumps(catalog, ensure_ascii=False).encode('utf-8')
    for name, value in files.items():
        path = payload / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, Path):
            if value.resolve() != path.resolve():
                shutil.copy2(value, path)
        else:
            path.write_bytes(value)
    manager = downloads / 'free-cur-windows-collection.zip'
    archive(manager, {name: payload / name for name in files})
    # Generate explicit file lists: never ship stale build entries or recursively delete user directories.
    install_lines, uninstall_lines = [], []
    for name in sorted(files):
        parent = Path(name).parent.as_posix()
        parent = '' if parent == '.' else '\\' + parent.replace('/', '\\')
        install_lines += ['SetOutPath "$INSTDIR' + parent + '"', 'File "' + str(payload / name) + '"']
        uninstall_lines.append('Delete "$INSTDIR\\' + name.replace('/', '\\') + '"')
    install_files = payload / 'install-files.nsh'
    uninstall_files = payload / 'uninstall-files.nsh'
    install_files.write_text('\n'.join(install_lines) + '\n')
    uninstall_files.write_text('\n'.join(uninstall_lines) + '\n')
    engine = payload / 'InstallEngine.exe'
    makensis = shutil.which('makensis') or str(TOOLCHAIN / 'bin/makensis')
    environment = os.environ.copy()
    if makensis == str(TOOLCHAIN / 'bin/makensis'):
        environment['NSISDIR'] = str(TOOLCHAIN / 'share/nsis')
    result = subprocess.run([makensis, '-V3', '-DOUTPUT=' + str(engine), '-DPAYLOAD=' + str(payload),
                             '-DINSTALL_FILES=' + str(install_files), '-DUNINSTALL_FILES=' + str(uninstall_files),
                             str(ROOT / 'windows/setup.nsi')], env=environment, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    print(result.stdout[-1800:], flush=True)
    output = downloads / ('FreeCur-Setup-'+VERSION+'-x64.exe')
    setup = ['mcs','-nologo','-noconfig','-nostdlib','-target:winexe','-platform:x64','-optimize+','-main:SetupProgram',
             '-out:'+str(output),'-win32res:'+str(resources),'-resource:'+str(engine)+',FreeCur.Engine',
             '-resource:'+str(ROOT/'dist/previews/diana/Character-Hand.gif')+',FreeCur.Diana']
    setup.extend('-r:'+str(path) for path in references())
    setup.extend(str(ROOT/'windows'/name) for name in ['Design.cs','Setup.cs'])
    subprocess.run(setup,check=True)
    shutil.copy2(output,downloads/'FreeCur-Setup-x64.exe')
    return descriptor(manager), dict(descriptor(output), version=VERSION, signed=False, windows_runtime=False)


def mono_environment():
    environment = os.environ.copy()
    environment['MONO_PATH'] = os.pathsep.join(str(path.parent) for path in (TOOLCHAIN / 'lib/mono/gac').glob('*/*/*.dll'))
    return environment
