"""
PyStratum
"""
import abc
import configparser
from typing import Dict, Optional

from pystratum.style.PyStratumStyle import PyStratumStyle

from pystratum.ConstantClass import ConstantClass
from pystratum.Util import Util


class Constants:
    """
    Abstract parent class for RDBMS specific classes for creating constants based on column widths, and auto increment
    columns and labels.
    """

    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self, io: PyStratumStyle):
        """
        Object constructor.

        :param PyStratumStyle io: The output decorator.
        """
        self._constants: Dict[str, int] = {}
        """
        All constants.
        """

        self._old_columns: Dict = {}
        """
        The previous column names, widths, and constant names (i.e. the content of $myConstantsFilename upon
        starting this program).
        """

        self._constants_filename: Optional[str] = None
        """
        Filename with column names, their widths, and constant names.
        """

        self._prefix: Optional[str] = None
        """
        The prefix used for designations a unknown constants.
        """

        self._class_name: str = ''
        """
        The name of the class that acts like a namespace for constants.
        """

        self._labels: Dict = {}
        """
        All primary key labels, their widths and constant names.
        """

        self._io: PyStratumStyle = io
        """
        The output decorator.
        """

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def connect(self) -> None:
        """
        Connects to the database.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def disconnect(self) -> None:
        """
        Disconnects from the database.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    def main(self, config_filename: str, regex: str) -> int:
        """
        :param str config_filename: The config filename.
        :param str regex: The regular expression for columns which we want to use.

        :rtype: int
        """
        self._read_configuration_file(config_filename)

        if self._constants_filename:
            self._io.title('Constants')

            self.connect()
            self._get_old_columns()
            self._get_columns()
            self._enhance_columns()
            self._merge_columns()
            self._write_columns()
            self._get_labels(regex)
            self._fill_constants()
            self.__write_constant_class()
            self.disconnect()
            self.__log_number_of_constants()
        else:
            self._io.log_verbose('Constants not enabled')

        return 0

    # ------------------------------------------------------------------------------------------------------------------
    def __log_number_of_constants(self) -> None:
        """
        Logs the number of constants generated.
        """
        n_id = len(self._labels)
        n_widths = len(self._constants) - n_id

        self._io.writeln('')
        self._io.text('Number of constants based on column widths: {0}'.format(n_widths))
        self._io.text('Number of constants based on database IDs : {0}'.format(n_id))

    # ------------------------------------------------------------------------------------------------------------------
    def _read_configuration_file(self, config_filename: str) -> None:
        """
        Reads parameters from the configuration file.

        :param str config_filename: The name of the configuration file.
        """
        config = configparser.ConfigParser()
        config.read(config_filename)

        self._constants_filename = config.get('constants', 'columns')
        self._prefix = config.get('constants', 'prefix')
        self._class_name = config.get('constants', 'class')

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _get_old_columns(self) -> None:
        """
        Reads from file constants_filename the previous table and column names, the width of the column,
        and the constant name (if assigned) and stores this data in old_columns.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _get_columns(self) -> None:
        """
        Retrieves metadata all columns in the MySQL schema.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _enhance_columns(self) -> None:
        """
        Enhances old_columns as follows:
        If the constant name is *, is is replaced with the column name prefixed by prefix in uppercase.
        Otherwise the constant name is set to uppercase.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _merge_columns(self) -> None:
        """
        Preserves relevant data in old_columns into columns.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _write_columns(self) -> None:
        """
        Writes table and column names, the width of the column, and the constant name (if assigned) to
        constants_filename.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _get_labels(self, regex: str) -> None:
        """
        Gets all primary key labels from the database.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _fill_constants(self) -> None:
        """
        Merges columns and labels (i.e. all known constants) into constants.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    def __write_constant_class(self) -> None:
        """
        Inserts new and replaces old (if any) constant declaration statements in the class that acts like a namespace
        for constants.
        """
        helper = ConstantClass(self._class_name, self._io)

        content = helper.source_with_constants(self._constants)

        Util.write_two_phases(helper.file_name(), content, self._io)

# ----------------------------------------------------------------------------------------------------------------------
