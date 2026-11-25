@echo off
chcp 65001 >nul
title Sistema CPA na rede interna - não feche esta janela
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo  O sistema ainda não foi instalado. Rode primeiro o arquivo "Instalar_CPA.bat".
  pause
  exit /b 1
)
echo.
echo  O sistema vai ficar disponível para outros computadores DA REDE INTERNA enquanto esta janela estiver aberta.
echo  Endereços deste computador (use o IPv4 no lugar de SEU_IP):
ipconfig | findstr /i "IPv4"
echo.
echo  Os outros acessam pelo navegador: http://SEU_IP:8501
echo  Se o Windows perguntar sobre o firewall, permita apenas em "Redes privadas".
echo.
".venv\Scripts\python.exe" -m streamlit run app.py --server.headless true --server.address 0.0.0.0 --server.port 8501
