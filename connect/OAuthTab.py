from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QWidget,
    QSizePolicy,
    QSpacerItem,
)
from qgis.core import *
from qgis.PyQt.QtCore import pyqtSignal
import webbrowser

from .util import *


class OAuthTab(QDialog):
    """Displayed when a user is logged in with OAuth. It tells the user to set a password."""

    returnsignal = pyqtSignal()

    def __init__(self):
        super(OAuthTab, self).__init__()
        self.setMinimumHeight(0)
        self.setMinimumWidth(0)

        self.constructUI()

    def sizeHint(self):
        a = QWidget.sizeHint(self)
        a.setHeight(SIZEH)
        a.setWidth(SIZEW)
        return a

    def takemethere(self):
        webbrowser.open("https://app.ellipsis-drive.com/account-settings/security")

    def back(self):
        self.returnsignal.emit()

    def constructUI(self):
        self.gridLayout = QGridLayout()
        self.label1 = QLabel()
        self.label1.setText(
            "Your account uses OAuth to log in."
        )

        self.label2 = QLabel()
        self.label2.setText("Please set a password on the website to use this plugin.")

        self.takemethereButton = QPushButton()
        self.takemethereButton.setText("Take me there")
        self.takemethereButton.clicked.connect(self.takemethere)

        self.backButton = QPushButton()
        self.backButton.setText("Back")
        self.backButton.clicked.connect(self.back)

        self.gridLayout.addWidget(self.label1, 0, 0)
        self.gridLayout.addWidget(self.label2, 1, 0)
        self.gridLayout.addWidget(self.takemethereButton, 2, 0)
        self.gridLayout.addWidget(self.backButton, 3, 0)

        self.spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gridLayout.addItem(self.spacer, 4, 0, 1, 2)
        self.setLayout(self.gridLayout)
