import requests
from PyQt5.QtWidgets import QCheckBox, QDialog, QGridLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QSpacerItem, QWidget
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

    def keyPressEvent(self, qKeyEvent):
        """ enable the user to press enter to log in """
        if qKeyEvent.key() == QtCore.Qt.Key_Return:
            self.loginButton()
        else:
            super().keyPressEvent(qKeyEvent)

    def sizeHint(self):
        """ used by qgis to set the size """
        a = QWidget.sizeHint(self)
        a.setHeight(SIZEH)
        a.setWidth(SIZEW)
        return a

    def constructUI(self):
        """ function that constructs the login UI """
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
        """ function called when the 'remember me' checkbox is clicked """
        self.rememberMe = button.isChecked()

    def confirmRemember(self):
        """ confirm if the user is sure that they want their info to be remembered """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)

        msg.setText("Remembering your login data should only be done on devices you trust.")
        msg.setWindowTitle("Are you sure?")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg.setDefaultButton(QMessageBox.Ok)
        retval = msg.exec_()
        return retval == QMessageBox.Ok

    def displayLoginError(self):
        """ displays an error, called when the login fails """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)

        msg.setText("Please enter your correct username and password.")
        msg.setWindowTitle("Login failed!")
        msg.setStandardButtons(QMessageBox.Ok)
        retval = msg.exec_()
        return

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

        apiurl = f"{V2URL}/account/login"
        log(f'Logging in: username: {self.username}, password: {self.password}')

        headers = CaseInsensitiveDict()
        headers["Content-Type"] = "application/json"
        data = '{"username": "%s", "password": "%s", "validFor": %i}' % (self.username, self.password, 30) # orignal value 3155760000

        log(data)
        try:
            resp = requests.post(apiurl, headers=headers, data=data)
        except requests.exceptions.RequestException as e:
            getMessageBox("Request failed", "Please check your internet connection").exec_()
            log(e)
            return
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
            success, data = getUserData(loginToken)
            if success:
                self.loginSignal.emit(loginToken, data)
            self.username = ""
            self.password = ""
            self.lineEdit_username.setText("")
            self.lineEdit_password.setText("")
        else:
            self.displayLoginError()
            log("Login failed")

    def onUsernameChange(self, text):
        """ makes the internal username match the form """
        self.username = text

    def onPasswordChange(self, text):
        """ makes the internal password match the form """
        self.password = text
