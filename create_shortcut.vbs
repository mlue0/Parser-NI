Set ws = CreateObject("WScript.Shell")
desk = ws.SpecialFolders("Desktop")
Set lnk = ws.CreateShortcut(desk & "\SimpleMeasure.lnk")
lnk.TargetPath = "C:\Programms\SimpleMeasure\dist\SimpleMeasure.exe"
lnk.WorkingDirectory = "C:\Programms\SimpleMeasure"
lnk.Description = "SimpleMeasure"
lnk.IconLocation = "C:\Programms\SimpleMeasure\dist\SimpleMeasure.exe,0"
lnk.Save
MsgBox "Shortcut created!", 64, "SimpleMeasure"
