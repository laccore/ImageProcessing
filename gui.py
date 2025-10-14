# LacCore/CSDCO
# Useful compound GUI objects and methods for PyQt applications.

import logging, os, platform

from PyQt5 import QtWidgets, QtCore

def warnbox(parent, title="Warning", message=""):
    QtWidgets.QMessageBox.warning(parent, title, message)
    
def errbox(parent, title="Error", message=""):
    QtWidgets.QMessageBox.critical(parent, title, message)

def infobox(parent, title="Information", message=""):    
    QtWidgets.QMessageBox.information(parent, title, message)

def promptbox(parent, title="Prompt", message=""):
    response = QtWidgets.QMessageBox.question(parent, title, message)
    return response == QtWidgets.QMessageBox.Yes

def chooseDirectory(parent, path=""):
    dlg = QtWidgets.QFileDialog(parent, "Choose directory", path)
    selectedDir = dlg.getExistingDirectory(parent)
    return selectedDir

def chooseFile(parent, path=""):
    dlg = QtWidgets.QFileDialog(parent, "Choose file", path)
    chosenFile = dlg.getOpenFileName(parent)
    return chosenFile

def chooseFiles(parent, path=""):
    dlg = QtWidgets.QFileDialog(parent, "Choose file(s)", path)
    chosenFiles = dlg.getOpenFileNames(parent)
    return chosenFiles

def chooseSaveFile(parent, path=""):
    dlg = QtWidgets.QFileDialog(parent, "Save file", path)
    saveFile = dlg.getSaveFileName(parent)
    return saveFile


# Provides file drag and drop support. Inheriting classes must call
# self.setAcceptDrops(True) and self.setAcceptMethod([provided method])
# for DnD behavior to work.
class DragAndDropMixin:
    def __init__(self):
        self.acceptMethod = None

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            paths = [u.toLocalFile() for u in event.mimeData().urls()]
            if self.acceptMethod:
                self.acceptMethod(paths)
        else:
            event.ignore()

    # client-provided method to handle a single arugment: a list of file paths
    def setAcceptMethod(self, method):
        self.acceptMethod = method


# list of files with Add and Remove buttons
class FileListPanel(QtWidgets.QWidget, DragAndDropMixin):
    def __init__(self, title):
        QtWidgets.QWidget.__init__(self)
        self.initUI(title)
        self.setAcceptDrops(True)
        self.setAcceptMethod(self.addFiles)        

    def initUI(self, title):
        vlayout = QtWidgets.QVBoxLayout(self)
        vlayout.addWidget(LabelFactory.makeItemLabel(title))
        self.sslist = QtWidgets.QListWidget()
        self.sslist.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        vlayout.addWidget(self.sslist)
        arlayout = QtWidgets.QHBoxLayout()
        self.addButton = QtWidgets.QPushButton("Add...")
        self.addButton.clicked.connect(self.onAdd)
        self.rmButton = QtWidgets.QPushButton("Remove")
        self.rmButton.clicked.connect(self.onRemove)
        self._enableRemove()
        arlayout.addWidget(self.addButton)
        arlayout.addWidget(self.rmButton)
        vlayout.setSpacing(0)
        vlayout.addLayout(arlayout)
        vlayout.setContentsMargins(0,0,0,0)
        
    def addFile(self, newfile):
        self.sslist.addItem(QtWidgets.QListWidgetItem(newfile))
        self._enableRemove()
        
    def addFiles(self, filelist):
        for f in filelist:
            self.addFile(f)
        
    def getFiles(self):
        return [self.sslist.item(idx).text() for idx in range(self.sslist.count())]

    def clear(self):
        self.sslist.clear()

    def onAdd(self):
        files = chooseFiles(self)
        for f in files[0]:
            self.addFile(f)
        
    def onRemove(self):
        for sel in self.sslist.selectedItems():
            self.sslist.takeItem(self.sslist.row(sel))
        self._enableRemove()
            
    def _enableRemove(self):
        self.rmButton.setEnabled(self.sslist.count() > 0)


class ProgressPanel(QtWidgets.QWidget):
    def __init__(self, parent, initialText='[progress text]'):
        QtWidgets.QWidget.__init__(self)
        self.parent = parent
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(initialText)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setMaximum(100)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)

    def setValue(self, val):
        self.progress.setValue(val)

    def setText(self, text):
        self.label.setText(text)

    def setValueAndText(self, val, text):
        self.setValue(val)
        self.setText(text)
        self._update()

    def _update(self):
        self.parent.app.processEvents()

    def clear(self):
        self.setValueAndText(0, "")


# Handler to direct python logging output to QTextEdit control
class LogTextArea(logging.Handler):
    def __init__(self, parent, label):
        self.parent = parent
        self.layout = QtWidgets.QVBoxLayout()
        logging.Handler.__init__(self)
        self.logText = QtWidgets.QTextEdit(parent)
        self.logText.setReadOnly(True)
        self.logText.setToolTip("It's all happening.")
        
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)
        self.layout.addWidget(QtWidgets.QLabel(label))
        self.layout.addWidget(self.logText)
        
        self.verboseCheckbox = QtWidgets.QCheckBox("Include Debugging Information")
        self.layout.addWidget(self.verboseCheckbox)
        
    def isVerbose(self):
        return self.verboseCheckbox.isChecked()

    def emit(self, record):
        msg = self.format(record)
        self.logText.insertPlainText(msg + "\n")
        self.parent.app.processEvents()

    def write(self, m):
        pass


class ButtonPanel(QtWidgets.QWidget):
    def __init__(self, button):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(button)


class TwoButtonPanel(QtWidgets.QWidget):
    def __init__(self, button1, button2):
        QtWidgets.QWidget.__init__(self)
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(button1)
        layout.addWidget(button2)

    
# add help text below widget
def HelpTextDecorator(widget, helpText, spacing=5):
    layout = QtWidgets.QVBoxLayout()
    layout.setSpacing(spacing)
    layout.setContentsMargins(0,0,0,0)
    layout.addWidget(widget)
    layout.addWidget(LabelFactory.makeDescLabel(helpText))
    return layout

# create appropriately-sized labels for the current OS
class LabelFactory:
    # main label for an item
    # On Mac, use standard font. On Windows, bold font.
    @classmethod
    def makeItemLabel(cls, text):
        label = QtWidgets.QLabel(text)
        if platform.system() == "Windows":
            label.setStyleSheet("QLabel {font-weight: bold;}")
        return label
    
    # label for help/description text
    # On Mac, use a smaller font. On Windows, standard font.
    @classmethod
    def makeDescLabel(cls, text):
        label = QtWidgets.QLabel(text)
        if platform.system() == "Darwin":
            label.setStyleSheet("QLabel {font-size: 11pt;}")
        return label
    