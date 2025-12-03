@echo off
REM Quick Start Script for Herbarium Specimen Tools (Windows)
REM
REM This script automates the complete setup process:
REM - Installs uv if needed
REM - Creates virtual environment
REM - Installs dependencies
REM - Generates sample images
REM - Configures environment
REM - Provides next steps

echo.
echo 🚀 Herbarium Specimen Tools - Quick Start
echo ==========================================
echo.

REM Check for uv
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 📦 uv not found. Installing...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

    REM Verify installation
    where uv >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ uv installation failed
        echo    Please install manually: https://github.com/astral-sh/uv
        pause
        exit /b 1
    )

    echo    ✅ uv installed successfully
) else (
    echo ✅ uv is already installed
)

echo.

REM Create virtual environment
echo 📦 Creating virtual environment...
if exist .venv (
    echo    ⚠️  .venv already exists, skipping creation
) else (
    uv venv
    echo    ✅ Virtual environment created
)

echo.

REM Activate virtual environment
echo 📦 Activating virtual environment...
call .venv\Scripts\activate.bat
echo    ✅ Virtual environment activated

echo.

REM Install dependencies
echo 📦 Installing dependencies...
uv pip install -e ".[dev]"
echo    ✅ Dependencies installed

echo.

REM Generate sample images
echo 🖼️  Generating sample specimen images...
python scripts\generate_sample_images.py

echo.

REM Setup .env
echo ⚙️  Setting up environment configuration...
echo    (You can press Enter to accept defaults)
echo.
python scripts\setup_env.py

echo.
echo ============================================
echo ✅ Quick Start Complete!
echo ============================================
echo.
echo Your herbarium specimen tools are ready to use.
echo.
echo To start the server:
echo   python mobile\run_mobile_server.py --dev
echo.
echo Then open your browser to:
echo   http://localhost:8000
echo.
echo Development credentials:
echo   Username: testuser
echo   Password: testpass123
echo.

pause
