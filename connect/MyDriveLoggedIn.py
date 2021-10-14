import json
import os
import urllib

from copy import copy

import requests
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog
from qgis.core import *
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtWidgets import QListWidgetItem, QMessageBox
from requests import api
from qgis.utils import iface

from .util import *

def initialSubMode(str):
    return ViewSubMode.GEOMETRYLAYERS if str == "WFS" else ViewSubMode.TIMESTAMPS

def mapViewMode(str):
    if str == "WMS":
        return ViewMode.WMS
    if str == "WMTS":
        return ViewMode.WMTS
    if str == "WFS":
        return ViewMode.WFS
    if str == "WCS":
        return ViewMode.WCS

class MyDriveLoggedInTab(QDialog):
    """ The LoggedIn tab, giving users access to their drive. Used in combination with the MyDriveTab and the MyDriveLoginTab"""
    logoutSignal = pyqtSignal()
    def __init__(self):
        super(MyDriveLoggedInTab, self).__init__()
        uic.loadUi(os.path.join(TABSFOLDER, "MyDriveLoggedInTab.ui"), self)
        self.loginToken = ""
        self.loggedIn = False
        self.userInfo = {}
        self.level = 0
        self.path = "/"
        self.folderStack = []
        self.currentlySelectedMap = None
        self.currentlySelectedId = ""
        #self.searching = False
        self.searchText = ""
        self.currentMetaData = None
        self.currentTimestamp = None
        self.currentMode = ViewMode.ROOT
        self.previousMode = None
        self.currentSubMode = ViewSubMode.NONE
        self.currentItem = None
        self.previousItem = None
        self.currentFolderId = None
        self.currentZoom = None
        self.stateBeforeSearch = {}

        self.listWidget_mydrive.itemDoubleClicked.connect(self.onListWidgetDoubleClick)
        self.listWidget_mydrive.itemClicked.connect(self.onListWidgetClick)

        self.pushButton_logout.clicked.connect(self.logOut)
        self.pushButton_stopsearch.clicked.connect(self.stopSearch)
        self.pushButton_stopsearch.setEnabled(False)

        if not DISABLESEARCH:
            self.lineEdit_search.textEdited.connect(self.onSearchChange)

        self.settings = QSettings('Ellipsis Drive', 'Ellipsis Drive Connect')
        self.fillListWidget()

    def addReturnItem(self):
        self.listWidget_mydrive.addItem(toListItem(Type.RETURN, "..", icon=RETURNICON))

    def getPathInfo(self, id):
        roots = ["myMaps", "shared", "favorites"]
        data1 = None
        theroot = None
        for root in roots:
            apiurl = f"{URL}/path/info"

            headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
            if (not self.loginToken == ""):
                headers["Authorization"] = f"Bearer {self.loginToken}"
            data = {
                "pathId": id,
                "root": root
            }

            j1 = requests.post(apiurl, json=data, headers=headers)

            if j1:
                data1 = json.loads(j1.text)
                theroot = root
        if data1 is None:
            log("getPathInfo failed")
        else:
            return [theroot, data1["path"]]

    def onListWidgetDoubleClick(self, item):
        itemdata = item.data((QtCore.Qt.UserRole)).getData()
        itemtype = item.data((QtCore.Qt.UserRole)).getType()
        """ handler for clicks on items in the folder listwidget """
        log(f"Clicked on type {itemtype}, current modi: {self.currentMode}, {self.currentSubMode}")

        # if we're searching, the regular rules don't apply
        if self.currentMode == ViewMode.SEARCH:
            root, folderpath = self.getPathInfo(itemdata)
            jlog(folderpath)
            folderpath.reverse()
            self.setPath(f"/{root}")
            self.folderStack = [root]
            self.level = 1
            
            first = True
            for folder in folderpath:
                if first and not itemtype == Type.FOLDER:
                    self.addToPath(folder["name"])
                    continue
                self.folderStack.append(folder["id"])
                self.addToPath(folder["name"])
                self.level += 1
                first = False    

            if itemtype == Type.FOLDER:
                self.currentMode = ViewMode.FOLDERS
                self.currentSubMode = ViewSubMode.NONE
            else:
                self.currentMetaData = getMetadata(itemdata, self.loginToken)
                self.currentMode = ViewMode.SHAPE
                self.currentSubMode = ViewSubMode.NONE
                if itemtype == Type.MAP:
                    self.currentMode = ViewMode.MAP
                self.currentItem = item

            self.lineEdit_search.clear()
            self.pushButton_stopsearch.setEnabled(False)
            self.fillListWidget()
            return

        if itemtype == Type.ERROR:
            return

        self.previousItem = self.currentItem
        self.currentItem = item

        if itemtype == Type.RETURN:

            if self.currentMode == ViewMode.FOLDERS:
                self.onPrevious()

            elif self.currentMode == ViewMode.MAP or self.currentMode == ViewMode.SHAPE:
                self.currentMode = ViewMode.FOLDERS
                self.removeFromPath()

            elif self.currentMode == ViewMode.WFS:
                self.currentMode = ViewMode.SHAPE
                self.currentSubMode = ViewSubMode.NONE
                self.removeFromPath()

            elif self.currentMode == ViewMode.WCS or self.currentMode == ViewMode.WMS or self.currentMode == ViewMode.WMTS:
                self.currentMode = ViewMode.MAP
                self.currentSubMode = ViewSubMode.NONE
                self.removeFromPath()
        
        elif self.currentMode == ViewMode.ROOT:
            self.onNext()

        elif self.currentMode == ViewMode.FOLDERS:

            if  itemtype == Type.FOLDER:
                self.onNext()

            elif itemtype == Type.SHAPE or itemtype == Type.MAP:
                self.currentMetaData = getMetadata(itemdata, self.loginToken)
                self.addToPath(self.currentMetaData["name"])
                if itemtype == Type.SHAPE:
                    self.currentMode = ViewMode.SHAPE
                else:
                    self.currentMode = ViewMode.MAP

        elif self.currentMode == ViewMode.SHAPE or self.currentMode == ViewMode.MAP:
            self.currentMode = mapViewMode(itemdata)
            self.currentSubMode = initialSubMode(itemdata)
            self.addToPath(itemdata)

        elif self.currentMode == ViewMode.WMS:
            self.WMSDoubleClick(item)

        elif self.currentMode == ViewMode.WMTS:
            self.WMTSDoubleClick(item)

        elif self.currentMode == ViewMode.WFS:
            self.WFSDoubleClick(item)

        elif self.currentMode == ViewMode.WCS:
            self.WCSDoubleClick(item)

        self.fillListWidget()

    def fillListWidget(self):
        log(f"fillListWidget called with modi: {self.currentMode} and {self.currentSubMode}")
        self.clearListWidget()

        if (self.currentMode == ViewMode.ROOT):
            self.populateListWithRoot()
            return

        self.addReturnItem()
        if (self.currentMode == ViewMode.FOLDERS):
            self.getFolder(self.folderStack[-1], isRoot=(self.level == 1))
            return

        item = self.currentItem.data((QtCore.Qt.UserRole))
        log(self.currentItem)

        if (self.currentMode == ViewMode.WMS or self.currentMode == ViewMode.WMTS or self.currentMode == ViewMode.WCS):
            
            if (self.currentSubMode == ViewSubMode.TIMESTAMPS):
                timestamps = self.currentMetaData["timestamps"]
                maplayers = self.currentMetaData["mapLayers"]
                for timestamp in timestamps:
                    self.listWidget_mydrive.addItem(toListItem(Type.TIMESTAMP, timestamp["dateTo"], data=timestamp, extra=maplayers))

            elif (self.currentSubMode == ViewSubMode.MAPLAYERS):
                self.currentTimestamp = item.getData()
                mapLayers = item.getExtra()
                for mapLayer in mapLayers:
                    self.listWidget_mydrive.addItem(toListItem(Type.MAPLAYER, mapLayer["name"], mapLayer))

        elif (self.currentMode == ViewMode.MAP or self.currentMode == ViewMode.SHAPE):
            self.populateListWithProtocols(Type.MAP if self.currentMode == ViewMode.MAP else Type.SHAPE)
        elif (self.currentMode == ViewMode.WFS):
            geometryLayers = self.currentMetaData["geometryLayers"]
            for geometryLayer in geometryLayers:
                self.listWidget_mydrive.addItem(toListItem(Type.TIMESTAMP, geometryLayer["name"], data=geometryLayer))

        elif (self.currentMode == ViewMode.WCS):
            timestamps = self.currentMetaData["timestamps"]
            for timestamp in timestamps:
                self.listWidget_mydrive.addItem(toListItem(Type.TIMESTAMP, timestamp["dateTo"], data=timestamp))

    def WMSDoubleClick(self, item):
        itemtype = item.data((QtCore.Qt.UserRole)).getType()
        itemdata = item.data((QtCore.Qt.UserRole)).getData()

        if itemtype == Type.TIMESTAMP:
            self.currentSubMode = ViewSubMode.MAPLAYERS
            self.previousItem = self.currentItem
            self.currentItem = item

        elif itemtype == Type.MAPLAYER:
            layerid = itemdata["id"]
            ids = f"{self.currentTimestamp['id']}_{layerid}"
            mapid = self.currentMetaData["id"]
            theurl = F"{URL}/wms/{mapid}/{self.loginToken}"
            actualurl = f"CRS=EPSG:3857&format=image/png&layers={ids}&styles&url={theurl}"
            log("WMS")
            log(actualurl)
            #rlayer = QgsRasterLayer(actualurl, f"{self.currentTimestamp['dateTo']}_{itemdata['name']}", 'WMS')
            iface.addRasterLayer(actualurl, f"{self.currentTimestamp['dateTo']}_{itemdata['name']}", 'wms')
            
            #if not rlayer.isValid():
            #    log("Layer failed to load!") 
            #else:
            #    QgsProject.instance().addMapLayer(rlayer)
            # we have to restore the previous item as the current item, to maintain the view (instead of 'opening' the layer)
            self.currentItem = self.previousItem

    def WMTSDoubleClick(self, item):
        # working example:
        # qgis.utils.iface.addRasterLayer("tileMatrixSet=matrix_18&crs=EPSG:3857&layers=1ebaff6b-96e7-4b47-9c97-099b11381158_3422997c-e7d6-4c70-818b-56bbad871f56&styles=&format=image/png&url=https://api.ellipsis-drive.com/v1/wmts/6b204b1b-f12c-43fb-ac24-b07896391ebe", "wmts master example","wms" )

        itemtype = item.data((QtCore.Qt.UserRole)).getType()
        itemdata = item.data((QtCore.Qt.UserRole)).getData()

        if itemtype == Type.TIMESTAMP:
            self.currentSubMode = ViewSubMode.MAPLAYERS
            self.currentItem = item
            log("WMTSDoubleClick, should be a timestamp:")
            self.currentZoom = itemdata["zoom"]

        elif itemtype == Type.MAPLAYER:
            jlog(self.currentMetaData)
            jlog(itemdata)
            data = itemdata
            ids = f"{self.currentTimestamp['id']}_{data['id']}"
            mapid = self.currentMetaData["id"]
            theurl = F"{URL}/wmts/{mapid}/{self.loginToken}"
            actualurl = f"tileMatrixSet=matrix_{self.currentZoom}&crs=EPSG:3857&layers={ids}&styles=&format=image/png&url={theurl}"
            log(actualurl)
            #rlayer = QgsRasterLayer(actualurl, f"{self.currentTimestamp['dateTo']}_{itemdata['name']}", 'WMS')
            
            iface.addRasterLayer(actualurl, f"{self.currentTimestamp['dateTo']}_{itemdata['name']}", 'wms')

            #if not rlayer.isValid():
            #    log("Layer failed to load!") 
            #else:
            #    QgsProject.instance().addMapLayer(rlayer)
            # same as above
            self.currentItem = self.previousItem


    def WFSDoubleClick(self, item):
        text = item.text()
        itemdata = item.data((QtCore.Qt.UserRole))
        #id = item.data((QtCore.Qt.UserRole)).getData()
        mapid = self.currentMetaData["id"]
        theurl = F"{URL}/wfs/{mapid}?"

        #typename moet dus layerId_{layer ID zijn}
        params = {
            'service': 'WFS',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typename': f'layerId_{itemdata.getData()["id"]}',
            'srsname': "EPSG:4326"
        }
        uri = f'{theurl}' + urllib.parse.unquote(urllib.parse.urlencode(params))
        log(uri)
        rlayer = QgsVectorLayer(uri, text, 'wfs')

        if not rlayer.isValid():
            log("Layer failed to load!") 
        else:
            QgsProject.instance().addMapLayer(rlayer)

    def WCSDoubleClick(self, item):
        itemdata = item.data((QtCore.Qt.UserRole))

        def makeWCSuri( url, layer ):
            params = {  'dpiMode': 7 , 'identifier': layer,'url': url.split('?')[0]  }
            uri = urllib.parse.unquote( urllib.parse.urlencode(params)  )
            return uri

        
        timestampid = itemdata.getData()["id"]

        mapid = self.currentMetaData["id"]
        theurl = F"{URL}/wcs/{mapid}"
        
        wcsUri = makeWCSuri(theurl, timestampid )
        rlayer = QgsRasterLayer(wcsUri, f'{self.currentMetaData["name"]}', 'wcs')
        if not rlayer.isValid():
            log("Layer failed to load!") 
        else:
            QgsProject.instance().addMapLayer(rlayer)
        # same as above
        self.currentItem = self.previousItem

    def stopSearch(self):
        """ handler for the Stop Search button: does what it says it does """
        self.pushButton_stopsearch.setEnabled(False)
        self.lineEdit_search.clear()
        self.setCurrentState(self.stateBeforeSearch)
        self.searchText = ""

    def resetState(self):
        """ helper function to reset our state (used when logging out) """
        self.clearListWidget()
        self.loginToken = ""
        self.loggedIn = False
        self.userInfo = {}
        self.level = 0
        self.path = "/"
        self.folderStack = []
        self.currentlySelectedMap = None
        self.currentlySelectedId = ""
        self.searchText = ""
        self.currentMetaData = None
        self.currentTimestamp = None
        self.currentMode = ViewMode.ROOT
        self.previousMode = None
        self.currentSubMode = ViewSubMode.NONE
        self.currentItem = None
        self.previousItem = None
        self.currentFolderId = None
        self.currentZoom = None
        self.stateBeforeSearch = {}
        self.setPath(self.path)

    @debounce(0.5)
    def performSearch(self):
        """ actually perform the search, using self.searchText as the string """
        if not self.currentMode == ViewMode.SEARCH:
            return
        log("performing search")

        self.clearListWidget()
        #self.currentlySelectedId = ""

        apiurl1 = f"{URL}/account/maps"
        apiurl2 = f"{URL}/account/shapes"
        apiurl3 = f"{URL}/account/folders"

        headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
        if (not self.loginToken == ""):
            headers["Authorization"] = f"Bearer {self.loginToken}"
        data = {
            "access": ["owned", "subscribed", "favorited"],
            "name": f"{self.searchText}",
        }

        j1 = requests.post(apiurl1, json=data, headers=headers)
        j2 = requests.post(apiurl2, json=data, headers=headers)
        j3 = requests.post(apiurl3, json=data, headers=headers)

        if not j1 or not j2 or not j3:
            log("performSearch failed!")
            log("Data:")
            log(data)
            log("Headers:")
            log(headers)
            if not j1:
                log("Maps:")
                log(apiurl1)
                log(j1.content)
            if not j2:
                log("Shapes:")
                log(apiurl2)
                log(j2.content)
            if not j3:
                log("Folders:")
                log(apiurl3)
                log(j3.content)

        data1 = json.loads(j1.text)
        data2 = json.loads(j2.text)
        data3 = json.loads(j3.text)

        #folders first

        [self.listWidget_mydrive.addItem(convertMapdataToListItem(folder, True, errorLevel=getErrorLevel(folder))) for folder in data3["result"]]

        [self.listWidget_mydrive.addItem(convertMapdataToListItem(mapdata, False, False, True, getErrorLevel(mapdata))) for mapdata in data1["result"]]
        [self.listWidget_mydrive.addItem(convertMapdataToListItem(mapdata, False, True, False, getErrorLevel(mapdata))) for mapdata in data2["result"]]
        if len(data1["result"]) == 0  and len(data2["result"]) == 0 and len(data3["result"]) == 0:
            listitem = QListWidgetItem()
            listitem.setText("No results found!")
            self.listWidget_mydrive.addItem(listitem)
            log("no search results")

    def getCurrentState(self):
        state = {
                "level" : (self.level),
                "path": (self.path),
                "folderStack": (self.folderStack),
                "currentlySelectedMap": (self.currentlySelectedMap),
                "currentlySelectedId": (self.currentlySelectedId),
                "currentMetaData": (self.currentMetaData),
                "currentTimestamp": (self.currentTimestamp),
                "currentMode": (self.currentMode),
                "previousMode": (self.previousMode),
                "currentSubMode": (self.currentSubMode),
                "currentItem": (self.currentItem),
                "previousItem": (self.previousItem),
                "currentFolderId": (self.currentFolderId),
                "currentZoom": (self.currentZoom),
        }
        return state

    def setCurrentState(self, state):
        """ reset to a certain state, and call fillListWidget to redraw the plugin """
        self.level = (state["level"])
        self.folderStack = (state["folderStack"])
        self.currentlySelectedMap = (state["currentlySelectedMap"])
        self.currentlySelectedId = (state["currentlySelectedId"])
        self.currentMetaData = (state["currentMetaData"])
        self.currentTimestamp = (state["currentTimestamp"])
        self.currentMode = (state["currentMode"])
        self.previousMode = (state["previousMode"])
        self.currentSubMode = (state["currentSubMode"])
        self.currentItem = (state["currentItem"] )
        self.previousItem = (state["previousItem"])
        self.currentFolderId = (state["currentFolderId"])
        self.currentZoom = (state["currentZoom"])
        self.setPath(state["path"])
        self.fillListWidget()

    def onSearchChange(self, text):
        """ handle changes of the search string """
        #self.pushButton_wcs.setText("Get WCS")
        if (text == ""):
            self.stopSearch()
        elif (self.currentMode == ViewMode.SEARCH):
            self.searchText = text
            self.performSearch()
        else:
            self.pushButton_stopsearch.setEnabled(True)
            self.stateBeforeSearch = self.getCurrentState()
            self.currentMode = ViewMode.SEARCH
            self.searchText = text
            self.setPath("Searching..")
            self.performSearch()

    def onMapItemClick(self, item):
        """ handler called when an item is clicked in the map/shape listwidget """
        if item.data((QtCore.Qt.UserRole)).getType() == Type.ERROR:
            return
        self.currentlySelectedId = item.data((QtCore.Qt.UserRole)).getData()
        self.currentlySelectedMap = item
        #log(f"{item.text()}, data type: {item.data(QtCore.Qt.UserRole).getType()}")
        #log(f"{item.text()}, data type: {item.data(QtCore.Qt.UserRole).getType()}, data value: {item.data(QtCore.Qt.UserRole).getData()}")
        wcs = (item.data(QtCore.Qt.UserRole).getDisableWCS())
        #if (wcs):
        #    self.pushButton_wcs.setText("Accesslevel too low")
        #else:
        #    self.pushButton_wcs.setText("Get WCS")
        #self.disableCorrectButtons(WCSDisabled = (item.data(QtCore.Qt.UserRole).getDisableWCS()))

    def removeFromPath(self):
        """ remove one level from the path, useful when going back in the folder structure """
        if (self.level == 0):
            self.setPath("/")
            return
        self.setPath(self.path.rsplit('/',1)[0])

    def addToPath(self, foldername):
        """ extends the current path string """
        if self.path == "/":
            self.path = ""
        self.setPath(f"{self.path}/{foldername}")

    def setPath(self, path):
        """ set the displayed path """
        self.path = path
        toolong = False
        newstr = ""
        if (len(path) > MAXPATHLEN):
            toolong = True
            folders = path.split("/")
            folders.reverse()
            newstr = folders.pop()
            for folder in folders:
                if len(newstr) + len(folder) < 40:
                    newstr = f"{folder}/{newstr}"
                else:
                    break;
        if toolong:
            self.label_path.setText(f"../{newstr}")            
        else:
            self.label_path.setText(f"{path}")

    def onNext(self):
        """ handler for the Next button, used for navigating the folder structure """
        #log("BEGIN")
        #log(self.folderStack)
        success = True
        if (self.level == 0 and not self.currentMode == ViewMode.SEARCH):
            success = self.onNextRoot()
        else:
            success = self.onNextNormal()
        if success:
            self.currentFolderId = self.currentItem.data(QtCore.Qt.UserRole).getData()
            self.currentMode = ViewMode.FOLDERS
            self.level += 1
            self.currentItem = None
            self.currentlySelectedMap = None
        else:
            msg = QMessageBox()
            msg.setWindowTitle("Error!")
            msg.setText("Cannot open this folder")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            log("cannot open the folder")

    def onNextNormal(self):
        """ non-root onNext """
        pathId = self.currentItem.data(QtCore.Qt.UserRole).getData()
        if self.getFolder(pathId):
            self.folderStack.append(pathId)
            self.addToPath(self.currentItem.text())
            return True
        else:
            log("Error! onNextNormal: getFolder failed")
            log(f"pathid: {pathId}")
            return False
        
        #self.addToPath(pathId = self.selected.get)

    def onNextRoot(self):
        """ onNext for root folders """
        root = self.currentItem.data(QtCore.Qt.UserRole).getData()
        if self.getFolder(root, True):
            self.folderStack.append(root)
            self.addToPath(root)
            return True
        else:
            log("Error! onNextRoot: getFolder failed")
            log(f"root: {root}")
            return False

    def getFolder(self, id, isRoot=False):
        """ clears the listwidgets and flls them with the folders and maps in the specified folder (by folder id) """
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
            log("Data:")
            log(data)
            log("Headers:")
            log(headers)
            log("Url:")
            log(apiurl)
            if not j1:
                log("Map:")
                log(j1.content)
            if not j2:
                log("Folder:")
                log(j2.content)
            return False

        maps = json.loads(j1.text)
        folders = json.loads(j2.text)

        [self.listWidget_mydrive.addItem(convertMapdataToListItem(folderdata, True, errorLevel=getErrorLevel(folderdata))) for folderdata in folders["result"]]
        [self.listWidget_mydrive.addItem(convertMapdataToListItem(mapdata, False, errorLevel=getErrorLevel(mapdata))) for mapdata in maps["result"]]

        return True

    def onPrevious(self):
        """ handles walking back through te folder tree """
        if self.currentMode == ViewMode.SEARCH:
            self.removeFromPath()
            self.currentItem = None
            self.folderStack.pop()
            return
        
        self.level -= 1
        self.removeFromPath()
        self.currentItem = None
        self.folderStack.pop()

        if self.level == 0:
            self.path = "/"
            self.folderStack = []
            self.currentMode = ViewMode.ROOT
            return

    def clearListWidget(self):
        for _ in range(self.listWidget_mydrive.count()):
            self.listWidget_mydrive.takeItem(0)

    def onListWidgetClick(self, item):
        pass

    def logOut(self):
        """ emits the logout signal and removes the login token from the settings """
        log("logging out")
        if (self.settings.contains("token")):
            self.settings.remove("token")
        self.logoutSignal.emit()

    def populateListWithProtocols(self, type):
        if type == Type.SHAPE:
            self.listWidget_mydrive.addItem(toListItem(Type.PROTOCOL, "WFS", "WFS"))

        elif type == Type.MAP:
            self.listWidget_mydrive.addItem(toListItem(Type.PROTOCOL, "WMS", "WMS"))
            self.listWidget_mydrive.addItem(toListItem(Type.PROTOCOL, "WMTS", "WMTS"))
            self.listWidget_mydrive.addItem(toListItem(Type.PROTOCOL, "WCS", "WCS"))

    def populateListWithRoot(self):
        """ Adds the 3 root folders to the widget """
        myprojects = ListData("rootfolder", "myMaps")
        sharedwithme = ListData("rootfolder", "shared")
        favorites = ListData("rootfolder", "favorites")

        myprojectsitem = QListWidgetItem()
        sharedwithmeitem = QListWidgetItem()
        favoritesitem = QListWidgetItem()

        myprojectsitem.setText("My Drive")
        sharedwithmeitem.setText("Shared with me")
        favoritesitem.setText("Favorites")

        myprojectsitem.setData(QtCore.Qt.UserRole, myprojects)
        sharedwithmeitem.setData(QtCore.Qt.UserRole, sharedwithme)
        favoritesitem.setData(QtCore.Qt.UserRole, favorites)

        myprojectsitem.setIcon(QIcon(FOLDERICON))
        sharedwithmeitem.setIcon(QIcon(FOLDERICON))
        favoritesitem.setIcon(QIcon(FOLDERICON))

        self.listWidget_mydrive.addItem(myprojectsitem)
        self.listWidget_mydrive.addItem(sharedwithmeitem)
        self.listWidget_mydrive.addItem(favoritesitem)
