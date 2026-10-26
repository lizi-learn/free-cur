#!/usr/bin/env python3
"""Local-only cursor switcher. No service, telemetry, credentials or root required."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent
STATE = Path.home() / '.local/share/free-cur'
ICONS = Path.home() / '.local/share/icons'


def extract_theme(archive, destination):
    with zipfile.ZipFile(archive) as z:
        if sum(x.file_size for x in z.infolist()) > 40 * 1024 * 1024:
            raise ValueError('Theme is too large')
        for item in z.infolist():
            target = (destination / item.filename).resolve()
            if not target.is_relative_to(destination.resolve()) or item.filename.startswith('/'):
                raise ValueError('Unsafe archive entry')
            if (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Symlinks are not allowed')
        z.extractall(destination)


def gnome_theme():
    return subprocess.check_output(['gsettings', 'get', 'org.gnome.desktop.interface', 'cursor-theme'], text=True).strip().strip("'")


def apply_theme(theme, size=48):
    if size is not None and (not isinstance(size,int) or not 1<=size<=256):
        raise ValueError('光标大小超出 1–256px；请选择预设大小')
    STATE.mkdir(parents=True, exist_ok=True)
    backup = STATE / 'previous.json'
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    if 'gnome' in desktop or 'unity' in desktop or 'cinnamon' in desktop:
        before_theme=gnome_theme()
        before_size=int(subprocess.check_output(['gsettings','get','org.gnome.desktop.interface','cursor-size'],text=True).strip())
        if not backup.exists():
            backup.write_text(json.dumps(dict(backend='gnome', theme=before_theme,size=before_size)))
        else:
            previous=json.loads(backup.read_text())
            if 'size' not in previous:
                previous['size']=before_size;backup.write_text(json.dumps(previous))
        try:
            if size is not None:
                subprocess.run(['gsettings','set','org.gnome.desktop.interface','cursor-size',str(size)],check=True)
            subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 'cursor-theme', theme], check=True)
        except Exception:
            subprocess.run(['gsettings','set','org.gnome.desktop.interface','cursor-size',str(before_size)],check=False)
            subprocess.run(['gsettings','set','org.gnome.desktop.interface','cursor-theme',before_theme],check=False)
            raise
    elif 'kde' in desktop and shutil.which('plasma-apply-cursortheme'):
        reader = shutil.which('kreadconfig6') or shutil.which('kreadconfig5')
        previous = subprocess.check_output([reader, '--file', 'kcminputrc', '--group', 'Mouse', '--key', 'cursorTheme'], text=True).strip() if reader else ''
        if not backup.exists():
            backup.write_text(json.dumps(dict(backend='kde', theme=previous or 'breeze_cursors')))
        subprocess.run(['plasma-apply-cursortheme', theme], check=True)
    else:
        raise RuntimeError('主题已安装。当前桌面请在系统外观设置中选择 ' + theme + '；本版本自动切换支持 GNOME / KDE。')


def main():
    catalog = json.loads((ROOT / 'catalog.json').read_text())
    items = sorted(catalog['themes'], key=lambda item: not item.get('pixel', False))
    win = tk.Tk()
    win.title('Free Cur · 光标切换器')
    win.geometry('640x480')
    win.configure(background='#f8f5fc')
    style = ttk.Style(win)
    style.configure('TLabel', font=('', 12), padding=4)
    style.configure('TButton', font=('', 12), padding=8)
    frame = ttk.Frame(win, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='把喜欢，带到指尖。', font=('', 20, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='只修改当前用户 · 可恢复 · 关闭后不占用后台资源').pack(anchor='w')
    query = tk.StringVar()
    entry = ttk.Entry(frame, textvariable=query)
    entry.pack(fill='x', pady=(16, 8))
    selector = ttk.Combobox(frame, state='readonly')
    selector.pack(fill='x')
    size_row=ttk.Frame(frame);size_row.pack(fill='x',pady=(12,0))
    ttk.Label(size_row,text='光标大小').pack(side='left')
    cursor_size=ttk.Combobox(size_row,state='readonly',values=['24px','32px','48px · 默认','64px'],width=18)
    cursor_size.current(2);cursor_size.pack(side='left',padx=10)
    ttk.Label(size_row,text='GNOME 自动应用；KDE 请在系统设置调整',font=('',9)).pack(side='left')
    note = ttk.Label(frame, text='选择主题后点击「安装并应用」。部分应用需重开才会更新。', wraplength=560)
    note.pack(fill='x', pady=18)
    filtered = []

    def search(*_):
        nonlocal filtered
        term = query.get().casefold()
        filtered = [x for x in items if term in (x['name'] + x['group'] + x['id']).casefold()]
        selector['values'] = [x['group'] + ' / ' + x['name'] for x in filtered]
        if filtered:
            selector.current(0)
    query.trace_add('write', search)
    search()

    def install():
        try:
            item = filtered[selector.current()]
            file = ROOT / 'packs' / (item['id'] + '-linux.zip')
            if hashlib.sha256(file.read_bytes()).hexdigest() != item['packages']['linux']['sha256']:
                raise ValueError('安装包校验失败，未修改系统')
            target = ICONS / ('FreeCur-' + item['id'])
            target.mkdir(parents=True, exist_ok=True)
            extract_theme(file, target)
            apply_theme(target.name,(24,32,48,64)[cursor_size.current()])
            note['text'] = '已应用：' + item['name'] + '。如部分窗口未变，请重新打开应用或注销后登录。'
        except Exception as e:
            messagebox.showerror('Free Cur', str(e))

    def restore():
        try:
            previous = json.loads((STATE / 'previous.json').read_text())
            apply_theme(previous['theme'],previous.get('size'))
            note['text'] = '已恢复安装前主题：' + previous['theme']
        except FileNotFoundError:
            messagebox.showinfo('Free Cur', '还没有修改过系统主题，无需恢复。')
        except Exception as e:
            messagebox.showerror('Free Cur', str(e))
    ttk.Button(frame, text='安装并应用', command=install).pack(side='left')
    ttk.Button(frame, text='恢复原主题', command=restore).pack(side='left', padx=10)
    win.mainloop()


if __name__ == '__main__':
    main()
