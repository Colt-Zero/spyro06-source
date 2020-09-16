set /p key= < keys/build_key.txt

py -3.6-32 -m PyInstaller spyropatch.spec --key=%key%
py -3.6-32 build.py

py -3.6 -m PyInstaller spyropatch.spec --key=%key%
py -3.6 build.py

pause