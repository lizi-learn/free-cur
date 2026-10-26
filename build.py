"""Deterministic native CUR/ANI, Xcursor and Mousecape exporter."""
import argparse
import hashlib
import io
import json
import math
import plistlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps
import pixel
from cursor_style import pointer

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'
BUILD = ROOT / 'build'
SIZES = (24, 32, 48, 64)
WINDOWS_SIZES = (24, 32, 48, 64, 96, 128)
ROLES = ['Arrow', 'Help', 'AppStarting', 'Wait', 'Crosshair', 'IBeam', 'NWPen', 'No',
         'SizeNS', 'SizeWE', 'SizeNWSE', 'SizeNESW', 'SizeAll', 'UpArrow', 'Hand']
NAMES = ['常规选择', '帮助选择', '后台运行', '忙碌', '精确选择', '文本选择', '手写', '不可用',
         '纵向调整', '横向调整', '对角调整 ↘', '对角调整 ↗', '移动', '候选选择', '链接选择']
ALIASES = {
 'Arrow': ['left_ptr', 'default', 'arrow', 'top_left_arrow'],
 'Help': ['help', 'question_arrow', 'left_ptr_help'],
 'AppStarting': ['progress', 'left_ptr_watch', 'half-busy'],
 'Wait': ['wait', 'watch'], 'Crosshair': ['crosshair', 'cross'],
 'IBeam': ['text', 'xterm', 'vertical-text'], 'NWPen': ['pencil', 'draft'],
 'No': ['not-allowed', 'crossed_circle', 'forbidden', 'no-drop'],
 'SizeNS': ['ns-resize', 'sb_v_double_arrow', 'size_ver', 'n-resize', 's-resize', 'top_side', 'bottom_side', 'v_double_arrow'],
 'SizeWE': ['ew-resize', 'sb_h_double_arrow', 'size_hor', 'w-resize', 'e-resize', 'left_side', 'right_side', 'h_double_arrow'],
 'SizeNWSE': ['nwse-resize', 'size_fdiag', 'top_left_corner', 'bottom_right_corner', 'nw-resize', 'se-resize'],
 'SizeNESW': ['nesw-resize', 'size_bdiag', 'top_right_corner', 'bottom_left_corner', 'ne-resize', 'sw-resize'],
 'SizeAll': ['move', 'fleur', 'all-scroll', 'size_all'],
 'UpArrow': ['up_arrow', 'center_ptr'],
 'Hand': ['pointer', 'hand2', 'hand1', 'grab', 'grabbing', 'openhand', 'closedhand'],
}
MAC_ROLES = {
 'Arrow': ['com.apple.coregraphics.Arrow', 'com.apple.coregraphics.ArrowCtx'],
 'Help': ['com.apple.cursor.40'], 'AppStarting': ['com.apple.cursor.4'],
 'Wait': ['com.apple.coregraphics.Wait'],
 'Crosshair': ['com.apple.cursor.7', 'com.apple.cursor.8'],
 'IBeam': ['com.apple.coregraphics.IBeam', 'com.apple.coregraphics.IBeamXOR'],
 'No': ['com.apple.cursor.3'],
 'SizeNS': ['com.apple.cursor.'+str(i) for i in (23,21,22,32,31,36)],
 'SizeWE': ['com.apple.cursor.'+str(i) for i in (19,17,18,28,27,38)],
 'SizeNWSE': ['com.apple.cursor.'+str(i) for i in (34,33,35)],
 'SizeNESW': ['com.apple.cursor.'+str(i) for i in (30,29,37)],
 'SizeAll': ['com.apple.coregraphics.Move','com.apple.cursor.12','com.apple.cursor.11'],
 'Hand': ['com.apple.cursor.13','com.apple.cursor.2'],
}
PORTRAITS = {}
FACE_BOXES = {'azi':(.30,0,.68,.34), 'fiona':(.24,.18,.78,.43), 'snow':(.38,.19,.65,.38)}


def png(image):
    out = io.BytesIO()
    image.save(out, 'PNG', optimize=True)
    return out.getvalue()


def portrait(item):
    if item['id'] in PORTRAITS:
        return PORTRAITS[item['id']]
    im = Image.open(ROOT / item['artwork']).convert('RGBA')
    if item['id'] in FACE_BOXES:
        a,b,c,d = FACE_BOXES[item['id']]
        im = im.crop((round(a*im.width),round(b*im.height),round(c*im.width),round(d*im.height)))
    alpha_box = im.getchannel('A').getbbox()
    if alpha_box:
        im = im.crop(alpha_box)
    white = Image.new('RGBA', im.size, 'white')
    white.alpha_composite(im)
    im = white
    # Trim the empty canvas around full-body wiki sheets before the head crop.
    corners = [im.getpixel(p) for p in [(0,0),(im.width-1,0),(0,im.height-1),(im.width-1,im.height-1)]]
    if all(min(c[:3]) > 245 for c in corners):
        bbox = ImageChops.difference(im.convert('RGB'),Image.new('RGB',im.size,'white')).convert('L').point(lambda v:255 if v>25 else 0).getbbox()
        if bbox:
            im = im.crop(bbox)
    # Preserve recognizability for tall character sheets: use their upper section.
    if im.height > im.width * 1.25:
        im = im.crop((0, 0, im.width, min(im.height, int(im.width * .82))))
    result = ImageOps.fit(im, (256, 256), method=Image.Resampling.LANCZOS, centering=(.5, .3))
    PORTRAITS[item['id']] = result
    return result


def artwork(item, role, size=64, frame=0):
    if pixel.enabled(item):
        return pixel.render(item, role, size, frame)
    im = Image.new('RGBA', (256, 256))
    d = ImageDraw.Draw(im)
    scale = 4
    color = item['color']
    face = portrait(item).resize((184, 184), Image.Resampling.LANCZOS)
    mask = Image.new('L', (184, 184))
    ImageDraw.Draw(mask).ellipse((3, 3, 180, 180), fill=255)
    base = Image.new('RGBA', face.size, '#ffffff')
    base.alpha_composite(face)
    im.paste(base, (68, 64), mask)
    d.ellipse((69, 65, 250, 246), outline='white', width=10)
    d.ellipse((72, 68, 247, 243), outline=color, width=5)

    def line(points, fill=color, width=4):
        xy = [(int(x * scale), int(y * scale)) for x, y in points]
        d.line(xy, fill='#292539', width=(width + 2) * scale, joint='curve')
        d.line(xy, fill=fill, width=width * scale, joint='curve')
        for x,y in (xy[0],xy[-1]):
            r=width*scale/2
            d.ellipse((x-r,y-r,x+r,y+r),fill=fill)

    def shape(points, fill=color):
        xy = [(int(x * scale), int(y * scale)) for x, y in points]
        d.polygon(xy, fill=fill)
        d.line(xy + [xy[0]], fill='#292539', width=2 * scale, joint='curve')

    hotspot = (3, 3)
    if role in ('Arrow', 'Help', 'AppStarting'):
        pointer(im, color)
        if role == 'Help':
            d.ellipse((76, 12, 145, 81), fill=color, outline='white', width=6)
            d.text((96, 20), '?', fill='white', stroke_width=1, font_size=42) if hasattr(d, 'font_size') else d.line((108, 23, 123, 23, 123, 40, 109, 48), fill='white', width=8)
    if role in ('Wait', 'AppStarting'):
        center = (16, 17) if role == 'Wait' else (28, 12)
        r = 11 if role == 'Wait' else 8
        x, y = center
        d.ellipse(((x-r)*4, (y-r)*4, (x+r)*4, (y+r)*4), fill='white', outline='#292539', width=6)
        angle = frame * math.tau / 8
        p = (x + math.cos(angle) * r * .72, y + math.sin(angle) * r * .72)
        d.ellipse(((p[0]-3)*4, (p[1]-3)*4, (p[0]+3)*4, (p[1]+3)*4), fill=color)
        if role == 'Wait':
            hotspot = center
    elif role == 'Hand':
        shape([(10, 28), (10, 6), (15, 3), (19, 6), (19, 22), (23, 15), (27, 16), (29, 21), (32, 18), (37, 21), (40, 27), (37, 45), (20, 46), (8, 35), (7, 30)])
        hotspot = (15, 4)
    elif role == 'IBeam':
        line([(12, 4), (28, 4)]);line([(20, 4), (20, 39)]);line([(12, 39), (28, 39)])
        hotspot = (20, 21)
    elif role == 'Crosshair':
        line([(20, 3), (20, 38)]);line([(3, 20), (37, 20)])
        hotspot = (20, 20)
    elif role == 'No':
        d.ellipse((12, 12, 147, 147), fill='white', outline='#292539', width=6)
        d.ellipse((28, 28, 131, 131), outline=color, width=14)
        d.line((42, 118, 117, 42), fill=color, width=14)
        hotspot = (20, 20)
    elif role == 'NWPen':
        shape([(5, 35), (25, 4), (34, 10), (14, 41), (3, 45)])
        hotspot = (3, 45)
    elif role == 'UpArrow':
        shape([(20, 3), (4, 21), (14, 21), (14, 41), (26, 41), (26, 21), (36, 21)])
        hotspot = (20, 3)
    elif role.startswith('Size'):
        directions = {'SizeNS': [(20, 4), (20, 36)], 'SizeWE': [(4, 20), (36, 20)],
            'SizeNWSE': [(6, 6), (34, 34)], 'SizeNESW': [(6, 34), (34, 6)],
            'SizeAll': [(20, 3), (20, 37), (3, 20), (37, 20)]}
        points = directions[role]
        for a, b in zip(points[::2], points[1::2]):
            line([a, b])
            for tip, other in [(a, b), (b, a)]:
                dx, dy = other[0]-tip[0], other[1]-tip[1]
                length = math.hypot(dx, dy)
                ux, uy = dx/length, dy/length
                line([(tip[0]+ux*7-uy*6, tip[1]+uy*7+ux*6), tip,
                      (tip[0]+ux*7+uy*6, tip[1]+uy*7-ux*6)], width=3)
        hotspot = (20, 20)
    result = im.resize((size, size), Image.Resampling.LANCZOS)
    return result, tuple(round(n * size / 64) for n in hotspot)


def cur(frames):
    images = []
    entries = []
    offset = 6 + len(frames) * 16
    for image, (hx, hy) in frames:
        w, h = image.size
        # 32-bit uncompressed DIB + bottom-up alpha pixels + AND transparency mask.
        row_mask = ((w + 31) // 32) * 4
        pixels = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).tobytes('raw', 'BGRA')
        mask = bytearray(row_mask * h)
        alpha = image.getchannel('A')
        for y in range(h):
            for x in range(w):
                if alpha.getpixel((x, h-1-y)) == 0:
                    mask[y * row_mask + x//8] |= 1 << (7 - x % 8)
        data = struct.pack('<IiiHHIIiiII', 40, w, h*2, 1, 32, 0, len(pixels), 0, 0, 0, 0) + pixels + mask
        entries.append(struct.pack('<BBBBHHII', w % 256, h % 256, 0, 0, hx, hy, len(data), offset))
        images.append(data)
        offset += len(data)
    return struct.pack('<HHH', 0, 2, len(frames)) + b''.join(entries) + b''.join(images)


def chunk(name, data):
    return name + struct.pack('<I', len(data)) + data + (b'\0' if len(data) % 2 else b'')


def ani(frames, duration_ms=100):
    header = struct.pack('<9I', 36, len(frames), len(frames), 0, 0, 32, 1, round(duration_ms*60/1000), 1)
    content = b'ACON' + chunk(b'anih', header) + chunk(b'LIST', b'fram' + b''.join(chunk(b'icon', f) for f in frames))
    return b'RIFF' + struct.pack('<I', len(content)) + content


def archive(path, files):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=8) as z:
        for name, data in files.items():
            z.writestr(name, data.read_bytes() if isinstance(data, Path) else data)


def descriptor(path):
    return dict(url='/downloads/' + path.name, bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def build_theme(item):
    ident = item['id']
    theme_name = 'FreeCur-' + ident
    folder = BUILD / ident
    folder.mkdir(parents=True, exist_ok=True)
    assets = DIST / 'previews' / ident
    assets.mkdir(parents=True, exist_ok=True)
    is_pixel=pixel.enabled(item)
    frame_ms=pixel.FRAME_MS if is_pixel else 100
    animated_roles=ROLES if is_pixel else ['Wait','AppStarting']
    face = pixel.pose(0,item) if is_pixel else portrait(item)
    if is_pixel:
        face.save(assets/'portrait.webp',lossless=True)
        for index in range(8):
            pixel.pose(index,item).save(assets/f'pose-{index}.png',optimize=True)
        for mood,sequence in pixel.MOODS.items():
            frames=[pixel.pose(index,item) for index in sequence]
            frames[0].save(assets/f'emoji-{mood}.gif',save_all=True,append_images=frames[1:],duration=frame_ms,loop=0,disposal=2)
            pixel.pose(pixel.MOOD_POSTERS[mood],item).save(assets/f'emoji-{mood}.png',optimize=True)
    else:
        face.convert('RGB').save(assets / 'portrait.webp', quality=90, method=6)
    windows, linux, mac = {}, {}, {}
    cursors = {}
    for role in ROLES:
        role_frame_ms=pixel.DURATIONS[role] if is_pixel else frame_ms
        if is_pixel:
            characters=[pixel.task_pose(role,f) if pixel.advanced(item) and role in pixel.TASK_ROLES else pixel.character_layer(role,f,item) for f in range(8)]
            characters[0].save(assets/f'Character-{role}.gif',save_all=True,append_images=characters[1:],duration=role_frame_ms,loop=0,disposal=2)
            characters[0].save(assets/f'Character-{role}.png',optimize=True)
        frame_count = 8 if role in animated_roles else 1
        encoded = []
        reps = {size: [] for size in SIZES}
        for frame in range(frame_count):
            native = [artwork(item, role, size, frame) for size in SIZES]
            encoded.append(cur(native+[artwork(item,role,size,frame) for size in WINDOWS_SIZES if size not in SIZES]))
            for size, pair in zip(SIZES, native):
                reps[size].append(pair)
        preview, hotspot = artwork(item, role, 64)
        preview.save(assets / (role + '.png'), optimize=True)
        if role in animated_roles:
            animated=[artwork(item,role,64,f)[0] for f in range(8)]
            animated[0].save(assets/(role+'.gif'),save_all=True,append_images=animated[1:],duration=role_frame_ms,loop=0,disposal=2)
            if is_pixel:
                for f,image in enumerate(animated):image.save(assets/f'{role}-{f}.png',optimize=True)
        data = ani(encoded,role_frame_ms) if frame_count > 1 else encoded[0]
        windows[role + ('.ani' if frame_count > 1 else '.cur')] = data
        configs = []
        for size in SIZES:
            for index, (image, hot) in enumerate(reps[size]):
                file = folder / (role + '-' + str(size) + '-' + str(index) + '.png')
                file.write_bytes(png(image))
                configs.append(f'{size} {hot[0]} {hot[1]} {file.name} {role_frame_ms}')
        config = folder / (role + '.cfg')
        config.write_text('\n'.join(configs) + '\n')
        output = folder / role
        subprocess.run(['xcursorgen', str(config.name), str(output.name)], cwd=folder, check=True, capture_output=True)
        linux['cursors/' + role] = output
        # Duplicate bytes rather than symlinks: safe extraction works on all clients.
        for alias in ALIASES[role]:
            linux['cursors/' + alias] = output
        for identifier in MAC_ROLES.get(role, []):
            representations = []
            for size in (32, 64):
                frames = reps[size]
                strip = Image.new('RGBA', (size, size * len(frames)))
                for index, (image, _) in enumerate(frames):
                    strip.alpha_composite(image, (0, index * size))
                representations.append(png(strip))
            hx, hy = reps[32][0][1]
            cursors[identifier] = dict(FrameCount=frame_count, FrameDuration=role_frame_ms/1000, HotSpotX=float(hx), HotSpotY=float(hy),
                PointsHigh=32., PointsWide=32., Representations=representations)

    readme = f'''Free Cur / {item['name']} / {item['group']}
Character artwork source: {item['source']}
Image source: {item.get('image_url', '')}
Artwork SHA256: {item['artwork_sha256']}
Character and artwork rights belong to their original owners. This is an unofficial, noncommercial fan conversion, not a transfer of copyright or a claim of authorization.
Style: {'AI-assisted pixel character reinterpretation; '+('12 task-specific sequences with 48 task keyframes and 8 casual poses.' if pixel.advanced(item) else '8 individually generated character poses, compiled into 15 animated roles; not the 48-keyframe advanced edition.')+' Not official sprites.' if is_pixel else 'Portrait companion cursors; only the loading ring animates.'}
15 Windows roles, 24/32/48/64/96/128 px. Pixel themes use nearest-neighbor rendering, not smoothed interpolation; larger sizes preserve pixel-art edges, not newly invented detail. Windows 2.5 can select an exact-size native ANI cache based on physical resolution and DPI. macOS is mapped to Mousecape roles; runtime compatibility depends on OS and Mousecape version and has not been tested on a Mac.
Animation is tied to system cursor roles, not global click hooks. A desktop click does not independently trigger a jump. The website demo can trigger a click reaction only inside its own page.
No telemetry, login, kernel drivers or privileged service. Read any installer script before running it.
https://free-cur.bismih.cn/
'''
    for files in (windows, linux, mac):
        files['SOURCE-AND-RIGHTS.txt'] = readme
        if is_pixel:
            files['PIXEL-DESIGN.txt']=(ROOT/f'artwork/pixel-{ident}/provenance.json').read_text()
            files['PIXEL-PROMPT.txt']=(ROOT/f'artwork/pixel-{ident}/prompt.txt').read_text()
            if pixel.advanced(item):
                files['TASK-KEYFRAMES-V2.json']=(ROOT/'artwork/pixel-diana-v2/provenance.json').read_text()
                for role in sorted(pixel.TASK_ROLES):
                    for i in range(4):files[f'design/task-v2/{role}/{i}.png']=ROOT/f'artwork/pixel-diana-v2/{role}/{i}.png'
            files['CURSOR-BEHAVIORS.txt']='\n\n'.join(
                role+' / '+pixel.behaviors(item)[role]['action']+'\n'+pixel.behaviors(item)[role]['meaning']+'\n'+pixel.behaviors(item)[role]['example'] for role in ROLES)
            for i in range(8):files[f'design/pose-{i}.png']=ROOT/f'artwork/pixel-{ident}/pose-{i}.png'
    windows['install.inf'] = ('[Version]\nSignature="$Windows NT$"\n[DefaultInstall]\nCopyFiles=CursorFiles\nAddReg=CursorScheme\n'
        '[DestinationDirs]\nCursorFiles=10,"Cursors\\' + theme_name + '"\n[CursorFiles]\n' +
        '\n'.join(k for k in windows if k.endswith(('.cur', '.ani'))) +
        '\n[CursorScheme]\nHKCU,"Control Panel\\Cursors\\Schemes","' + theme_name + '",0x00020000,"' +
        ','.join('%10%\\Cursors\\' + theme_name + '\\' + role + ('.ani' if role in animated_roles else '.cur') for role in ROLES) + '"\n').encode('utf-16')
    windows['README.txt'] = '可右键 install.inf 安装方案，再到鼠标设置选择该方案。也可使用本站 Windows 管理器，无需管理员权限应用／恢复。未经过 Windows 真机验收。\n'.encode('utf-8-sig')
    linux['index.theme'] = f'[Icon Theme]\nName={theme_name}\nComment={item["name"]} / Free Cur\nInherits=Adwaita\n'
    linux['install.sh'] = '''#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
theme="''' + theme_name + '''"
dest="$HOME/.local/share/icons/$theme"
mkdir -p "$dest"
cp -R cursors index.theme SOURCE-AND-RIGHTS.txt "$dest/"
printf 'Installed %s. Select it in your desktop appearance settings, or use Free Cur Manager.\n' "$theme"
'''
    cape = dict(Author='Free Cur contributors / original artwork owners credited separately', CapeName='Free Cur · ' + item['name'],
        CapeVersion=1., Identifier='cn.bismih.freecur.' + ident, Cloud=False, HiDPI=True,
        MinimumVersion=2., Version=2., Cursors=cursors)
    mac[theme_name + '.cape'] = plistlib.dumps(cape, fmt=plistlib.FMT_XML)
    mac['README.txt'] = '安装可信来源的 Mousecape 后，导入本 .cape 文件并应用；登录后自动应用需在 Mousecape 内启用 Helper。请勿关闭 SIP 或绕过系统安全功能。macOS 未做真机验证。\n官方软件：https://github.com/alexzielenski/Mousecape/releases\n'
    packages = {}
    for platform, files in [('windows', windows), ('linux', linux), ('macos', mac)]:
        output = DIST / 'downloads' / (ident + '-' + platform + '.zip')
        archive(output, files)
        packages[platform] = descriptor(output)
    return dict(id=ident, name=item['name'], group=item['group'], color=item['color'], subtitle=item.get('subtitle', ''),
        preview='/previews/' + ident + '/portrait.webp', source=item['source'], image_source=item.get('image_url'),
        rights=item['rights'], style='像素动态' if is_pixel else '头像伴随型', packages=packages,
        pixel=is_pixel, animated_roles=animated_roles,
        animation=dict(frames=8,duration_ms=frame_ms,durations_ms=pixel.DURATIONS,hotspots=pixel.HOTSPOTS,behaviors=pixel.behaviors(item),revision='task-keyframes-v2' if pixel.advanced(item) else 'character-poses-v1',redrawn_roles=sorted(pixel.TASK_ROLES) if pixel.advanced(item) else [],pose_count=8,task_keyframes=48 if pixel.advanced(item) else 0) if is_pixel else None,
        verification=dict(formats=True, linux='Xcursor 解析验收', windows='格式验证 · 待真机', macos='格式验证 · 待真机'))


def manager_packages(catalog):
    downloads = DIST / 'downloads'
    catalog_bytes = json.dumps(catalog, ensure_ascii=False).encode()
    lin = {'catalog.json': catalog_bytes, 'manager.py': (ROOT / 'manager_linux.py'),
           'start.sh': '#!/bin/sh\ncd -- "$(dirname -- "$0")"\nexec python3 manager.py\n',
           'README.txt': '安装 Python 3 与 python3-tk 后运行 python3 manager.py。仅在用户点击后安装主题并改变当前用户设置。\n'}
    mac = {'README.txt': '解压后用 Mousecape 导入需要的 .cape 文件，即可在软件里切换主题。本站不捆绑或修改 Mousecape。来源和版权见各主题。未做 Mac 真机验证。\n'}
    for item in catalog['themes']:
        ident = item['id']
        lin['packs/' + ident + '-linux.zip'] = downloads / (ident + '-linux.zip')
        with zipfile.ZipFile(downloads / (ident + '-macos.zip')) as z:
            name = 'FreeCur-' + ident + '.cape'
            mac[name] = z.read(name)
    managers = {}
    for platform, files in [('linux',lin),('macos',mac)]:
        file = downloads / ('free-cur-' + platform + '-collection.zip')
        archive(file, files)
        managers[platform] = descriptor(file)
    import windows_build
    managers['windows'], managers['windows_exe'] = windows_build.build(catalog, downloads, archive, descriptor)
    # Debian package contains the same auditable offline manager and packed themes.
    deb = BUILD / ('deb-' + hashlib.sha256(catalog_bytes).hexdigest()[:16])
    app = deb / 'usr/share/free-cur'
    app.mkdir(parents=True, exist_ok=True)
    for name, value in lin.items():
        path = app / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value.read_bytes() if isinstance(value,Path) else value.encode() if isinstance(value,str) else value)
    metadata = deb / 'DEBIAN'
    metadata.mkdir(exist_ok=True)
    (metadata / 'control').write_text('Package: free-cur-manager\nVersion: 0.1.0\nSection: x11\nPriority: optional\nArchitecture: all\nMaintainer: Free Cur\nDepends: python3 (>= 3.10), python3-tk\nDescription: Local-only noncommercial cursor theme switcher\n Contains attributed fictional-character cursor theme conversions.\n')
    executable = deb / 'usr/bin/free-cur-manager'
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text('#!/bin/sh\nexec python3 /usr/share/free-cur/manager.py "$@"\n')
    executable.chmod(0o755)
    entry = deb / 'usr/share/applications/free-cur.desktop'
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text('[Desktop Entry]\nType=Application\nName=Free Cur 光标切换器\nExec=free-cur-manager\nIcon=input-mouse\nTerminal=false\nCategories=Settings;DesktopSettings;\n')
    file = downloads / 'free-cur-manager_0.1.0_all.deb'
    subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(deb), str(file)], check=True, capture_output=True)
    managers['deb'] = descriptor(file)
    return managers


def build_mac_only(item):
    """Refresh a platform without regenerating the verified Windows/Linux bytes."""
    cursors={}
    for role, identifiers in MAC_ROLES.items():
        count=8 if pixel.enabled(item) or role in ('Wait','AppStarting') else 1
        reps=[]
        for size in (32,64):
            strip=Image.new('RGBA',(size,size*count))
            for frame in range(count):
                image,hot=artwork(item,role,size,frame)
                strip.alpha_composite(image,(0,frame*size))
            reps.append(png(strip))
        _,hot=artwork(item,role,32)
        for identifier in identifiers:
            cursors[identifier]=dict(FrameCount=count,FrameDuration=pixel.DURATIONS[role]/1000 if pixel.enabled(item) else .1,HotSpotX=float(hot[0]),HotSpotY=float(hot[1]),PointsHigh=32.,PointsWide=32.,Representations=reps)
    cape=dict(Author='Free Cur contributors / original artwork owners credited separately',CapeName='Free Cur · '+item['name'],CapeVersion=1.,Identifier='cn.bismih.freecur.'+item['id'],Cloud=False,HiDPI=True,MinimumVersion=2.,Version=2.,Cursors=cursors)
    output=DIST/'downloads'/(item['id']+'-macos.zip')
    with zipfile.ZipFile(output) as old:
        files={name:old.read(name) for name in old.namelist() if not name.endswith('.cape')}
    files['FreeCur-'+item['id']+'.cape']=plistlib.dumps(cape,fmt=plistlib.FMT_XML)
    files['MOUSECAPE-MAPPING.txt']='Identifiers follow Mousecape/mousecloak/MCDefs.m in https://github.com/alexzielenski/Mousecape . Mapping verification is not Mac runtime validation.\n'+'\n'.join(role+': '+', '.join(ids) for role,ids in MAC_ROLES.items())+'\n'
    archive(output,files)
    return descriptor(output)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--only',nargs='+',help='Rebuild named themes, retaining other verified packages')
    parser.add_argument('--mac-only',action='store_true')
    parser.add_argument('--catalog-only',action='store_true',help='Reuse active native theme packages; rebuild all collections')
    args=parser.parse_args()
    DIST.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    for name in ['downloads', 'previews']:
        (DIST / name).mkdir(exist_ok=True)
    sources = json.loads((ROOT / 'sources.json').read_text())
    allowed=set(json.loads((ROOT/'release-policy.json').read_text())['active_groups'])
    sources=[item for item in sources if item['group'] in allowed]
    previous=json.loads((DIST/'catalog.json').read_text()) if args.only or args.mac_only or args.catalog_only else {}
    existing={x['id']:x for x in previous.get('themes',[])}
    themes = []
    for item in sources:
        if item.get('available'):
            if args.catalog_only:
                themes.append(existing[item['id']])
            elif args.mac_only:
                theme=existing[item['id']]
                theme['packages']['macos']=build_mac_only(item)
                themes.append(theme)
            else:
                themes.append(existing[item['id']] if args.only and item['id'] not in args.only else build_theme(item))
    catalog = dict(version='0.8.0-hidpi', updated='2026-10-20', themes=themes,
                   roles=[dict(id=r, name=n) for r,n in zip(ROLES,NAMES)],
                   pending=[dict(name=x['name'], group=x['group'], reason=x.get('reason')) for x in sources if not x.get('available')])
    catalog['managers'] = manager_packages(catalog)
    (DIST / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, separators=(',',':')))
    for path in (ROOT / 'web').iterdir():
        if path.is_dir():
            shutil.copytree(path, DIST / path.name, dirs_exist_ok=True)
        elif path.is_file():
            shutil.copy2(path, DIST / path.name)
    installer = (ROOT / 'install-linux.sh.in').read_text().replace('# @PAYLOAD@', (ROOT / 'install_linux.py').read_text())
    (DIST / 'install-linux.sh').write_text(installer)
    import legal
    legal.build(DIST)
    print(json.dumps(dict(themes=len(themes), packages=len(themes)*3+5,
                         pending=catalog['pending'], managers=catalog['managers']), ensure_ascii=False))


if __name__ == '__main__':
    main()
