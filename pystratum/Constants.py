import configparser
import abc
from pystratum.Util import Util


# ----------------------------------------------------------------------------------------------------------------------
class Constants:
    """
    Class for creating constants based on column widths, and auto increment columns and labels.
    """
    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self):
        """
        Object constructor.
        """

        self._constants = {}
        """
        All constants.

        :type: dict
        """

        self._old_columns = {}
        """
        The previous column names, widths, and constant names (i.e. the content of $myConstantsFilename upon
        starting this program).

        :type: dict
        """

        self._database = None
        """
        The database name.

        :type: string
        """

        self._host_name = None
        """
        The hostname of the MySQL instance.

        :type: string
        """

        self._password = None
        """
        Password required for logging in on to the MySQL instance.

        :type: string
        """

        self._user_name = None
        """
        User name.

        :type: string
        """

        self._constants_filename = None
        """
        Filename with column names, their widths, and constant names.

        :type: string
        """

        self._prefix = None
        """
        The prefix used for designations a unknown constants.

        :type: string
        """

        self._template_config_filename = None
        """
        Template filename under which the file is generated with the constants.

        :type: string
        """

        self._config_filename = None
        """
        The destination filename with constants.

        :type: string
        """

        self._columns = {}
        """
        All columns in the MySQL schema.

        :type: dict
        """

        self._labels = {}
        """
        All primary key labels, their widths and constant names.

        :type: dict
        """

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def connect(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def disconnect(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def main(self, config_filename: str) -> int:
        """
        :param: config_filename string The config filename.
        :return: int
        """
        self._read_configuration_file(config_filename)
        self.connect()
        self._get_old_columns()
        self._get_columns()
        self._enhance_columns()
        self._merge_columns()
        self._write_columns()
        self._get_labels()
        self._fill_constants()
        self._write_target_config_file()
        self.disconnect()

        return 0

    # ------------------------------------------------------------------------------------------------------------------
    def _read_configuration_file(self, config_filename: str):
        """
        Reads parameters from the configuration file.
        :param config_filename string
        """
        config = configparser.ConfigParser()
        config.read(config_filename)

        self._host_name = config.get('database', 'host_name')
        self._user_name = config.get('database', 'user_name')
        self._password = config.get('database', 'password')
        self._database = config.get('database', 'database_name')

        self._constants_filename = config.get('constants', 'columns')
        self._prefix = config.get('constants', 'prefix')
        self._template_config_filename = config.get('constants', 'config_template')
        self._config_filename = config.get('constants', 'config')

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _get_old_columns(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _get_columns(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _enhance_columns(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _merge_columns(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _write_columns(self):
        pass
    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _get_labels(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def _fill_constants(self):
        pass

    # ------------------------------------------------------------------------------------------------------------------
    def _write_target_config_file(self):
        """
        Creates a python configuration file with constants.
        :return:
        """
        content = ''
        for constant, value in sorted(self._constants.items()):
            content += "%s = %s\n" % (str(constant), str(value))

            # Save the configuration file.
        Util.write_two_phases(self._config_filename, content)

# ----------------------------------------------------------------------------------------------------------------------
