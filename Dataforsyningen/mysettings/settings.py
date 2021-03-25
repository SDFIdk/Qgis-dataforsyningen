# -*- coding: utf-8 -*-
import os
from PyQt5.QtCore import QFileInfo, QObject
from qgis.PyQt import QtCore

from qgis.utils import active_plugins
from .qgissettingmanager import *
CONFIG_FILE_URL = 'https://cdn.dataforsyningen.dk/qgis/qgis_dataforsynings_plugin_udentoken.qlr'
class Settings(SettingManager):
    settings_updated = QtCore.pyqtSignal()

    def __init__(self):
        SettingManager.__init__(self, 'Dataforsyningen')
        self.add_setting(String('token', Scope.Global, ''))
        self.add_setting(Bool('use_custom_file', Scope.Global, False))
        self.add_setting(String('custom_qlr_file', Scope.Global, ''))
        self.add_setting(Bool('only_background', Scope.Global, False))
        path = QFileInfo(os.path.realpath(__file__)).path()
        df_path = path + '/df/'
        if not os.path.exists(df_path):
            os.makedirs(df_path)
            
        self.add_setting(String('cache_path', Scope.Global, df_path))
        self.add_setting(String('df_qlr_url', Scope.Global, CONFIG_FILE_URL))
        
    def is_set(self):
        is_set = False
        if self.value('token'):
            is_set = True
        elif "Kortforsyningen" in active_plugins: # Take the token from kortforsyning plugin
            s = QtCore.QSettings()
            kortforsyningen_token = s.value("plugins/Kortforsyningen/token")
            if kortforsyningen_token:
                self.set_value('token', kortforsyningen_token)
                is_set = True
        
        return is_set
    
    def emit_updated(self):
        self.settings_updated.emit()

