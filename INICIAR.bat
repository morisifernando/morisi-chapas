@echo off
chcp 65001 >nul
title Chapas Perforadas Cordini
cd /d "%~dp0"

echo.
echo  ========================================
echo     Chapas Perforadas Cordini - Iniciando...
echo  ========================================
echo.

REM Buscar Python
where python >nul 2>&1
if %errorlevel%==0 (
    set PY=python
) else (
    where py >nul 2>&1
    if %errorlevel%==0 (
        set PY=py
    ) else (
        echo  [ERROR] No se encontro Python.
        echo  Instala Python desde https://www.python.org/downloads/
        echo  Marca la casilla "Add Python to PATH" al instalar.
        echo.
        pause
        exit /b 1
    )
)

echo  Verificando dependencias...
%PY% -m pip show streamlit >nul 2>&1
if %errorlevel% neq 0 (
    echo  Instalando librerias la primera vez...
    %PY% -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo  [ERROR] No se pudieron instalar las dependencias.
        pause
        exit /b 1
    )
)

echo.
echo  Abriendo la app en el navegador...
echo  (Para cerrar: cierra esta ventana o apreta Ctrl+C)
echo.

%PY% -m streamlit run app.py --server.headless true --browser.gatherUsageStats false

pause
