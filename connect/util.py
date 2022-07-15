""" This file contains functions and constants used by the LogIn/LoggedIn/Community tabs """

import json
import os
from enum import Enum, auto, unique
from threading import Timer

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
REFRESHICON = os.path.join(ICONSFOLDER,"refresh.svg")

PRODUCTIONURL = 'https://api.ellipsis-drive.com/v1'
DEVURL = 'https://dev.api.ellipsis-drive.com/v1'

V1URL = 'https://api.ellipsis-drive.com/v1'
V2URL = 'https://api.ellipsis-drive.com/v2'

SIZEW = 0
SIZEH = 500

URL = V1URL

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

@unique
class Type(Enum):
    """ enum that describes what type an item has """
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

@unique
class ViewMode(Enum):
    """ describes what we are currently viewing """
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

@unique
class ViewSubMode(Enum):
    """ inside a single viewmode there exists submodes, this represents which one we are viewing """
    NONE = auto()
    TIMESTAMPS = auto()
    MAPLAYERS = auto()
    GEOMETRYLAYERS = auto()
    INFOLDER = auto()

@unique
class ErrorLevel(Enum):
    """ enum to describe the error level, NORMAL means nothing wrong with the map """
    NORMAL = auto()
    DISABLED = auto()
    NOLAYERS = auto()
    NOTIMESTAMPS = auto()
    DELETED = auto()
    WCSACCESS = auto()
    NOACCESS = auto()

@unique
class ReqType(Enum):
    """ enum describing the type of request result """
    SUCC = auto()
    FAIL = auto()
    CONNERR = auto()
    AUTHERR = auto()

    def __bool__(self):
        return self == ReqType.SUCC

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
    """ convert a root 'name' to its representing string """
    if root in rootName:
        return rootName[root]
    return root

def getUserData(token):
    """ TODO this should use makeRequest """
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

def makeRequest(url, headers, data=None, version=0):
    """ makes api requests, and returns a tuple of (resulttype, result/None) """

    if version == 0:
        APIURL = URL
    elif version == 1:
        APIURL = V1URL
    elif version == 2:
        APIURL = V2URL

    FULLURL = f"{APIURL}{url}"   

    log(f"Requesting '{FULLURL}'")
    log(data)
    log(headers)

    success = ReqType.SUCC
    try:
        j1 = requests.post(f"{FULLURL}", json=data, headers=headers)
        if not j1:
            log("Request failed!")
            log(f"{FULLURL}")
            log(data)
            log(headers)
            log(j1)
            log(j1.reason)
            success = ReqType.FAIL
        
            if j1.status_code == 401:
                # token is probably expired
                log("token expired")
                return ReqType.AUTHERR, None
        else:
            log("Request successful")
            log(f"{FULLURL}")
            log(data)
            log(headers)
            log(j1)
            success = ReqType.SUCC
        return success, json.loads(j1.text)
    except requests.ConnectionError:
        # displayMessageBox("Request failed", "Please check your internet connection")
        return ReqType.CONNERR, None

def getMessageBox(title, text):
    """ utility function that returns a messagebox """
    msg = QMessageBox()
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.Ok)
    return msg

def connected_to_internet(url=URL, timeout=5):
    """ check for connection error """
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
    elif map["yourAccess"]["accessLevel"] == 0:
        return ErrorLevel.NOACCESS
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
    if icon is not None:
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
    if errorLevel == 0 or errorLevel == ErrorLevel.NORMAL or errorLevel == ErrorLevel.WCSACCESS:
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
            ErrorLevel.WCSACCESS: "Access level too low",
            ErrorLevel.NOACCESS: "Access level is 0"
        }
        if isFolder and errorLevel != ErrorLevel.NORMAL:
            errmsgdict[ErrorLevel.DELETED] = "Folder deleted"
            errmsgdict[ErrorLevel.DISABLED] = "Folder disabled"

        item = ListData(Type.ERROR)
        newitem.setText(f'{mapdata["name"]} ({errmsgdict[errorLevel]})')
        newitem.setData(QtCore.Qt.UserRole, item)
        newitem.setIcon(QIcon(ERRORICON))
        return newitem

def getUrl(mode, mapId, token = None):
    """ constructs the url and copies it to the clipboard"""
    theurl = ""
    if token is None:
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
        """ setter """
        self.extra = extra
    
    def getExtra(self):
        """ getter """
        return self.extra

    def setData(self, type, data, isaShape):
        """ setter """
        self.type = type
        self.data = data
        self.isaShape = isaShape

    def getData(self):
        """ getter """
        return self.data

    def getType(self):
        """ getter """
        return self.type
    
    def isShape(self):
        """ getter """
        return self.isaShape

    def isEmpty(self):
        """ check if data is empty """
        return self.type == "none" and self.data == ""

def log(text):
    """ only prints when DEBUG is True """
    if DEBUG:
        print(text)

def jlog(obj):
    """ logs a JSON object"""
    text = json.dumps(obj, sort_keys=True, indent=4)
    log(text)
