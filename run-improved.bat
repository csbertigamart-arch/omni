@echo off
echo Starting Improved Ecommerce Integration Platform...
echo.

echo Checking Python...
python --version
if errorlevel 1 (
    echo Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Checking Node.js...
node --version
if errorlevel 1 (
    echo Node.js is not installed or not in PATH
    pause
    exit /b 1
)

echo.
echo Starting Backend Server...
start "Backend Server" cmd /k "cd backend && python app.py"

echo Waiting for backend to start...
timeout /t 5 /nobreak

echo.
echo Starting Frontend Development Server...
start "Frontend Server" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo Deployment Successful!
echo ========================================
echo - Backend: http://localhost:5000
echo - Frontend: http://localhost:5173
echo.
echo Both servers are now running in separate windows.
echo This window will close in 3 seconds...

:: Countdown dengan dots
echo Closing.
timeout /t 1 /nobreak >nul
echo Closing..
timeout /t 1 /nobreak >nul
echo Closing...
timeout /t 1 /nobreak >nul

exit