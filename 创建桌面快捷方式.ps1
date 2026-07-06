# 创建 AI 晨报桌面快捷方式

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath("Desktop") + "\AI 晨报.lnk")

# 快捷方式目标
$Shortcut.TargetPath = "D:\开发\ai-morning-brief\启动晨报.bat"
$Shortcut.WorkingDirectory = "D:\开发\ai-morning-brief"
$Shortcut.Description = "双击启动 AI 晨报网站"

# 设置图标（可选，使用系统默认图标）
# $Shortcut.IconLocation = "shell32.dll,13"

$Shortcut.Save()

Write-Host "Desktop shortcut created: AI 晨报.lnk" -ForegroundColor Green