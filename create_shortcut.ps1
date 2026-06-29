$exePath  = "C:\Programms\SimpleMeasure\dist\SimpleMeasure.exe"
$workDir  = "C:\Programms\SimpleMeasure"
$desk     = [Environment]::GetFolderPath("Desktop")
$lnkPath  = Join-Path $desk "SimpleMeasure.lnk"

$ws  = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath       = $exePath
$lnk.WorkingDirectory = $workDir
$lnk.Description      = "SimpleMeasure — загрузка данных разбраковки кристаллов"
$lnk.IconLocation     = "$exePath,0"
$lnk.Save()

Write-Host "Ярлык создан: $lnkPath"
