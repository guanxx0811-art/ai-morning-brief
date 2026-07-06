# Delete existing shortcut first
$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = $desktop + "\AI Morning Brief.lnk"
if (Test-Path $lnkPath) { Remove-Item $lnkPath }

# Create new shortcut with icon
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($lnkPath)
$Shortcut.TargetPath = "D:\开发\ai-morning-brief\run.bat"
$Shortcut.WorkingDirectory = "D:\开发\ai-morning-brief"
$Shortcut.IconLocation = "D:\开发\ai-morning-brief\晨报图标_v1太阳报纸.ico"
$Shortcut.Save()
Write-Host "Shortcut recreated with icon" -ForegroundColor Green