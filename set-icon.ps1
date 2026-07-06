$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath("Desktop") + "\AI Morning Brief.lnk")
$Shortcut.TargetPath = "D:\开发\ai-morning-brief\run.bat"
$Shortcut.WorkingDirectory = "D:\开发\ai-morning-brief"
$Shortcut.IconLocation = "D:\开发\ai-morning-brief\晨报图标_v1太阳报纸.ico,0"
$Shortcut.Save()
Write-Host "Shortcut icon updated to 晨报图标_v1太阳报纸.ico" -ForegroundColor Green