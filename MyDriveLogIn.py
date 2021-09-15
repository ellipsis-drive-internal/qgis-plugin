import os
import requests
from requests.structures import CaseInsensitiveDict

from PyQt5.QtWidgets import QDialog

from qgis.PyQt import uic

from qgis.PyQt.QtCore import QSettings, pyqtSignal

from qgis.PyQt.QtWidgets import QMessageBox
from .util import *

class MyDriveLoginTab(QDialog):
    """ login tab, sends a signal with the token on succesful login """
    loginSignal = pyqtSignal(object, object)
    def __init__(self):
        super(MyDriveLoginTab, self).__init__()
        uic.loadUi(os.path.join(TABSFOLDER, "MyDriveLoginTab.ui"), self)
        self.pushButton_login.clicked.connect(self.loginButton)
        self.lineEdit_username.textChanged.connect(self.onUsernameChange)
        self.lineEdit_password.textChanged.connect(self.onPasswordChange)
        self.checkBox_remember.stateChanged.connect(lambda:self.onChangeRemember(self.checkBox_remember))
        
        self.settings = QSettings('Ellipsis Drive', 'Ellipsis Drive Connect')

        self.username = ""
        self.password = ""
        self.userInfo = {}
        self.rememberMe = self.checkBox_remember.isChecked()
        self.loggedIn = False
    
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