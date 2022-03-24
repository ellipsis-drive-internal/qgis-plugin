""" This file contains functions and constants used by the LogIn/LoggedIn/Community tabs """

import json
import os
from enum import Enum, auto
from threading import Timer
from typing import List

import requests
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from qgis.PyQt.QtWidgets import QListWidgetItem, QMessageBox
from requests.structures import CaseInsensitiveDict

TABSFOLDER = os.path.join(os.path.dirname(__file__), "..", "tabs/")
ICONSFOLDER = os.path.join(os.path.dirname(__file__), "..", "icons/")

FOLDERICON = os.path.join(ICONSFOLDER,"folder.svg")
VECTORICON = os.path.join(ICONSFOLDER,"vector.svg")
RASTERICON = os.path.join(ICONSFOLDER,"raster.svg")
ERRORICON = os.path.join(ICONSFOLDER,"error.svg")
RETURNICON = os.path.join(ICONSFOLDER,"return.svg")

PRODUCTIONURL = 'https://api.ellipsis-drive.com/v1'
DEVURL = 'https://dev.api.ellipsis-drive.com/v1'

SIZEW = 0
SIZEH = 500

URL = PRODUCTIONURL

MAXPATHLEN = 45

DEBUG = True
DISABLESEARCH = False

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

class Type(Enum):
    ROOT = auto()
    FOLDER = auto()
    MAP = auto()
    SHAPE = auto()
    PROTOCOL = auto()
    TIMESTAMP = auto()
    MAPLAYER = auto()
    ACTION = auto()
    RETURN = auto()
    ERROR = auto()
    MESSAGE = auto()

class ViewMode(Enum):
    BASE = auto()
    ROOT = auto()
    FOLDERS = auto()
    SHAPE = auto()
    MAP = auto()
    WMS = auto()
    WMTS = auto()
    WFS = auto()
    WCS = auto()
    SEARCH = auto()

class ViewSubMode(Enum):
    NONE = auto()
    TIMESTAMPS = auto()
    MAPLAYERS = auto()
    GEOMETRYLAYERS = auto()
    INFOLDER = auto()

class ErrorLevel(Enum):
    NORMAL = 1
    DISABLED = 2
    NOLAYERS = 3
    NOTIMESTAMPS = 4
    DELETED = 5
    WCSACCESS = 6

rootName = {
    "myMaps": "My Drive",
    "shared": "Shared",
    "favorites": "Favorites",
}

nameRoot = {
    "My Drive": "myMaps",
    "Shared": "shared",
    "Favorites": "favorites",
}

protToString = {
    ViewMode.WMS: "WMS",
    ViewMode.WMTS: "WMTS",
    ViewMode.WCS: "WCS",
    ViewMode.WFS: "WFS",
}

stringToProt = {
    "WMS": ViewMode.WMS,
    "WMTS": ViewMode.WMTS,
    "WCS": ViewMode.WCS,
    "WFS": ViewMode.WFS,
}

def getRootName(root):
    if root in rootName:
        return rootName[root]
    return root

def getUserData(token):
    log("Getting user data")
    apiurl = f"{URL}/account/info"
    headers = CaseInsensitiveDict()
    headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(apiurl, headers=headers)
    if (resp):
        data = resp.json()
        jlog(data)
        log("getUserData success")
        return True, data
    log("getUserData failed")
    log(resp.reason)
    return False, None

def makeRequest(url, headers, data=None):
        log(f"Requesting {url}")
        success = True
        try:
            j1 = requests.post(f"{URL}{url}", json=data, headers=headers)
            if not j1:
                log("Request failed!")
                log(f"{URL}{url}")
                log(data)
                log(headers)
                log(j1)
                log(j1.reason)
                success = False
            else:
                log("Request successful")
                log(f"{URL}{url}")
                log(data)
                log(headers)
                log(j1)
                success = True
            return success, json.loads(j1.text)
        except requests.ConnectionError:
            displayMessageBox("Request failed", "Please check your internet connection")
            return False, None

@debounce(0.5)
def displayMessageBox(title, text):
    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()

def connected_to_internet(url=URL, timeout=5):
    try:
        _ = requests.head(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        log("No internet connection available.")
    return False

def getErrorLevel(map):
    """ receives a map object (from the api) and returns whether there is something wrong with it or not """
    if map["deleted"]:
        return ErrorLevel.DELETED
    elif map["type"] == "map" and len(map["timestamps"]) == 0:
        return ErrorLevel.NOTIMESTAMPS
    elif map["type"] == "shape" and len(map["geometryLayers"]) == 0:
        return ErrorLevel.NOLAYERS
    elif map["disabled"]:
        return ErrorLevel.DISABLED
    elif map["yourAccess"]["accessLevel"] < 200:
        return ErrorLevel.WCSACCESS
    else:
        return ErrorLevel.NORMAL

def toListItem(type, text, data = None, extra = None, icon = None):
    """ same as convertMapdataToListItem, but for timestamps and maplayers. should be refactored sometime """
    listitem = QListWidgetItem()
    listdata = ListData(type, data, extra = extra)
    listitem.setData(QtCore.Qt.UserRole, listdata)
    listitem.setText(text)
    if not icon is None:
        listitem.setIcon(QIcon(icon))
    return listitem


def convertMapdataToListItem(mapdata, isFolder = True, isShape = False, isMap = False, errorLevel = ErrorLevel.NORMAL):
    """ turns a mapdata object into a listwidgetitem, depending on what type of object it is and its errorlevel """
    newitem = QListWidgetItem()
    icon = QIcon()
    if isShape:
        icon = QIcon(VECTORICON)
        item = ListData(Type.SHAPE, mapdata["id"], True)
    elif isMap:
        icon= QIcon(RASTERICON)
        item = ListData(Type.MAP, mapdata["id"], False)
    elif isFolder:
        icon = QIcon(FOLDERICON)
        item = ListData(Type.FOLDER, mapdata["id"], extra=mapdata["name"])
    elif mapdata["type"] == "shape":
        icon = QIcon(VECTORICON)
        item = ListData(Type.SHAPE, mapdata["id"], True)
    else:
        icon = QIcon(RASTERICON)
        item = ListData(Type.MAP, mapdata["id"], False)

    # now we handle the errorLevel
    if errorLevel == 0 or errorLevel == ErrorLevel.NORMAL:
        newitem.setText(mapdata["name"])
        newitem.setData(QtCore.Qt.UserRole, item)
        newitem.setIcon(icon)
        return newitem
    else:
        errmsgdict = {
            ErrorLevel.DELETED: "Project deleted",
            ErrorLevel.NOTIMESTAMPS: "Map has no timestamps",
            ErrorLevel.NOLAYERS: "Shape has no layers",
            ErrorLevel.DISABLED: "Project disabled",
            ErrorLevel.WCSACCESS: "Access level too low"
        }
        if isFolder and errorLevel != ErrorLevel.NORMAL:
            errmsgdict[ErrorLevel.DELETED] = "Folder deleted"
            errmsgdict[ErrorLevel.DISABLED] = "Folder disabled"

        item = ListData(Type.ERROR)
        newitem.setText(f'{mapdata["name"]} ({errmsgdict[errorLevel]})')
        newitem.setData(QtCore.Qt.UserRole, item)
        newitem.setIcon(QIcon(ERRORICON))
        return newitem

def getUrl(mode, mapId, token = "empty"):
    """ constructs the url and copies it to the clipboard"""
    theurl = ""
    if token == "empty":
        theurl = f"{URL}/{mode}/{mapId}"
    else:
        theurl = f"{URL}/{mode}/{mapId}/{token}"
    log(f"getUrl: {theurl}")
    return theurl

class ListData:
    """ Class used for objects in the QList of the EllipsisConnect plugin """
    def __init__(self, type="none", data="", isaShape=None, extra=None):
        self.type = type
        self.data = data
        self.isaShape = isaShape
        self.extra = extra

    def setExtra(self, extra):
        self.extra = extra
    
    def getExtra(self):
        return self.extra

    def setData(self, type, data, isaShape):
        self.type = type
        self.data = data
        self.isaShape = isaShape

    def getData(self):
        return self.data

    def getType(self):
        return self.type
    
    def isShape(self):
        return self.isaShape

    def isEmpty(self):
        return self.type == "none" and self.data == ""

def log(text):
    """ only prints when DEBUG is True """
    if DEBUG:
        print(text)

def jlog(obj):
    """ logs a JSON object"""
    text = json.dumps(obj, sort_keys=True, indent=4)
    log(text)
