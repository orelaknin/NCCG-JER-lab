Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

appDir = fso.GetParentFolderName(WScript.ScriptFullName)
repoDir = fso.GetParentFolderName(appDir)
pythonExe = repoDir & "\.venv\Scripts\python.exe"

If Not fso.FileExists(pythonExe) Then
    MsgBox "Python environment not found:" & vbCrLf & pythonExe, vbCritical, "Datasheet Scanner"
    WScript.Quit 1
End If

stopCmd = "powershell -NoProfile -ExecutionPolicy Bypass -Command ""Get-CimInstance Win32_Process ^| Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -match 'Datasheets_scanner\\app.py|\\app.py' } ^| ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"""
shell.Run stopCmd, 0, True

cmd = "cmd /c cd /d """ & appDir & """ && start """" /min """ & pythonExe & """ ""app.py"""
shell.Run cmd, 0, False

WScript.Sleep 3000
shell.Run "http://127.0.0.1:5000", 1, False
