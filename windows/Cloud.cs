using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Xml;
using Microsoft.Win32;

internal static class Cloud {
    internal const string Origin = "https://free-cur.bismih.cn";
    internal const string Endpoint = "/api/windows/catalog.xml";
    internal static string Cache { get { return Path.Combine(Core.Store, "catalog-cache.xml"); } }
    internal static string Digest(byte[] bytes) { using (var hash = SHA256.Create()) return BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant(); }

    internal static byte[] Get(string path, int limit) {
        if (!path.StartsWith("/") || path.StartsWith("//") || path.Contains("?") || path.Contains("#") || path.Contains(".."))
            throw new InvalidDataException("云端资源路径不合法");
        var request = (HttpWebRequest)WebRequest.Create(Origin + path);
        request.AllowAutoRedirect = false; request.Timeout = 12000; request.ReadWriteTimeout = 15000;
        request.UserAgent = "FreeCur/2.5"; request.AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate;
        using (var response = (HttpWebResponse)request.GetResponse()) {
            if (response.StatusCode != HttpStatusCode.OK || response.ContentLength > limit) throw new InvalidDataException("云端响应异常");
            using (var source = response.GetResponseStream())
            using (var target = new MemoryStream()) {
                var buffer = new byte[16384]; int length;
                while ((length = source.Read(buffer, 0, buffer.Length)) > 0) {
                    if (target.Length + length > limit) throw new InvalidDataException("云端资源超过大小限制");
                    target.Write(buffer, 0, length);
                }
                return target.ToArray();
            }
        }
    }

    internal static void AtomicWrite(string path, byte[] data) {
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        string temporary = Path.Combine(Path.GetDirectoryName(path), ".free-cur-" + Guid.NewGuid().ToString("N") + ".tmp");
        try {
            File.WriteAllBytes(temporary, data);
            if (File.Exists(path)) File.Replace(temporary, path, null); else File.Move(temporary, path);
        } finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }

    internal static List<Theme> CachedOrBundled(string root) {
        try { if (File.Exists(Cache)) return OfflineThemes(root,Core.ReadXml(Cache)); } catch { }
        return Core.ReadThemes(root);
    }

    internal static List<Theme> OfflineThemes(string root,XmlDocument cached) {
        var entries=Core.ParseThemes(cached,true);var bundled=Core.ReadXml(Path.Combine(root,"themes.xml"));
        Version previous,current;
        if(Version.TryParse(cached.DocumentElement.GetAttribute("version"),out previous)&&
                Version.TryParse(bundled.DocumentElement.GetAttribute("version"),out current)&&previous<current) {
            var local=Core.ParseThemes(bundled,false).ToDictionary(x=>x.Id);
            // Upgrade listed themes from the new offline bundle. Do not add hidden IDs or revive an empty catalogue.
            return entries.Select(x=>local.ContainsKey(x.Id)?local[x.Id]:x).ToList();
        }
        return entries;
    }

    internal static List<Theme> Sync(string root) {
        byte[] bytes = Get(Endpoint, 2 * 1024 * 1024);
        string pending = Path.Combine(Core.Store, "feed-" + Guid.NewGuid().ToString("N") + ".tmp");
        Directory.CreateDirectory(Core.Store);
        List<Theme> themes;
        try { File.WriteAllBytes(pending, bytes); themes = Core.ParseThemes(Core.ReadXml(pending), true); }
        finally { if (File.Exists(pending)) File.Delete(pending); }
        AtomicWrite(Cache, bytes); // Only a fully parsed data-only feed replaces the cache.
        foreach (var theme in themes) {
            if (File.Exists(Path.Combine(root, "assets", theme.Id + ".png")) || theme.PreviewUrl == "") continue;
            string preview = PreviewPath(root, theme);
            if (File.Exists(preview)) continue;
            try {
                byte[] image = Get(theme.PreviewUrl, 2 * 1024 * 1024);
                if (image.LongLength != theme.PreviewBytes || Digest(image) != theme.PreviewHash || image.Length < 8
                        || image[0] != 137 || image[1] != 80 || image[2] != 78 || image[3] != 71) continue;
                AtomicWrite(preview, image);
            } catch { /* Missing artwork never blocks a valid catalogue. */ }
        }
        return themes;
    }

    internal static string PreviewPath(string root, Theme theme) {
        string bundled = Path.Combine(root, "assets", theme.Id + ".png");
        return File.Exists(bundled) ? bundled : Path.Combine(Core.Store, "previews", theme.Id + "-" + theme.Hash.Substring(0, 16) + ".png");
    }

    internal static string EnsurePack(string root, Theme theme) {
        string bundled = Path.Combine(root, "packs", theme.Id + "-windows.zip");
        if (File.Exists(bundled)) {
            try { Core.ValidatePackFile(bundled, theme); return bundled; } catch (InvalidDataException) { }
        }
        string target = Path.Combine(Core.Store, "downloads", theme.Hash + ".zip");
        if (File.Exists(target)) { Core.ValidatePackFile(target, theme); return target; }
        byte[] bytes = Get(theme.PackUrl, 40 * 1024 * 1024);
        if (bytes.LongLength != theme.Bytes || Digest(bytes) != theme.Hash) throw new InvalidDataException("下载包校验失败，未修改光标");
        AtomicWrite(target, bytes);
        Core.ValidatePackFile(target, theme);
        return target;
    }

    internal static bool AutoStartEnabled() {
        using (var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run"))
            return key != null && Convert.ToString(key.GetValue("FreeCur", "")).IndexOf("FreeCur.exe", StringComparison.OrdinalIgnoreCase) >= 0;
    }

    internal static void SetAutoStart(bool enabled) {
        using (var key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run")) {
            string expected = "\"" + Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "FreeCur.exe") + "\" --tray";
            if (enabled) key.SetValue("FreeCur", expected, RegistryValueKind.String);
            else if (Convert.ToString(key.GetValue("FreeCur", "")).IndexOf("FreeCur.exe", StringComparison.OrdinalIgnoreCase) >= 0)
                key.DeleteValue("FreeCur", false);
        }
    }
}
