@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ===================================================
echo             CodeContext Desktop Launcher
echo ===================================================

if not exist "venv\Scripts\python.exe" (
    echo [*] Создание виртуального окружения Python...
    py -3.11 -m venv venv 2>nul || py -3.12 -m venv venv 2>nul || python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

if not exist "backend\codecontext_core.pyd" (
    echo [!] Внимание: В папке backend\ отсутствует codecontext_core.pyd
    echo     Приложение запустится в режиме Python (без ускорения Rust ядра).
)

if not exist "dist_ui\index.html" (
    echo [*] Папка dist_ui не найдена. Если запущен локальный сервер Angular,
    echo     окно подключится к http://127.0.0.1:4200.
)

echo.
echo [*] Запуск приложения CodeContext Desktop...
python main.py

if errorlevel 1 (
    echo.
    echo [!] Ошибка запуска приложения.
    pause
)