import os
import json
import requests
from threading import Timer
from qgis.PyQt.QtWidgets import QListWidgetItem, QMessageBox
from PyQt5 import QtCore

from enum import Enum

from PyQt5.QtGui import QIcon

TABSFOLDER = os.path.join(os.path.dirname(__file__), "tabs/")
ICONSFOLDER = os.path.join(os.path.dirname(__file__), "icons/")

FOLDERICON = os.path.join(ICONSFOLDER,"folder.svg")
VECTORICON = os.path.join(ICONSFOLDER,"vector.svg")
RASTERICON = os.path.join(ICONSFOLDER,"raster.svg")
ERRORICON = os.path.join(ICONSFOLDER,"error.svg")

URL = 'https://api.ellipsis-drive.com/v1'
#URL = 'http://dev.api.ellipsis-drive.com/v1'

# for reference
# API = 'https://api.ellipsis-drive.com/v1'
DEVAPI = 'http://dev.api.ellipsis-drive.com/v1'

DEBUG = True

class ErrorLevel(Enum):
    NORMAL = 1
    DISABLED = 2
    NOLAYERS = 3
    NOTIMESTAMPS = 4
    DELETED = 5
    WCSACCESS = 6

# TODO
# - pagination of folders and maps
# - Trash folder?
# - properly allign the 'My Drive' and 'Community Library' tabs (buttons should remain stationary when switching)
# - create seperate files for the tabs
# - clean up the file
# - when the path becomes too long, a part is cut-off: find fix for this

def getErrorLevel(map):
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

def convertMapdataToListItem(mapdata, isFolder = True, isShape = False, isMap = False, errorLevel = ErrorLevel.NORMAL):
    # TODO other object as data, maybe the entire mapdata object?
    newitem = QListWidgetItem()
    icon = QIcon()
    if isShape:
        icon = QIcon(VECTORICON)
        item = ListData("id", mapdata["id"], True)
    elif isMap:
        icon= QIcon(RASTERICON)
        item = ListData("id", mapdata["id"], False)
    elif isFolder:
        icon = QIcon(FOLDERICON)
        item = ListData("id", mapdata["id"])
    elif mapdata["isShape"]:
        icon = QIcon(VECTORICON)
        item = ListData("id", mapdata["id"], mapdata["isShape"])
    else:
        icon = QIcon(RASTERICON)
        item = ListData("id", mapdata["id"], mapdata["isShape"])

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
        item = ListData("error")
        newitem.setText(f'{mapdata["name"]} ({errmsgdict[errorLevel]})')
        newitem.setData(QtCore.Qt.UserRole, item)
        newitem.setIcon(QIcon(ERRORICON))
        return newitem
     


def getMetadata(mapid):
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
    # we no longer have a pop up, but we might use this code sometime in the future
    try:
        if PYCLIP:
            pyclip.copy(theurl)
            msg = QMessageBox()
            msg.setWindowTitle("Success")
            msg.setIcon(QMessageBox.Information)
            msg.setText("Url copied to clipboard!")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
        else:
            msg = QInputDialog()
            msg.setWindowTitle("Success")
            msg.setLabelText(f"Please copy the following url.")
            msg.setTextValue(theurl)
            msg.setOption(QInputDialog.NoButtons)
            msg.exec_()
    except:
        msg = QInputDialog()
        msg.setWindowTitle("Success")
        msg.setLabelText(f"Please copy the following url.")
        msg.setTextValue(theurl)
        msg.setOption(QInputDialog.NoButtons)
        msg.exec_()

class ListData:
    """ Class used for objects in the QList of the EllipsisConnect plugin """
    def __init__(self, type="none", data="", isaShape=None, shouldDisableWCS=False):
        self.type = type
        self.data = data
        self.isaShape = isaShape
        self.shouldDisableWCS = shouldDisableWCS
    
    def setDisableWCS(self, val):
        self.shouldDisableWCS = val

    def getDisableWCS(self):
        return self.shouldDisableWCS

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