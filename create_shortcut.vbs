' Creates a desktop shortcut that opens the Downloads Organizer window.
' Double-click this file once. Then right-click the new shortcut -> Pin to taskbar.
Set sh = CreateObject("WScript.Shell")
folder = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
desktop = sh.SpecialFolders("Desktop")
Set lnk = sh.CreateShortcut(desktop & "\Downloads Organizer.lnk")
lnk.TargetPath = folder & "\.venv\Scripts\pythonw.exe"
lnk.Arguments = """" & folder & "\app.pyw"""
lnk.WorkingDirectory = folder
lnk.IconLocation = "%SystemRoot%\System32\shell32.dll,45"
lnk.Description = "Downloads Organizer - AI agent"
lnk.Save
MsgBox "Done! A shortcut 'Downloads Organizer' was added to your desktop." & vbCrLf & "Right-click it and choose 'Pin to taskbar'."
