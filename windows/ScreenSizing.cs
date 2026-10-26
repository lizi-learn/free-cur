// Read-only physical resolution + effective DPI; never changes a display mode.
using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

internal sealed class ScreenProfile {
    internal int Width,Height,Dpi,Recommended;
    internal string Device,Source;
    internal string Description { get { return Width+" × "+Height+" · "+ScreenSizing.Tier(Width,Height)+" · 缩放 "+Math.Round(Dpi*100.0/96)+"%"; } }
}

internal static class ScreenSizing {
    [DllImport("user32.dll",CharSet=CharSet.Unicode,EntryPoint="EnumDisplaySettingsW")]
    private static extern bool EnumDisplaySettings(string device,uint mode,IntPtr data);
    [DllImport("user32.dll")] private static extern uint GetDpiForWindow(IntPtr window);
    internal static int Recommend(int width,int height,int dpi) {
        if(width<320||height<320||width>32768||height>32768||dpi<48||dpi>768)
            throw new ArgumentOutOfRangeException("display","显示分辨率或 DPI 不在有效范围内。");
        int shorter=Math.Min(width,height);
        // Fan-art pointers have a smaller visible character than their canvas.
        // Take max, not resolution * scaling: avoid double enlargement at 1440p/150%.
        int byResolution=shorter>=2160?128:shorter>=1440?96:shorter>=900?64:48;
        double desired=Math.Max(byResolution,48*dpi/96.0);
        foreach(int size in Core.CursorSizes)if(size>=desired)return size;
        return 128;
    }
    internal static string Tier(int width,int height) {
        int shorter=Math.Min(width,height);
        return shorter>=2160?"4K / UHD":shorter>=1440?"2K / QHD":shorter>=900?"1080p / FHD 档":"低分辨率档";
    }
    internal static ScreenProfile Preview() { return new ScreenProfile { Width=2560,Height=1440,Dpi=120,Recommended=96,Device="preview",Source="开发预览，非硬件检测" }; }
    internal static ScreenProfile Read(IntPtr window) {
        if(Environment.OSVersion.Platform!=PlatformID.Win32NT)
            return new ScreenProfile { Width=1920,Height=1080,Dpi=96,Recommended=64,Device="fallback",Source="未检测到 Windows；保守回退" };
        var screen=window==IntPtr.Zero?Screen.PrimaryScreen:Screen.FromHandle(window);
        int width=screen.Bounds.Width,height=screen.Bounds.Height,dpi=96;string source="屏幕边界回退";
        IntPtr mode=Marshal.AllocHGlobal(220);
        try {
            Marshal.Copy(new byte[220],0,mode,220);Marshal.WriteInt16(mode,68,220);
            // DEVMODEW: dmPelsWidth/Height at 172/176. This API is not DPI virtualized.
            if(EnumDisplaySettings(screen.DeviceName,0xffffffff,mode)) {
                int w=Marshal.ReadInt32(mode,172),h=Marshal.ReadInt32(mode,176);
                if(w>=320&&h>=320&&w<=32768&&h<=32768) { width=w;height=h;source="Windows 物理像素"; }
            }
        } catch(EntryPointNotFoundException) { } catch(DllNotFoundException) { }
        finally { Marshal.FreeHGlobal(mode); }
        try { uint value=GetDpiForWindow(window);if(value>=48&&value<=768)dpi=(int)value; }
        catch(EntryPointNotFoundException) { } catch(DllNotFoundException) { }
        if(dpi==96)using(var graphics=Graphics.FromHwnd(window)) {
            int value=(int)Math.Round(graphics.DpiX);if(value>=48&&value<=768)dpi=value;
        }
        return new ScreenProfile { Width=width,Height=height,Dpi=dpi,Recommended=Recommend(width,height,dpi),Device=screen.DeviceName,Source=source };
    }
}
