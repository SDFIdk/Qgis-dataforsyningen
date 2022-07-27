# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Dataforsyningen
                                 A QGIS plugin
 Easy access to WMS from Dataforsyningen (A service by The Danish geodataservice. Styrelsen for Dataforsyning og Infrastruktur)
                              -------------------
        begin                : 2015-05-01
        git sha              : $Format:%H$
        copyright            : (C) 2015 Agency for Data Supply and Infrastructure
        email                : dataforsyningen@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os.path
import datetime
from PyQt5.QtGui import QDesktopServices
from qgis.core import *
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QFileInfo,
    QUrl,
    QSettings,
    QTranslator,
    qVersion,
)
from qgis.PyQt.QtWidgets import QAction, QMenu, QPushButton
from qgis.PyQt.QtGui import QIcon
from .mysettings import *
from .config import Config
from .layerlocatorfilter import LayerLocatorFilter

ABOUT_FILE_URL = (
        "https://qgisplugin.dataforsyningen.dk/qgis_plugin_dataforsyningen_vejledning.html"
)
FILE_MAX_AGE = datetime.timedelta(hours=12)


def log_message(message):
    QgsMessageLog.logMessage(message, "Dataforsyningen plugin")


class Dataforsyningen(object):
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize options
        self.settings = Settings()
        self.settings.settings_updated.connect(self.reloadMenu)
        self.options_factory = OptionsFactory(self.settings)
        self.options_factory.setTitle(self.tr("Dataforsyningen"))
        iface.registerOptionsWidgetFactory(self.options_factory)

        self.config = Config(self.settings)
        self.config.df_con_error.connect(self.show_df_error)
        self.config.df_settings_warning.connect(self.show_df_settings_warning)
        self.config.loaded.connect(self.fillMenu)

        self.layer_locator_filter = LayerLocatorFilter()
        self.iface.registerLocatorFilter(self.layer_locator_filter)
        self.menu = None
        # An error menu object, set to None.
        self.error_menu = None
        # Categories
        self.categories = []
        self.category_lists = []
        self.nodes_by_index = {}
        self.node_count = 0
        self.category_menus = []

        # initialize locale
        path = QFileInfo(os.path.realpath(__file__)).path()
        try:
            settings = QSettings()
            locale = settings.value("locale/userLocale")[0:2]
        except:
            locale = "da"
        locale_path = os.path.join(path, "i18n", "{}.qm".format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > "4.3.3":
                QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        self.createMenu()

    def show_df_error(self):
        title = self.tr("No contact to Dataforsyningen")
        message = self.tr("Check internet connection and Dataforsyningen settings")
        log_message(message)
        self.show_messagebar_linked_to_settings(title, message)

    def show_df_settings_warning(self):
        title = self.tr("Dataforsyningen")

        message = self.tr("Token not set or wrong")
        log_message(message)
        self.show_messagebar_linked_to_settings(title, message)

    def show_messagebar_linked_to_settings(
        self, title, message, level=Qgis.Warning, duration=15
    ):
        button_text = self.tr(u"Open settings")
        widget = self.iface.messageBar().createMessage(title, message)
        button = QPushButton(widget)
        button.setText(button_text)
        button.pressed.connect(
            lambda: self.iface.showOptionsDialog(currentPage="dataforsyningenOptions")
        )
        widget.layout().addWidget(button)
        self.iface.messageBar().pushWidget(widget, level=level, duration=duration)

    def createMenu(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        menu_bar = self.iface.mainWindow().menuBar()
        self.menu = QMenu(menu_bar)
        self.menu.setObjectName(self.tr("Dataforsyningen"))
        self.menu.setTitle(self.tr("Dataforsyningen"))
        menu_bar.insertMenu(self.iface.firstRightStandardMenu().menuAction(), self.menu)
        self.config.begin_load()

    def fillMenu(self):
        self.categories = self.config.get_categories()
        self.category_lists = self.config.get_category_lists()
        searchable_layers = []

        if self.error_menu:
            self.menu.addAction(self.error_menu)

        # Add menu object for each theme
        self.category_menus = []
        df_helper = lambda _id: lambda: self.open_df_node(_id)
        local_helper = lambda _id: lambda: self.open_local_node(_id)

        for category_list in self.category_lists:
            list_categorymenus = []
            for category in category_list:
                category_menu = QMenu()
                category_menu.setTitle(category["name"])
                for selectable in category["selectables"]:
                    q_action = QAction(selectable["name"], self.iface.mainWindow())
                    if selectable["source"] == "df":
                        q_action.triggered.connect(df_helper(selectable["id"]))
                    else:
                        q_action.triggered.connect(local_helper(selectable["id"]))
                    category_menu.addAction(q_action)
                    searchable_layers.append(
                        {
                            "title": selectable["name"],
                            "category": category["name"],
                            "action": q_action,
                        }
                    )
                list_categorymenus.append(category_menu)
                self.category_menus.append(category_menu)
            for category_menukuf in list_categorymenus:
                self.menu.addMenu(category_menukuf)
            self.menu.addSeparator()
        self.layer_locator_filter.set_searchable_layers(searchable_layers)
        # Add about
        icon_path_info = os.path.join(
            os.path.dirname(__file__), "images/icon_about.png"
        )
        self.about_menu = QAction(
            QIcon(icon_path_info),
            self.tr("About the plugin") + "...",
            self.iface.mainWindow(),
        )
        self.about_menu.setObjectName(self.tr("About the plugin"))
        self.about_menu.triggered.connect(self.about_dialog)
        self.menu.addAction(self.about_menu)

    def open_local_node(self, id):
        node = self.config.get_local_maplayer_node(id)
        self.open_node(node, id)

    def open_df_node(self, id):
        node = self.config.get_df_maplayer_node(id)
        layer = self.open_node(node, id)

    def open_node(self, node, id):
        QgsProject.instance().readLayer(node)
        layer = QgsProject.instance().mapLayer(id)
        # if layer:
        # self.iface.legendInterface().refreshLayerSymbology(layer)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        return QCoreApplication.translate("Dataforsyningen", message)

    # Taken directly from menu_from_project
    def getFirstChildByTagNameValue(self, elt, tagName, key, value):
        nodes = elt.elementsByTagName(tagName)
        i = 0
        while i < nodes.count():
            node = nodes.at(i)
            idNode = node.namedItem(key)
            if idNode is not None:
                child = idNode.firstChild().toText().data()
                # layer found
                if child == value:
                    return node
            i += 1
        return None

    def about_dialog(self):
        lang = ""
        try:
            locale = QSettings().value("locale/userLocale")
            if locale != None:
                lang = "#" + locale[:2]
        except:
            pass
        QDesktopServices.openUrl(QUrl(ABOUT_FILE_URL))

    def unload(self):
        if self.options_factory:
            self.iface.unregisterOptionsWidgetFactory(self.options_factory)
            self.options_factory = None
        if self.layer_locator_filter:
            self.iface.deregisterLocatorFilter(self.layer_locator_filter)
            self.layer_locator_filter = None
        self.clearMenu()

    def reloadMenu(self):
        self.clearMenu()
        self.createMenu()

    def clearMenu(self):
        # Remove the submenus
        for submenu in self.category_menus:
            if submenu:
                submenu.deleteLater()
        self.category_menus = []
        # remove the menu bar item
        if self.menu:
            self.menu.deleteLater()
            self.menu = None
