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
        self.useCustomAPIUrl = self.settings.value("useCustomAPIUrl", False)

        self.setMinimumHeight(0)
        self.setMinimumWidth(0)

        self.constructUI()

    def sizeHint(self):
        a = QWidget.sizeHint(self)
        a.setHeight(SIZEH)
        a.setWidth(SIZEW)
        return a

    def back(self):
        self.returnsignal.emit()

    def onChangeUseAPI(self, button):
        """function called when the 'use this api url' checkbox is clicked"""
        self.useCustomAPIUrl = button.isChecked()
        # save to the settings
        self.settings.setValue("useCustomAPIUrl", self.useCustomAPIUrl)

    def constructUI(self):
        self.gridLayout = QGridLayout()
        self.label = QLabel()
        self.label.setText("API Settings:")

        self.apiUrl = QLineEdit()
        self.apiUrl.setText(URL)

        self.useThisApi = QCheckBox()
        self.useThisApi.setText("Use this API url")
        self.useThisApi.setChecked(self.useCustomAPIUrl)
        self.useThisApi.stateChanged.connect(
            lambda: self.onChangeUseAPI(self.useThisApi)
        )

        self.backButton = QPushButton()
        self.backButton.setText("Back")
        self.backButton.clicked.connect(self.back)

        self.gridLayout.addWidget(self.label, 0, 0)
        self.gridLayout.addWidget(self.apiUrl, 1, 0)
        self.gridLayout.addWidget(self.useThisApi, 2, 0)
        self.gridLayout.addWidget(self.backButton, 2, 1)

        self.spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gridLayout.addItem(self.spacer, 3, 0, 1, 2)
        self.setLayout(self.gridLayout)
