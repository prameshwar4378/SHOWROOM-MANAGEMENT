@echo off
title Tractor Showroom - Local WhatsApp Bridge
echo ========================================================
echo   TRACTOR SHOWROOM MANAGEMENT ERP
echo   Starting Local WhatsApp Web Gateway Service...
echo ========================================================
echo.
cd /d "%~dp0whatsapp_bridge"
node server.js
pause
