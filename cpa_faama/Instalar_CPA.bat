@echo off
chcp 65001 >nul
title Instalação do Sistema CPA
cd /d "%~dp0"
echo.
echo  Instalando o Sistema CPA (só é preciso fazer uma vez)...
echo.
py -3.12 --version >nul 2>&1
if errorlevel 1 (
  echo  [ERRO] Python 3.12 não encontrado.
  echo  Instale em https://www.python.org/downloads/ (versão 3.12, Windows 64-bit) e rode este arquivo de novo.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo  [ERRO] Falha ao instalar as bibliotecas. Envie esta tela para o suporte.
  pause
  exit /b 1
)
if not exist ".env" (
  echo.
  echo  [ATENÇÃO] Falta o arquivo .env com o acesso à API do TOTVS. Peça ao responsável pelo sistema.
)
echo.
echo  Instalação concluída. Para abrir o sistema, use o arquivo "Abrir_CPA.bat".
pause
