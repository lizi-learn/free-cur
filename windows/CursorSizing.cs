// Pick an exact embedded bitmap for every ANI frame. No Windows bitmap stretching.
using System;
using System.IO;
using System.Text;

internal static class CursorSizing {
    internal const string Revision="native-size-v1";
    private static bool Tag(byte[] bytes,int offset,string tag) { return Encoding.ASCII.GetString(bytes,offset,4)==tag; }
    private static int Number(byte[] bytes,int offset) { return checked((int)BitConverter.ToUInt32(bytes,offset)); }
    private static byte[] Cursor(byte[] bytes,int start,int size) {
        int count=BitConverter.ToUInt16(bytes,start+4);
        for(int i=0;i<count;i++) {
            int at=start+6+16*i,w=bytes[at]==0?256:bytes[at],h=bytes[at+1]==0?256:bytes[at+1];
            if(w!=size||h!=size)continue;
            int length=Number(bytes,at+8),offset=Number(bytes,at+12);
            using(var memory=new MemoryStream())using(var writer=new BinaryWriter(memory)) {
                writer.Write((ushort)0);writer.Write((ushort)2);writer.Write((ushort)1);
                writer.Write(bytes,at,12);writer.Write(22);writer.Write(bytes,start+offset,length);return memory.ToArray();
            }
        }
        throw new InvalidDataException("主题缺少原生 "+size+"px；请同步新版主题后重试，不会模糊拉伸旧小图。");
    }
    private static void Chunk(BinaryWriter writer,byte[] tag,byte[] data) {
        writer.Write(tag);writer.Write(data.Length);writer.Write(data);if(data.Length%2!=0)writer.Write((byte)0);
    }
    internal static byte[] Exact(byte[] input,int size) {
        Core.ValidateSize(size);
        byte[] bytes=HdrColor.Transform(input,0); // Reuse strict bounds / DIB / animation validation.
        if(!Tag(bytes,0,"RIFF"))return Cursor(bytes,0,size);
        using(var content=new MemoryStream())using(var writer=new BinaryWriter(content)) {
            writer.Write(Encoding.ASCII.GetBytes("ACON"));
            for(int at=12;at<bytes.Length;) {
                int length=Number(bytes,at+4);var data=new byte[length];Buffer.BlockCopy(bytes,at+8,data,0,length);
                if(Tag(bytes,at,"LIST")&&Tag(bytes,at+8,"fram")) {
                    using(var frames=new MemoryStream())using(var frameWriter=new BinaryWriter(frames)) {
                        frameWriter.Write(Encoding.ASCII.GetBytes("fram"));
                        for(int p=at+12;p<at+8+length;) {
                            int n=Number(bytes,p+4);Chunk(frameWriter,Encoding.ASCII.GetBytes("icon"),Cursor(bytes,p+8,size));p+=8+n+n%2;
                        }
                        data=frames.ToArray();
                    }
                } else if(Tag(bytes,at,"anih")) {
                    Buffer.BlockCopy(BitConverter.GetBytes(size),0,data,12,4);Buffer.BlockCopy(BitConverter.GetBytes(size),0,data,16,4);
                }
                var tag=new byte[4];Buffer.BlockCopy(bytes,at,tag,0,4);Chunk(writer,tag,data);at+=8+length+length%2;
            }
            using(var result=new MemoryStream())using(var output=new BinaryWriter(result)) {
                output.Write(Encoding.ASCII.GetBytes("RIFF"));output.Write((int)content.Length);output.Write(content.ToArray());return result.ToArray();
            }
        }
    }
}
