# start-project.ps1
Write-Host "Starting Manager Service..."
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd manager_service; .\venv\Scripts\Activate.ps1; python manager_service.py'

Write-Host "Starting Requirements Service..."
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd requirements_service; .\venv\Scripts\Activate.ps1; python requirements_manager.py'

Write-Host "Starting Transcription Service..."
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd transcription_service; .\venv\Scripts\Activate.ps1; python transcribe_service.py'

Write-Host "Starting Frontend..."
Start-Process powershell -ArgumentList '-NoExit', '-Command', 'cd timeless_ui; npm run dev'
