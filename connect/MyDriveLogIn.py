import os
from PyQt5.QtCore import QLine, QSize

import requests
from PyQt5.QtWidgets import QCheckBox, QDialog, QDockWidget, QGridLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QSpacerItem, QWidget
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtWidgets import QMessageBox
from requests.structures import CaseInsensitiveDict

from .util import *


class MyDriveLoginTab(QDialog):
    """ login tab, sends a signal with the token on succesful login. Used in combination with the MyDriveLoggedInTab"""
    loginSignal = pyqtSignal(object, object)
    def __init__(self):
        super(MyDriveLoginTab, self).__init__()
        #uic.loadUi(os.path.join(TABSFOLDER, "MyDriveLoginTab.ui"), self)
        self.settings = QSettings('Ellipsis Drive', 'Ellipsis Drive Connect')

        self.constructUI()

        self.username = ""
        self.password = ""
        self.userInfo = {}
        self.rememberMe = self.checkBox_remember.isChecked()
        self.loggedIn = False

    def sizeHint(self):
        a = QWidget.sizeHint(self)
        a.setHeight(SIZEH)
        a.setWidth(SIZEW)
        return a

    def constructUI(self):
        self.gridLayout = QGridLayout()
        
        self.label_username = QLabel()
        self.label_username.setText("Username")

        self.label_password = QLabel()
        self.label_password.setText("Password")

        self.checkBox_remember = QCheckBox()
        self.checkBox_remember.setChecked(True)
        self.checkBox_remember.setText("Remember me")

        self.lineEdit_password = QLineEdit()
        self.lineEdit_username = QLineEdit()
        self.pushButton_login = QPushButton()
        self.pushButton_login.setText("Login")
        self.spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.pushButton_login.clicked.connect(self.loginButton)
        self.lineEdit_username.textChanged.connect(self.onUsernameChange)
        self.lineEdit_password.textChanged.connect(self.onPasswordChange)
        self.lineEdit_password.setEchoMode(QLineEdit.Password)
        self.checkBox_remember.stateChanged.connect(lambda:self.onChangeRemember(self.checkBox_remember))
        

        self.gridLayout.addWidget(self.label_username, 0, 0)
        self.gridLayout.addWidget(self.lineEdit_username, 1, 0, 1, 2)
        self.gridLayout.addWidget(self.label_password, 2, 0)
        self.gridLayout.addWidget(self.lineEdit_password, 3, 0, 1, 2)
        self.gridLayout.addWidget(self.checkBox_remember, 4, 0)
        self.gridLayout.addWidget(self.pushButton_login, 4, 1)
        self.gridLayout.addItem(self.spacer, 5, 0, 1, 2)
        
        self.setLayout(self.gridLayout)

    def onChangeRemember(self, button):
        self.rememberMe = button.isChecked()

    def confirmRemember(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)

        msg.setText("Remembering your login data should only be done on devices you trust.")
        msg.setWindowTitle("Are you sure?")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        retval = msg.exec_()
        return retval == QMessageBox.Ok

    def displayLoginError(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)

        msg.setText("Please enter your correct username and password.")
        msg.setWindowTitle("Login failed!")
        msg.setStandardButtons(QMessageBox.Ok)
        retval = msg.exec_()
        return

    def getUserData(self, token):
        log("Getting user data")
        apiurl = f"{URL}/account/info"
        headers = CaseInsensitiveDict()
        headers["Authorization"] = f"Bearer {token}"
        resp = requests.get(apiurl, headers=headers)
        data = resp.json()
        jlog(data)
        if (resp):
            log("getUserData success")
            self.userInfo = data
            return True
        log("getUserData failed")
        return False
        

    def loginButton(self):
        """ handler for the log in button """
        actual_remember = False
        # check if the user is sure that they want us to remember their login token
        if (self.rememberMe):
            confirm_remember = self.confirmRemember()
            if (not confirm_remember):
                return
            else:
                actual_remember = True

        apiurl = f"{URL}/account/login"
        log(f'Logging in: username: {self.username}, password: {self.password}')

        headers = CaseInsensitiveDict()
        headers["Content-Type"] = "application/json"
        data = '{"username": "%s", "password": "%s", "validFor": %i}' % (self.username, self.password, 3155760000)

        log(data)
        resp = requests.post(apiurl, headers=headers, data=data)
        data = resp.json()
        jlog(data)
        if resp:
            #print(f"Token: {data['token']}")
            self.loggedIn = True
            loginToken = data['token']
            log("logged in")
            if actual_remember:
                self.settings.setValue("token",data["token"])
                log("login token saved to settings")
            else:
                log("token NOT saved to settings")
            
            if self.getUserData(loginToken):
                self.loginSignal.emit(loginToken, self.userInfo)
            self.username = ""
            self.password = ""
            self.lineEdit_username.setText("")
            self.lineEdit_password.setText("")
        else:
            self.displayLoginError()
            log("Login failed")

    def onUsernameChange(self, text):
        self.username = text

    def onPasswordChange(self, text):
        self.password = text
