# build a Mac application bundle using pyinstaller
pyinstaller --debug all --clean --onefile --windowed --noconfirm --name "LacCore Geotek Converter" --icon assets/laccore.icns qtmain_geotek.py