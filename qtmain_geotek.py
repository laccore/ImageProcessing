# LacCore/CSDCO
# qtmain_geotek.py
# PyQt GUI wrapper of Geotek processing logic

import logging, os, re, sys, time, traceback

from PyQt5 import QtWidgets, QtCore

import common
import geotek_opencv as geotek
from gui import FileListPanel, errbox, infobox, ProgressPanel, TwoButtonPanel, ButtonPanel
from prefs import Preferences


class MainWindow(QtWidgets.QDialog):
    def __init__(self, app):
        QtWidgets.QDialog.__init__(self)
        self.VERSION = "2.4"
        self.app = app
        self.app_path = None # init'd in self.initAppPath()

        self.initAppPath()
        self.initGUI()
        self.installRulers()
        self.initPrefs()

    def initGUI(self):
        self.setWindowTitle("CSD Facility Geotek Image Converter v{}".format(self.VERSION))
        
        vlayout = QtWidgets.QVBoxLayout(self)
        vlayout.setContentsMargins(10,5,10,5)

        listLabel = "Images to be converted: click Add, or drag and drop files into the list below."
        self.imageList = FileListPanel(listLabel)
        self.imageList.addButton.setAutoDefault(False)
        self.imageList.rmButton.setAutoDefault(False)
        vlayout.addWidget(self.imageList, 1)

        settingsGroupBox = QtWidgets.QGroupBox("Converter Settings")
        settingsGroupLayout = QtWidgets.QVBoxLayout()

        self.dpi = QtWidgets.QLineEdit()
        self.trim = QtWidgets.QLineEdit()
        self.icdScaling = QtWidgets.QLineEdit()
        self.fooDefaultsButton = QtWidgets.QToolButton()
        self.fooDefaultsButton.setText("Save Current Settings as Default")
        self.fooDefaultsButton.clicked.connect(self.saveDefaultSettings)

        dpiLayout = QtWidgets.QHBoxLayout()
        dpiLayout.setSpacing(5)
        dpiLayout.addWidget(QtWidgets.QLabel("Image and Ruler resolution:"))
        dpiLayout.addWidget(self.dpi, QtCore.Qt.AlignLeft)
        self.dpi.setFixedWidth(50)
        dpiLayout.addWidget(QtWidgets.QLabel("DPI"))
        dpiLayout.addStretch(5)

        trimLayout = QtWidgets.QHBoxLayout()
        trimLayout.setSpacing(5)
        trimLayout.addWidget(QtWidgets.QLabel("Trim from top of core image:"))
        trimLayout.addWidget(self.trim)
        self.trim.setFixedWidth(50)
        trimLayout.addWidget(QtWidgets.QLabel("inches"))
        trimLayout.addStretch(3)

        icdScalingLayout = QtWidgets.QHBoxLayout()
        icdScalingLayout.setSpacing(5)
        icdScalingLayout.addWidget(QtWidgets.QLabel("Resize ICD-ready image to:"))
        icdScalingLayout.addWidget(self.icdScaling)
        self.icdScaling.setFixedWidth(50)
        icdScalingLayout.addWidget(QtWidgets.QLabel("% of original"))
        icdScalingLayout.addStretch(3)

        rulerLayout = QtWidgets.QHBoxLayout()
        self.rulerCombo = QtWidgets.QComboBox()
        self.rulerCombo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        rulerLayout.addWidget(QtWidgets.QLabel("Add Ruler:"))
        rulerLayout.addWidget(self.rulerCombo)

        outputNamingLayout = QtWidgets.QHBoxLayout()
        self.outputNamingCombo = QtWidgets.QComboBox()
        self.outputNamingCombo.addItems(["Use input file's name", "Use name of input file's parent directory"])
        self.outputNamingCombo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        outputNamingLayout.addWidget(QtWidgets.QLabel("Output Naming:"))
        outputNamingLayout.addWidget(self.outputNamingCombo)

        settingsGroupLayout.addLayout(dpiLayout)
        settingsGroupLayout.addLayout(trimLayout)
        settingsGroupLayout.addLayout(icdScalingLayout)
        settingsGroupLayout.addLayout(rulerLayout)
        settingsGroupLayout.addLayout(outputNamingLayout)
        settingsGroupLayout.addSpacing(15)
        settingsGroupLayout.addWidget(self.fooDefaultsButton)

        settingsGroupBox.setLayout(settingsGroupLayout)

        vlayout.addSpacing(10)
        vlayout.addWidget(settingsGroupBox)

        self.convertButton = QtWidgets.QPushButton("Convert Images")
        self.convertButton.clicked.connect(self.processImageFiles)
        self.convertButton.setAutoDefault(False)
        # Button appearance is odd in QStackedLayout without adding to ButtonPanel
        self.buttonPanel = ButtonPanel(self.convertButton)

        self.progressPanel = ProgressPanel(self)

        self.stackedLayout = QtWidgets.QStackedLayout()
        self.stackedLayout.addWidget(self.buttonPanel)
        self.stackedLayout.addWidget(self.progressPanel)
        self.stackedLayout.setCurrentIndex(0)

        vlayout.addLayout(self.stackedLayout, stretch=0)

    def showProgressLayout(self, show):
        self.stackedLayout.setCurrentIndex(1 if show else 0)

    def initAppPath(self):
        try:
            self.app_path = common.get_app_path()
        except common.InvalidApplicationPathError as iape:
            errbox(self, "Invalid Application Path", "Couldn't find application directory, exiting.")
            raise iape # re-raise and bail

    def initPrefs(self):
        prefPath = os.path.join(self.app_path, "prefs.pk")
        self.prefs = Preferences(prefPath)
        self.installPrefs()

    def installRulers(self):
        rulersPath = os.path.join(self.app_path, "rulers")
        try:
            common.mkdir_if_needed(rulersPath)
        except:
            err = sys.exc_info()
            errbox(self, "Process failed", "{}".format("Failed to create {}.\nUnhandled error {}: {}".format(rulersPath, err[0], err[1])))
            logging.error(traceback.format_exc())            
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
        ruler = self.prefs.get("ruler", "")
        rulerIdx = self.rulerCombo.findText(ruler)
        self.rulerCombo.setCurrentIndex(rulerIdx if rulerIdx >= 0 else 0)
        # default to input file name
        self.outputNamingCombo.setCurrentIndex(self.prefs.get("outputNaming", 0))

    def savePrefs(self):
        self.prefs.set("windowGeometry", self.geometry())
        self.prefs.write()

    def saveDefaultSettings(self):
        self.prefs.set("dpi", self.dpi.text())
        self.prefs.set("trim", self.trim.text())
        self.prefs.set("icdScaling", self.icdScaling.text())
        self.prefs.set("ruler", self.rulerCombo.currentText())
        self.prefs.set("outputNaming", self.outputNamingCombo.currentIndex())
        infobox(self, "Saved Default Settings", f"Saved Default Settings.\n\nResolution: {self.dpi.text()} DPI\nTrim: {self.trim.text()} inches\nICD Scaling: {self.icdScaling.text()}%\nRuler: {self.rulerCombo.currentText()}\nOutput Naming: {self.outputNamingCombo.currentText()}")

    # override QWidget.closeEvent()
    def closeEvent(self, event):
        self.savePrefs()
        event.accept() # allow window to close - event.ignore() to veto close

    def getRulerPath(self):
        return os.path.join(self.app_path, "rulers", str(self.rulerCombo.currentText()))

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
            if dpi <= 0:
                errbox(self, "Invalid DPI", "DPI must be greater than zero.")
                return
            trimTxt = self.trim.text()
            trim = float(trimTxt if len(trimTxt) > 0 else 0)
            if trim < 0:
                errbox(self, "Invalid trim length", "Trim length cannot be negative.")
                return
            icdScaling = float(self.icdScaling.text())
            if icdScaling <= 0:
                errbox(self, "Invalid ICD Scaling", "ICD scaling % must be greater than zero.")
                return
            parentDirBasename = self.outputNamingCombo.currentIndex() == 1
            for imgPath in imgFiles:
                if parentDirBasename:
                    outputBaseName = os.path.basename(os.path.dirname(os.path.normpath(imgPath)))
                else:
                    outputBaseName, _ = os.path.splitext(os.path.basename(imgPath))
                geotek.prepare_geotek(imgPath, self.getRulerPath(), dpi, trim, icdScaling, outputBaseName, self.app_path)
            success = True
        except common.RulerTooShortError as e:
            errbox(self, "Ruler Too Short", "{}".format(e.message))
        except common.UnexpectedColorDepthError as e:
            errbox(self, "Unexpected Color Depth", "{}".format(e.message))
        except ValueError: # raised by float()
            errbox(self, "Expected Numeric Input", "Invalid DPI, trim, or ICD Scaling value, all of which must be numeric.")
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


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(app)
    window.setModal(False)
    window.show()
    sys.exit(app.exec_())
