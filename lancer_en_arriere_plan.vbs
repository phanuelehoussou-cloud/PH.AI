Set WshShell = CreateObject("WScript.Shell")
strDir = WshShell.CurrentDirectory

pythonExe = strDir & "\venv\Scripts\python.exe"
If Not CreateObject("Scripting.FileSystemObject").FileExists(pythonExe) Then
    pythonExe = "python"
End If

scriptPath = strDir & "\wake_word_listener.py"

' Lancer en arrière-plan sans AUCUNE fenêtre visible (paramètre 0)
WshShell.Run """" & pythonExe & """ """ & scriptPath & """", 0, False

MsgBox " L'écoute vocale de PH.AI est activée en arrière-plan !" & vbCrLf & vbCrLf & "Vous pouvez fermer toutes vos fenêtres." & vbCrLf & "Dites simplement 'LET'S GO' ou 'ARISE' à tout moment pour démarrer PH.AI !", vbInformation, "PH.AI — Écoute Vocale Activée"
