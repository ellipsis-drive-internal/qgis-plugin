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

TABSFOLDER = os.path.join(os.path.dirname(__file__), "..", "tabs/")
ICONSFOLDER = os.path.join(os.path.dirname(__file__), "..", "icons/")

FOLDERICON = os.path.join(ICONSFOLDER,"folder.svg")
VECTORICON = os.path.join(ICONSFOLDER,"vector.svg")
RASTERICON = os.path.join(ICONSFOLDER,"raster.svg")
ERRORICON = os.path.join(ICONSFOLDER,"error.svg")
RETURNICON = os.path.join(ICONSFOLDER,"return.svg")

URL = 'https://api.ellipsis-drive.com/v1'
DEVURL = f'https://dev.api.ellipsis-drive.com/v1'

MAXPATHLEN = 40

DEBUG = True
DISABLESEARCH = True

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

class ViewMode(Enum):
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

def getErrorLevel(map):
    """ receives a map object (from the api) and returns whether there is something wrong with it or not """
    if "deleted" in map and map["deleted"]:
        return ErrorLevel.DELETED
    elif "isShape" in map and "timestamps" in map and (not map["isShape"] and len(map["timestamps"]) == 0):
        return ErrorLevel.NOTIMESTAMPS
    elif "isShape" in map and "geometryLayers" and (map["isShape"] and len(map["geometryLayers"]) == 0):
        return ErrorLevel.NOLAYERS
    elif "disabled" in map and map["disabled"]:
        return ErrorLevel.DISABLED
    elif "accessLevel" in map and map["accessLevel"] < 200:
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
        item = ListData(Type.FOLDER, mapdata["id"])
    elif mapdata["isShape"]:
        icon = QIcon(VECTORICON)
        item = ListData(Type.SHAPE, mapdata["id"], mapdata["isShape"])
    else:
        icon = QIcon(RASTERICON)
        item = ListData(Type.MAP, mapdata["id"], mapdata["isShape"])

    # now we handle the errorLevel
    if errorLevel == 0 or errorLevel == ErrorLevel.NORMAL or errorLevel == ErrorLevel.WCSACCESS:
        item.setDisableWCS(errorLevel == ErrorLevel.WCSACCESS)
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
        }
        if isFolder and errorLevel != ErrorLevel.NORMAL:
            errmsgdict[ErrorLevel.DELETED] = "Folder deleted"
            errmsgdict[ErrorLevel.DISABLED] = "Folder disabled"

        item = ListData(Type.ERROR)
        newitem.setText(f'{mapdata["name"]} ({errmsgdict[errorLevel]})')
        newitem.setData(QtCore.Qt.UserRole, item)
        newitem.setIcon(QIcon(ERRORICON))
        return newitem
     


def getMetadata(mapid, token):
    """ Returns metadata (in JSON) for a map (by mapid) by calling the Ellipsis API"""
    apiurl = F"{URL}/metadata"
    headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
    headers["Authorization"] = f"Bearer {token}"
    data = {
        "mapId": f"{mapid}",
    }
    j1 = requests.post(apiurl, json=data, headers=headers)
    if not j1:
        log("getMetadata failed!")
        return {}
    data = json.loads(j1.text)
    log(f"metadata of map with id {mapid}")
    jlog(data)
    log("end of metadata")
    return data

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
    def __init__(self, type="none", data="", isaShape=None, shouldDisableWCS=False, extra=None):
        self.type = type
        self.data = data
        self.isaShape = isaShape
        self.shouldDisableWCS = shouldDisableWCS
        self.extra = extra
    
    def setDisableWCS(self, val):
        self.shouldDisableWCS = val

    def getDisableWCS(self):
        return self.shouldDisableWCS

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
