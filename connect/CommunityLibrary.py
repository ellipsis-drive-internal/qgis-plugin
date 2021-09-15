import os
import json
import requests

from PyQt5.QtWidgets import QDialog

from qgis.PyQt import uic

from qgis.PyQt.QtCore import QSettings

from PyQt5 import QtCore


from .util import *


class CommunityTab(QDialog):
    def __init__(self):
        super(CommunityTab, self).__init__()
        uic.loadUi(os.path.join(TABSFOLDER, "CommunityTab.ui"), self)
        self.communitySearch = ""
        self.currentlySelectedId = ""
        self.currentlySelectedMap = None
        self.loginToken = ""

        self.listWidget_community.itemClicked.connect(self.onCommunityItemClick)
        self.listWidget_community.itemSelectionChanged.connect(lambda:self.pushButton_wcs.setText("Get WCS"))
        self.lineEdit_communitysearch.textChanged.connect(self.onCommunitySearchChange)

        self.pushButton_wms.clicked.connect(lambda:self.onClickGet("wms"))
        self.pushButton_wmts.clicked.connect(lambda:self.onClickGet("wmts"))
        self.pushButton_wfs.clicked.connect(lambda:self.onClickGet("wfs"))
        self.pushButton_wcs.clicked.connect(lambda:self.onClickGet("wcs"))
        

        self.disableCorrectButtons(True)

        self.settings = QSettings('Ellipsis Drive', 'Ellipsis Drive Connect')

        if (self.settings.contains("token")):
            self.loginToken = self.settings.value("token")

        self.getCommunityList()

    # api.ellipsis-drive.com/v1/wms/mapId
    # api.ellipsis-drive.com/v1/wmts/mapId
    # api.ellipsis-drive.com/v1/wfs/mapId

    def onClickGet(self, mode):
        self.lineEdit_theurl.setText(getUrl(mode, self.currentlySelectedId, self.loginToken))
        self.label_instr.setText("Copy the following url:")

    def onRemoveClickGet(self):
        self.lineEdit_theurl.setText("")
        self.label_instr.setText("")

    def disableCorrectButtons(self, disableAll = False, disableWCS = False):
        """ enable and disable the correct buttons in the community library tab """

        self.pushButton_wms.setEnabled(False)
        self.pushButton_wmts.setEnabled(False)
        self.pushButton_wfs.setEnabled(False)
        self.pushButton_wcs.setEnabled(False)
        
        if disableAll or self.currentlySelectedMap is None:
            return

        if self.currentlySelectedMap.data((QtCore.Qt.UserRole)).isShape():
            self.pushButton_wfs.setEnabled(True)
        else:
            self.pushButton_wms.setEnabled(True)
            self.pushButton_wmts.setEnabled(True)
            if not disableWCS:
                self.pushButton_wcs.setEnabled(True)

    
    @debounce(0.5)
    def getCommunityList(self):
        """ gets the list of public projects and add them to the list widget on the community tab """

        # reset the list before updating it
        # self.listWidget_community.clear()

        print(f"getCommunityList called, token = '{self.loginToken}'")
        self.onRemoveClickGet()
        for _ in range(self.listWidget_community.count()):
            self.listWidget_community.takeItem(0)
        
        self.currentlySelectedId = ""
        self.disableCorrectButtons(True)

        apiurl1 = f"{URL}/account/maps"
        apiurl2 = f"{URL}/account/shapes"
        log("Getting community maps")
        headers = {'Content-Type': 'application/json', 'Accept':'application/json'}
        if (not self.loginToken == ""):
            headers["Authorization"] = f"Bearer {self.loginToken}"
        data1 = {
            "access": ["public"],
            "name": f"{self.communitySearch}",
            "disabled": False,
            "hasTimestamps": True
        }

        data2= {
            "access": ["public"],
            "name": f"{self.communitySearch}",
            "disabled": False,
            "hasGeometryLayers": True
        }

        j1 = requests.post(apiurl1, json=data1, headers=headers)
        j2 = requests.post(apiurl2, json=data2, headers=headers)
        if not j1 or not j2:
            log("getCommunityList failed!")
            return
        data = json.loads(j1.text)
        data2 = json.loads(j2.text)

        [self.listWidget_community.addItem(convertMapdataToListItem(mapdata, False, False, True, errorLevel=getErrorLevel(mapdata))) for mapdata in data["result"]]
        [self.listWidget_community.addItem(convertMapdataToListItem(mapdata, False, True, False, errorLevel=getErrorLevel(mapdata))) for mapdata in data2["result"]]
        
    def onCommunitySearchChange(self, text):
        """ Change the internal state of the community search string """
        self.communitySearch = text
        self.pushButton_wcs.setText("Get WCS")
        self.getCommunityList()

    def onCommunityItemClick(self, item):
        self.onRemoveClickGet()
        self.currentlySelectedId = item.data(QtCore.Qt.UserRole).getData()
        self.currentlySelectedMap = item
        log(f"{item.text()}, data type: {item.data(QtCore.Qt.UserRole).getType()}, data value: {item.data(QtCore.Qt.UserRole).getData()}")
        wcs = item.data(QtCore.Qt.UserRole).getDisableWCS()
        if (wcs):
            self.pushButton_wcs.setText("Accesslevel too low")
        else:
            self.pushButton_wcs.setText("Get WCS")
        self.disableCorrectButtons(disableWCS=wcs)