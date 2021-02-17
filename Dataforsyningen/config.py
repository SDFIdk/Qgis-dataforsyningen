from qgis.PyQt import QtCore
from .df_config import DfConfig
from .local_config import LocalConfig


class Config(QtCore.QObject):

    df_con_error = QtCore.pyqtSignal()
    df_settings_warning = QtCore.pyqtSignal()
    loaded = QtCore.pyqtSignal()

    def __init__(self, settings):
        super(Config, self).__init__()
        self.settings = settings
        self.categories = []
        self.categories_list = []
        self.df_categories = []
        self.local_categories = []
        self.df_config = DfConfig(settings)
        self.df_config.df_con_error.connect(self.propagate_df_con_error)
        self.df_config.df_settings_warning.connect(self.propagate_df_settings_warning)
        self.df_config.loaded.connect(self._handle_df_config_loaded)

        self.local_config = LocalConfig(settings)

    def propagate_df_settings_warning(self):
        self.df_settings_warning.emit()

    def propagate_df_con_error(self):
        self.df_con_error.emit()

    def begin_load(self):
        self.df_config.begin_load()

    def _handle_df_config_loaded(self):
        self.categories = []
        self.categories_list = []
        if self.settings.value("use_custom_file") and self.settings.value(
            "only_background"
        ):
            self.df_categories = []
            background_category = self.df_config.get_background_category()
            if background_category:
                self.df_categories.append(background_category)
        else:
            self.df_categories = self.df_config.get_categories()
        self.local_categories = self.local_config.get_categories()
        self.categories = self.df_categories + self.local_categories
        self.categories_list.append(self.df_categories)
        self.categories_list.append(self.local_categories)

        # Tell the world
        self.loaded.emit()

    def get_category_lists(self):
        return self.categories_list

    def get_categories(self):
        return self.categories

    def get_df_maplayer_node(self, id):
        return self.df_config.get_maplayer_node(id)

    def get_local_maplayer_node(self, id):
        return self.local_config.get_maplayer_node(id)
