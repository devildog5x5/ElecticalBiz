# Creates a desktop shortcut with the PowerFlow warrior icon
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Icon = Join-Path $ProjectRoot "static\img\icon.ico"
$Python = (Get-Command python).Source
$Target = Join-Path $ProjectRoot "main.py"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "PowerFlow.lnk"

$Wsh = New-Object -ComObject WScript.Shell
$Shortcut = $Wsh.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $Python
$Shortcut.Arguments = "`"$Target`""
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.IconLocation = "$Icon,0"
$Shortcut.Description = "PowerFlow Electrical Business Manager"
$Shortcut.Save()

Write-Host "Shortcut created: $ShortcutPath"
