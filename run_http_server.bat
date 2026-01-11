@echo off
REM Launch SpireComm HTTP Server
cd /d "%~dp0"
python -m spirecomm.http_server %*
