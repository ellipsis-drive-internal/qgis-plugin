# -*- coding: utf-8 -*-
"""
/***************************************************************************
 EllipsisConnectDialog
                                 A QGIS plugin
 Connect to Ellipsis Drive
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2021-06-24
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Ellipsis Drive
        email                : floydremmerswaal@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import sys
import json
import requests
from requests import api
from requests.structures import CaseInsensitiveDict

from threading import Timer

from PyQt5.QtWidgets import QCheckBox, QDialog, QLineEdit, QMainWindow

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

from qgis.PyQt.QtCore import QSettings, pyqtSignal

from PyQt5 import QtCore

from qgis.PyQt.QtWidgets import QAction, QListWidgetItem, QListWidget, QMessageBox, QWidget, QGridLayout, QLabel

try:
    import pyclip
except ImportError:
    this_dir = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(this_dir, 'pyclip-0.5.4-py3-none-any')
    sys.path.append(path)
    import pyclip

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ellipsis_drive_dialog_base.ui'))

# definitions of constants

TABSFOLDER = os.path.join(os.path.dirname(__file__), "tabs/")

URL = 'https://api.ellipsis-drive.com/v1'
#URL = 'http://dev.api.ellipsis-drive.com/v1'

# for reference
# API = 'https://api.ellipsis-drive.com/v1'
DEVAPI = 'http://dev.api.ellipsis-drive.com/v1'

DEBUG = True

# api.ellipsis-drive.com/v1/wms/mapId
# api.ellipsis-drive.com/v1/wmts/mapId
# api.ellipsis-drive.com/v1/wfs/mapId

# TODO
# - pagination of folders and maps
# - Trash folder?

def convertMapdataToListItem(mapdata):
    newitem = QListWidgetItem()
    newitem.setText(mapdata["name"])
    item = ListData("id", mapdata["id"])
    newitem.setData(QtCore.Qt.UserRole, item)
    return newitem

def getMetadata(mapid, token):
    """ Returns metadata (in JSON) for a map (by mapid) by calling the Ellipsis API"""
    apiurl = F"{URL}/metadata"
    headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
    data = {
        "mapId": f"{mapid}",
    }
    j1 = requests.post(apiurl, json=data, headers=headers)
    if not j1:
        log("getMetadata failed!")
        return {}
    data = json.loads(j1.text)
    jlog(data)
    return data

def getUrl(mode, mapId):
    """ constructs the url and copies it to the clipboard"""
    theurl = f"{URL}/{mode}/{mapId}"
    log(f"getUrl: {theurl}")
    pyclip.copy(theurl)
    msg = QMessageBox()
    msg.setWindowTitle("Success")
    msg.setIcon(QMessageBox.Information)
    msg.setText("Url copied to clipboard!")
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()

class ListData:
    """ Class used for objects in the QList of the EllipsisConnect plugin """
    def __init__(self, type="none", data=""):
        self.type = type
        self.data = data
    
    def setData(self, type, data):
        self.type = type
        self.data = data

    def getData(self):
        return self.data

    def getType(self):
        return self.type

    def isEmpty(self):
        return self.type == "none" and self.data == ""

# taken from https://gist.github.com/walkermatt/2871026
def debounce(wait):
    """ Decorator that will postpone a functions
        execution until after wait seconds
        have elapsed since the last time it was invoked. """
    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)
            try:
                debounced.t.cancel()
            except(AttributeError):
                pass
            debounced.t = Timer(wait, call_it)
            debounced.t.start()
        return debounced
    return decorator

def log(text):
    """ only prints when DEBUG is True """
    if DEBUG:
        print(text)

def jlog(obj):
    """ logs a JSON object"""
    text = json.dumps(obj, sort_keys=True, indent=4)
    log(text)

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
        self.rememberMe = False
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
    
    # als de gebruiker 'remember me' niet heeft ingevuld: gewoon inloggen
    # als de gebruiker 'remember me' wel invult: verifiëren
    # Zo ja: inloggen en opslaan
    # Zo nee: niet inloggen

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
            log("Login failed")

    def onUsernameChange(self, text):
        self.username = text

    def onPasswordChange(self, text):
        self.password = text

class MyDriveLoggedInTab(QDialog):
    """ The LoggedIn tab, giving users access to their drive"""
    logoutSignal = pyqtSignal()
    def __init__(self):
        super(MyDriveLoggedInTab, self).__init__()
        uic.loadUi(os.path.join(TABSFOLDER, "MyDriveLoggedInTab.ui"), self)
        self.loginToken = ""
        self.loggedIn = False
        self.userInfo = {}
        self.selected = None
        self.level = 0
        self.mode = ""
        self.path = "/"
        self.folderstack = []
        self.currentlySelectedId = ""
        self.radioState = "raster"
        self.listWidget_mydrive.itemClicked.connect(self.onListWidgetClick)

        self.pushButton_logout.clicked.connect(self.logOut)
        self.pushButton_previous.clicked.connect(self.onPrevious)
        self.pushButton_next.clicked.connect(self.onNext)

        self.pushButton_wms.clicked.connect(lambda:getUrl("wms", self.currentlySelectedId))
        self.pushButton_wmts.clicked.connect(lambda:getUrl("wmts", self.currentlySelectedId))
        self.pushButton_wfs.clicked.connect(lambda:getUrl("wfs", self.currentlySelectedId))

        self.radioRaster.toggled.connect(lambda:self.manageRadioState(self.radioRaster))
        self.radioVector.toggled.connect(lambda:self.manageRadioState(self.radioVector))

        self.listWidget_mydrive_maps.itemClicked.connect(self.onMapItemClick)
        
        self.settings = QSettings('Ellipsis Drive', 'Ellipsis Drive Connect')
        self.fixEnabledButtons(True)
        self.disableCorrectButtons(True)
        self.populateListWithRoot()

    def disableCorrectButtons(self, disableAll = False):
        """ helper function to fix the currently enabled buttons """
        if disableAll:
            self.pushButton_wms.setEnabled(False)
            self.pushButton_wmts.setEnabled(False)
            self.pushButton_wfs.setEnabled(False)
        elif self.radioState == "raster":
            self.pushButton_wms.setEnabled(True)
            self.pushButton_wmts.setEnabled(True)
            self.pushButton_wfs.setEnabled(False)
        else:
            self.pushButton_wms.setEnabled(False)
            self.pushButton_wmts.setEnabled(False)
            self.pushButton_wfs.setEnabled(True)

    def manageRadioState(self, b):
        if b.text() == "Raster data":
            if b.isChecked():
                self.radioState = "raster"
            else:
                self.radioState = "vector"
        elif b.text() == "Vector data":
            if b.isChecked():
                self.radioState = "vector"
            else:
                self.radioState = "raster"
        if (self.currentlySelectedId != ""):
            self.disableCorrectButtons()
        else:
            self.disableCorrectButtons(True)

    def onMapItemClick(self, item):
        self.disableCorrectButtons()
        self.currentlySelectedId = item.data((QtCore.Qt.UserRole)).getData()
        log(f"{item.text()}, data type: {item.data((QtCore.Qt.UserRole)).getType()}, data value: {item.data((QtCore.Qt.UserRole)).getData()}")

    def removeFromPath(self):
        """ remove one level from the path, useful when going back in the folder structure """
        if (self.level == 0):
            self.setPath("/")
            return
        self.setPath(self.path.rsplit('/',1)[0])

    def addToPath(self, foldername):
        if self.path == "/":
            self.path = ""
        self.setPath(f"{self.path}/{foldername}")

    def setPath(self, path):
        """ set the displayed path """
        self.path = path
        self.label_path.setText(f"Path: {path}")

    def onNext(self):
        """ handler for the Next button, used for navigating the folder structure """
        log("BEGIN")
        log(self.folderstack)
        if (self.level == 0):
            self.onNextRoot()
        else:
            self.onNextNormal()
        self.level += 1
        self.selected = None
        self.disableCorrectButtons()
        self.fixEnabledButtons()
        log(self.folderstack)
        log("END")
        # TODO using addToPath

    def onNextNormal(self):
        """ non-root onNext"""
        pathId = self.selected.data(QtCore.Qt.UserRole).getData()
        self.getFolder(pathId)
        self.folderstack.append(pathId)
        self.addToPath(self.selected.text())
        
        #self.addToPath(pathId = self.selected.get)

    def onNextRoot(self):
        """ onNext for root folders """
        root = self.selected.data(QtCore.Qt.UserRole).getData()
        self.getFolder(root, True)
        self.folderstack.append(root)
        self.addToPath(root)
    

    def getFolder(self, id, isRoot=False):
        """ clears the listwidgets and fills them with the folders and maps in the specified folder """
        apiurl = ""
        headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
        headers["Authorization"] = f"Bearer {self.loginToken}"
        data = {}
        data2= {}
        if (isRoot):
            apiurl = f"{URL}/path/listRoot"
            data = {
            "root": f"{id}",
            "type": "map"
            }
            data2 = {
                "root": f"{id}",
                "type": "folder"
            }
        else:
            apiurl = f"{URL}/path/listFolder"
            data = {
                "pathId": f"{id}",
                "type": "map"
            }
            data2 = {
                "pathId": f"{id}",
                "type": "folder"
            }

        j1 = requests.post(apiurl, json=data, headers=headers)
        j2 = requests.post(apiurl, json=data2, headers=headers)

        if not j1 or not j2:
            log("getFolder failed!")
            if not j1:
                jlog(j1.reason)
            if not j2:
                jlog(j2.reason)
            return False
        
        self.clearListWidget()
        maps = json.loads(j1.text)
        folders = json.loads(j2.text)

        [self.listWidget_mydrive_maps.addItem(convertMapdataToListItem(mapdata)) for mapdata in maps["result"]]
        [self.listWidget_mydrive.addItem(convertMapdataToListItem(folderdata)) for folderdata in folders["result"]]

    def onPrevious(self):
        log("onPrevious start")
        log(self.folderstack)
        self.level -= 1
        self.removeFromPath()
        self.fixEnabledButtons()
        self.selected = None

        if self.level == 0:
            self.populateListWithRoot()
            self.path = "/"
            self.folderstack = []
            self.disableCorrectButtons(True)
            log(self.folderstack)
            log("onPrevious level 0 end")
            return
        
        if self.level == 1:
            self.folderstack.pop()
            self.getFolder(self.folderstack[0], True)
            self.disableCorrectButtons()
            log(self.folderstack)
            log("onPrevious level 1 end")
            return

        self.folderstack.pop()
        self.getFolder(self.folderstack[len(self.folderstack) - 1])
        self.disableCorrectButtons()
        log(self.folderstack)
        log("onPrevious regular end")
        
    
    def fixEnabledButtons(self, disableAll=False):
        """ correctly enable and disable buttons in the MyDrive tab """
        if disableAll:
            self.pushButton_previous.setEnabled(False)
            self.pushButton_next.setEnabled(False)
            return
        
        self.pushButton_previous.setEnabled(True)
        self.pushButton_next.setEnabled(False)

        if not (self.selected is None):
            self.pushButton_next.setEnabled(True)
        
        if self.level == 0:
            self.pushButton_previous.setEnabled(False)

    def clearListWidget(self, which=0):
        """ clears list widgets, 0 = both, 1 = folders, 2 = maps. defaults to both"""
        # boolean statement could be improved, but I think this is more readable
        if (which == 0 or which == 1):
            for _ in range(self.listWidget_mydrive.count()):
                self.listWidget_mydrive.takeItem(0)
        
        if (which == 0 or which == 2):
            for _ in range(self.listWidget_mydrive_maps.count()):
                self.listWidget_mydrive_maps.takeItem(0)
        

    def onListWidgetClick(self, item):
        self.selected = item
        self.fixEnabledButtons()

    def logOut(self):
        """ emits the logout signal and removes the login token from the settings """
        log("logging out")
        if (self.settings.contains("token")):
            self.settings.remove("token")
        self.logoutSignal.emit()

    def populateListWithRoot(self):
        """ Clears the listwidgets and adds the 3 root folders to the folder widget """
        self.clearListWidget()
        myprojects = ListData("rootfolder", "myMaps")
        sharedwithme = ListData("rootfolder", "shared")
        favorites = ListData("rootfolder", "favorites")

        myprojectsitem = QListWidgetItem()
        sharedwithmeitem = QListWidgetItem()
        favoritesitem = QListWidgetItem()

        myprojectsitem.setText("My Projects")
        sharedwithmeitem.setText("Shared with me")
        favoritesitem.setText("Favorites")


        myprojectsitem.setData(QtCore.Qt.UserRole, myprojects)
        sharedwithmeitem.setData(QtCore.Qt.UserRole, sharedwithme)
        favoritesitem.setData(QtCore.Qt.UserRole, favorites)

        self.listWidget_mydrive.addItem(myprojectsitem)
        self.listWidget_mydrive.addItem(sharedwithmeitem)
        self.listWidget_mydrive.addItem(favoritesitem)

class MyDriveTab(QDialog):
    def __init__(self):
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
        self.userInfo = userInfo
        self.stackedWidget.setCurrentIndex(1)
    
    def handleLogoutSignal(self):
        log("logout signal received!")
        self.loggedIn = False
        self.loginToken = ""
        self.loggedInWidget.loggedIn = False
        self.loggedInWidget.loginToken = ""
        self.stackedWidget.setCurrentIndex(0)
    
class CommunityTab(QDialog):
    def __init__(self):
        super(CommunityTab, self).__init__()
        uic.loadUi(os.path.join(TABSFOLDER, "CommunityTab.ui"), self)
        self.communitySearch = ""
        self.radioState = "raster"
        self.currentlySelectedId = ""

        self.listWidget_community.itemClicked.connect(self.onCommunityItemClick)
        self.lineEdit_communitysearch.textChanged.connect(self.onCommunitySearchChange)

        self.pushButton_wms.clicked.connect(lambda:getUrl("wms", self.currentlySelectedId))
        self.pushButton_wmts.clicked.connect(lambda:getUrl("wmts", self.currentlySelectedId))
        self.pushButton_wfs.clicked.connect(lambda:getUrl("wfs", self.currentlySelectedId))

        self.disableCorrectButtons(True)
        
        self.radioRaster.toggled.connect(lambda:self.manageRadioState(self.radioRaster))
        self.radioVector.toggled.connect(lambda:self.manageRadioState(self.radioVector))

        self.getCommunityList()

    # api.ellipsis-drive.com/v1/wms/mapId
    # api.ellipsis-drive.com/v1/wmts/mapId
    # api.ellipsis-drive.com/v1/wfs/mapId

    def disableCorrectButtons(self, all = False):
        """ enable and disable the correct buttons in the community library tab """
        if all:
            self.pushButton_wms.setEnabled(False)
            self.pushButton_wmts.setEnabled(False)
            self.pushButton_wfs.setEnabled(False)
        elif self.radioState == "raster":
            self.pushButton_wms.setEnabled(True)
            self.pushButton_wmts.setEnabled(True)
            self.pushButton_wfs.setEnabled(False)
        else:
            self.pushButton_wms.setEnabled(False)
            self.pushButton_wmts.setEnabled(False)
            self.pushButton_wfs.setEnabled(True)

    def manageRadioState(self, b):
        if b.text() == "Raster data":
            if b.isChecked():
                self.radioState = "raster"
            else:
                self.radioState = "vector"
        elif b.text() == "Vector data":
            if b.isChecked():
                self.radioState = "vector"
            else:
                self.radioState = "raster"
        if (self.currentlySelectedId != ""):
            self.disableCorrectButtons()
        else:
            self.disableCorrectButtons(True)

    @debounce(0.5)
    def getCommunityList(self):
        """ gets the list of public projects and add them to the list widget on the community tab """

        # reset the list before updating it
        # self.listWidget_community.clear()

        for _ in range(self.listWidget_community.count()):
            self.listWidget_community.takeItem(0)
        
        self.currentlySelectedId = ""
        self.disableCorrectButtons(True)

        apiurl = f"{URL}/account/maps"
        log("Getting community maps")
        headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
        data = {
            "access": ["public"],
            "name": f"{self.communitySearch}"
        }

        j1 = requests.post(apiurl, json=data, headers=headers)
        if not j1:
            log("getCommunityList failed!")
            return []
        data = json.loads(j1.text)
        for mapdata in data["result"]:
            self.listWidget_community.addItem(convertMapdataToListItem(mapdata))
        
    def onCommunitySearchChange(self, text):
        """ Change the internal state of the community search string """
        self.communitySearch = text
        self.getCommunityList()

    def onCommunityItemClick(self, item):
        self.disableCorrectButtons()
        self.currentlySelectedId = item.data((QtCore.Qt.UserRole)).getData()
        log(f"{item.text()}, data type: {item.data((QtCore.Qt.UserRole)).getType()}, data value: {item.data((QtCore.Qt.UserRole)).getData()}")

        
class EllipsisConnectDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(EllipsisConnectDialog, self).__init__(parent)
        self.setupUi(self)
        self.tabWidget.addTab(MyDriveTab(), "My Drive")
        self.tabWidget.addTab(CommunityTab(), "Community Library")