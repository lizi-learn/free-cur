// Opt-in workaround for an sRGB cursor treated as linear light by an HDR cursor plane.
// This is NOT an HDR display switch, ICC profile, or a universal driver repair.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

internal static class HdrColor {
    internal const string Revision = "hdr-srgb-v1";
    internal static void ValidateStrength(int strength) {
        if(strength<0||strength>100)throw new ArgumentOutOfRangeException("strength","HDR 补偿强度只允许 0–100%。");
    }
    internal static byte[] Lookup(int strength) {
        ValidateStrength(strength);var result=new byte[256];double blend=strength/100.0;
        for(int i=0;i<256;i++) {
            double encoded=i/255.0;
            double linear=encoded<=0.04045?encoded/12.92:Math.Pow((encoded+0.055)/1.055,2.4);
            result[i]=(byte)Math.Max(0,Math.Min(255,Math.Round(255*((1-blend)*encoded+blend*linear),MidpointRounding.AwayFromZero)));
        }
        return result;
    }
    internal static byte[] Transform(byte[] original,int strength) {
        ValidateStrength(strength);
        if(original==null||original.Length<12||original.Length>4*1024*1024)throw new InvalidDataException("指针文件大小异常。");
        var bytes=(byte[])original.Clone();var table=Lookup(strength);
        if(Tag(bytes,0,"RIFF")&&Tag(bytes,8,"ACON")) {
            if(Read32(bytes,4)!=bytes.Length-8)throw new InvalidDataException("ANI 长度不一致。");
            int frames=0,expected=-1,lists=0;
            for(int p=12;p<bytes.Length;) {
                Require(p,8,bytes.Length);int length=Read32(bytes,p+4);int content=p+8;
                Require(content,length,bytes.Length);
                if(Tag(bytes,p,"anih")) {
                    if(expected!=-1||length<36)throw new InvalidDataException("ANI 头异常。");
                    expected=Read32(bytes,content+4);
                }
                if(Tag(bytes,p,"LIST")&&length>=4&&Tag(bytes,content,"fram")) {
                    lists++;int end=content+length;
                    for(int at=content+4;at<end;) {
                        Require(at,8,end);int n=Read32(bytes,at+4);Require(at+8,n,end);
                        if(!Tag(bytes,at,"icon"))throw new InvalidDataException("未知 ANI 帧类型。");
                        Cursor(bytes,at+8,n,table);frames++;if(frames>256)throw new InvalidDataException("ANI 帧过多。");
                        at=checked(at+8+n+(n%2));if(at>end)throw new InvalidDataException("ANI 对齐异常。");
                    }
                }
                p=checked(content+length+(length%2));if(p>bytes.Length)throw new InvalidDataException("ANI 对齐异常。");
            }
            if(lists!=1||frames<1||frames!=expected)throw new InvalidDataException("ANI 帧数不一致。");
        } else Cursor(bytes,0,bytes.Length,table);
        return bytes;
    }
    private static void Cursor(byte[] bytes,int start,int length,byte[] table) {
        int end=checked(start+length);Require(start,6,end);
        if(Read16(bytes,start)!=0||Read16(bytes,start+2)!=2)throw new InvalidDataException("需要 CUR 图像帧。");
        int count=Read16(bytes,start+4);if(count<1||count>64)throw new InvalidDataException("CUR 尺寸数异常。");
        Require(start+6,checked(count*16),end);int lastEnd=start+6+count*16;
        for(int i=0;i<count;i++) {
            int entry=start+6+i*16,w=bytes[entry]==0?256:bytes[entry],h=bytes[entry+1]==0?256:bytes[entry+1];
            if(Read16(bytes,entry+4)>=w||Read16(bytes,entry+6)>=h)throw new InvalidDataException("CUR 热点越界。");
            int size=Read32(bytes,entry+8),offset=checked(start+Read32(bytes,entry+12));Require(offset,size,end);
            if(offset<lastEnd)throw new InvalidDataException("CUR 图像区重叠。");lastEnd=checked(offset+size);
            Require(offset,40,lastEnd);
            if(Read32(bytes,offset)!=40||Read32(bytes,offset+4)!=w||Read32(bytes,offset+8)!=h*2
                    ||Read16(bytes,offset+12)!=1||Read16(bytes,offset+14)!=32||Read32(bytes,offset+16)!=0)
                throw new InvalidDataException("HDR 兼容仅处理 32 位未压缩 DIB 指针。");
            int pixelStart=offset+40,pixelBytes=checked(w*h*4),maskBytes=checked(((w+31)/32)*4*h);
            if(size!=40+pixelBytes+maskBytes)throw new InvalidDataException("CUR 像素或掩码长度异常。");
            Require(pixelStart,pixelBytes+maskBytes,lastEnd);
            for(int p=pixelStart;p<pixelStart+pixelBytes;p+=4) {
                // Preserve all transparency, mask bytes and structural metadata exactly.
                if(bytes[p+3]==0)continue;
                if(bytes[p+3]!=255)throw new InvalidDataException("HDR 像素兼容暂不接受半透明指针。");
                bytes[p]=table[bytes[p]];bytes[p+1]=table[bytes[p+1]];bytes[p+2]=table[bytes[p+2]];
            }
        }
    }
    private static void Require(int offset,int length,int end) {
        if(offset<0||length<0||offset>end||length>end-offset)throw new InvalidDataException("指针文件边界异常。");
    }
    private static int Read16(byte[] bytes,int offset) { Require(offset,2,bytes.Length);return bytes[offset]|bytes[offset+1]<<8; }
    private static int Read32(byte[] bytes,int offset) { Require(offset,4,bytes.Length);uint value=BitConverter.ToUInt32(bytes,offset);if(value>int.MaxValue)throw new InvalidDataException("指针长度溢出。");return (int)value; }
    private static bool Tag(byte[] bytes,int offset,string value) {
        return offset>=0&&offset<=bytes.Length-4&&Encoding.ASCII.GetString(bytes,offset,4)==value;
    }
    internal static string CacheSuffix(int strength) { ValidateStrength(strength);return strength==0?"":"-"+Revision+"-"+strength; }
    internal static Dictionary<string,byte[]> Prepare(Dictionary<string,byte[]> files,int strength) {
        ValidateStrength(strength);return files.ToDictionary(x=>x.Key,x=>strength==0?(byte[])x.Value.Clone():Transform(x.Value,strength));
    }
}
