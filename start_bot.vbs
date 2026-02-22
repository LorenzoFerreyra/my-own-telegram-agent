Set WshShell = CreateObject("WScript.Shell")
sDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Start Ollama in background (no window), ignore if already running
WshShell.Run "ollama serve", 0, False
WScript.Sleep 3000

Do
    WshShell.Run "cmd /c cd /d """ & sDir & """ && .venv\Scripts\python.exe main.py >> bot_log.txt 2>&1", 0, True
    WScript.Sleep 5000
Loop
