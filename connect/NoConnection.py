from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QPushButton, QWidget
from qgis.core import *
from qgis.PyQt.QtCore import pyqtSignal

from .util import *


class NoConnectionTab(QDialog):
    """ The LoggedIn tab, giving users access to their drive. Used in combination with the MyDriveTab and the MyDriveLoginTab"""
    connectedSignal = pyqtSignal()
    def __init__(self):
        super(NoConnectionTab, self).__init__()
        self.waittime = 2
        self.setMinimumHeight(0)
        self.setMinimumWidth(0)

        self.constructUI()

    def sizeHint(self):
        a = QWidget.sizeHint(self)
        a.setHeight(SIZEH)
        a.setWidth(SIZEW)
        return a

    def retry(self):
        if (connected_to_internet(timeout=self.waittime)):
            self.connectedSignal.emit()
        else:
            self.waittime += 1
        
    def constructUI(self):
        self.gridLayout = QGridLayout()
        self.label = QLabel()
        self.label.setText("No internet connection detected!")
        
        self.retryButton = QPushButton()
        self.retryButton.setText("Retry")
        self.retryButton.clicked.connect(self.retry)

        self.gridLayout.addWidget(self.label, 0, 0)
        self.gridLayout.addWidget(self.retryButton, 0, 1)
        self.setLayout(self.gridLayout)