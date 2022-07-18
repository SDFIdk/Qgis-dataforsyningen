from builtins import str
import codecs
import os
import datetime
import traceback
import json
import hashlib
import glob
from qgis.core import QgsMessageLog, QgsNetworkContentFetcher
from qgis.PyQt.QtCore import (
    QFile,
    QUrl,
    QIODevice,
)
from qgis.PyQt import QtCore
from .qlr_file import QlrFile

FILE_MAX_AGE = datetime.timedelta(hours=12)
DF_SERVICES_URL = (
    "https://api.dataforsyningen.dk/userpermissions/{{df_token}}"
)


def log_message(message):
    QgsMessageLog.logMessage(message, "Dataforsyningen plugin")


class DfConfig(QtCore.QObject):

    df_con_error = QtCore.pyqtSignal()
    df_settings_warning = QtCore.pyqtSignal()
    loaded = QtCore.pyqtSignal()

    def __init__(self, settings):
        super(DfConfig, self).__init__()
        self.settings = settings
        self.cached_df_qlr_filename = None
        self.allowed_df_services = {}
        self.df_qlr_file = None
        self.background_category = None
        self.categories = None

        # Network
        self._services_network_fetcher = QgsNetworkContentFetcher()
        self._qlr_network_fetcher = QgsNetworkContentFetcher()
        self._services_network_fetcher.finished.connect(self._handle_services_response)
        self._qlr_network_fetcher.finished.connect(self._handle_qlr_response)

    def begin_load(self):
        self.cached_df_qlr_filename = (
            self.settings.value("cache_path")
            + hashlib.md5(self.settings.value("token").encode()).hexdigest()
            + "_dataforsyning_data.qlr"
        )
        self.allowed_df_services = {}
        if self.settings.is_set():
            try:
                self._request_services()
            except Exception as e:
                log_message(traceback.format_exc())
                self.df_con_error.emit()
                self.background_category = None
                self.categories = []
            self.debug_write_allowed_services()
        else:
            self.df_settings_warning.emit()
            self.background_category = None
            self.categories = []

    def _request_services(self):
        url_to_get = self.insert_token(DF_SERVICES_URL)
        self._services_network_fetcher.fetchContent(QUrl(url_to_get))

    def _handle_services_response(self):
        network_reply = self._services_network_fetcher.reply()

        if network_reply.error():
            self.background_category = None
            self.categories = []
            self.df_con_error.emit()
            log_message(
                f"Network error getting services from df. Error code : "
                + str(network_reply.error())
            )
            return
        response = str(network_reply.readAll(), "utf-8")
        doc = json.loads(response)
        allowed = {}
        allowed["any_type"] = {"services": []}
        for i in doc:
            allowed["any_type"]["services"].append(i["name"])
        self.allowed_df_services = allowed
        if not allowed["any_type"]["services"]:
            self.df_con_error.emit()
            log_message(
                f"Dataforsyningen returned an empty list of allowed services for token: {self.settings.value('token')}"
            )
        # Go on and get QLR
        self._get_qlr_file()

    def _get_qlr_file(self):
        local_file_exists = os.path.exists(self.cached_df_qlr_filename)
        if local_file_exists:
            local_file_time = datetime.datetime.fromtimestamp(
                os.path.getmtime(self.cached_df_qlr_filename)
            )
            use_cached = local_file_time > datetime.datetime.now() - FILE_MAX_AGE
            if use_cached:
                # Skip requesting remote qlr
                self._load_config_from_cached_df_qlr()
                return
        # Get qlr from DF
        self._request_df_qlr_file()

    def _request_df_qlr_file(self):
        url_to_get = self.settings.value("df_qlr_url")
        self._qlr_network_fetcher.fetchContent(QUrl(url_to_get))

    def _handle_qlr_response(self):
        network_reply = self._qlr_network_fetcher.reply()

        if network_reply.error():
            log_message(
                "No contact to the configuration at "
                + self.settings.value("df_qlr_url")
                + ". Error code : "
                + str(network_reply.error())
            )
        else:
            response = str(network_reply.readAll(), "utf-8")
            response = self.insert_token(response)
            self.write_cached_df_qlr(response)
        # Now load and use it
        self._load_config_from_cached_df_qlr()

    def _load_config_from_cached_df_qlr(self):
        self.df_qlr_file = QlrFile(self._read_cached_df_qlr())
        self.background_category, self.categories = self.get_df_categories()
        self.loaded.emit()

    def get_categories(self):
        return self.categories

    def get_background_category(self):
        return self.background_category

    def get_maplayer_node(self, id):
        return self.df_qlr_file.get_maplayer_node(id)

    def get_df_categories(self):
        df_categories = []
        df_background_category = None
        groups_with_layers = self.df_qlr_file.get_groups_with_layers()
        for group in groups_with_layers:
            df_category = {"name": group["name"], "selectables": []}
            for layer in group["layers"]:
                if self.user_has_access(layer["service"]):
                    df_category["selectables"].append(
                        {
                            "type": "layer",
                            "source": "df",
                            "name": layer["name"],
                            "id": layer["id"],
                        }
                    )
            if len(df_category["selectables"]) > 0:
                df_categories.append(df_category)
                if group["name"] == "Baggrundskort":
                    df_background_category = df_category
        return df_background_category, df_categories

    def user_has_access(self, service_name):
        return service_name in self.allowed_df_services["any_type"]["services"]

    def get_custom_categories(self):
        return []

    def _read_cached_df_qlr(self):
        # return file(unicode(self.cached_df_qlr_filename)).read()
        f = QFile(self.cached_df_qlr_filename)
        f.open(QIODevice.ReadOnly)
        return f.readAll()

    def write_cached_df_qlr(self, contents):
        """We only call this function IF we have a new version downloaded"""
        # Remove old versions file
        for filename in glob.glob(
            self.settings.value("cache_path") + "*_dataforsyning_data.qlr"
        ):
            os.remove(filename)

        # Write new version
        with codecs.open(self.cached_df_qlr_filename, "w", "utf-8") as f:
            f.write(contents)

    def debug_write_allowed_services(self):
        try:
            debug_filename = (
                self.settings.value("cache_path")
                + self.settings.value("username")
                + ".txt"
            )
            if os.path.exists(debug_filename):
                os.remove(debug_filename)
            with codecs.open(debug_filename, "w", "utf-8") as f:
                f.write(
                    json.dumps(
                        self.allowed_df_services["any_type"]["services"], indent=2
                    )
                    .replace("[", "")
                    .replace("]", "")
                )
        except Exception:
            pass

    def insert_token(self, text):
        result = text
        replace_vars = {}
        replace_vars["df_token"] = self.settings.value("token")
        for i, j in replace_vars.items():
            result = result.replace("{{" + str(i) + "}}", str(j))
        return result
