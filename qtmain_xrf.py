# LacCore/CSDCO
# qtmain_xrf.py
# PyQt GUI wrapper of XRF processing logic

import logging, os, sys, time, traceback

from PyQt5 import QtWidgets

import common
import xrf_opencv as xrf
from gui import FileListPanel, errbox, infobox, ProgressPanel, TwoButtonPanel
from prefs import Preferences


class MainWindow(QtWidgets.QDialog):
    def __init__(self, app):
        QtWidgets.QDialog.__init__(self)
        self.VERSION = "1.3"
        self.app = app
        self.app_path = None # init'd in self.initPrefs()

        self.initAppPath()
        self.initGUI()
        self.installRulers()
        self.initPrefs()

    def initGUI(self):
        self.setWindowTitle("LacCore/CSDCO XRF Image Converter v{}".format(self.VERSION))
        
        vlayout = QtWidgets.QVBoxLayout(self)

        listLabel = "Images to be converted: click Add, or drag and drop files onto the list below to add images."
        self.imageList = FileListPanel(listLabel)
        self.imageList.addButton.setAutoDefault(False)
        self.imageList.rmButton.setAutoDefault(False)
        vlayout.addWidget(self.imageList, 1)

        self.gamma = QtWidgets.QLineEdit()
        gammaLayout = QtWidgets.QHBoxLayout()
        gammaLayout.addWidget(QtWidgets.QLabel("Gamma Correction:"))
        gammaLayout.addWidget(self.gamma)
        gammaLayout.addWidget(QtWidgets.QLabel("typically between 0.8 (darker) and 2.3 (brighter)"), stretch=1)
        vlayout.addLayout(gammaLayout, 0)

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

        outputNamingLayout = QtWidgets.QHBoxLayout()
        self.outputNamingCombo = QtWidgets.QComboBox()
        self.outputNamingCombo.addItems(["Use input file's name", "Use name of input file's parent directory"])
        self.outputNamingCombo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, self.outputNamingCombo.sizePolicy().verticalPolicy())
        outputNamingLayout.addWidget(QtWidgets.QLabel("Output Naming:"))
        outputNamingLayout.addWidget(self.outputNamingCombo)
        vlayout.addLayout(outputNamingLayout)

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
        self.gamma.setText(self.prefs.get("gamma", "1.4"))
        ruler = self.prefs.get("ruler", "")
        rulerIdx = self.rulerCombo.findText(ruler)
        self.rulerCombo.setCurrentIndex(rulerIdx if rulerIdx >= 0 else 0)
        # default to input file name
        self.outputNamingCombo.setCurrentIndex(self.prefs.get("outputNaming", 0))        

    def savePrefs(self):
        self.prefs.set("windowGeometry", self.geometry())
        self.prefs.write()

    def saveDefaultSettings(self):
        self.prefs.set("gamma", self.gamma.text())
        self.prefs.set("ruler", self.rulerCombo.currentText())
        self.prefs.set("outputNaming", self.outputNamingCombo.currentIndex())

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

        try:
            gamma = float(self.gamma.text())
            if (gamma <= 0.0):
                infobox(self, "Invalid Gamma", "Gamma correction must be greater than 0.0")
                return
        except ValueError:
            errbox(self, "Invalid Gamma", "Gamma value must be numeric and greater than 0.0")
            return

        success = False
        self.showProgressLayout(True)
        self.progressPanel.clear()
        xrf.setProgressListener(self.progressPanel)
        try:
            parentDirBasename = self.outputNamingCombo.currentIndex() == 1
            for imgPath in imgFiles:
                if parentDirBasename:
                    outputBaseName = os.path.basename(os.path.dirname(os.path.normpath(imgPath)))
                else:
                    outputBaseName, _ = os.path.splitext(os.path.basename(imgPath))            
                xrf.prepare_xrf(imgPath, self.getRulerPath(), gamma, outputBaseName, destDir=self.app_path)
            success = True
        except common.UnexpectedColorDepthError as e:
            errbox(self, "Unexpected Color Depth", "{}".format(e.message))
        except common.UnexpectedComponentCountError as e:
            errbox(self, "Unexpected Component Count", "{}".format(e.message))
        except common.RulerTooShortError as e:
            errbox(self, "Ruler Too Short", "{}".format(e.message))
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
    