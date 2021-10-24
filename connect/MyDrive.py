import os

import requests
from PyQt5.QtWidgets import QDialog, QDockWidget, QGridLayout, QLabel, QLineEdit, QCheckBox, QPushButton, QSizePolicy, QSpacerItem, QStackedWidget
from qgis.PyQt import uic, QtGui, QtWidgets, uic

from qgis.PyQt.QtCore import QSettings, pyqtSignal
from requests.structures import CaseInsensitiveDict
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

        # idea: use QStacketWidget to switch between logged in and logged out

        self.loginWidget = MyDriveLoginTab()
        self.loggedInWidget = MyDriveLoggedInTab()
        self.noconnectionWidget = NoConnectionTab()

        self.stackedWidget = QStackedWidget()

        self.layout.addWidget(self.stackedWidget)
        self.setLayout(self.layout)

        self.loggedIn = False
        self.loginToken = ""

        self.userInfo = {}

        self.loginWidget.loginSignal.connect(self.handleLoginSignal)
        self.loggedInWidget.logoutSignal.connect(self.handleLogoutSignal)
        self.noconnectionWidget.connectedSignal.connect(self.handleConnectedSignal)

        self.stackedWidget.addWidget(self.loginWidget)
        self.stackedWidget.addWidget(self.loggedInWidget)
        self.stackedWidget.addWidget(self.noconnectionWidget)

        self.isOnline = connected_to_internet()

        self.loginWidget.isOnline = self.isOnline
        self.loggedInWidget.isOnline = self.isOnline
        
        self.settings = QSettings('Ellipsis Drive', 'Ellipsis Drive Connect')

        if not self.isOnline:
            self.stackedWidget.setCurrentIndex(2)
        elif (self.settings.contains("token")):
            log("Login data found")
            self.loggedIn = True
            self.loginToken = self.settings.value("token")
            self.loggedInWidget.loginToken = self.loginToken
            log("Getting username")
            apiurl = f"{URL}/account/info"
            headers = CaseInsensitiveDict()
            headers["Authorization"] = f"Bearer {self.loginToken}"
            resp = requests.get(apiurl, headers=headers)
            data = resp.json()
            jlog(data)
            if (resp):
                log("getting user info success")
                self.loggedInWidget.userInfo = data
                self.loggedInWidget.label.setText(f"Welcome {data['username']}!")
            else:
                log("getUserData failed")

            self.stackedWidget.setCurrentIndex(1)
        else:
            log("No login data found")

    def loadLoginUI(self):
        # mydrive_gridLayout
        log("loading login UI")

        usernameLabel = QLabel()
        passwordLabel = QLabel()
        usernameLineEdit = QLineEdit()
        passwordLineEdit = QLineEdit()

        rememberMeCheckBox = QCheckBox()
        rememberMeLabel = QLabel()

        loginButton = QPushButton()

        spacer = QSpacerItem(0, 40, hPolicy=QSizePolicy.Minimum, vPolicy=QSizePolicy.Expanding)

        usernameLabel.setText("Username:")
        passwordLabel.setText("Password:")
        rememberMeLabel.setText("Remember me")

        passwordLineEdit.setEchoMode(QLineEdit.Password)

        loginButton.setText("Log in")
        loginButton.clicked.connect(self.onLogin)

        self.layout.addWidget(usernameLabel, 0,0)
        self.layout.addWidget(usernameLineEdit, 1,0)
        self.layout.addWidget(passwordLabel, 2,0)
        self.layout.addWidget(passwordLineEdit, 3,0)
        self.layout.addWidget(rememberMeCheckBox, 4,0)
        self.layout.addWidget(rememberMeLabel, 4,1)
        self.layout.addWidget(loginButton, 5,1)
        self.layout.addWidget(spacer, 6,0)
        
    def handleConnectedSignal(self):
        self.stackedWidget.setCurrentIndex(0 if not self.loggedIn else 1)
        

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
        self.loginToken = ""
        self.loggedInWidget.loggedIn = False
        self.loggedInWidget.loginToken = ""
        self.loggedInWidget.resetState()
        self.stackedWidget.setCurrentIndex(0)
        