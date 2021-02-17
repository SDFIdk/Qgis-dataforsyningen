# -*- coding: utf-8 -*-
import os
from PyQt5 import QtGui, uic
from PyQt5.QtWidgets import QFileDialog
from qgis.gui import (QgsOptionsPageWidget)
from qgis.PyQt.QtWidgets import  QVBoxLayout
from .qgissettingmanager import *



WIDGET, BASE = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), 'settings.ui')
)

class ConfigOptionsPage(QgsOptionsPageWidget):

    def __init__(self, parent, settings):
        super(ConfigOptionsPage, self).__init__(parent)
        self.settings = settings
        self.config_widget = ConfigDialog(self.settings)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setMargin(0)
        self.setLayout(layout)
        layout.addWidget(self.config_widget)
        self.setObjectName('dataforsyningenOptions')

    def apply(self):
        self.config_widget.accept_dialog()
        self.settings.emit_updated()

class ConfigDialog(WIDGET, BASE, SettingDialog):
    def __init__(self, settings):
        super(ConfigDialog, self).__init__(None)
        self.setupUi(self)
        SettingDialog.__init__(self, settings)
        self.settings = settings
        if self.settings.value('use_custom_file'):
        #if self.use_custom_file.isChecked():
            self.only_background.setEnabled(True)
            self.browseLocalFileButton.setEnabled(True)
        else:
            self.only_background.setEnabled(False)
            self.browseLocalFileButton.setEnabled(False)

        self.browseLocalFileButton.clicked.connect(self.browseLocalFile)
        self.use_custom_file.clicked.connect(self.useLocalChanged)
        
    def browseLocalFile(self):
        qlr_file, f = QFileDialog.getOpenFileName(
            self,
            "Lokal qlr",
            self.custom_qlr_file.text(),
            "Qlr (*.qlr)"
        )
        if qlr_file:
            #self.settings.set_value('custom_qlr_file', qlr_file)
            self.custom_qlr_file.setText(qlr_file)

    def useLocalChanged(self, checked):
        if self.use_custom_file.isChecked():
            self.only_background.setEnabled(True)
            self.browseLocalFileButton.setEnabled(True)
        else:
            self.only_background.setEnabled(False)
            self.browseLocalFileButton.setEnabled(False)

