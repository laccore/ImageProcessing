
# LacCore/CSDCO
# qtmain_geotek.py
# PyQt GUI wrapper of Geotek processing logic

import logging
import os
import sys
import time
import traceback

from PyQt5 import QtWidgets, QtCore, Qt

import geotek
from gui import FileListPanel, errbox, infobox, ProgressPanel, TwoButtonPanel
from prefs import Preferences


class MainWindow(QtWidgets.QDialog):
    def __init__(self, app):
        QtWidgets.QDialog.__init__(self)
        self.app = app

        self.initGUI()
        self.initPrefs()
        self.installRulers()

    def initGUI(self):
        self.setWindowTitle("LacCore/CSDCO Geotek Image Converter v2.0")
        
        vlayout = QtWidgets.QVBoxLayout(self)

        listLabel = "Images to be converted: click Add, or drag and drop files in the list below to add images."
        self.imageList = FileListPanel(listLabel)
        self.imageList.addButton.setAutoDefault(False)
        self.imageList.rmButton.setAutoDefault(False)
        vlayout.addWidget(self.imageList, 1)

        self.dpi = QtWidgets.QLineEdit()
        self.trim = QtWidgets.QLineEdit()
        self.icdScaling = QtWidgets.QLineEdit()
        dpiLayout = QtWidgets.QHBoxLayout()
        dpiLayout.addWidget(QtWidgets.QLabel("Image and Ruler DPI:"))
        dpiLayout.addWidget(self.dpi)
        dpiLayout.addSpacing(20)
        dpiLayout.addWidget(QtWidgets.QLabel("Trim"))
        dpiLayout.addWidget(self.trim)
        dpiLayout.addWidget(QtWidgets.QLabel("inches from top of core image"))
        dpiLayout.addSpacing(20)
        dpiLayout.addWidget(QtWidgets.QLabel("Scale ICD-ready image by:"))
        dpiLayout.addWidget(self.icdScaling)
        dpiLayout.addWidget(QtWidgets.QLabel("%"))

        vlayout.addSpacing(10)
        vlayout.addLayout(dpiLayout, 0)

        rulerLayout = QtWidgets.QHBoxLayout()
        self.rulerCombo = QtWidgets.QComboBox()
        self.rulerCombo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, self.rulerCombo.sizePolicy().verticalPolicy())
        rulerLayout.addWidget(QtWidgets.QLabel("Ruler:"))
        rulerLayout.addWidget(self.rulerCombo)
        vlayout.addLayout(rulerLayout, 0)

        self.saveDefaultsButton = QtWidgets.QPushButton("Save Settings as Default")
        self.saveDefaultsButton.clicked.connect(self.saveDefaultSettings)
        self.saveDefaultsButton.setAutoDefault(False)
        self.convertButton = QtWidgets.QPushButton("Convert Images")
        self.convertButton.clicked.connect(self.processImageFiles)
        self.convertButton.setAutoDefault(False)
        self.buttonPanel = TwoButtonPanel(self.saveDefaultsButton, self.convertButton)

        self.progressPanel = ProgressPanel(self)

        self.stackedLayout = QtWidgets.QStackedLayout()        
        self.stackedLayout.addWidget(self.buttonPanel)
        self.stackedLayout.addWidget(self.progressPanel)
        self.stackedLayout.setCurrentIndex(0)
        vlayout.addLayout(self.stackedLayout, stretch=0)

    def showProgressLayout(self, show):
        self.stackedLayout.setCurrentIndex(1 if show else 0)

    def initPrefs(self):
        prefPath = os.path.join(os.getcwd(), "prefs.pk")
        self.prefs = Preferences(prefPath)
        self.installPrefs()

    def installRulers(self):
        rulersPath = os.path.join(os.getcwd(), "rulers")
        if not os.path.exists(rulersPath):
            os.mkdir(rulersPath)
        rulerFiles = [f for f in os.listdir(rulersPath) if os.path.isfile(os.path.join(rulersPath, f))
            and os.path.basename(f)[0] != '.'] # no hidden files
        if len(rulerFiles) == 0:
            errbox(self, message="No ruler files were found. Add one or more ruler files to the rulers folder and restart.")
        else:
            self.rulerCombo.addItems(rulerFiles)
        
    def installPrefs(self):
        geom = self.prefs.get("windowGeometry", None)
        if geom is not None:
            self.setGeometry(geom)
        self.dpi.setText(self.prefs.get("dpi", "508"))
        self.trim.setText(self.prefs.get("trim", "0.25"))
        self.icdScaling.setText(self.prefs.get("icdScaling", "30"))

    def savePrefs(self):
        self.prefs.set("windowGeometry", self.geometry())
        self.prefs.write()

    def saveDefaultSettings(self):
        self.prefs.set("dpi", self.dpi.text())
        self.prefs.set("trim", self.trim.text())
        self.prefs.set("icdScaling", self.icdScaling.text())

    # override QWidget.closeEvent()
    def closeEvent(self, event):
        self.savePrefs()
        event.accept() # allow window to close - event.ignore() to veto close

    def getRulerPath(self):
        return os.path.join(os.getcwd(), "rulers", str(self.rulerCombo.currentText()))

    def processImageFiles(self):
        imgFiles = self.imageList.getFiles()
        if len(imgFiles) == 0:
            infobox(self, "No Images", "Add at least one image to be converted.")
            return

        success = False
        self.showProgressLayout(True)
        self.progressPanel.clear()
        geotek.setProgressListener(self.progressPanel)
        try:
            dpi = float(self.dpi.text())
            trim = float(self.trim.text())
            icdScaling = float(self.icdScaling.text())
            parentDirBasename = True
            for imgPath in imgFiles:
                if parentDirBasename:
                    outputBaseName = os.path.basename(os.path.dirname(os.path.normpath(imgPath)))
                else:
                    outputBaseName, _ = os.path.splitext(os.path.basename(imgPath))
                geotek.prepare_geotek(imgPath, self.getRulerPath(), dpi, trim, icdScaling, outputBaseName, os.getcwd())
            success = True
        except:
            err = sys.exc_info()
            errbox(self, "Process failed", "{}".format("Unhandled error {}: {}".format(err[0], err[1])))
            logging.error(traceback.format_exc())
        finally:
            self.showProgressLayout(False)
            self.progressPanel.clear()
            if success:
                infobox(self, "Yay!", "Successfully converted {} image files.".format(len(imgFiles)))
                self.imageList.clear()

# Tried a threaded approach to getting around spotty progress bar updates
# during processing before discovering that QDialog (vs QWidget) responds
# well to updates.
#
# class GeotekProcessThread(QtCore.QThread):
#     def __init__(self, imgPath, rulerPath, dpi, icdScaling, outputBaseName, destDir):
#         QtCore.QThread.__init__(self)
#         self.imgPath = imgPath
#         self.rulerPath = rulerPath
#         self.dpi = dpi
#         self.icdScaling = icdScaling
#         self.outputBaseName = outputBaseName
#         self.destDir = destDir
# 
#     def __del__(self):
#         self.wait()
# 
#     def run(self):
#         geotek.prepare_geotek(self.imgPath, self.rulerPath, self.dpi, self.icdScaling, self.outputBaseName, self.destDir)
# 
# in processImageFiles:
                # geotekThread = GeotekProcessThread(imgPath, self.getRulerPath(), dpi, icdScaling, outputBaseName, os.getcwd())
                # geotekThread.start()
                # while not geotekThread.isFinished():
                #     self.app.processEvents()
                #     time.sleep(0.1)
                    #print("Waiting...")


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(app)
    window.setModal(False)
    window.show()
    sys.exit(app.exec_())
    
    
