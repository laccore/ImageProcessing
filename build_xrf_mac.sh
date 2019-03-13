# build a Mac application bundle using pyinstaller
pyinstaller --debug all --clean --onefile --windowed --noconfirm --name "LacCore XRF Converter" --icon assets/feldmanicon.icns qtmain_xrf.py