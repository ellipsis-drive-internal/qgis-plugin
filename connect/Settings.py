from PyQt5.QtWidgets import (
    QDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QWidget,
    QLineEdit,
    QCheckBox,
    QSizePolicy,
    QSpacerItem,
)
from qgis.core import *
from qgis.PyQt.QtCore import pyqtSignal, QSettings

from .util import *


class SettingsTab(QDialog):
    """Displayed when a user is logged in with OAuth. It tells the user to set a password."""

    returnsignal = pyqtSignal()

    def __init__(self):
        super(SettingsTab, self).__init__()

        self.settings = QSettings("Ellipsis Drive", "Ellipsis Drive Connect")
        self.apiUrl = self.settings.value("apiUrl", URL)

        self.setMinimumHeight(0)
        self.setMinimumWidth(0)

        self.constructUI()

    def sizeHint(self):
        a = QWidget.sizeHint(self)
        a.setHeight(SIZEH)
        a.setWidth(SIZEW)
        return a

    def back(self):
        # check if the api url is valid
        if isValidAPIUrl(self.apiUrl):
            # save the api url
            self.settings.setValue("apiUrl", self.apiUrl)
            self.returnsignal.emit()
        else:
            # show an error message
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("The API URL does not seem to be valid. Please try again.")
            msg.setWindowTitle("Error")
            msg.exec_()

    def resetApiUrl(self):
        self.apiUrlEdit.setText(URL)
        self.onApiUrlChange(URL)

    def onApiUrlChange(self, text):
        # save the api url
        self.apiUrl = text
        self.settings.setValue("apiUrl", text)

    def constructUI(self):
        self.gridLayout = QGridLayout()
        self.label = QLabel()
        self.label.setText("API Settings:")

        self.apiUrlEdit = QLineEdit()
        self.apiUrlEdit.setText(self.apiUrl)
        self.apiUrlEdit.textChanged.connect(self.onApiUrlChange)

        self.resetButton = QPushButton()
        self.resetButton.setText("Reset")
        self.resetButton.clicked.connect(self.resetApiUrl)

        self.backButton = QPushButton()
        self.backButton.setText("Back")
        self.backButton.clicked.connect(self.back)

        self.gridLayout.addWidget(self.label, 0, 0)
        self.gridLayout.addWidget(self.apiUrlEdit, 1, 0)
        self.gridLayout.addWidget(self.resetButton, 2, 0)
        self.gridLayout.addWidget(self.backButton, 2, 1)

        self.spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gridLayout.addItem(self.spacer, 3, 0, 1, 2)
        self.setLayout(self.gridLayout)
