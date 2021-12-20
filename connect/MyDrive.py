import os
from PyQt5.QtCore import QSize
from qgis.utils import isPluginLoaded

import requests
from PyQt5.QtWidgets import QDialog, QDockWidget, QGridLayout, QLabel, QLineEdit, QCheckBox, QPushButton, QSizePolicy, QSpacerItem, QStackedWidget, QWidget
from qgis.PyQt import uic, QtGui, QtWidgets, uic

from qgis.PyQt.QtCore import QSettings, pyqtSignal
from .MyDriveLoggedIn import MyDriveLoggedInTab
from .MyDriveLogIn import MyDriveLoginTab
from .NoConnection import NoConnectionTab
from .util import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(TABSFOLDER, "MyDriveStack.ui"))

class MyDriveTab(QDockWidget, FORM_CLASS):
    loginSignal = pyqtSignal(object)
    logoutSignal = pyqtSignal()
    closingPlugin = pyqtSignal()
    def __init__(self):
        """ Tab that contains a stacked widget: the login tab and the logged in tab """
        super(MyDriveTab, self).__init__()
        uic.loadUi(os.path.join(TABSFOLDER, "MyDriveStack.ui"), self)
        log("__init__ of MyDriveTab")

        #self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setMinimumSize(QSize(0,0))

        self.loginWidget = MyDriveLoginTab()
        self.loggedInWidget = MyDriveLoggedInTab()
        self.noconnectionWidget = NoConnectionTab()

        self.stackedWidget = QStackedWidget()

        self.stackedWidget.setMinimumSize(QSize(0,0))

        self.layout.addWidget(self.stackedWidget)
        self.setLayout(self.layout)

        self.loggedIn = False
        self.loginToken = None

        self.userInfo = {}

        self.loginWidget.loginSignal.connect(self.handleLoginSignal)
        self.loggedInWidget.logoutSignal.connect(self.handleLogoutSignal)
        self.noconnectionWidget.connectedSignal.connect(self.handleConnectedSignal)

        self.stackedWidget.addWidget(self.loginWidget)
        self.stackedWidget.addWidget(self.loggedInWidget)
        self.stackedWidget.addWidget(self.noconnectionWidget)
        
        self.settings = QSettings('Ellipsis Drive', 'Ellipsis Drive Connect')

        self.checkOnlineAndSetIndex()

    def sizeHint(self):
        a = QWidget.sizeHint(self)
        a.setHeight(SIZEH)
        a.setWidth(SIZEW)
        return a
        
    def checkOnlineAndSetIndex(self):
        self.isOnline = connected_to_internet()

        self.loginWidget.isOnline = self.isOnline
        self.loggedInWidget.isOnline = self.isOnline

        self.loggedIn, self.loginToken = self.isLoggedIn()

        if not self.isOnline:
            self.stackedWidget.setCurrentIndex(2)
        elif self.loggedIn:
            success, data = getUserData(self.loginToken)
            if success:
                self.loggedInWidget.userInfo = data
                self.loggedInWidget.label.setText(f"Welcome {data['username']}")
            self.loggedInWidget.loggedIn = True
            self.loggedInWidget.loginToken = self.loginToken
            self.stackedWidget.setCurrentIndex(1)
        else:
            self.stackedWidget.setCurrentIndex(0)

    def isLoggedIn(self):
        if not self.settings.contains("token"):
            return [False, None]
        else:
            return [True, self.settings.value("token")]

    def handleConnectedSignal(self):
        self.checkOnlineAndSetIndex()
        
    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def handleLoginSignal(self, token, userInfo):
        log("login signal received!")
        self.loginToken = token
        self.loggedIn = True
        self.loggedInWidget.loginToken = token
        self.loggedInWidget.loggedIn = True
        self.loggedInWidget.userInfo = userInfo
        self.loggedInWidget.label.setText(f"Welcome {userInfo['username']}!")
        self.userInfo = userInfo
        self.loginSignal.emit(token)
        self.loggedInWidget.fillListWidget()
        self.stackedWidget.setCurrentIndex(1)
    
    def handleLogoutSignal(self):
        log("logout signal received!")
        self.loggedIn = False
        self.loginToken = None
        self.loggedInWidget.loggedIn = False
        self.loggedInWidget.loginToken = None
        self.loggedInWidget.resetState()
        self.stackedWidget.setCurrentIndex(0)
        