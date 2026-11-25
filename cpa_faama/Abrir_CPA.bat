@echo off
chcp 65001 >nul
title Sistema CPA - não feche esta janela enquanto usar o sistema
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo  O sistema ainda não foi instalado. Rode primeiro o arquivo "Instalar_CPA.bat".
  pause
  exit /b 1
)
echo.
echo  Abrindo o Sistema CPA no navegador...
echo  Para fechar o sistema, feche esta janela.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless false --server.address 127.0.0.1
