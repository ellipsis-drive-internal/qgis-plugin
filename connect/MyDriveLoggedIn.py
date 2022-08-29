import urllib
import webbrowser
from PyQt5.uic.uiparser import QtWidgets
from PyQt5 import QtCore
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QGridLayout, QLabel, QLineEdit, QListWidget, QPushButton, QWidget
from qgis.core import *
from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtWidgets import QListWidgetItem
from qgis.utils import iface
from requests import api

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
    """ 
    The LoggedIn tab, giving users access to their drive. 
    Used in combination with the MyDriveTab and the MyDriveLoginTab
    """
    logoutSignal = pyqtSignal()
    def __init__(self):
        super(MyDriveLoggedInTab, self).__init__()
        #uic.loadUi(os.path.join(TABSFOLDER, "MyDriveLoggedInTab.ui"), self)

        QgsProject.instance().layersAdded.connect(self.zoomHandler)

        self.loginToken = None
        self.loggedIn = False
        self.userInfo = {}
        self.path = "/"
        self.folderStack = [["base", "base"]]
        self.searchText = ""
        self.currentMetaData = None
        self.currentTimestamp = None
        self.currentMode = ViewMode.FOLDERS
        self.previousMode = None
        self.currentSubMode = ViewSubMode.NONE
        self.currentItem = None
        self.previousItem = None
        self.currentFolderId = None
        self.currentZoom = None
        self.highlightedID = ""
        self.highlightedType = None
        self.stateBeforeSearch = {}

        self.setMinimumHeight(0)
        self.setMinimumWidth(0)

        self.constructUI()

        self.settings = QSettings('Ellipsis Drive', 'Ellipsis Drive Connect')
        self.setPath()
        self.fillListWidget()

    def sizeHint(self):
        a = QWidget.sizeHint(self)
        a.setHeight(SIZEH)
        a.setWidth(SIZEW)
        return a

    def constructUI(self):

        self.gridLayout = QGridLayout()

        self.label = QLabel()
        self.label_path = QLabel()
        self.lineEdit_search = QLineEdit()
        self.listWidget_mydrive = QListWidget()
        self.pushButton_logout = QPushButton()
        self.pushButton_logout.setText("Logout")
        self.pushButton_stopsearch = QPushButton()
        self.pushButton_stopsearch.setText("Stop search")

        self.pushButton_refresh = QPushButton()
        self.pushButton_refresh.setIcon(QIcon(REFRESHICON))
        self.pushButton_refresh.clicked.connect(self.onRefresh)

        self.pushButton_openBrowser = QPushButton()
        self.pushButton_openBrowser.setText("Open in browser")
        self.pushButton_openBrowser.clicked.connect(self.onOpenBrowser)
        self.pushButton_openBrowser.setEnabled(True)

        self.label.setText("Welcome!")
        self.lineEdit_search.setPlaceholderText("Search..")

        self.listWidget_mydrive.itemDoubleClicked.connect(self.onListWidgetDoubleClick)
        self.listWidget_mydrive.itemClicked.connect(self.onListWidgetClick)

        self.pushButton_logout.clicked.connect(self.logOut)
        self.pushButton_stopsearch.clicked.connect(self.stopSearch)
        self.pushButton_stopsearch.setEnabled(False)

        if not DISABLESEARCH:
            self.lineEdit_search.textEdited.connect(self.onSearchChange)

        self.gridLayout.addWidget(self.label, 0, 0)
        self.gridLayout.addWidget(self.pushButton_logout, 0, 1)
        self.gridLayout.addWidget(self.lineEdit_search, 1, 0)
        self.gridLayout.addWidget(self.pushButton_stopsearch, 1, 1)
        self.gridLayout.addWidget(self.label_path, 2, 0)
        self.gridLayout.addWidget(self.pushButton_refresh, 2,1)
        self.gridLayout.addWidget(self.listWidget_mydrive, 3, 0, 1, 2)
        self.gridLayout.addWidget(self.pushButton_openBrowser, 4,0, 1, 2)
        
        self.setLayout(self.gridLayout)

    def onRefresh(self):
        # what we have to do depends on the state that we're in

        self.pushButton_refresh.setEnabled(False)
        label = self.label_path.text()
        self.clearListWidget()

        self.label_path.setText("Refreshing")

        if self.currentMode == ViewMode.FOLDERS:
            folder = self.folderStack[-1]
            if folder[0] == "base":
                self.populateListWithRoot()
            elif folder[0] == "root":
                self.fillListWidget()
                #self.getFolder(folder[1], True)
            else:
                self.fillListWidget()
                #self.getFolder(folder[1], False)
        elif self.currentMode in [ViewMode.SHAPE, ViewMode.MAP]:
            self.fillListWidget()
        elif self.currentMode in [ViewMode.WMS, ViewMode.WMTS, ViewMode.WFS, ViewMode.WCS]:
            _, self.currentMetaData = self.getMetadata(self.currentMetaData["id"])
            self.fillListWidget()
        elif self.currentMode == ViewMode.SEARCH:
            self.performSearch()

        self.pushButton_refresh.setEnabled(True)
        self.label_path.setText(label)

    def onOpenBrowser(self):
        log(self.currentMode)
        log(self.currentSubMode)
        log(self.folderStack)
        url = ""

        if self.currentMode == ViewMode.FOLDERS:
            folder = self.folderStack[-1]
            if folder[0] == "base": # starting location
                url = "https://app.ellipsis-drive.com/"
            elif folder[0] == "root": # root folders
                if folder[1] == "myDrive":
                    url = "https://app.ellipsis-drive.com/drive/projects"
                elif folder[1] == "sharedWithMe":
                    url = "https://app.ellipsis-drive.com/drive/shared"
                elif folder[1] == "favorites":
                    url = "https://app.ellipsis-drive.com/drive/favorites"
            else: # regular folder
                url = f"https://app.ellipsis-drive.com/drive/projects?pathId={folder[1]}"
            pass
        elif self.currentMode in [ViewMode.SHAPE, ViewMode.MAP, ViewMode.WMS, ViewMode.WMTS, ViewMode.WFS, ViewMode.WCS]:
            mapid = self.currentMetaData["path"]["path"][0]["id"]
            url = f"https://app.ellipsis-drive.com/view?mapId={mapid}"
        elif self.currentMode == ViewMode.SEARCH:
            url = f"https://app.ellipsis-drive.com/drive/search?q={self.searchText}"

        if not url == "":
            webbrowser.open(url)

    def addReturnItem(self):
        self.listWidget_mydrive.addItem(toListItem(Type.RETURN, "..", icon=RETURNICON))

    def getMetadata(self, mapid):
        data = {
            "pathId": mapid,
        }
        rettype, content = self.request(f"/path/{mapid}", data=data)
        log("METADATA:")
        log(content)
        return rettype, content

    def getPathInfo(self, id):
        success, output = self.getMetadata(id)
        if success:
            return [output["path"]["root"], output["path"]["path"]]
        return [None, None]


    def onListWidgetDoubleClick(self, item):
        itemdata = item.data((QtCore.Qt.UserRole)).getData()
        itemtype = item.data((QtCore.Qt.UserRole)).getType()
        """ handler for clicks on items in the folder listwidget """
        log(f"Clicked on type {itemtype}, current modi: {self.currentMode}, {self.currentSubMode}")

        if itemtype == Type.MESSAGE:
            #don't do anything when a message is clicked
            return

        # if we're searching, the regular rules don't apply
        if self.currentMode == ViewMode.SEARCH:
            root, folderpath = self.getPathInfo(itemdata)
            log(root)
            if root is None and folderpath is None:
                return
            #root = "shared" if root == "sharedWithMe" else root # ugly fix for weird api
            folderpath.reverse()
            self.folderStack = [[ "base", "base"], ["root", root]]
            for folder in folderpath:
                log("Adding 'regular' folder")
                log(folder)
                self.folderStack.append([folder["name"], folder["id"]])

            if itemtype == Type.FOLDER:
                self.currentMode = ViewMode.FOLDERS
                self.currentSubMode = ViewSubMode.NONE
            else:
                self.folderStack.pop()
                success, self.currentMetaData = self.getMetadata(itemdata)
                if not success:
                    return
                self.currentMode = ViewMode.SHAPE
                self.currentSubMode = ViewSubMode.NONE
                if itemtype == Type.MAP:
                    self.currentMode = ViewMode.MAP
                self.currentItem = item

            self.lineEdit_search.clear()
            self.pushButton_stopsearch.setEnabled(False)
            self.setPath()
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
                #self.removeFromPath()

            elif self.currentMode == ViewMode.WFS:
                self.currentMode = ViewMode.SHAPE
                self.currentSubMode = ViewSubMode.NONE
                #self.removeFromPath()

            elif self.currentMode == ViewMode.WCS or self.currentMode == ViewMode.WMS or self.currentMode == ViewMode.WMTS:
                if self.currentSubMode == ViewSubMode.TIMESTAMPS:
                    self.currentMode = ViewMode.MAP
                    self.currentSubMode = ViewSubMode.NONE
                elif self.currentSubMode == ViewSubMode.MAPLAYERS:
                    self.currentSubMode = ViewSubMode.TIMESTAMPS
                #self.removeFromPath()

        elif self.currentMode == ViewMode.FOLDERS:

            if  itemtype == Type.FOLDER or itemtype == Type.ROOT:
                self.onNext()

            elif itemtype == Type.SHAPE or itemtype == Type.MAP:
                success, self.currentMetaData = self.getMetadata(itemdata)
                if not success:
                    return
                #self.addToPath(self.currentMetaData["name"])
                if itemtype == Type.SHAPE:
                    self.currentMode = ViewMode.SHAPE
                else:
                    self.currentMode = ViewMode.MAP

        elif self.currentMode == ViewMode.SHAPE or self.currentMode == ViewMode.MAP:
            self.currentMode = mapViewMode(itemdata)
            self.currentSubMode = initialSubMode(itemdata)
            #self.addToPath(itemdata)

        elif self.currentMode == ViewMode.WMS:
            self.WMSDoubleClick(item)

        elif self.currentMode == ViewMode.WMTS:
            self.WMTSDoubleClick(item)

        elif self.currentMode == ViewMode.WFS:
            self.WFSDoubleClick(item)

        elif self.currentMode == ViewMode.WCS:
            self.WCSDoubleClick(item)

        self.setPath()
        self.fillListWidget()

    def fillListWidget(self):
        log(f"fillListWidget called with modi: {self.currentMode} and {self.currentSubMode}")
        self.clearListWidget()

        if (not self.currentMode == ViewMode.SEARCH):
            self.setPath()

        if (self.currentMode == ViewMode.FOLDERS):
            log(self.folderStack)
            if (len(self.folderStack) == 1):
                self.populateListWithRoot()
            elif (len(self.folderStack) == 2):
                self.addReturnItem()
                self.getFolder(self.folderStack[1][1], isRoot=True)
            else:
                self.addReturnItem()
                self.getFolder(self.folderStack[-1][1])
            return

        item = self.currentItem.data((QtCore.Qt.UserRole))

        self.highlightedID = item.getData()
        self.highlightedType = item.getType()

        self.addReturnItem()

        maptype = self.currentMetaData["type"]

        if (self.currentMode == ViewMode.WMS or self.currentMode == ViewMode.WMTS or self.currentMode == ViewMode.WCS):
            
            if (self.currentSubMode == ViewSubMode.TIMESTAMPS):
                timestamps = self.currentMetaData[maptype]["timestamps"]
                maplayers = self.currentMetaData[maptype]["layers"]
                for timestamp in timestamps:
                    if timestamp["status"] == "finished":
                        self.listWidget_mydrive.addItem(toListItem(Type.TIMESTAMP, timestamp["dateTo"], data=timestamp, extra=maplayers))

            elif (self.currentSubMode == ViewSubMode.MAPLAYERS):
                self.currentTimestamp = item.getData()
                mapLayers = item.getExtra()
                for mapLayer in mapLayers:
                    self.listWidget_mydrive.addItem(toListItem(Type.MAPLAYER, mapLayer["name"], mapLayer))

        elif (self.currentMode == ViewMode.MAP or self.currentMode == ViewMode.SHAPE):
            level = self.currentMetaData["yourAccess"]["accessLevel"]
            WCSaccess = level >= 200
            self.populateListWithProtocols(Type.MAP if self.currentMode == ViewMode.MAP else Type.SHAPE, WCSAccess=WCSaccess)
        elif (self.currentMode == ViewMode.WFS):
            geometryLayers = self.currentMetaData["geometryLayers"]
            for geometryLayer in geometryLayers:
                if not geometryLayer["deleted"] and not geometryLayer["availability"]["blocked"]:
                    self.listWidget_mydrive.addItem(toListItem(Type.TIMESTAMP, geometryLayer["name"], data=geometryLayer))

        elif (self.currentMode == ViewMode.WCS):
            timestamps = self.currentMetaData["raster"]["timestamps"]
            for timestamp in timestamps:
                if timestamp["status"] == "finished":
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
            rlayer = QgsRasterLayer(actualurl, f"{self.currentTimestamp['dateTo']}_{itemdata['name']}", 'wms')
            
            # iface.addRasterLayer(actualurl, f"{self.currentTimestamp['dateTo']}_{itemdata['name']}", 'wms')
            
            if not rlayer.isValid():
                getMessageBox("Error loading layer", "Layer failed to load.").exec_()
                log("Layer failed to load!")
                log(rlayer)
                log(rlayer.error())
                log(dir(rlayer))
            else:
                QgsProject.instance().addMapLayer(rlayer)
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
            rlayer = QgsRasterLayer(actualurl, f"{self.currentTimestamp['dateTo']}_{itemdata['name']}", 'wms')
            
            # iface.addRasterLayer(actualurl, f"{self.currentTimestamp['dateTo']}_{itemdata['name']}", 'wms')

            if not rlayer.isValid():
                getMessageBox("Error loading layer", "Layer failed to load.").exec_()
                log("Layer failed to load!")
            else:
               QgsProject.instance().addMapLayer(rlayer)
            # same as above
            self.currentItem = self.previousItem


    def zoomHandler(self, layers):
        log("Zooming to layers")
        log(layers)
        iface.setActiveLayer(layers[0])
        QtCore.QTimer.singleShot(500, lambda:iface.zoomToActiveLayer())

    def WFSDoubleClick(self, item):
        
        # !!!! WFS should be CAPITALS, the other protocols should be lowercase

        text = item.text()
        itemdata = item.data((QtCore.Qt.UserRole))
        #id = item.data((QtCore.Qt.UserRole)).getData()
        mapid = self.currentMetaData["id"]
        theurl = F"{URL}/wfs/{mapid}/{self.loginToken}?"

        extend = itemdata.getData()["extent"]

        #typename moet dus layerId_{layer ID zijn}
        params = {
            'service': 'WFS',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typename': f'layerId_{itemdata.getData()["id"]}',
            'srsname': "EPSG:4326",
            'BBOX': f"{extend['xMin']},{extend['xMax']},{extend['yMin']},{extend['yMax']}",
            'restrictToRequestBBOX': 1
        }


        uri = f'{theurl}' + urllib.parse.unquote(urllib.parse.urlencode(params))
        
        rlayer = QgsVectorLayer(uri, text, 'WFS')
        # iface.addVectorLayer(uri, text, 'WFS')

        if not rlayer.isValid():
            getMessageBox("Error loading layer", "Layer failed to load.").exec_()
            log("Layer failed to load!")
        else:
            QgsProject.instance().addMapLayer(rlayer)
        
        self.currentItem = self.previousItem

    def WCSDoubleClick(self, item):
        itemdata = item.data((QtCore.Qt.UserRole))

        def makeWCSuri( url, layer ):
            params = {  'dpiMode': 7 , 'identifier': layer,'url': url.split('?')[0]  }
            uri = urllib.parse.unquote( urllib.parse.urlencode(params)  )
            return uri

        
        timestampid = itemdata.getData()["id"]

        mapid = self.currentMetaData["id"]
        theurl = F"{URL}/wcs/{mapid}/{self.loginToken}"
        
        wcsUri = makeWCSuri(theurl, timestampid )

        # display loading item while the layer is loading
        self.clearListWidget()
        self.listWidget_mydrive.addItem(toListItem(Type.MESSAGE, "Loading..."))

        rlayer = QgsRasterLayer(wcsUri, f'{self.currentMetaData["name"]}', 'wcs')

        if not rlayer.isValid():
            getMessageBox("Error loading layer", "Layer failed to load.").exec_()
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
        self.loginToken = None
        self.loggedIn = False
        self.userInfo = {}
        self.path = "/"
        self.folderStack = [["base", "base"]]
        self.searchText = ""
        self.currentMetaData = None
        self.currentTimestamp = None
        self.currentMode = ViewMode.FOLDERS
        self.previousMode = None
        self.currentSubMode = ViewSubMode.NONE
        self.currentItem = None
        self.previousItem = None
        self.currentFolderId = None
        self.currentZoom = None
        self.highlightedID = ""
        self.highlightedType = None
        self.stateBeforeSearch = {}
        self.lineEdit_search.clear()
        self.setPath()

    def getCurrentState(self):
        state = {
                "path": (self.path),
                "folderStack": (self.folderStack),
                "currentMetaData": (self.currentMetaData),
                "currentTimestamp": (self.currentTimestamp),
                "currentMode": (self.currentMode),
                "previousMode": (self.previousMode),
                "currentSubMode": (self.currentSubMode),
                "currentItem": (self.currentItem),
                "previousItem": (self.previousItem),
                "currentFolderId": (self.currentFolderId),
                "currentZoom": (self.currentZoom),
                "highlightedID": (self.highlightedID),
                "highlightedType": (self.highlightedType),
        }
        return state

    def setCurrentState(self, state):
        """ reset to a certain state, and call fillListWidget to redraw the plugin """
        self.folderStack = (state["folderStack"])
        self.currentMetaData = (state["currentMetaData"])
        self.currentTimestamp = (state["currentTimestamp"])
        self.currentMode = (state["currentMode"])
        self.previousMode = (state["previousMode"])
        self.currentSubMode = (state["currentSubMode"])
        self.currentItem = (state["currentItem"] )
        self.previousItem = (state["previousItem"])
        self.currentFolderId = (state["currentFolderId"])
        self.currentZoom = (state["currentZoom"])
        self.highlightedID = (state["highlightedID"])
        self.highlightedType = (state["highlightedType"])
        self.setPath()
        self.fillListWidget()

    def onSearchChange(self, text):
        """ handle changes of the search string """
        #self.pushButton_wcs.setText("Get WCS")
        if (text == ""):
            self.stopSearch()
        elif (self.currentMode == ViewMode.SEARCH):
            self.label_path.setText("Searching..")
            self.searchText = text
            self.performSearch()
        else:
            self.pushButton_stopsearch.setEnabled(True)
            self.stateBeforeSearch = self.getCurrentState()
            self.currentMode = ViewMode.SEARCH
            self.searchText = text
            self.label_path.setText("Searching..")
            self.performSearch()

    def pathFromStack(self):
        log("Getting path from stack")
        #log(self.folderStack)
        revfolders = self.folderStack[::-1]

        if len(self.folderStack) == 1:
            return "/"

        path = ""
        if self.currentMode in [ViewMode.MAP, ViewMode.SHAPE]:
            log(self.currentMetaData)
            path = f"/{self.currentMetaData['name']}"
        elif self.currentMode in [ViewMode.WMS, ViewMode.WMTS, ViewMode.WCS, ViewMode.WFS]:
            path = f"/{self.currentMetaData['name']}/{protToString[self.currentMode]}"

        for folder in revfolders:
            if folder[0] == "base" and folder[1] == "base":
                continue
            if len(path) + len(folder[0]) < MAXPATHLEN:
                if folder[0] == "root":
                    path = f"/{getRootName(folder[1])}{path}"
                else:
                    path = f"/{getRootName(folder[0])}{path}"
            else:
                path = f"..{path}"
                break
        log(path)
        return path

    def removeFromPath(self):
        """ remove one level from the path, useful when going back in the folder structure """
        self.folderStack.pop()
        self.setPath()
        return
        if (len(self.folderStack == 1)):
            self.setPath("/")
            return
        self.setPath(self.path.rsplit('/',1)[0])

    def addToPath(self, foldername):
        """ extends the current path string """
        if self.path == "/":
            self.path = ""
        self.setPath(f"{self.path}/{foldername}")

    def setPath(self):
        """ set the displayed path to the one specified in self.folderstack"""
        thepath = self.pathFromStack()
        self.label_path.setText(f"{thepath}")
        return
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
        success = ReqType.SUCC
        if (len(self.folderStack) == 1 and not self.currentMode == ViewMode.SEARCH):
            success = self.onNextRoot()
        else:
            success = self.onNextNormal()
        if success:
            self.currentFolderId = self.currentItem.data(QtCore.Qt.UserRole).getData()
            self.currentMode = ViewMode.FOLDERS
            self.currentItem = None
        elif success == ReqType.AUTHERR:
            pass
        elif success == ReqType.FAIL:
            getMessageBox("Error!", "Cannot open this folder").exec_()
        self.setPath()

    def onNextNormal(self):
        """ non-root onNext """
        log("onnextnormal")
        pathId = self.currentItem.data(QtCore.Qt.UserRole).getData()
        name = self.currentItem.data(QtCore.Qt.UserRole).getExtra()
        rettype = self.getFolder(pathId)
        if rettype:
            self.folderStack.append([name, pathId])
            self.setPath()
            return True
        else:
            log("Error! onNextNormal: getFolder failed")
            log(f"pathid: {pathId}")
            return rettype

    def onNextRoot(self):
        """ onNext for root folders """
        log("onnextroot")
        root = self.currentItem.data(QtCore.Qt.UserRole).getData()
        rettype = self.getFolder(root, True)
        if rettype:
            self.folderStack.append(["root", root])
            return True
        else:
            log("Error! onNextRoot: getFolder failed")
            log(f"root: {root}")
            return rettype

    def request(self, url, data, headers=None, method="GET"):
        if headers is None:
            headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
            headers["Authorization"] = f"Bearer {self.loginToken}"
        status, content =  makeRequest(url, headers, data, version=2, method=method)
        log(content)
        if status == ReqType.AUTHERR:
            # token expired!
            # display message, logout the user
            log("Token expired!!")
            getMessageBox("Authentication error", "Your login token has probably expired, please log in again.").exec_()
            self.logOut()
        elif status == ReqType.CONNERR:
            # connection error!
            # display messagebox I think? maybe go to no internet screen
            log("Connection error!")
            getMessageBox("Connection error", "Please check your internet connection and try again.").exec_()
        
        return status, content

    @debounce(0.5)
    def performSearch(self):
        """ actually perform the search, using self.searchText as the string """
        if not self.currentMode == ViewMode.SEARCH:
            return
        log("performing search")

        self.clearListWidget()

        apiurlmaps = f"/account/maps"
        apiurlshapes = f"/account/shapes"
        apiurlfolders = f"/account/folders"

        data = {
            "access": ["owned", "subscribed", "favorited"],
            "name": f"{self.searchText}",
        }

        sucm, resmaps = self.request(apiurlmaps, data)

        if sucm == ReqType.AUTHERR:
            return ReqType.AUTHERR

        sucs, resshapes = self.request(apiurlshapes, data)

        if sucm == ReqType.AUTHERR:
            return ReqType.AUTHERR

        sucf, resfolders = self.request(apiurlfolders, data)

        if sucm == ReqType.AUTHERR:
            return ReqType.AUTHERR
        
        havefolders = False
        haveshapes = False
        havemaps = False

        if sucm and "result" in resmaps and resmaps["result"]:
            log("Have maps")
            maps = resmaps["result"]
            havemaps = True

        if sucs and "result" in resshapes and resshapes["result"]:
            log("Have shapes")
            log(resshapes["result"])
            shapes = resshapes["result"]
            haveshapes = True

        if sucf and "result" in resfolders and resfolders["result"]:
            havefolders = True
            folders = resfolders["result"]

        # "pagination"
        while havefolders and (not resfolders["nextPageStart"] is None):
            log("pagination on folders in search")
            data["pageStart"] = resfolders["nextPageStart"]
            rettype, resfolders = self.request(apiurlfolders, data)
            if rettype:
                folders += resfolders["result"]
            else:
                break

        while havemaps and (not resmaps["nextPageStart"] is None):
            log("pagination on maps in search")
            data["pageStart"] = resmaps["nextPageStart"]
            rettype, resmaps = self.request(apiurlmaps, data)
            if rettype:
                maps += resmaps["result"]
            else:
                break
        
        while haveshapes and (not resshapes["nextPageStart"] is None):
            log("pagination on shapes in search")
            data["pageStart"] = resshapes["nextPageStart"]
            rettype, resshapes = self.request(apiurlshapes, data)
            if rettype:
                shapes += resshapes["result"]
            else:
                break

        #folders first
        if havefolders and self.currentMode == ViewMode.SEARCH:
            [self.listWidget_mydrive.addItem(convertMapdataToListItem(folder, True, errorLevel=getErrorLevel(folder))) for folder in folders]

        if havemaps and self.currentMode == ViewMode.SEARCH:
            [self.listWidget_mydrive.addItem(convertMapdataToListItem(mapdata, False, False, True, getErrorLevel(mapdata))) for mapdata in maps]
        
        if haveshapes and self.currentMode == ViewMode.SEARCH:
            [self.listWidget_mydrive.addItem(convertMapdataToListItem(mapdata, False, True, False, getErrorLevel(mapdata))) for mapdata in shapes]

        if not havefolders and not havemaps and not haveshapes:
            # users may stop the search
            if (self.currentMode == ViewMode.SEARCH):
                self.clearListWidget()
                self.listWidget_mydrive.addItem(toListItem(Type.MESSAGE, "No results found!"))
                log("no search results")
        self.label_path.setText("Search done")

    def getFolder(self, id, isRoot=False):
        """ clears the listwidgets and flls them with the folders and maps in the specified folder (by folder id) """
        apiurl = ""
        datamap = {}
        datafolder= {}
        if (isRoot):
            apiurl = f"/account/root/{id}"
            datamap = {
                "rootName": f"{id}",
                "isFolder": "false"
            }
            datafolder = {
                "rootName": f"{id}",
                "isFolder": "true"
            }
        else:
            apiurl = f"/path/{id}/list"
            datamap = {
                "pathId": f"{id}",
                "isFolder": "false"
            }
            datafolder = {
                "pathId": f"{id}",
                "isFolder": "true"
            }

        success1, resmaps = self.request(apiurl, datamap)

        if success1 == ReqType.AUTHERR:
            return ReqType.AUTHERR

        success2, resfolders = self.request(apiurl, datafolder)

        if success2 == ReqType.AUTHERR:
            return ReqType.AUTHERR

        if not success1 and not success2:
            return False

        havefolders = False
        havemaps = False

        if success1 and "result" in resmaps:
            maps = resmaps["result"]
            havemaps = True

        if success2 and "result" in resfolders:
            havefolders = True
            folders = resfolders["result"]

        # "pagination"
        
        while havefolders and (not resfolders["nextPageStart"] is None):
            log("Pagination on folders in getFolder")
            datafolder["pageStart"] = resfolders["nextPageStart"]
            rettype, resfolders = self.request(apiurl, datafolder)
            if rettype:
                 folders += resfolders["result"]
            else:
                break

        while havemaps and (not resmaps["nextPageStart"] is None):
            log("Pagination on maps in getFolder")
            datamap["pageStart"] = resmaps["nextPageStart"]
            rettype, resmaps = self.request(apiurl, datamap)
            if rettype:
                maps += resmaps["result"]
            else:
                break

        if havefolders:
            [self.listWidget_mydrive.addItem(convertMapdataToListItem(folderdata, True, errorLevel=getErrorLevel(folderdata))) for folderdata in folders]
        
        if havemaps:
            [self.listWidget_mydrive.addItem(convertMapdataToListItem(mapdata, False, errorLevel=getErrorLevel(mapdata))) for mapdata in maps]
        return True

    def onPrevious(self):
        """ handles walking back through te folder tree """
        if self.currentMode == ViewMode.SEARCH:
            self.currentItem = None
            self.removeFromPath()
            return
        
        log("folderStack before popping:")
        log(self.folderStack)

        self.currentItem = None
        self.removeFromPath()


    def clearListWidget(self):
        for _ in range(self.listWidget_mydrive.count()):
            self.listWidget_mydrive.takeItem(0)

    def onListWidgetClick(self, item):
        item = item.data((QtCore.Qt.UserRole))
        itemtype = item.getType()
        itemdata = item.getData()

        if itemtype == Type.MESSAGE:
            # don't do anything when a message is clicked
            return

        self.highlightedID = itemdata
        self.highlightedType = itemtype


    def logOut(self):
        """ emits the logout signal and removes the login token from the settings """
        log("logging out")
        if (self.settings.contains("token")):
            self.settings.remove("token")
        self.logoutSignal.emit()

    def populateListWithProtocols(self, type, WCSAccess = True):
        log(f"listing protocols for {type}")
        log(f"WCSACCESS: {WCSAccess}")
        if type == Type.SHAPE:
            self.listWidget_mydrive.addItem(toListItem(Type.PROTOCOL, "WFS", "WFS"))

        elif type == Type.MAP:
            self.listWidget_mydrive.addItem(toListItem(Type.PROTOCOL, "WMS", "WMS"))
            self.listWidget_mydrive.addItem(toListItem(Type.PROTOCOL, "WMTS", "WMTS"))
            if WCSAccess:
                self.listWidget_mydrive.addItem(toListItem(Type.PROTOCOL, "WCS", "WCS"))
            else:
                listitem = toListItem(Type.ERROR, "WCS (Accesslevel too low)", "WCS Accesslevel error")
                self.listWidget_mydrive.addItem(listitem)

    def populateListWithRoot(self):
        """ Adds the 3 root folders to the widget """
        myprojects = ListData(Type.ROOT, "myDrive")
        sharedwithme = ListData(Type.ROOT, "sharedWithMe")
        favorites = ListData(Type.ROOT, "favorites")

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
