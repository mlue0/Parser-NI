@echo off
cd /d "C:\Programms\SimpleMeasure"
del /f ".git\index.lock" 2>nul
git config user.email "shelamkovivan813@gmail.com"
git config user.name "mlue0"
git add -A
git commit -m "feat: update project"
git push origin main
pause
