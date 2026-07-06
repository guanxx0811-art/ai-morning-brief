Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

Dim desktop, shortcutPath
desktop = WshShell.SpecialFolders("Desktop")
shortcutPath = desktop & "\AI Morning Brief.lnk"

If fso.FileExists(shortcutPath) Then
    fso.DeleteFile shortcutPath
End If

Set shortcut = WshShell.CreateShortcut(shortcutPath)
shortcut.TargetPath = "D:\开发\ai-morning-brief\run.bat"
shortcut.WorkingDirectory = "D:\开发\ai-morning-brief"
shortcut.IconLocation = "D:\开发\ai-morning-brief\晨报图标_v1太阳报纸.ico"
shortcut.Save

WScript.Echo "Shortcut created successfully"