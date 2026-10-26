using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Win32;

internal sealed class SetupForm : Form {
    private readonly Label step=Look.Text("准备把一点喜欢，带到你的桌面。",12,Look.Ink,true);
    private readonly Label detail=Look.Text("仅安装到当前用户，不需要管理员权限。",10,Look.Muted);
    private readonly SoftButton action=new SoftButton { Text="安装到我的电脑",Accent=true,Size=new Size(220,46) };
    private readonly ProgressBar progress=new ProgressBar();
    private bool working,complete;
    internal SetupForm(bool preview) {
        Text="Free Cur · 安装";ClientSize=new Size(890,610);MinimumSize=Size;MaximumSize=Size;
        StartPosition=FormStartPosition.CenterScreen;AutoScaleDimensions=new SizeF(96,96);AutoScaleMode=AutoScaleMode.Dpi;Font=Look.Font(10);BackColor=Look.Cream;
        var layout=new TableLayoutPanel { Dock=DockStyle.Fill,ColumnCount=2,RowCount=1,Margin=Padding.Empty };
        layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,230));layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
        layout.Controls.Add(Look.Sidebar("MAKE IT YOURS / 2.5","一小只，\n陪你每一天。","当前用户安装\n可恢复，不需要常驻\n无广告 / 无远控"),0,0);
        var body=new Panel { Dock=DockStyle.Fill,Padding=new Padding(30) };
        var eyebrow=Look.Text("A SOFT LITTLE UPGRADE",8,Look.Pink,true);eyebrow.SetBounds(34,30,530,24);
        var title=Look.Text("让桌面，多一点可爱。",25,Look.Ink,true);title.SetBounds(30,67,550,52);
        var intro=Look.Text("角色光标主题库  /  Windows x64",11,Look.Muted);intro.SetBounds(33,127,530,30);
        var options=new CardPanel { Size=new Size(550,176),Location=new Point(32,179) };
        string[] lines={"01   不动原光标       安装后由你选择应用","02   云端主题库       新上架 / 下架静默同步","03   轻量、可恢复     应用后可退出，自启动可选"};
        for(int i=0;i<3;i++) { var line=Look.Text(lines[i],11,Look.Ink,i==1);line.SetBounds(19,22+i*48,515,35);options.Controls.Add(line); }
        var location=Look.Text("安装位置  "+Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","FreeCur"),8,Look.Muted);
        location.SetBounds(34,371,548,45);
        step.SetBounds(34,431,550,27);detail.SetBounds(34,467,550,36);
        progress.SetBounds(34,508,550,7);progress.Visible=false;progress.Style=ProgressBarStyle.Marquee;
        action.Location=new Point(34,535);
        var privacy=Look.Text("自动检查主题目录；不上传账号、鼠标、屏幕或文档。",8,Look.Muted);privacy.SetBounds(270,538,318,42);
        action.Click+=async delegate { if(preview)return;if(complete) { Launch();return; }await Install(); };
        body.Controls.AddRange(new Control[]{eyebrow,title,intro,options,location,step,detail,progress,action,privacy});layout.Controls.Add(body,1,0);Controls.Add(layout);
        FormClosing+=delegate(object sender,FormClosingEventArgs e) { if(working)e.Cancel=true; };
    }
    private static string InstallPath { get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","FreeCur"); } }
    private void Launch() { Process.Start(new ProcessStartInfo(Path.Combine(InstallPath,"FreeCur.exe")) { UseShellExecute=true });Close(); }
    private async Task Install() {
        working=true;action.Enabled=false;progress.Visible=true;step.Text="正在安装并核对主题文件…";detail.Text="不会更改你当前使用的光标，请稍候。";
        try {
            int code=await Task.Run(()=>RunEngine());
            if(code!=0) {
                string message=code==10?"请先关闭已经打开的 Free Cur，再重试。":code==50?"请先通过 Windows 更新安装 .NET Framework 4.8。":
                    code==51?"需要 Windows 10 / 11 x64。":code==11?"安装目录存在其他文件，已保留，请先检查。":"安装未完成（错误码 "+code+"）。";
                string log=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"FreeCur","install-error.txt");
                if(code==20&&File.Exists(log))message+=" "+File.ReadAllText(log,System.Text.Encoding.Unicode);
                throw new InvalidOperationException(message);
            }
            complete=true;step.Text="安装好了。欢迎来到 Free Cur。";detail.Text="你的原光标还在。打开主题库，选一只喜欢的小角色。";action.Text="打开我的主题库";
        } catch(Exception error) { step.Text="这一步没有完成，当前光标未修改。";detail.Text=error.Message;action.Text="重新安装"; }
        finally { working=false;action.Enabled=true;progress.Visible=false; }
    }
    private static int RunEngine() {
        string folder=Path.Combine(Path.GetTempPath(),"FreeCur-setup-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(folder);
        string path=Path.Combine(folder,"engine.exe");
        try {
            using(var input=Assembly.GetExecutingAssembly().GetManifestResourceStream("FreeCur.Engine"))
            using(var output=new FileStream(path,FileMode.CreateNew,FileAccess.Write)) { if(input==null)throw new InvalidDataException("安装器资源缺失");input.CopyTo(output); }
            using(var process=Process.Start(new ProcessStartInfo(path,"/S") { UseShellExecute=false,CreateNoWindow=true })) { process.WaitForExit();return process.ExitCode; }
        } finally { try { if(File.Exists(path))File.Delete(path);Directory.Delete(folder); } catch(IOException) { } }
    }
}

internal static class SetupProgram {
    [STAThread] private static int Main(string[] args) {
        if(args.Length==2&&args[0]=="--extract-engine") {
            using(var source=Assembly.GetExecutingAssembly().GetManifestResourceStream("FreeCur.Engine"))
            using(var output=new FileStream(args[1],FileMode.CreateNew,FileAccess.Write))source.CopyTo(output);
            return 0;
        }
        Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
        if(args.Length==2&&args[0]=="--render-preview") {
            using(var form=new SetupForm(true)) { form.Show();form.PerformLayout();Application.DoEvents();form.Refresh();
                Look.Render(form,args[1]);form.Close(); }return 0;
        }
        if(Environment.OSVersion.Platform!=PlatformID.Win32NT)return 1;
        Application.Run(new SetupForm(false));return 0;
    }
}
