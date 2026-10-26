"""Static policy documents; no invented third-party license or legal clearance."""
from pathlib import Path

PAGES = {
 'terms.html': ('免责声明与使用说明', '''
 <p>更新日期：2026 年 10 月 20 日。本项目是免费的非官方光标主题转换与交流站，不收费、不售卖主题、不投放广告。</p>
 <div class="notice"><strong>免费、非商业不等于获得版权授权。</strong><p>角色、名称、商标和原图的权利仍归各自权利人所有。本站不能授予自己并不拥有的素材再分发权，也不将百科的文字许可套用到其中的图片。</p></div>
 <h2>一、非官方二次创作</h2><p>本站与 A-SOUL、EOE、星瞳、阿梓、四禧丸子、永雏塔菲及其制作、运营方均无隶属或代言关系。角色收录不代表当前成员名单或活动状态。</p>
 <h2>二、素材与授权</h2><p>每个主题的详情及压缩包内 SOURCE-AND-RIGHTS.txt 均保留角色页面、图片来源和文件校验信息。图片按原始权利归属标注，未获得独立商业许可；请勿把本站素材转售、用于仿冒官方身份或声称拥有原作版权。</p><p>若你是权利人或其授权代理人，请通过<a href="https://github.com/lizi-learn" target="_blank" rel="noopener noreferrer">维护者公开主页</a>提供作品链接、权属说明、对应主题和诉求。核实后将处理移除、替换或补充署名。免责声明本身不免除法定责任。</p>
 <h2>三、软件与系统兼容</h2><p>19 个角色均提供独立生成的像素底稿：新补充的 18 个角色各有 8 张姿势，编排为 15 种动态光标状态；嘉然另保留 12 种功能专用动作、48 张关键帧的精修版。基础版不冒称达到同等专用动作细节。均为 AI 辅助二创，不是官方像素素材，也不冒称纯人工逐像素手绘。</p><p>系统动画按常规、链接、文本、忙碌等角色播放；不安装全局鼠标点击监听器，桌面点击本身不会独立触发动作。网页里的点击反应仅限本页。macOS 仅映射已明确的系统角色，其余由系统保留默认样式。</p><p>格式和热点校验不等于真实系统兼容保证。本次未进行 Windows、macOS 真机验收。Linux 的 GNOME / KDE、X11 / Wayland 及具体应用可能存在主题覆盖差异。更换后部分应用需要重开、注销或重新登录。</p>
 <h2>四、安装与恢复</h2><p>网页试用只影响本页，不会安装或更改系统。需要你主动下载并运行安装器，或在系统 / Mousecape 内应用主题。切换器在首次修改前备份原设置；请勿删除该备份后再要求自动恢复。</p><p>Windows 2.5 是 C# 界面与当前用户安装器，不使用 PowerShell 包装或修改执行策略。安装不会自动更换光标；云端上架／下架只改变可选目录，不强制替换已应用的主题。请仅从可信来源下载并核对 SHA-256，安装前可阅读随包源码。不要关闭 SIP、防病毒软件、SmartScreen 或其它系统安全保护来强行运行文件。</p><p>HDR 指针偏白补偿为默认关闭、手动选择强度的实验兼容选项，适用于指针传递函数不匹配的情况，不等于通用 HDR 校准。只生成独立的本地指针缓存，不修改原主题、HDR 开关、ICC 或整屏色彩。尚未在发生问题的 HDR 电脑完成实测；混合 HDR / SDR 显示器共享系统指针，需逐屏核对效果。</p>
 <p>Windows 2.5 增加只读的分辨率／DPI 自动推荐和 96／128px 原生动画帧；保留手动 32–128px。推荐不代表能得知屏幕真实英寸或个人视觉偏好，选好后仍需主动应用。像素风最近邻放大保持硬边，不等于增加原画细节。多屏窗口移动会更新推荐；程序关闭后不常驻跟踪全局鼠标，实际跨屏光标仍由 Windows 管理。</p><h2>五、责任边界</h2><p>软件按现状提供，可能存在错误。不承诺适用于所有系统或用途。若有异常请先恢复默认主题并退出切换器。上述说明不排除适用法律下不可排除的责任。</p>
 '''),
 'privacy.html': ('隐私条款', '''
 <p>更新日期：2026 年 10 月 20 日。Free Cur 尽量以静态文件和本地操作完成工作，不需要你提供账号、密码、手机号或其它身份资料。</p>
 <h2>一、网站在本机保存什么</h2><p>浏览器 localStorage 仅保存你收藏的主题 ID 和明暗主题选择。网页试用状态只在当前页面内存中存在。这些信息不会主动上传服务器，可通过清除本网站的站点数据删除。</p>
 <h2>二、网络请求与基础信息</h2><p>网页会向本站请求 HTML、样式、主题索引、预览图和下载包。本站不启用广告、第三方统计脚本、跨站跟踪或用户登录。操作系统识别仅在本机用于预选下载格式，可手动修改。</p><p>服务器、DNS、TLS 或网络服务商在传输请求时会接触 IP、时间、请求路径等必要信息，并可能依其政策保留基础安全日志。因此不保证绝对匿名，也不把“无业务统计”说成网络层面完全不留记录。</p>
 <h2>三、本地切换器与云端目录</h2><p>Windows 2.5 打开时自动向 free-cur.bismih.cn 请求主题目录，运行期间约每 30 分钟静默检查；新主题在你点击应用时下载，仅访问本站 HTTPS 目录、PNG 预览和 ZIP 素材。下架只移出可选目录，不删除本地文件或强制替换正在使用的光标；断网使用最近缓存。不下载运行新 EXE、脚本或其它远程指令。Linux 现版切换器仍离线工作。</p><p>切换器不读取浏览记录、剪贴板、账号凭据或用户文档，不上报设备标识、屏幕、鼠标或应用记录。正常下载请求的 IP、时间、路径仍会被网络服务处理，路径也可能表明请求了哪个主题。Windows 自启动默认关闭，可由你选择启动到托盘；退出后不常驻、不继续同步。</p><p>Linux 状态保存于 ~/.local/share/free-cur，主题保存于 ~/.local/share/icons/FreeCur-*；Windows 状态、目录缓存与主题保存于 %LOCALAPPDATA%\\FreeCur，设置限于当前用户鼠标指针注册表；可选自启动只写当前用户的 Run 项。系统或包管理器会记录正常安装信息。</p>
 <p>HDR 补偿强度和大小保存在当前用户的本地设置中，派生指针缓存也仅保存在本机。「检测显示」只读取活动显示器的色彩状态，不上传检测结果，不修改 HDR、ACM、ICC 或系统伽马。</p><h2>四、第三方软件与链接</h2><p>macOS 使用第三方 Mousecape 导入 .cape；其隐私政策与兼容性由该项目负责。本站不捆绑 Mousecape。角色来源、GitHub 和维护者主页链接在你主动点击后会访问相应网站，其信息处理按各自政策执行。</p>
 <p>Windows 2.5 的自动大小推荐只在本机读取当前屏幕物理分辨率与有效 DPI，不上传屏幕型号、分辨率或缩放。auto/manual 模式与最后应用大小保存在已有的本地设置中，不安装驱动、全局鼠标钩子或额外后台服务，也不更改显示分辨率或系统缩放。</p><h2>五、删除与联系</h2><p>可清除浏览器站点数据；本地请先恢复原光标，再删除主题目录、切换器及其备份。DEB 可使用包管理器卸载。问题或权利请求可通过<a href="https://github.com/lizi-learn" target="_blank" rel="noopener noreferrer">维护者公开主页</a>联系。</p>
 '''),
 'about.html': ('关于 Free Cur 与素材来源', '''
 <p>把喜欢的角色带到指尖：一个可预览、可下载、有来源记录的非商业光标主题库。</p>
 <h2>做了什么</h2><p>以公开角色形象为参考，用内置图像生成工具分别创作角色像素底稿，再切片、对齐脚底、统一调色板，编排动画、固定热点，并导出 Windows ANI、Linux Xcursor、macOS Mousecape .cape。全部 19 个角色均已换成像素版，未把旧头像套滤镜或嘉然改色当作新角色。</p><p>18 个新增基础像素版各有 8 张姿势；嘉然保留 12 种功能专用动作、48 张关键帧及 8 种休闲表情的精修版。两种细节等级明确区分。每包包含本角色底稿、原作链接、生成提示词、版权说明和 SHA-256 校验值。</p>
 <div class="notice"><strong>当前是可用的格式与安装链路首版，不是所有平台都已经实机验收。</strong><p>网站每个主题都对应实际生成的文件，不把待补充角色计入可下载数量。Windows / macOS 的真机体验仍待验证；预览不会偷偷修改系统。</p></div>
 <h2>参考与技术</h2><ul>
 <li>使用自研 CUR / ANI、Xcursor 与 Mousecape 格式生成器。源码采用 MIT 许可，角色素材的来源与权利说明另见项目仓库。</li>
 <li><a href="https://learn.microsoft.com/en-us/windows/win32/menurc/about-cursors" target="_blank" rel="noopener noreferrer">Microsoft：Windows 光标与热点</a>。</li>
 <li><a href="https://gitlab.freedesktop.org/xorg/app/xcursorgen" target="_blank" rel="noopener noreferrer">X.Org xcursorgen</a>：将各尺寸图像编译成原生 Xcursor。</li>
 <li><a href="https://github.com/alexzielenski/Mousecape" target="_blank" rel="noopener noreferrer">Mousecape</a>：.cape 格式和后台切换路线；本站不修改或重新打包其程序。</li></ul>
 <h2>角色资料与图像</h2><p>形象参考来自<a href="https://zh.moegirl.org.cn/" target="_blank" rel="noopener noreferrer">萌娘百科</a>对应条目的公开图片。当前像素主题收录 A-SOUL 的向晚、贝拉、珈乐、嘉然、乃琳、心宜、思诺；EOE 的露早、柚恩、莞儿、米诺、虞莫；四禧丸子的梨安、沐霂、恬豆、又一，以及星瞳、阿梓、永雏塔菲，共 19 个。角色各自的原图只作为形象参考，不是直接缩小成圆头像。</p><p>各主题详情链接到具体出处，包内另保留原图 URL。百科文字许可不等于图片许可，本站不声称已获得素材权利人的独立授权。</p>
 <h2>云端只管理主题目录</h2><p>普通访客无需登录。维护者有单独身份验证的上架／下架后台；Windows 客户端只读取经过校验的数据目录，保持本地缓存，不接收可执行指令。云端下架不强制更换你已应用的光标。软件可选启动到托盘，默认关闭自启动；Linux 用本地窗口，macOS 用 Mousecape。无需把鼠标或屏幕发送到云端。</p>
 '''),
}


def build(destination):
    for name, (title, content) in PAGES.items():
        html = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>''' + title + ''' · Free Cur</title><link rel="stylesheet" href="/style.css"><link rel="icon" href="/favicon.svg"></head><body><header class="header"><a class="brand" href="/">free<span>cur</span></a><nav><a href="/#library">主题库</a><a href="/#install">安装指南</a><a href="/about.html">关于</a></nav></header><main class="legal"><span class="eyebrow">FREE CUR · TRANSPARENCY</span><h1>''' + title + '</h1>' + content + '''<p class="notice"><a href="/">← 返回主题库</a> · <a href="/terms.html">免责声明</a> · <a href="/privacy.html">隐私条款</a></p></main></body></html>'''
        (destination / name).write_text(html)
