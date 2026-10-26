Unicode true
; Standard x86 bootstrap runs on x64 Windows; the installed application is native x64.
Target x86-unicode
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"
!include "x64.nsh"
Name "Free Cur 光标切换器"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\FreeCur"
RequestExecutionLevel user
SetCompressor /SOLID lzma
CRCCheck on
ManifestDPIAware true
VIProductVersion "2.5.0.0"
VIAddVersionKey /LANG=2052 "ProductName" "Free Cur 光标切换器"
VIAddVersionKey /LANG=2052 "FileDescription" "Free Cur 离线安装包（仅当前用户）"
VIAddVersionKey /LANG=2052 "FileVersion" "2.5.0"
VIAddVersionKey /LANG=2052 "LegalCopyright" "Free Cur contributors / artwork credited separately"
!define MUI_ICON "${PAYLOAD}/free-cur.ico"
!define MUI_UNICON "${PAYLOAD}/free-cur.ico"
!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "安装 Free Cur 光标切换器"
!define MUI_WELCOMEPAGE_TEXT "原生 Windows EXE，内含离线光标主题。$\r$\n$\r$\n仅安装到当前用户，不需要管理员权限，不修改安全策略、不安装服务、不自动启动。$\r$\n$\r$\n安装不会改变光标；完成后在切换器里选择主题并应用。$\r$\n$\r$\n免费、非商业、非官方二创。素材权利归原权利人。"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\FreeCur.exe"
!define MUI_FINISHPAGE_RUN_TEXT "打开 Free Cur 光标切换器"
!define MUI_FINISHPAGE_LINK "访问 Free Cur 网站"
!define MUI_FINISHPAGE_LINK_LOCATION "https://free-cur.bismih.cn/"
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "English"

!macro Fail Code Text
 CreateDirectory "$LOCALAPPDATA\FreeCur"
 FileOpen $8 "$LOCALAPPDATA\FreeCur\install-error.txt" w
 FileWriteUTF16LE $8 "${Text}"
 FileClose $8
 SetErrorLevel ${Code}
 Quit
!macroend

Function CheckNotRunning
 System::Call 'kernel32::OpenMutexW(i 0x100000, i 0, w "Local\FreeCur.Manager") p.r0'
 ${If} $0 != 0
  System::Call 'kernel32::CloseHandle(p r0)'
  !insertmacro Fail 10 "请先关闭 Free Cur 光标切换器，然后重试。"
 ${EndIf}
FunctionEnd

Function .onInit
 SetShellVarContext current
 SetRegView 64
 ${IfNot} ${RunningX64}
  !insertmacro Fail 51 "需要 64 位 Windows 10 / 11。"
 ${EndIf}
 ${IfNot} ${AtLeastWin10}
  !insertmacro Fail 51 "需要 Windows 10 / 11 x64。"
 ${EndIf}
 ReadRegDWORD $0 HKLM "SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full" "Release"
 ${If} $0 < 528040
  !insertmacro Fail 50 "请通过 Windows 更新安装 .NET Framework 4.8 后重试。"
 ${EndIf}
 IfFileExists "$INSTDIR\FreeCur.exe" 0 managed_ok
 IfFileExists "$INSTDIR\free-cur-managed.txt" managed_ok 0
 !insertmacro Fail 11 "安装目录中有其他程序，已保留。"
 managed_ok:
 Call CheckNotRunning
FunctionEnd

Section "Free Cur" SEC_MAIN
 SetShellVarContext current
 SetRegView 64
 SetOverwrite on
 SetOutPath "$INSTDIR"
 !include "${INSTALL_FILES}"
 nsExec::ExecToStack '"$INSTDIR\FreeCur.exe" --verify-packages "$INSTDIR"'
 Pop $0
 Pop $1
 ${If} $0 != 0
  !insertmacro Fail 20 "$1"
 ${EndIf}
 CreateDirectory "$SMPROGRAMS\Free Cur"
 CreateShortcut "$SMPROGRAMS\Free Cur\Free Cur.lnk" "$INSTDIR\FreeCur.exe"
 WriteUninstaller "$INSTDIR\Uninstall.exe"
 CreateShortcut "$SMPROGRAMS\Free Cur\卸载 Free Cur.lnk" "$INSTDIR\Uninstall.exe"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FreeCur" "DisplayName" "Free Cur 光标切换器"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FreeCur" "DisplayVersion" "2.5.0"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FreeCur" "Publisher" "Free Cur contributors"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FreeCur" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FreeCur" "InstallLocation" "$INSTDIR"
 WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FreeCur" "DisplayIcon" "$INSTDIR\FreeCur.exe"
 WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FreeCur" "NoModify" 1
 WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FreeCur" "NoRepair" 1
SectionEnd

Function un.onInit
 SetShellVarContext current
 SetRegView 64
 System::Call 'kernel32::OpenMutexW(i 0x100000, i 0, w "Local\FreeCur.Manager") p.r0'
 ${If} $0 != 0
  System::Call 'kernel32::CloseHandle(p r0)'
  MessageBox MB_OK|MB_ICONINFORMATION "请先关闭 Free Cur 光标切换器，再卸载。"
  Abort
 ${EndIf}
FunctionEnd

Section "Uninstall"
 nsExec::ExecToStack '"$INSTDIR\FreeCur.exe" --prepare-uninstall'
 Pop $0
 Pop $1
 ${If} $0 != 0
  MessageBox MB_OK|MB_ICONSTOP "未能恢复当前光标，暂停卸载以保留可用文件。请打开切换器恢复原主题后重试。$\r$\n$1"
  Abort
 ${EndIf}
 !include "${UNINSTALL_FILES}"
 Delete "$INSTDIR\Uninstall.exe"
 RMDir "$INSTDIR\packs"
 RMDir "$INSTDIR\source"
 RMDir "$INSTDIR"
 Delete "$SMPROGRAMS\Free Cur\Free Cur.lnk"
 Delete "$SMPROGRAMS\Free Cur\卸载 Free Cur.lnk"
 RMDir "$SMPROGRAMS\Free Cur"
 DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\FreeCur"
 ; Keep user theme backup/cache, and never recursively remove an unknown directory.
SectionEnd
