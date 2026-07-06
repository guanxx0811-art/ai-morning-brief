$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath("Desktop") + "\AI Morning Brief.lnk")
$Shortcut.TargetPath = "D:\开发\ai-morning-brief\启动晨报.bat"
$Shortcut.WorkingDirectory = "D:\开发\ai-morning-brief"
$Shortcut.IconLocation = "shell32.dll,41"
$Shortcut.Save()
Write-Host "Shortcut created: AI Morning Brief.lnk" -ForegroundColor Green