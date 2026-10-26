// Free Cur: current-user cursor settings; metadata-only cloud catalogue, no remote code.
using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;
using System.Xml;
using Microsoft.Win32;

[assembly: AssemblyTitle("Free Cur 光标切换器")]
[assembly: AssemblyDescription("Offline, current-user cursor theme manager")]
[assembly: AssemblyCompany("Free Cur contributors")]
[assembly: AssemblyProduct("Free Cur")]
[assembly: AssemblyVersion("2.5.0.0")]
[assembly: AssemblyFileVersion("2.5.0.0")]

internal sealed class Theme {
    internal string Id, Name, Group, Hash, PackUrl, PreviewUrl, PreviewHash;
    internal long PreviewBytes;
    internal long Bytes;
    internal bool Pixel;
    internal Dictionary<string, string> Files = new Dictionary<string, string>();
    public override string ToString() { return Group + " / " + Name + (Pixel ? " · 像素动态" : " · 旧版头像"); }
}

internal static class Core {
    internal static readonly string[] Roles = { "Arrow", "Help", "AppStarting", "Wait", "Crosshair", "IBeam", "NWPen", "No", "SizeNS", "SizeWE", "SizeNWSE", "SizeNESW", "SizeAll", "UpArrow", "Hand" };
    internal const string RegistryPath = @"Control Panel\Cursors";
    internal static string Store { get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "FreeCur"); } }
    internal static string BackupFile { get { return Path.Combine(Store, "previous-native.xml"); } }
    [DllImport("user32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool SystemParametersInfo(uint action, uint param, IntPtr data, uint flags);
    [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern IntPtr LoadImage(IntPtr instance,string name,uint type,int width,int height,uint flags);
    [DllImport("user32.dll", SetLastError=true)]
    private static extern bool SetSystemCursor(IntPtr cursor,uint id);
    [DllImport("user32.dll", SetLastError=true)]
    private static extern bool DestroyCursor(IntPtr cursor);
    internal static readonly int[] CursorSizes={32,48,64,96,128};
    internal static bool PreferredAutomaticSize() {
        try { return ReadXml(Path.Combine(Store,"cursor-preferences.xml")).SelectSingleNode("/settings/size-mode").InnerText!="manual"; }
        catch { return true; }
    }
    internal static int PreferredSize() {
        try { int current=int.Parse(ReadXml(Path.Combine(Store,"cursor-preferences.xml")).SelectSingleNode("/settings/size").InnerText);if(CursorSizes.Contains(current))return current; } catch { }
        try { int value=int.Parse(File.ReadAllText(Path.Combine(Store,"cursor-size.txt")));return CursorSizes.Contains(value)?value:48; }
        catch { return 48; }
    }
    internal static int PreferredHdrStrength() {
        try { int value=int.Parse(ReadXml(Path.Combine(Store,"cursor-preferences.xml")).SelectSingleNode("/settings/hdr-strength").InnerText);HdrColor.ValidateStrength(value);return value; }
        catch { return 0; }
    }
    internal static void ValidateSize(int size) {
        if(!CursorSizes.Contains(size))throw new ArgumentOutOfRangeException("size","只允许 32、48、64、96、128px。");
    }
    private static void ApplySizedCursors(string target,Theme theme,int size) {
        // Owned LoadImage handles are consumed by successful SetSystemCursor calls.
        var ids=new Dictionary<string,uint>{{"Arrow",32512},{"IBeam",32513},{"Wait",32514},{"Crosshair",32515},
            {"UpArrow",32516},{"SizeNWSE",32642},{"SizeNESW",32643},{"SizeWE",32644},{"SizeNS",32645},
            {"SizeAll",32646},{"No",32648},{"Hand",32649},{"AppStarting",32650},{"Help",32651}};
        foreach(var pair in ids) {
            IntPtr handle=LoadImage(IntPtr.Zero,Path.Combine(target,theme.Files[pair.Key]),2,size,size,0x10);
            if(handle==IntPtr.Zero)throw new InvalidOperationException("加载光标尺寸失败："+pair.Key);
            if(!SetSystemCursor(handle,pair.Value)) {
                DestroyCursor(handle);throw new InvalidOperationException("系统未接受光标尺寸："+pair.Key);
            }
        }
        // NWPen uses the standard persisted theme path, not an undocumented OCR_PEN call.
    }

    internal static XmlDocument ReadXml(string path) {
        var document = new XmlDocument { XmlResolver = null };
        var settings = new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null, MaxCharactersInDocument = 2 * 1024 * 1024 };
        using (var reader = XmlReader.Create(path, settings)) document.Load(reader);
        return document;
    }

    internal static List<Theme> ReadThemes(string root) {
        return ParseThemes(ReadXml(Path.Combine(root, "themes.xml")), false);
    }

    internal static List<Theme> ParseThemes(XmlDocument document, bool allowEmpty) {
        var result = new List<Theme>();
        if (document.DocumentElement.Name != "free-cur") throw new InvalidDataException("主题索引格式错误");
        foreach (XmlElement element in document.DocumentElement.SelectNodes("theme")) {
            var theme = new Theme { Id = element.GetAttribute("id"), Name = element.GetAttribute("name"), Group = element.GetAttribute("group"),
                Hash = element.GetAttribute("sha256"), Pixel = element.GetAttribute("pixel") == "true" };
            if (!Regex.IsMatch(theme.Id, "^[a-z0-9]+(?:-[a-z0-9]+)*$") || result.Any(x => x.Id == theme.Id)
                    || !Regex.IsMatch(theme.Hash, "^[0-9a-f]{64}$") || !long.TryParse(element.GetAttribute("bytes"), out theme.Bytes)
                    || theme.Bytes < 1 || theme.Bytes > 40 * 1024 * 1024) throw new InvalidDataException("主题索引校验失败");
            foreach (XmlElement role in element.SelectNodes("role")) {
                string name = role.GetAttribute("name"), file = role.GetAttribute("file");
                if (!Roles.Contains(name) || (file != name + ".ani" && file != name + ".cur") || theme.Files.ContainsKey(name))
                    throw new InvalidDataException("不安全的光标角色路径");
                theme.Files.Add(name, file);
            }
            if (theme.Files.Count != Roles.Length) throw new InvalidDataException("光标角色不完整");
            theme.PackUrl = element.GetAttribute("url");
            if (theme.PackUrl == "") theme.PackUrl = "/downloads/" + theme.Id + "-windows.zip";
            if (theme.PackUrl != "/downloads/" + theme.Id + "-windows.zip") throw new InvalidDataException("主题下载路径不合法");
            theme.PreviewUrl = element.GetAttribute("preview");
            theme.PreviewHash = element.GetAttribute("preview-sha256");
            long.TryParse(element.GetAttribute("preview-bytes"), out theme.PreviewBytes);
            if (theme.PreviewUrl != "" && (theme.PreviewUrl != "/previews/" + theme.Id + "/Arrow.png"
                    || !Regex.IsMatch(theme.PreviewHash, "^[0-9a-f]{64}$") || theme.PreviewBytes < 1 || theme.PreviewBytes > 2 * 1024 * 1024))
                throw new InvalidDataException("预览索引不合法");
            result.Add(theme);
        }
        if ((!allowEmpty && result.Count < 1) || result.Count > 100) throw new InvalidDataException("主题数量异常");
        return result.OrderByDescending(x => x.Pixel).ToList();
    }

    internal static Dictionary<string, byte[]> ValidatePack(string root, Theme theme) {
        return ValidatePackFile(Path.Combine(root, "packs", theme.Id + "-windows.zip"), theme);
    }

    internal static Dictionary<string, byte[]> ValidatePackFile(string pack, Theme theme) {
        using (var stream = File.OpenRead(pack)) {
            if (stream.Length != theme.Bytes) throw new InvalidDataException("安装包大小不符：" + theme.Name);
            using (var hash = SHA256.Create()) {
                string digest = BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
                if (digest != theme.Hash) throw new InvalidDataException("安装包 SHA-256 校验失败：" + theme.Name);
            }
        }
        var output = new Dictionary<string, byte[]>();
        using (var stream = File.OpenRead(pack))
        using (var archive = new ZipArchive(stream, ZipArchiveMode.Read)) {
            long size = 0;
            var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            if (archive.Entries.Count > 500) throw new InvalidDataException("安装包文件过多");
            foreach (var entry in archive.Entries) {
                string name = entry.FullName.TrimEnd(new char[] { '/' });
                if (string.IsNullOrEmpty(name) || name.Contains("\\") || name.Contains(":") || name.StartsWith("/")
                        || name.Split('/').Any(x => x == ".." || x == "." || x == "") || !names.Add(name)
                        || ((entry.ExternalAttributes >> 16) & 0xF000) == 0xA000)
                    throw new InvalidDataException("安装包包含不安全路径");
                size += entry.Length;
                if (size > 40 * 1024 * 1024) throw new InvalidDataException("安装包解压大小异常");
                if (!theme.Files.Values.Contains(entry.FullName)) continue;
                if (entry.Length < 12 || entry.Length > 4 * 1024 * 1024) throw new InvalidDataException("光标文件大小异常");
                using (var source = entry.Open())
                using (var memory = new MemoryStream()) {
                    source.CopyTo(memory);
                    byte[] data = memory.ToArray();
                    bool valid = entry.FullName.EndsWith(".ani")
                        ? Encoding.ASCII.GetString(data, 0, 4) == "RIFF" && Encoding.ASCII.GetString(data, 8, 4) == "ACON"
                        : data[0] == 0 && data[1] == 0 && data[2] == 2 && data[3] == 0;
                    if (!valid) throw new InvalidDataException("光标文件头错误");
                    output.Add(entry.FullName, data);
                }
            }
        }
        if (output.Count != Roles.Length) throw new InvalidDataException("安装包缺少光标文件");
        return output;
    }

    private static XmlDocument Snapshot() {
        var document = new XmlDocument();
        var root = document.CreateElement("cursors"); document.AppendChild(root);
        using (var key = Registry.CurrentUser.OpenSubKey(RegistryPath)) {
            var size=document.CreateElement("base-size");
            bool sizeExists=key!=null&&key.GetValueNames().Contains("CursorBaseSize");
            size.SetAttribute("exists",sizeExists.ToString());
            if(sizeExists) {
                if(key.GetValueKind("CursorBaseSize")!=RegistryValueKind.DWord)throw new InvalidDataException("原光标大小设置类型异常");
                size.InnerText=Convert.ToInt32(key.GetValue("CursorBaseSize")).ToString();
            }
            root.AppendChild(size);
            foreach (string role in Roles) {
                var item = document.CreateElement("role"); item.SetAttribute("name", role);
                bool exists = key != null && key.GetValueNames().Contains(role);
                item.SetAttribute("exists", exists.ToString());
                if (exists) {
                    var kind = key.GetValueKind(role);
                    if (kind != RegistryValueKind.String && kind != RegistryValueKind.ExpandString)
                        throw new InvalidDataException("已有指针设置类型异常，未修改系统");
                    item.SetAttribute("kind", kind.ToString());
                    item.InnerText = (string)key.GetValue(role, "", RegistryValueOptions.DoNotExpandEnvironmentNames);
                }
                root.AppendChild(item);
            }
        }
        return document;
    }

    private static void SaveOriginal(XmlDocument document) {
        Directory.CreateDirectory(Store);
        if (File.Exists(BackupFile)) {
            var original=ReadXml(BackupFile);
            if(original.SelectSingleNode("/cursors/base-size")==null) {
                original.DocumentElement.AppendChild(original.ImportNode(document.SelectSingleNode("/cursors/base-size"),true));
                string upgraded=BackupFile+".upgrade-"+Guid.NewGuid().ToString("N");
                original.Save(upgraded);
                try { File.Replace(upgraded,BackupFile,null); } finally { if(File.Exists(upgraded))File.Delete(upgraded); }
            }
            return;
        }
        string pending = Path.Combine(Store, "backup-" + Guid.NewGuid().ToString("N") + ".tmp");
        try {
            document.Save(pending);
            File.Move(pending, BackupFile); // No overwrite of an earlier backup.
        } finally { if (File.Exists(pending)) File.Delete(pending); }
    }

    private static void Reload() {
        if (!SystemParametersInfo(0x0057, 0, IntPtr.Zero, 0)) throw new InvalidOperationException("系统未确认刷新，请打开 Windows 鼠标设置检查");
    }

    private static void RestoreDocument(XmlDocument document, bool onlyOurValues) {
        var elements = document.SelectNodes("/cursors/role").Cast<XmlElement>().ToList();
        if (elements.Count != Roles.Length || !new HashSet<string>(elements.Select(x => x.GetAttribute("name"))).SetEquals(Roles))
            throw new InvalidDataException("备份角色不完整，未修改系统");
        foreach (var item in elements) {
            if (item.GetAttribute("exists") != "True" && item.GetAttribute("exists") != "False") throw new InvalidDataException("备份格式异常");
            if (item.GetAttribute("exists") == "True" && item.GetAttribute("kind") != "String" && item.GetAttribute("kind") != "ExpandString")
                throw new InvalidDataException("备份类型异常");
        }
        var sizeNode=document.SelectSingleNode("/cursors/base-size") as XmlElement;
        int previousSize=32;
        if(sizeNode!=null&&(sizeNode.GetAttribute("exists")!="True"&&sizeNode.GetAttribute("exists")!="False"
                ||sizeNode.GetAttribute("exists")=="True"&&!int.TryParse(sizeNode.InnerText,out previousSize)))
            throw new InvalidDataException("光标大小备份异常");
        using (var key = Registry.CurrentUser.CreateSubKey(RegistryPath)) {
            string ownPrefix = Path.Combine(Store, "themes") + Path.DirectorySeparatorChar;
            bool allOurs=Roles.All(role=>(key.GetValue(role,"") as string??"").StartsWith(ownPrefix,StringComparison.OrdinalIgnoreCase));
            foreach (var item in elements) {
                string role = item.GetAttribute("name");
                string current = key.GetValue(role, "", RegistryValueOptions.DoNotExpandEnvironmentNames) as string ?? "";
                if (onlyOurValues && !current.StartsWith(ownPrefix, StringComparison.OrdinalIgnoreCase)) continue;
                if (item.GetAttribute("exists") == "True")
                    key.SetValue(role, item.InnerText, item.GetAttribute("kind") == "String" ? RegistryValueKind.String : RegistryValueKind.ExpandString);
                else key.DeleteValue(role, false);
            }
            if(sizeNode!=null&&(!onlyOurValues||allOurs)) {
                if(sizeNode.GetAttribute("exists")=="True")key.SetValue("CursorBaseSize",previousSize,RegistryValueKind.DWord);
                else key.DeleteValue("CursorBaseSize",false);
            }
        }
        Reload();
    }

    internal static void Restore(bool uninstall) {
        if (!File.Exists(BackupFile)) {
            if (uninstall) return;
            throw new InvalidOperationException("还没有应用过主题，无需恢复。");
        }
        RestoreDocument(ReadXml(BackupFile), uninstall);
    }

    internal static void Apply(string root, Theme theme) { Apply(root,theme,PreferredSize()); }

    internal static void Apply(string root, Theme theme,int size) { Apply(root,theme,size,PreferredHdrStrength()); }

    internal static void Apply(string root, Theme theme,int size,int hdrStrength) { Apply(root,theme,size,hdrStrength,false); }

    internal static void Apply(string root, Theme theme,int size,int hdrStrength,bool automatic) {
        ValidateSize(size);HdrColor.ValidateStrength(hdrStrength);
        var sourceFiles = ValidatePackFile(Cloud.EnsurePack(root, theme), theme); // Validate before touching settings.
        var files=HdrColor.Prepare(sourceFiles,hdrStrength); // Derived cache, never alter a signed/hash-checked source pack.
        files=files.ToDictionary(x=>x.Key,x=>CursorSizing.Exact(x.Value,size));
        string folder = Path.Combine(Store, "themes"); Directory.CreateDirectory(folder);
        string target = Path.Combine(folder, theme.Id + "-" + theme.Hash.Substring(0, 16)+HdrColor.CacheSuffix(hdrStrength)+"-"+CursorSizing.Revision+"-"+size);
        if (Directory.Exists(target)) {
            if (Directory.GetFiles(target).Length != files.Count || files.Any(pair => !File.Exists(Path.Combine(target, pair.Key))
                    || !File.ReadAllBytes(Path.Combine(target, pair.Key)).SequenceEqual(pair.Value)))
                throw new InvalidDataException("已安装主题被本地修改，保留原文件；请先检查 " + target);
        } else {
            string staging = Path.Combine(folder, ".stage-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(staging);
            try {
                foreach (var pair in files) File.WriteAllBytes(Path.Combine(staging, pair.Key), pair.Value);
                Directory.Move(staging, target);
            } finally { if (Directory.Exists(staging)) Directory.Delete(staging, true); }
        }
        XmlDocument before = Snapshot();
        SaveOriginal(before);
        try {
            using (var key = Registry.CurrentUser.CreateSubKey(RegistryPath)) {
                foreach (var pair in theme.Files) key.SetValue(pair.Key, Path.Combine(target, pair.Value), RegistryValueKind.ExpandString);
                key.SetValue("CursorBaseSize",size,RegistryValueKind.DWord);
            }
            Reload();
            ApplySizedCursors(target,theme,size);
            Cloud.AtomicWrite(Path.Combine(Store,"cursor-preferences.xml"),Encoding.UTF8.GetBytes("<settings><size>"+size+"</size><size-mode>"+(automatic?"auto":"manual")+"</size-mode><hdr-strength>"+hdrStrength+"</hdr-strength></settings>"));
        } catch { RestoreDocument(before, false); throw; }
    }
}

internal sealed class ManagerForm : Form {
    private readonly string root;
    private readonly List<Theme> themes;
    private readonly ComboBox selection = new ComboBox();
    private readonly Label note = new Label();
    internal ManagerForm(string directory) {
        root = directory; themes = Core.ReadThemes(root);
        Text = "Free Cur · 光标切换器"; StartPosition = FormStartPosition.CenterScreen;
        ClientSize = new Size(660, 400); MinimumSize = new Size(600, 430); AutoScaleMode = AutoScaleMode.Dpi;
        Font = new Font("Microsoft YaHei UI", 11); BackColor = Color.FromArgb(251, 248, 242);
        string icon = Path.Combine(root, "free-cur.ico"); if (File.Exists(icon)) Icon = new Icon(icon);
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(28), ColumnCount = 1, RowCount = 6 };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 52));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 40));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 48));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 48));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 54));
        var title = new Label { Text = "把喜欢，带到指尖。", AutoSize = true, Font = new Font(Font.FontFamily, 21, FontStyle.Bold) };
        var subtitle = new Label { Text = "离线可用 · 仅当前用户 · 应用后可关闭，无需后台常驻", AutoSize = true, ForeColor = Color.DimGray };
        var search = new TextBox { Dock = DockStyle.Top, AccessibleName = "搜索角色或系列" };
        selection.Dock = DockStyle.Top; selection.DropDownStyle = ComboBoxStyle.DropDownList; selection.AccessibleName = "选择光标主题";
        note.Text = "安装没有改变你的光标。选择主题后点击「安装并应用」。"; note.Dock = DockStyle.Fill; note.ForeColor = Color.FromArgb(110, 85, 105);
        var actions = new FlowLayoutPanel { Dock = DockStyle.Fill, WrapContents = false };
        var apply = new Button { Text = "安装并应用", AutoSize = true, Height = 42, BackColor = Color.FromArgb(187, 83, 119), ForeColor = Color.White, FlatStyle = FlatStyle.Flat };
        var restore = new Button { Text = "恢复原主题", AutoSize = true, Height = 42 };
        apply.Click += delegate { Guard(delegate { if (selection.SelectedItem == null) return; var theme = (Theme)selection.SelectedItem;
            Core.Apply(root, theme); note.Text = "已应用：" + theme.Name + "。现在可以关闭切换器；主题设置会保留。"; }); };
        restore.Click += delegate { Guard(delegate { Core.Restore(false); note.Text = "已恢复第一次应用前的光标设置。"; }); };
        actions.Controls.Add(apply); actions.Controls.Add(restore);
        layout.Controls.Add(title, 0, 0); layout.Controls.Add(subtitle, 0, 1); layout.Controls.Add(search, 0, 2);
        layout.Controls.Add(selection, 0, 3); layout.Controls.Add(note, 0, 4); layout.Controls.Add(actions, 0, 5); Controls.Add(layout);
        Action filter = delegate { selection.Items.Clear(); foreach (var theme in themes.Where(x => (x.Name + " " + x.Group + " " + x.Id).IndexOf(search.Text, StringComparison.OrdinalIgnoreCase) >= 0)) selection.Items.Add(theme);
            if (selection.Items.Count > 0) selection.SelectedIndex = 0; };
        search.TextChanged += delegate { filter(); }; filter();
    }
    private void Guard(Action action) { try { UseWaitCursor = true; action(); } catch (Exception error) {
        MessageBox.Show(this, error.Message, "Free Cur", MessageBoxButtons.OK, MessageBoxIcon.Information);
    } finally { UseWaitCursor = false; } }
}

internal static class Program {
    [STAThread]
    private static int Main(string[] args) {
        try {
            if(args.Length==4&&args[0]=="--recommend-size") { Console.WriteLine(ScreenSizing.Recommend(int.Parse(args[1]),int.Parse(args[2]),int.Parse(args[3])));return 0; }
            if(args.Length==1&&args[0]=="--screen-status") { var profile=ScreenSizing.Read(IntPtr.Zero);Console.WriteLine(profile.Description+" · 推荐 "+profile.Recommended+"px · "+profile.Source);return 0; }
            if(args.Length==3&&args[0]=="--check-offline-catalog") { foreach(var theme in Cloud.OfflineThemes(Path.GetFullPath(args[1]),Core.ReadXml(args[2])))Console.WriteLine(theme.Id+":"+theme.Hash);return 0; }
            if(args.Length==5&&args[0]=="--convert-size") {
                byte[] converted=CursorSizing.Exact(File.ReadAllBytes(args[1]),int.Parse(args[3]));
                if(args[4]!="file-only")throw new ArgumentException("诊断转换仅允许 file-only。");
                using(var output=new FileStream(args[2],FileMode.CreateNew,FileAccess.Write))output.Write(converted,0,converted.Length);
                Console.WriteLine("Selected exact native bitmap; no system settings changed.");return 0;
            }
            if(args.Length==5&&args[0]=="--export-sized-packages") {
                int size=int.Parse(args[2]),strength=int.Parse(args[3]);Core.ValidateSize(size);HdrColor.ValidateStrength(strength);
                string destination=Path.GetFullPath(args[4]);if(Directory.Exists(destination)||File.Exists(destination))throw new IOException("输出目录已存在，拒绝覆盖。");
                var entries=Core.ReadThemes(Path.GetFullPath(args[1]));
                foreach(var entry in entries) {
                    var files=HdrColor.Prepare(Core.ValidatePack(Path.GetFullPath(args[1]),entry),strength);
                    foreach(var file in files) {
                        byte[] converted=CursorSizing.Exact(file.Value,size);string folder=Path.Combine(destination,entry.Id);Directory.CreateDirectory(folder);
                        using(var stream=new FileStream(Path.Combine(folder,file.Key),FileMode.CreateNew,FileAccess.Write))stream.Write(converted,0,converted.Length);
                    }
                }
                Console.WriteLine("Selected native {0}px: {1} themes / {2} cursor roles; no system settings changed.",size,entries.Count,entries.Count*Core.Roles.Length);return 0;
            }
            if(args.Length==2&&args[0]=="--hdr-lut") { Console.WriteLine(string.Join(",",HdrColor.Lookup(int.Parse(args[1])).Select(x=>x.ToString()).ToArray()));return 0; }
            if(args.Length==3&&args[0]=="--check-color-mode") { Console.WriteLine(HdrDisplay.Interpret(uint.Parse(args[1]),args[2]=="legacy"?(int?)null:int.Parse(args[2])));return 0; }
            if(args.Length==1&&args[0]=="--display-status") { Console.WriteLine(HdrDisplay.Summary());return 0; }
            if(args.Length==5&&args[0]=="--convert-hdr") {
                int strength=int.Parse(args[3]);HdrColor.ValidateStrength(strength);
                byte[] converted=HdrColor.Transform(File.ReadAllBytes(args[1]),strength);
                if(args[4]!="file-only")throw new ArgumentException("诊断转换仅允许 file-only。");
                using(var output=new FileStream(args[2],FileMode.CreateNew,FileAccess.Write))output.Write(converted,0,converted.Length);
                Console.WriteLine("Converted cursor data only; no display or registry changes.");return 0;
            }
            if(args.Length==4&&args[0]=="--export-hdr-packages") {
                int strength=int.Parse(args[2]);HdrColor.ValidateStrength(strength);
                string destination=Path.GetFullPath(args[3]);if(Directory.Exists(destination)||File.Exists(destination))throw new IOException("输出目录已存在，拒绝覆盖。");
                string source=Path.GetFullPath(args[1]);var entries=Core.ReadThemes(source);
                foreach(var entry in entries) {
                    var converted=HdrColor.Prepare(Core.ValidatePack(source,entry),strength);
                    string folder=Path.Combine(destination,entry.Id);Directory.CreateDirectory(folder);
                    foreach(var file in converted)using(var stream=new FileStream(Path.Combine(folder,file.Key),FileMode.CreateNew,FileAccess.Write))stream.Write(file.Value,0,file.Value.Length);
                }
                Console.WriteLine("Converted {0} themes / {1} cursor roles; no system settings changed.",entries.Count,entries.Count*Core.Roles.Length);return 0;
            }
            if(args.Length==2&&args[0]=="--check-size") { int size=int.Parse(args[1]);Core.ValidateSize(size);Console.WriteLine("Cursor size: "+size);return 0; }
            if (args.Length == 2 && args[0] == "--render-preview") { PreviewRenderer.Render(args[1]); return 0; }
            if (args.Length == 2 && args[0] == "--check-feed") {
                var entries = Core.ParseThemes(Core.ReadXml(args[1]), true);
                Console.WriteLine("Feed themes: " + entries.Count); return 0;
            }
            if (args.Length == 2 && args[0] == "--verify-packages") {
                var themes = Core.ReadThemes(Path.GetFullPath(args[1]));
                foreach (var theme in themes) Core.ValidatePack(Path.GetFullPath(args[1]), theme);
                Console.WriteLine("Verified {0} offline themes / {1} cursor roles", themes.Count, themes.Count * Core.Roles.Length); return 0;
            }
            if (Environment.OSVersion.Platform != PlatformID.Win32NT) { Console.Error.WriteLine("Windows 10/11 x64 required."); return 1; }
            if (args.Length == 1 && args[0] == "--prepare-uninstall") { Core.Restore(true); Cloud.SetAutoStart(false); return 0; }
            bool tray = args.Length == 1 && args[0] == "--tray";
            if (args.Length > 0 && !tray) return 2;
            bool created;
            using (var mutex = new Mutex(true, @"Local\FreeCur.Manager", out created)) {
                if (!created) { MessageBox.Show("切换器已打开，请先切换到已有窗口。", "Free Cur"); return 0; }
                Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
                Application.Run(new LibraryForm(AppDomain.CurrentDomain.BaseDirectory, false, tray));
            }
            return 0;
        } catch (Exception error) {
            if (args.Length > 0) Console.Error.WriteLine(error.Message);
            else MessageBox.Show(error.Message, "Free Cur", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }
}
