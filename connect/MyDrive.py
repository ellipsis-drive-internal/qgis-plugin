import os
from PyQt5.QtCore import QSize

from PyQt5.QtWidgets import QDockWidget, QStackedWidget, QWidget
from qgis.PyQt import uic

from qgis.PyQt.QtCore import QSettings, pyqtSignal
from .MyDriveLoggedIn import MyDriveLoggedInTab
from .MyDriveLogIn import MyDriveLoginTab
from .NoConnection import NoConnectionTab
from .util import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(TABSFOLDER, "MyDriveStack.ui"))

class MyDriveTab(QDockWidget, FORM_CLASS):
    """ the class that encapsulates the other views that are actually shown """
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
        """ size hint for qgis """
        a = QWidget.sizeHint(self)
        a.setHeight(SIZEH)
        a.setWidth(SIZEW)
        return a
        
    def checkOnlineAndSetIndex(self):
        """ check if we have an internet connection, and set the (starting) tabindex accordingly """
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
                self.loggedInWidget.label.setText(f"Welcome {data['username']}!")
            self.loggedInWidget.loggedIn = True
            self.loggedInWidget.loginToken = self.loginToken
            self.stackedWidget.setCurrentIndex(1)
        else:
            self.stackedWidget.setCurrentIndex(0)

    def isLoggedIn(self):
        """ checks if a token is present, returns a tuple of (bool, token/None) """
        if not self.settings.contains("token"):
            return [False, None]
        else:
            curToken = self.settings.value("token")

            #check if token is still valid
            log("Token found, checking validity")
            headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
            headers["Authorization"] = f"Bearer {curToken}"
            status, content = makeRequest("/validate", headers, version=2, method="POST")
            log(content)
            if status and content["valid"]:
                log("Token still valid")
                return [True, self.settings.value("token")]
            else:
                # remove invalid token
                log("Removing invalid token")
                self.settings.remove("token")
                return [False, None]

    def handleConnectedSignal(self):
        """ signal handler """
        self.checkOnlineAndSetIndex()
        
    def closeEvent(self, event):
        """ event handler """
        self.closingPlugin.emit()
        event.accept()

    def handleLoginSignal(self, token, userInfo):
        """ login signlar handler"""
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
        """ logout singal handler """
        log("logout signal received!")
        self.loggedIn = False
        self.loginToken = None
        self.loggedInWidget.loggedIn = False
        self.loggedInWidget.loginToken = None
        self.loggedInWidget.resetState()
        self.stackedWidget.setCurrentIndex(0)
        