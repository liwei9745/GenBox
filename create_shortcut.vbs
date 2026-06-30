' Create desktop shortcut for Image Gen Studio
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
desktop = WshShell.SpecialFolders("Desktop")
shortcutPath = desktop & "\ImageGenStudio.lnk"

Set shortcut = WshShell.CreateShortcut(shortcutPath)
shortcut.TargetPath = fso.BuildPath(scriptDir, "launch_silent.vbs")
shortcut.WorkingDirectory = scriptDir
shortcut.Description = "Image Gen Studio"
shortcut.WindowStyle = 7
shortcut.Save

MsgBox "桌面快捷方式已创建！", vbInformation, "Image Gen Studio"
