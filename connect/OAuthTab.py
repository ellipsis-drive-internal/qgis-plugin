from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QPushButton, QWidget
from qgis.core import *
from qgis.PyQt.QtCore import pyqtSignal

from .util import *


class OAuthTab(QDialog):
    """The LoggedIn tab, giving users access to their drive. Used in combination with the MyDriveTab and the MyDriveLoginTab"""

    returnsignal = pyqtSignal()

    def __init__(self):
        super(OAuthTab, self).__init__()
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
        self.returnsignal.emit()

    def constructUI(self):
        self.gridLayout = QGridLayout()
        self.label = QLabel()
        self.label.setText("For OAuth, you have to login by setting a password!")

        self.retryButton = QPushButton()
        self.retryButton.setText("Retry")
        self.retryButton.clicked.connect(self.retry)

        self.gridLayout.addWidget(self.label, 0, 0)
        self.gridLayout.addWidget(self.retryButton, 0, 1)
        self.setLayout(self.gridLayout)
