Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

Dim desktop, shortcutPath, iconPath
desktop = WshShell.SpecialFolders("Desktop")
shortcutPath = desktop & "\AI Morning Brief.lnk"
iconPath = fso.GetParentFolderName(WScript.ScriptFullName) & "\app.ico"

If fso.FileExists(shortcutPath) Then
    fso.DeleteFile shortcutPath
End If

Set shortcut = WshShell.CreateShortcut(shortcutPath)
shortcut.TargetPath = "D:\开发\ai-morning-brief\run.bat"
shortcut.WorkingDirectory = "D:\开发\ai-morning-brief"
shortcut.IconLocation = iconPath
shortcut.Save

WScript.Echo "Shortcut created with icon: " & iconPath