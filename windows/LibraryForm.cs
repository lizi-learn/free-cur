using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;

internal sealed class LibraryForm : Form {
    private readonly string root;
    private readonly bool preview;
    private List<Theme> themes;
    private readonly FlowLayoutPanel grid=new FlowLayoutPanel();
    private readonly Label status=Look.Text("读取本地目录…",9,Look.Muted);
    private readonly Label note=Look.Text("选择一只小角色，陪你工作。",10,Look.Muted);
    private readonly Label displayInfo=Look.Text("正在识别屏幕…",9,Look.Muted);
    private readonly TextBox search=new TextBox();
    private readonly ComboBox group=new ComboBox();
    private readonly ComboBox cursorSize=new ComboBox();
    private readonly CheckBox hdrCompatibility=new CheckBox();
    private readonly ComboBox hdrStrength=new ComboBox();
    private readonly Timer timer=new Timer();
    private readonly NotifyIcon tray=new NotifyIcon();
    private bool syncing,busy,myOnly;
    private bool profilePending;
    private ScreenProfile screenProfile;

    internal LibraryForm(string directory,bool renderPreview,bool startHidden) {
        root=directory; preview=renderPreview; themes=preview?Core.ReadThemes(root):Cloud.CachedOrBundled(root);
        screenProfile=preview?ScreenSizing.Preview():ScreenSizing.Read(IntPtr.Zero);
        Text="Free Cur · 角色光标库"; ClientSize=new Size(1120,780); MinimumSize=new Size(960,680);
        StartPosition=FormStartPosition.CenterScreen; AutoScaleDimensions=new SizeF(96,96);AutoScaleMode=AutoScaleMode.Dpi; Font=Look.Font(10); BackColor=Look.Cream;
        string icon=Path.Combine(root,"free-cur.ico"); if(File.Exists(icon)) Icon=new Icon(icon);
        var layout=new TableLayoutPanel { Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,Margin=Padding.Empty };
        layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,230)); layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
        var sidebar=Look.Sidebar("A LITTLE JOY, EVERY DAY","让喜欢，\n陪在指尖。","主题目录静默同步\n已有光标可离线使用\n不采集鼠标或屏幕数据");
        var discover=new SoftButton { Text="发现主题",Accent=true }; discover.SetBounds(24,565,180,42);
        var mine=new SoftButton { Text="我的主题" }; mine.SetBounds(24,615,180,42);
        sidebar.Resize+=delegate { discover.Top=sidebar.Height-120;mine.Top=sidebar.Height-70; };
        discover.Click+=delegate { myOnly=false; discover.Accent=true; mine.Accent=false; discover.Invalidate();mine.Invalidate();RenderCards(); };
        mine.Click+=delegate { myOnly=true; discover.Accent=false; mine.Accent=true; discover.Invalidate();mine.Invalidate();RenderCards(); };
        sidebar.Controls.Add(discover); sidebar.Controls.Add(mine);
        var content=new TableLayoutPanel { Dock=DockStyle.Fill,Padding=new Padding(28,25,25,18),ColumnCount=1,RowCount=7 };
        content.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
        content.RowStyles.Add(new RowStyle(SizeType.Absolute,82)); content.RowStyles.Add(new RowStyle(SizeType.Absolute,55));
        content.RowStyles.Add(new RowStyle(SizeType.Absolute,32));content.RowStyles.Add(new RowStyle(SizeType.Absolute,45));content.RowStyles.Add(new RowStyle(SizeType.Percent,100)); content.RowStyles.Add(new RowStyle(SizeType.Absolute,58)); content.RowStyles.Add(new RowStyle(SizeType.Absolute,51));
        var header=new Panel { Dock=DockStyle.Fill };
        var title=Look.Text("今天，让谁陪你？",24,Look.Ink,true);title.SetBounds(0,0,420,45);
        status.SetBounds(2,51,520,24); header.Controls.Add(title);header.Controls.Add(status);
        var sync=new SoftButton { Text="同步目录",Size=new Size(110,38),Anchor=AnchorStyles.Right|AnchorStyles.Top };
        sync.Location=new Point(650,8);sync.Click+=async delegate { await SyncCatalogue(); };header.Controls.Add(sync);
        header.Resize+=delegate { sync.Left=Math.Max(425,header.Width-sync.Width); };
        var toolbar=new TableLayoutPanel { Dock=DockStyle.Fill,ColumnCount=3,RowCount=1 };
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,130));toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,225));
        var searchBox=new CardPanel { Dock=DockStyle.Fill,Padding=new Padding(13,10,13,7),Margin=new Padding(0,0,12,12) };
        search.BorderStyle=BorderStyle.None;search.BackColor=Look.Paper;search.ForeColor=Look.Ink;search.Dock=DockStyle.Fill;search.AccessibleName="搜索角色或系列";searchBox.Controls.Add(search);
        var hint=Look.Text("搜索角色 / 系列",10,Look.Muted);hint.Dock=DockStyle.Fill;hint.BackColor=Look.Paper;searchBox.Controls.Add(hint);hint.BringToFront();
        hint.Click+=delegate { hint.Visible=false;search.Focus(); };search.Enter+=delegate { hint.Visible=false; };
        search.Leave+=delegate { hint.Visible=search.Text.Length==0; };
        group.Dock=DockStyle.Top; group.DropDownStyle=ComboBoxStyle.DropDownList; group.FlatStyle=FlatStyle.Flat;group.BackColor=Look.Paper;group.AccessibleName="系列分类";
        toolbar.Controls.Add(searchBox,0,0);toolbar.Controls.Add(group,1,0);
        cursorSize.Dock=DockStyle.Top;cursorSize.DropDownStyle=ComboBoxStyle.DropDownList;cursorSize.FlatStyle=FlatStyle.Flat;
        cursorSize.BackColor=Look.Paper;cursorSize.AccessibleName="光标大小，选好后点击应用主题";
        cursorSize.Items.Add("自动 · "+screenProfile.Recommended+"px 推荐");
        cursorSize.Items.AddRange(new object[]{"小 · 32px","适中 · 48px","大 · 64px","更大 · 96px","特大 · 128px"});
        cursorSize.SelectedIndex=preview||Core.PreferredAutomaticSize()?0:Array.IndexOf(Core.CursorSizes,Core.PreferredSize())+1;
        toolbar.Controls.Add(cursorSize,2,0);
        cursorSize.SelectedIndexChanged+=delegate { RenderCards();note.Text="预览大小已改变；点击主题的应用按钮，才会修改系统光标。"; };
        displayInfo.Dock=DockStyle.Fill;displayInfo.Text=ScreenDescription();
        var colorRow=new FlowLayoutPanel { Dock=DockStyle.Fill,WrapContents=false,Padding=new Padding(0,3,0,0) };
        int preferred=preview?0:Core.PreferredHdrStrength();
        hdrCompatibility.Text="HDR 指针偏白补偿（实验）";hdrCompatibility.AutoSize=true;hdrCompatibility.Font=Look.Font(9);hdrCompatibility.ForeColor=Look.Ink;
        hdrCompatibility.Margin=new Padding(0,7,12,0);hdrCompatibility.Checked=preferred>0;
        hdrCompatibility.AccessibleName="HDR 指针色彩兼容，不关闭 HDR";
        hdrStrength.DropDownStyle=ComboBoxStyle.DropDownList;hdrStrength.FlatStyle=FlatStyle.Flat;hdrStrength.BackColor=Look.Paper;
        hdrStrength.Width=125;hdrStrength.AccessibleName="HDR 补偿强度";
        hdrStrength.Items.AddRange(new object[]{"轻度 · 25%","中等 · 50%","较强 · 75%","标准 · 100%"});
        hdrStrength.SelectedIndex=preferred>0?Math.Max(0,Math.Min(3,(preferred+24)/25-1)):3;hdrStrength.Enabled=hdrCompatibility.Checked;
        var detection=new SoftButton { Text="检测显示",Size=new Size(96,31),Margin=new Padding(12,0,0,0) };
        detection.Click+=delegate { if(!preview)MessageBox.Show(this,HdrDisplay.Summary(),"HDR / ACM 显示检测（只读）",MessageBoxButtons.OK,MessageBoxIcon.Information); };
        hdrCompatibility.CheckedChanged+=delegate { hdrStrength.Enabled=hdrCompatibility.Checked;note.Text=hdrCompatibility.Checked?"保持 HDR 开启。仅点击应用后补偿实际指针；卡片保留原色参考。效果需本机核对。":"已选择原色；点击主题的应用按钮恢复原色，不改动 HDR。"; };
        hdrStrength.SelectedIndexChanged+=delegate { note.Text="补偿强度已选择；点击主题的应用按钮生效。不同驱动可能需要不同强度。"; };
        colorRow.Controls.Add(hdrCompatibility);colorRow.Controls.Add(hdrStrength);colorRow.Controls.Add(detection);
        grid.Dock=DockStyle.Fill;grid.AutoScroll=true;grid.WrapContents=true;grid.Margin=Padding.Empty;grid.Padding=new Padding(0,0,4,0);
        search.TextChanged+=delegate { RenderCards(); };group.SelectedIndexChanged+=delegate { RenderCards(); };
        note.Dock=DockStyle.Fill;note.Padding=new Padding(2,9,0,0);
        var footer=new FlowLayoutPanel { Dock=DockStyle.Fill,WrapContents=false,Padding=Padding.Empty };
        var restore=new SoftButton { Text="恢复原光标",Size=new Size(148,40) };
        restore.Click+=async delegate { await Operation(delegate { Core.Restore(false); },"已恢复第一次应用前的光标。无需重启电脑。"); };
        var autostart=new CheckBox { Text="登录时启动到托盘（可选）",AutoSize=true,Font=Look.Font(9),ForeColor=Look.Muted,Margin=new Padding(20,11,0,0) };
        autostart.Checked=!preview&&Cloud.AutoStartEnabled();autostart.Enabled=!preview;
        autostart.CheckedChanged+=delegate { try { Cloud.SetAutoStart(autostart.Checked); note.Text=autostart.Checked?"已启用可选自启动；启动到托盘，不弹出主窗口。":"已关闭自启动。应用好的光标仍然会保留。"; } catch(Exception error) { note.Text=error.Message; } };
        footer.Controls.Add(restore);footer.Controls.Add(autostart);
        content.Controls.Add(header,0,0);content.Controls.Add(toolbar,0,1);content.Controls.Add(displayInfo,0,2);content.Controls.Add(colorRow,0,3);content.Controls.Add(grid,0,4);content.Controls.Add(note,0,5);content.Controls.Add(footer,0,6);
        layout.Controls.Add(sidebar,0,0);layout.Controls.Add(content,1,0);Controls.Add(layout);
        FillGroups(); RenderCards(); status.Text=preview?themes.Count+" 套可选 · "+themes.Count(x=>x.Pixel)+" 套像素角色 · 目录已缓存":"正在使用缓存目录 · 联网后自动同步";
        timer.Interval=30*60*1000;timer.Tick+=async delegate { await SyncCatalogue(); };
        if(!preview) {
            Shown+=delegate { RefreshScreen(); };
            LocationChanged+=delegate { if(IsHandleCreated&&!busy&&Screen.FromHandle(Handle).DeviceName!=screenProfile.Device)ScheduleScreenRefresh(); };
            tray.Icon=Icon;tray.Text="Free Cur · 主题目录";
            var menu=new ContextMenuStrip();menu.Items.Add("打开主题库",null,delegate { ShowInTaskbar=true;Show();WindowState=FormWindowState.Normal;Activate(); });
            menu.Items.Add("恢复原光标",null,async delegate { await Operation(delegate { Core.Restore(false); },"已恢复原光标。"); });
            menu.Items.Add("退出",null,delegate { Close(); });tray.ContextMenuStrip=menu;
            tray.DoubleClick+=delegate { ShowInTaskbar=true;Show();WindowState=FormWindowState.Normal;Activate(); };
            Shown+=async delegate { if(startHidden) { tray.Visible=true;ShowInTaskbar=false;Hide(); } timer.Start();await SyncCatalogue(); };
        }
        FormClosed+=delegate { timer.Stop();timer.Dispose();tray.Visible=false;tray.Dispose(); };
    }

    private int ChosenSize() { return cursorSize.SelectedIndex<=0?screenProfile.Recommended:Core.CursorSizes[cursorSize.SelectedIndex-1]; }
    private string ScreenDescription() { return screenProfile.Description+" · 推荐 "+screenProfile.Recommended+"px · "+(preview?screenProfile.Source:"当前窗口所在屏幕；应用后生效"); }
    private void RefreshScreen() {
        if(preview||IsDisposed||!IsHandleCreated)return;
        try {
            screenProfile=ScreenSizing.Read(Handle);int selected=cursorSize.SelectedIndex;
            cursorSize.Items[0]="自动 · "+screenProfile.Recommended+"px 推荐";cursorSize.SelectedIndex=selected;
            displayInfo.Text=ScreenDescription();RenderCards();
            // Keep a scaled window inside the current work area, including 1080p/150%.
            Rectangle area=Screen.FromHandle(Handle).WorkingArea;
            if(Width>area.Width||Height>area.Height) {
                MinimumSize=new Size(Math.Min(MinimumSize.Width,area.Width),Math.Min(MinimumSize.Height,area.Height));
                Size=new Size(Math.Min(Width,area.Width),Math.Min(Height,area.Height));
            }
        } catch { displayInfo.Text="屏幕检测暂不可用；保留当前推荐，也可手动选择大小。"; }
    }
    private void ScheduleScreenRefresh() {
        if(preview||profilePending||IsDisposed||!IsHandleCreated)return;profilePending=true;
        BeginInvoke((Action)delegate { profilePending=false;if(!IsDisposed)RefreshScreen(); });
    }
    protected override void WndProc(ref Message message) {
        int kind=message.Msg;base.WndProc(ref message);
        if(kind==0x02e0||kind==0x007e)ScheduleScreenRefresh(); // WM_DPICHANGED / WM_DISPLAYCHANGE, not polling.
    }

    private void FillGroups() { string previous=Convert.ToString(group.SelectedItem);group.Items.Clear();group.Items.Add("全部系列");
        foreach(string name in themes.Select(x=>x.Group).Distinct())group.Items.Add(name);
        group.SelectedIndex=group.Items.Contains(previous)?group.Items.IndexOf(previous):0;
    }

    private bool Installed(Theme theme) {
        string folder=Path.Combine(Core.Store,"themes"),prefix=theme.Id+"-"+theme.Hash.Substring(0,16);
        return Directory.Exists(Path.Combine(folder,prefix))||(Directory.Exists(folder)&&
            (Directory.GetDirectories(folder,prefix+"-"+HdrColor.Revision+"-*").Length>0||Directory.GetDirectories(folder,prefix+"-"+CursorSizing.Revision+"-*").Length>0));
    }

    private void RenderCards() {
        if(group.SelectedIndex<0)return;
        grid.SuspendLayout();
        foreach(Control card in grid.Controls.Cast<Control>().ToArray()) { foreach(var picture in card.Controls.OfType<PictureBox>())if(picture.Image!=null)picture.Image.Dispose();grid.Controls.Remove(card);card.Dispose(); }
        var selected=themes.Where(x=>(group.SelectedIndex==0||x.Group==Convert.ToString(group.SelectedItem))
            &&(x.Name+" "+x.Group+" "+x.Id).IndexOf(search.Text,StringComparison.OrdinalIgnoreCase)>=0&&(!myOnly||Installed(x))).ToList();
        foreach(var theme in selected) {
            var card=new CardPanel { Size=new Size(233,285),Margin=new Padding(0,0,13,15) };
            var picture=new CursorPicture { PreviewPixels=ChosenSize()*7/4,BackColor=Look.Paper };picture.SetBounds(22,18,188,120);
            string path=Cloud.PreviewPath(root,theme);
            if(File.Exists(path)) { using(var image=Image.FromFile(path)) {
                picture.Image=new Bitmap(image); // Draw original pixels directly at the final DPI, never stretch an intermediate thumbnail.
            } }
            var name=Look.Text(theme.Name,16,Look.Ink,true);name.SetBounds(18,150,198,35);
            var caption=Look.Text(theme.Group+" · "+(theme.Pixel?"像素动态":"旧版头像"),9,Look.Muted);caption.SetBounds(19,186,198,23);
            var apply=new SoftButton { Text=Installed(theme)?"再次应用":"应用主题",Accent=true,Size=new Size(194,42),Location=new Point(18,226),Enabled=!busy };
            apply.Click+=async delegate { RefreshScreen();int size=ChosenSize(),hdr=hdrCompatibility.Checked?(hdrStrength.SelectedIndex+1)*25:0;bool automatic=cursorSize.SelectedIndex==0;
                await Operation(delegate { Core.Apply(root,theme,size,hdr,automatic); },"已应用「"+theme.Name+"」· "+(automatic?"自动 ":"")+size+"px 原生帧 · "+(hdr>0?"HDR 补偿 "+hdr+"%":"原色")+"。可关闭软件；未改动 HDR 开关。"); };
            card.Controls.AddRange(new Control[]{picture,name,caption,apply});
            float scale=preview?1:screenProfile.Dpi/96f;if(scale!=1)card.Scale(new SizeF(scale,scale));
            grid.Controls.Add(card);
        }
        if(selected.Count==0) { var empty=Look.Text(myOnly?"还没有安装的可选主题。去「发现主题」挑选吧。":"没有匹配的主题。",12,Look.Muted);empty.Size=new Size(600,100);grid.Controls.Add(empty); }
        grid.ResumeLayout();
    }

    private async Task SyncCatalogue() {
        if(preview||syncing)return;syncing=true;
        try { var updated=await Task.Run(()=>Cloud.Sync(root));if(IsDisposed)return;themes=updated;FillGroups();RenderCards();
            status.Text=themes.Count+" 套可选 · 目录更新于 "+DateTime.Now.ToString("HH:mm")+" · 下次静默检查约 30 分钟后";
        } catch { if(!IsDisposed)status.Text="暂时离线，继续使用已缓存的主题目录。"; }
        finally { syncing=false; }
    }

    private async Task Operation(Action action,string success) {
        if(preview||busy)return;busy=true;cursorSize.Enabled=false;hdrCompatibility.Enabled=false;hdrStrength.Enabled=false;RenderCards();note.Text="正在准备主题并校验文件，请稍候…";
        try { await Task.Run(action);if(!IsDisposed)note.Text=success; }
        catch(Exception error) { if(!IsDisposed)note.Text="操作未完成："+error.Message; }
        finally { busy=false;if(!IsDisposed){cursorSize.Enabled=true;hdrCompatibility.Enabled=true;hdrStrength.Enabled=hdrCompatibility.Checked;RenderCards();} }
    }
}

internal static class PreviewRenderer {
    internal static void Render(string destination) {
        Directory.CreateDirectory(destination);Application.EnableVisualStyles();
        using(var form=new LibraryForm(AppDomain.CurrentDomain.BaseDirectory,true,false)) {
            form.Show();form.PerformLayout();Application.DoEvents();form.Refresh();
            Look.Render(form,Path.Combine(destination,"manager.png"));
            form.Close();
        }
    }
}
