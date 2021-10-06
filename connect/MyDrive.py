import os

import requests
from PyQt5.QtWidgets import QDialog
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from requests.structures import CaseInsensitiveDict

from .MyDriveLoggedIn import MyDriveLoggedInTab
from .MyDriveLogIn import MyDriveLoginTab
from .util import *


class MyDriveTab(QDialog):
    loginSignal = pyqtSignal(object)
    logoutSignal = pyqtSignal()
    def __init__(self):
        """ Tab that contains a stacked widget: the login tab and the logged in tab """
        super(MyDriveTab, self).__init__()
        uic.loadUi(os.path.join(TABSFOLDER, "MyDriveStack.ui"), self)

        # idea: use QStacketWidget to switch between logged in and logged out

        self.loginWidget = MyDriveLoginTab()
        self.loggedInWidget = MyDriveLoggedInTab()

        self.loggedIn = False
        self.loginToken = ""

        self.userInfo = {}

        self.loginWidget.loginSignal.connect(self.handleLoginSignal)
        self.loggedInWidget.logoutSignal.connect(self.handleLogoutSignal)

        self.stackedWidget.addWidget(self.loginWidget)
        self.stackedWidget.addWidget(self.loggedInWidget)
        
        self.settings = QSettings('Ellipsis Drive', 'Ellipsis Drive Connect')

        if (self.settings.contains("token")):
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
        self.stackedWidget.setCurrentIndex(1)
    
    def handleLogoutSignal(self):
        log("logout signal received!")
        self.loggedIn = False
        self.loginToken = ""
        self.loggedInWidget.loggedIn = False
        self.loggedInWidget.loginToken = ""
        self.loggedInWidget.resetState()
        self.stackedWidget.setCurrentIndex(0)
        