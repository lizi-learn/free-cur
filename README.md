# Free Cur

像素动态鼠标指针与主题切换器。包含 Windows C# / WinForms 客户端、Linux
Python / Tkinter 客户端、三平台主题生成器、静态预览网站和可选的只读目录服务。

[在线预览与下载](https://free-cur.bismih.cn/) ·
[安装使用](https://free-cur.bismih.cn/#install) ·
[MIT 代码许可](LICENSE) · [素材来源与权利说明](NOTICE.md)

## 功能

- 19 套像素角色主题，15 类系统光标状态；同一套动画导出 Windows CUR / ANI、Linux Xcursor 和 macOS Mousecape `.cape`。
- Windows 2.5.0：当前用户安装、主题应用与恢复、目录同步、托盘和可选自启动；只读识别分辨率 / DPI，推荐尺寸，支持手动 32–128px。
- Windows HDR 指针偏白补偿为默认关闭的实验选项；不改变系统 HDR、ICC 或全屏颜色。
- Linux：应用和恢复 GNOME / KDE 当前用户主题，提供 DEB 和便携包。
- 网站：搜索、分类、分页、收藏、15 状态预览、仅网页内试用及平台下载。
- 包大小和 SHA-256 校验、路径越界防护、失败回滚；桌面客户端不上传屏幕、鼠标或用户文件。

角色动作由系统光标状态驱动，没有全局点击钩子。嘉然含 48 张功能关键帧；其余角色为
8 姿势基础版。Windows / macOS 的格式与程序测试不等于真机安装验收，HDR 和混合 DPI
屏幕效果仍需在对应设备上确认。macOS 主题需要另装 [Mousecape](https://github.com/alexzielenski/Mousecape)。

## 从源码构建

以下为 Ubuntu 24.04 / Debian 系 Linux 构建主机的流程，不会安装或应用桌面光标。
需要 Python 3.10+、Node.js 22+；普通用户执行构建，只有系统依赖安装需要管理员权限。

```sh
sudo apt-get update
sudo apt-get install mono-devel nsis x11-apps libxcursor1 dpkg-dev p7zip-full python3-venv python3-tk
git clone https://github.com/lizi-learn/free-cur.git
cd free-cur
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/prepare_net48.py
.venv/bin/python build.py
.venv/bin/python verify.py
.venv/bin/python -m unittest discover -p 'test_*.py' -v
```

`tools/prepare_net48.py` 从 NuGet 官方源下载固定版本的 .NET Framework 4.8 参考程序集，
验证 SHA-256 后解压到被 Git 忽略的 `build/toolchain/net48/`。不上传依赖二进制，不把
Mono API 程序集冒充 Windows 框架引用。`mcs`、Mono 和 `makensis` 使用系统软件源版本。

构建使用仓库内的像素帧，不需要重新采集百科图像、登录账号或访问生产服务器。
`dist/` 中生成网站、安装包、主题合集、校验清单和每主题来源说明。构建包含角色素材，
其权利边界见 [NOTICE.md](NOTICE.md)，MIT 许可仅覆盖自研代码。

本地预览：

```sh
.venv/bin/python -m http.server 3477 --bind 127.0.0.1 --directory dist
```

打开 `http://127.0.0.1:3477`。网页试用只影响当前网页。没有 Windows / macOS 真机时，
不要把离屏 Mono 预览或格式校验写成实际系统安装、恢复或颜色验收通过。

## 素材处理与网站发布

提供自己的、具备所需权利的透明角色图后，可选运行原始像素切片工具：

```sh
npm ci
node prepare-pixel.mjs /path/to/4x2-sheet.png character-id
node prepare-role-frames.mjs /path/to/sheet-0.png /path/to/sheet-1.png /path/to/sheet-2.png
```

第二个命令处理嘉然功能关键帧的三张 4×4 表；不要用其他角色图直接覆盖该目录。
生成工具固定使用最近邻、二值透明、共享调色板、对齐基线和独立热点。
`sources.json` / `roster.json` / `release-policy.json` 管理当前 19 套主题；`collect.py`
是可选的公开来源采集器，默认构建不运行它。

```sh
.venv/bin/python deploy.py --output build/public-site
```

这会将校验通过的站点文件复制到一个**全新**目录，排除缓存和不在当前目录中的历史主题。
可将输出放到你自己的静态托管或 Web 服务器，Python 测试服务器只用于本地预览。
仓库不包含原服务器部署工具或访问凭据。

Windows 客户端的目录、安装脚本和主题下载默认使用 `https://free-cur.bismih.cn`。
自行托管时需明确修改 `windows/Cloud.cs`、`control.py`、`install_linux.py`、
`install-linux.sh.in` 和 `web/index.html` 中的站点地址，再重新构建；这些同源约束
用于防止目录把客户端重定向成任意文件下载器，不应直接放开。

## 可选目录服务

```sh
.venv/bin/python control.py --database build/catalog.sqlite3 --seed dist/windows-feed.xml --port 18467
```

服务只监听 `127.0.0.1`。公共路径 `/api/windows/catalog.xml` 返回数据；维护者路径
`/admin/`、`/api/admin/` 必须由反向代理加身份认证，不能直接转发到公网。
上架 / 下架有 CSRF 和修订冲突检查，目录更新不执行远程代码、不自动更新 EXE，
也不会强制替换用户已应用的光标。只需静态站时可直接提供构建后的 `windows-feed.xml`。

## 目录

| 路径 | 用途 |
| --- | --- |
| `windows/` | 原生客户端、DPI / HDR / 光标缓存、安装与恢复 |
| `manager_linux.py`、`install_linux.py` | Linux 切换器与安装器 |
| `build.py`、`pixel.py`、`windows_build.py` | 多平台主题与安装包生成 |
| `web/` | 无框架静态网站 |
| `artwork/`、`sources.json` | 当前像素主题、提示词、来源与权利记录 |
| `control.py`、`admin.*` | 可选目录服务和维护者界面 |
| `test_*.py`、`verify.py` | 单元测试、真实格式与包完整性检查 |

提交问题前请说明系统版本、客户端版本与复现步骤。不要提交 Cookie、私钥或账号密码。
