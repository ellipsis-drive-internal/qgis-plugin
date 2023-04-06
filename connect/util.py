""" This file contains functions and constants used by the LogIn/LoggedIn/Community tabs """

from email import header
import json
import os
from enum import Enum, auto, unique
from threading import Timer
from urllib import parse

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

V1URL = 'https://api.ellipsis-drive.com/v1'
V2URL = 'https://api.ellipsis-drive.com/v2'
V3URL = 'https://api.ellipsis-drive.com/v3'

SIZEW = 0
SIZEH = 500

URL = V3URL

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
    RASTER = auto()
    VECTOR = auto()
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
    VECTOR = auto()
    RASTER = auto()
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
    """ enum to describe the error level, NORMAL means nothing wrong with the layer """
    NORMAL = auto()
    DISABLED = auto()
    NOLAYERS = auto()
    NOTIMESTAMPS = auto()
    DELETED = auto()
    WCSACCESS = auto()
    NOACCESS = auto()
    TRASHED = auto()
    RELOCATING = auto()
    REINDEXING = auto()
    NOUPLOADS = auto()
    ACTIVATING = auto()
    PAUSING = auto()
    NOACTIVETIMESTAMPS = auto()


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
    "myDrive": "My Drive",
    "sharedWithMe": "Shared",
    "favorites": "Favorites",
}

nameRoot = {
    "My Drive": "myDrive",
    "Shared": "sharedWithMe",
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
    """ retrieves user data from API """
    log("Getting user data")
    headers = CaseInsensitiveDict()
    headers["Authorization"] = f"Bearer {token}"
    return makeRequest("/account", headers=headers)

def GET(url, headers, data):
    """ make GET request """
    coded_data = ""
    CALLURL = f"{url}"
    if data is not None:
        coded_data = parse.urlencode(query=data)
        CALLURL = f"{url}?{coded_data}"
    log(f"Callurl = {CALLURL}")
    return requests.get(CALLURL, headers=headers)

def POST(url, headers, data):
    """ make POST request """
    log("POST")
    log(headers)
    log(data)
    return requests.post(url, json=data, headers=headers)

def makeRequest(url, headers, data=None, version=3, method="GET"):
    """ makes api requests, and returns a tuple of (resulttype, result/None) """

    log("makeRequest")
    log(headers)
    log(data)

    def req(url, h, d):
        if method == "GET":
            return GET(url, headers=h, data=d)
        else: # method == "POST"
            return POST(url, headers=h, data=d)

    if version == 1:
        APIURL = V1URL
    elif version == 2:
        APIURL = V2URL
    elif version == 3:
        APIURL = V3URL
    else:
        APIURL = URL

    FULLURL = f"{APIURL}{url}"

    log(f"Requesting '{FULLURL}'")
    log(method)
    log(data)
    log(headers)

    FULLURL = f"{FULLURL}"

    success = ReqType.SUCC
    try:
        j1 = req(f"{FULLURL}", h=headers, d=data)
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


# TODO rewrite this


def funcFind(pred, iter):
    """ python version of JS find function"""
    return next(filter(pred, iter), None)

def findReason(reason, iter):
    return funcFind(lambda x: isValidTimestamp(x)[1] == reason, iter) is not None

def isValidTimestamp(t):
    """ returns true if timestamp is valid """
    if t["status"] != "active":
        return (False, "Timestamp not active")
    if t["availability"]["blocked"]:
        return (False, t["availability"]["reason"])
    return (True, "")

def isValidMap(m):
    """ checks if a layer is valid or not """
    # m: the layer
    # t: type of the layer
    # ts: timestamps of the layer

    t = m["type"]

    if not m:
        return (False, "No Layer")
    if m["type"] != "raster" and m["type"] != "vector":
        return (True, "")
    if m["user"]["disabled"]:
        return (False, "Layer disabled")
    if m["trashed"]:
        return (False, "Layer trashed")
    if m["yourAccess"]["accessLevel"] == 0:
        return (False, "No access")
    
    ts = m[t]["timestamps"]

    if len(list(filter(lambda x: isValidTimestamp(x)[0] , ts))) == 0:
        if findReason("relocation", ts):
            return (False, "Relocating layer")
        elif findReason("reindexing", ts):
            return (False, "Reindexing layer")
        elif t == "raster" and len(list(filter(lambda x: x["totalSize"] > 0, ts))) == 0:
            return (False, "No uploads")
        elif findReason("activating", ts):
            return (False, "Activating files")
        elif findReason("pausing", ts):
            return (False, "Pausing files")
        elif findReason("paused", ts):
            return (False, "No active timestamps")
        else:
            return (False, "No timestamps")

    return (True, "")

""" 
JS version
  isValidMap = (m) => {
    const t = m.type;
    if (!m) {
      return { available: false, reason: "No Layer" };
    }
    if (m.type !== "raster" && m.type !== "vector") {
      return { available: true };
    }
    if (m.disabled) {
      return { available: false, reason: "Layer disabled" };
    }
    if (m.trashed) {
      return { available: false, reason: "Layer trashed" };
    }
    if (m.yourAccess.accessLevel === 0) {
      return { available: false, reason: "No access" };
    }
    if (
      m[t].timestamps.filter((t) => this.isValidTimestamp(t, m).available)
        .length === 0
    ) {
      if (
        m[t].timestamps.find((t) => t.availability?.reason === "relocation")
      ) {
        return { available: false, reason: "Relocating layer" };
      } else if (
        m[t].timestamps.find((t) => t.availability?.reason === "reindexing")
      ) {
        return { available: false, reason: "Reindexing layer" };
      } else if (
        t === "raster" &&
        m[t].timestamps.filter((t) => t.totalSize > 0).length === 0
      ) {
        return { available: false, reason: "No uploads" };
      } else if (m[t].timestamps.find((t) => t.status === "activating")) {
        return { available: false, reason: "Activating files" };
      } else if (m[t].timestamps.find((t) => t.status === "pausing")) {
        return { available: false, reason: "Pausing files" };
      } else if (m[t].timestamps.find((t) => t.status === "paused")) {
        return { available: false, reason: "No active timestamps" };
      } else {
        return { available: false, reason: "No timestamps" };
      }
    }
    return { available: true };
  };
"""

def toListItem(type, text, data = None, extra = None, icon = None):
    """ same as convertMapdataToListItem, but for timestamps and maplayers. should be refactored sometime """
    listitem = QListWidgetItem()
    listdata = ListData(type, data, extra = extra)
    listitem.setData(QtCore.Qt.UserRole, listdata)
    listitem.setText(text)
    if icon is not None:
        listitem.setIcon(QIcon(icon))
    return listitem


def convertMapdataToListItem(obj, objtype):
    """ turns a mapdata object into a listwidgetitem, depending on what type of object it is """
    newitem = QListWidgetItem()
    icon = QIcon()

    isValid, errmsg = isValidMap(obj)

    if objtype == Type.VECTOR:
        icon = QIcon(VECTORICON)
        item = ListData(Type.VECTOR, obj["id"], True)
    elif objtype == Type.RASTER:
        icon= QIcon(RASTERICON)
        item = ListData(Type.RASTER, obj["id"], False)
    elif objtype == Type.FOLDER:
        icon = QIcon(FOLDERICON)
        item = ListData(Type.FOLDER, obj["id"], extra=obj["name"])
    elif obj["type"] == "vector":
        icon = QIcon(VECTORICON)
        item = ListData(Type.VECTOR, obj["id"], True)
    else:
        icon = QIcon(RASTERICON)
        item = ListData(Type.RASTER, obj["id"], False)

    # now we handle the errorLevel
    if isValid:
        newitem.setText(obj["name"])
        newitem.setData(QtCore.Qt.UserRole, item)
        newitem.setIcon(icon)
        return newitem
    else:
        item = ListData(Type.ERROR)
        newitem.setText(f'{obj["name"]} ({errmsg})')
        newitem.setData(QtCore.Qt.UserRole, item)
        newitem.setIcon(QIcon(ERRORICON))
        return newitem
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
