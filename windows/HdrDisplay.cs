// Read-only CCD display status. Never calls a display/colour setting API.
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;

internal static class HdrDisplay {
    [DllImport("user32.dll")] private static extern int GetDisplayConfigBufferSizes(uint flags,out uint paths,out uint modes);
    [DllImport("user32.dll")] private static extern int QueryDisplayConfig(uint flags,ref uint paths,IntPtr pathArray,ref uint modes,IntPtr modeArray,IntPtr topology);
    [DllImport("user32.dll")] private static extern int DisplayConfigGetDeviceInfo(IntPtr packet);
    internal static string Interpret(uint flags,int? mode) {
        if(mode.HasValue) return mode==2?"HDR 已开启":mode==1?"广色域 / ACM 已开启":mode==0?"SDR":"未知色彩模式";
        return (flags&2)!=0?"高级颜色已开启（旧 API 无法区分 HDR / ACM）":"高级颜色未开启";
    }
    private static byte[] Info(uint kind,uint size,int low,int high,int id) {
        IntPtr memory=Marshal.AllocHGlobal((int)size);
        try {
            Marshal.Copy(new byte[size],0,memory,(int)size);
            Marshal.WriteInt32(memory,0,(int)kind);Marshal.WriteInt32(memory,4,(int)size);
            Marshal.WriteInt32(memory,8,low);Marshal.WriteInt32(memory,12,high);Marshal.WriteInt32(memory,16,id);
            if(DisplayConfigGetDeviceInfo(memory)!=0)return null;
            var bytes=new byte[size];Marshal.Copy(memory,bytes,0,(int)size);return bytes;
        } finally { Marshal.FreeHGlobal(memory); }
    }
    internal static string Summary() {
        if(Environment.OSVersion.Platform!=PlatformID.Win32NT)return "显示检测仅支持 Windows；未更改任何显示设置。";
        try {
            for(int attempt=0;attempt<3;attempt++) {
                uint paths,modes;if(GetDisplayConfigBufferSizes(2,out paths,out modes)!=0||paths<1||paths>128||modes>1024)break;
                IntPtr pathMemory=Marshal.AllocHGlobal(checked((int)paths*72)),modeMemory=Marshal.AllocHGlobal(checked((int)Math.Max(1,modes)*64));
                try {
                    int result=QueryDisplayConfig(2,ref paths,pathMemory,ref modes,modeMemory,IntPtr.Zero);
                    if(result==122)continue;if(result!=0)break;
                    var lines=new List<string>();var seen=new HashSet<string>();
                    for(int i=0;i<paths;i++) {
                        IntPtr target=IntPtr.Add(pathMemory,i*72+20);int low=Marshal.ReadInt32(target),high=Marshal.ReadInt32(target,4),id=Marshal.ReadInt32(target,8);
                        if(!seen.Add(low+":"+high+":"+id))continue;
                        var newer=Info(15,36,low,high,id);var older=newer==null?Info(9,32,low,high,id):null;
                        string status=newer!=null?Interpret(BitConverter.ToUInt32(newer,20),BitConverter.ToInt32(newer,32)):
                            older!=null?Interpret(BitConverter.ToUInt32(older,20),null):"无法读取色彩模式";
                        lines.Add("显示输出 "+(lines.Count+1)+"："+status);
                    }
                    return string.Join("\n",lines.ToArray())+"\n\n只读检测，不开关 HDR / ACM。\nHDR 兼容是可调的指针传递函数补偿，不等于 HDR 校准。\n混合 HDR / SDR 多屏共用系统指针，需逐屏核对；不宣称自动跨屏校准。";
                } finally { Marshal.FreeHGlobal(pathMemory);Marshal.FreeHGlobal(modeMemory); }
            }
        } catch { }
        return "未能读取显示模式。可手动选择 HDR 指针兼容；没有更改 HDR 或色彩设置。";
    }
}
