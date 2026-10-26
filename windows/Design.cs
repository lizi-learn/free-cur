using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Windows.Forms;

[assembly: System.Runtime.Versioning.TargetFramework(".NETFramework,Version=v4.8")]

internal static class Look {
    internal static readonly Color Cream = Color.FromArgb(251,248,242), Paper = Color.White,
        Pink = Color.FromArgb(187,83,119), Blush = Color.FromArgb(250,233,240), Ink = Color.FromArgb(64,51,70),
        Muted = Color.FromArgb(137,122,137), Line = Color.FromArgb(232,221,228);
    private static readonly List<Stream> Images = new List<Stream>();
    internal static Font Font(float size, bool bold = false) {
        string family = Environment.GetEnvironmentVariable("FREECUR_RENDER") == "1" ? "Noto Sans CJK SC" : "Microsoft YaHei UI";
        return new Font(family, size, bold ? FontStyle.Bold : FontStyle.Regular, GraphicsUnit.Point);
    }
    internal static Image Diana() {
        var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream("FreeCur.Diana");
        if (stream == null) return null; Images.Add(stream); return Image.FromStream(stream);
    }
    internal static Label Text(string text, float size, Color color, bool bold = false) {
        return new Label { Text = text, AutoSize = false, Font = Font(size,bold), ForeColor = color,
            BackColor = Color.Transparent, UseCompatibleTextRendering = false };
    }
    internal static GraphicsPath Round(Rectangle rectangle, int radius) {
        int diameter = Math.Max(2,radius * 2); var path = new GraphicsPath();
        path.AddArc(rectangle.X,rectangle.Y,diameter,diameter,180,90);
        path.AddArc(rectangle.Right-diameter,rectangle.Y,diameter,diameter,270,90);
        path.AddArc(rectangle.Right-diameter,rectangle.Bottom-diameter,diameter,diameter,0,90);
        path.AddArc(rectangle.X,rectangle.Bottom-diameter,diameter,diameter,90,90); path.CloseFigure(); return path;
    }
    internal static Panel Sidebar(string eyebrow, string heading, string subtitle) {
        var panel = new Panel { Dock = DockStyle.Fill, BackColor = Blush };
        var brand = Text("↖  freecur",25,Ink,true); brand.SetBounds(24,30,200,48);
        var tag = Text(eyebrow,8,Pink,true); tag.SetBounds(28,99,195,24);
        var title = Text(heading,22,Ink,true); title.SetBounds(24,137,200,100);
        var image = new PixelPicture { Image = Diana(), SizeMode = PictureBoxSizeMode.Zoom, BackColor = Blush };
        image.SetBounds(22,245,185,185);
        var note = Text(subtitle,10,Muted); note.SetBounds(26,445,180,82);
        panel.Controls.AddRange(new Control[]{brand,tag,title,image,note}); return panel;
    }
    internal static void Render(Control value,string file) {
        using(var bitmap=new Bitmap(value.Width,value.Height)) {
            value.DrawToBitmap(bitmap,new Rectangle(Point.Empty,value.Size));
            using(var graphics=Graphics.FromImage(bitmap))PaintChildren(value,graphics,Point.Empty);
            bitmap.Save(file);
        }
    }
    private static void PaintChildren(Control parent,Graphics graphics,Point offset) {
        var saved=graphics.Save();graphics.SetClip(new Rectangle(offset,parent.ClientSize),CombineMode.Intersect);
        foreach(Control child in parent.Controls.Cast<Control>().Reverse()) {
            if(!child.Visible||child.Width<1||child.Height<1)continue;
            var point=new Point(offset.X+child.Left,offset.Y+child.Top);
            using(var bitmap=new Bitmap(child.Width,child.Height)) { child.DrawToBitmap(bitmap,new Rectangle(Point.Empty,child.Size));graphics.DrawImageUnscaled(bitmap,point); }
            PaintChildren(child,graphics,point);
        }
        graphics.Restore(saved);
    }
}

internal sealed class SoftButton : Button {
    internal bool Accent = false;
    private bool hover;
    internal SoftButton() { SetStyle(ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.AllPaintingInWmPaint,true);
        FlatStyle=FlatStyle.Flat; FlatAppearance.BorderSize=0; Font=Look.Font(10,true); Cursor=Cursors.Hand; Size=new Size(145,42); }
    protected override void OnMouseEnter(EventArgs e) { hover=true; Invalidate(); base.OnMouseEnter(e); }
    protected override void OnMouseLeave(EventArgs e) { hover=false; Invalidate(); base.OnMouseLeave(e); }
    protected override void OnPaint(PaintEventArgs e) {
        e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        var rectangle=new Rectangle(0,0,Math.Max(2,Width-1),Math.Max(2,Height-1));
        using(var path=Look.Round(rectangle,10))
        using(var brush=new SolidBrush(!Enabled?Look.Line:Accent?(hover?Color.FromArgb(165,67,103):Look.Pink):hover?Look.Blush:Look.Paper))
        using(var pen=new Pen(Accent?Look.Pink:Look.Line)) { e.Graphics.FillPath(brush,path); e.Graphics.DrawPath(pen,path); }
        TextRenderer.DrawText(e.Graphics,Text,Font,rectangle,!Enabled?Look.Muted:Accent?Color.White:Look.Ink,
            TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.EndEllipsis);
        if(Focused) ControlPaint.DrawFocusRectangle(e.Graphics,new Rectangle(6,6,Width-13,Height-13));
    }
}

internal sealed class CardPanel : Panel {
    internal Color Fill = Look.Paper;
    internal CardPanel() { DoubleBuffered=true; BackColor=Look.Cream; }
    protected override void OnPaint(PaintEventArgs e) { e.Graphics.SmoothingMode=SmoothingMode.AntiAlias;
        using(var path=Look.Round(new Rectangle(0,0,Width-1,Height-1),13))
        using(var brush=new SolidBrush(Fill)) using(var pen=new Pen(Look.Line)) { e.Graphics.FillPath(brush,path); e.Graphics.DrawPath(pen,path); }
        base.OnPaint(e);
    }
}

internal sealed class PixelPicture : PictureBox {
    protected override void OnPaint(PaintEventArgs pe) {
        pe.Graphics.InterpolationMode=InterpolationMode.NearestNeighbor;
        pe.Graphics.PixelOffsetMode=PixelOffsetMode.Half; base.OnPaint(pe);
    }
}

internal sealed class CursorPicture : PictureBox {
    internal int PreviewPixels=112;
    protected override void OnPaint(PaintEventArgs e) {
        e.Graphics.Clear(BackColor);if(Image==null)return;
        int size=Math.Max(1,Math.Min(PreviewPixels,Math.Min(ClientSize.Width,ClientSize.Height)-2));
        var target=new Rectangle((ClientSize.Width-size)/2,(ClientSize.Height-size)/2,size,size);
        e.Graphics.InterpolationMode=InterpolationMode.NearestNeighbor;e.Graphics.PixelOffsetMode=PixelOffsetMode.Half;
        e.Graphics.DrawImage(Image,target,0,0,Image.Width,Image.Height,GraphicsUnit.Pixel);
    }
}
