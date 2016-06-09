import abc
import os
import re
import sys


# ----------------------------------------------------------------------------------------------------------------------
class RoutineLoaderHelper:
    """
    Class for loading a single stored routine into a RDBMS instance from a (pseudo) SQL file.
    """
    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 routine_filename,
                 routine_file_encoding,
                 pystratum_old_metadata,
                 replace_pairs,
                 rdbms_old_metadata):
        """
        Object constructor.

        :param str routine_filename: The filename of the source of the stored routine.
        :param str routine_file_encoding: The encoding of the source file.
        :param dict pystratum_old_metadata: The metadata of the stored routine from PyStratum.
        :param dict[str,str] replace_pairs: A map from placeholders to their actual values.
        :param dict rdbms_old_metadata: The old metadata of the stored routine from MS SQL Server.
        """

        self._source_filename = routine_filename
        """
        The source filename holding the stored routine.

        :type: str
        """

        self._routine_file_encoding = routine_file_encoding
        """
        The encoding of the routine file.
        """

        self._pystratum_old_metadata = pystratum_old_metadata
        """
        The old metadata of the stored routine.  Note: this data comes from the metadata file.

        :type: dict
        """

        self._pystratum_metadata = {}
        """
        The metadata of the stored routine. Note: this data is stored in the metadata file and is generated by
        pyStratum.

        :type: dict
        """

        self._replace_pairs = replace_pairs
        """
        A map from placeholders to their actual values.

        :type: dict
        """

        self._rdbms_old_metadata = rdbms_old_metadata
        """
        The old information about the stored routine. Note: this data comes from the metadata of the RDBMS instance.

        :type: dict
        """

        self._m_time = 0
        """
        The last modification time of the source file.

        :type: int
        """

        self._routine_name = None
        """
        The name of the stored routine.

        :type: str
        """

        self._routine_source_code = None
        """
        The source code as a single string of the stored routine.

        :type: str
        """

        self._routine_source_code_lines = []
        """
        The source code as an array of lines string of the stored routine.

        :type: list
        """

        self._replace = {}
        """
        The replace pairs (i.e. placeholders and their actual values).
        :type: dict
        """

        self._routine_type = None
        """
        The stored routine type (i.e. procedure or function) of the stored routine.

        :type: str
        """

        self._designation_type = None
        """
        The designation type of the stored routine.

        :type: str
        """

        self._columns_types = None
        """
        The column types of columns of the table for bulk insert of the stored routine.

        :type: list
        """

        self._fields = None
        """
        The keys in the dictionary for bulk insert.

        :type: list
        """

        self._parameters = []
        """
        The information about the parameters of the stored routine.

        :type: list
        """

        self._table_name = None
        """
        If designation type is bulk_insert the table name for bulk insert.

        :type: str
        """

        self._columns = None
        """
        The key or index columns (depending on the designation type) of the stored routine.

        :type: list
        """

    # ------------------------------------------------------------------------------------------------------------------
    def load_stored_routine(self) -> dict:
        """
        Loads the stored routine into the instance of MySQL.

        Returns the metadata of the stored routine if the stored routine is loaded successfully. Otherwise return False.

        :rtype: dict[str,str]|bool
        """
        try:
            self._routine_name = os.path.splitext(os.path.basename(self._source_filename))[0]

            if os.path.exists(self._source_filename):
                if os.path.isfile(self._source_filename):
                    self._m_time = int(os.path.getmtime(self._source_filename))
                else:
                    raise Exception("Unable to get mtime of file '%s'." % self._source_filename)
            else:
                raise Exception("Source file '%s' does not exist." % self._source_filename)

            if self._pystratum_old_metadata:
                self._pystratum_metadata = self._pystratum_old_metadata

            load = self._must_reload()
            if load:
                with open(self._source_filename, 'r', encoding=self._routine_file_encoding) as file:
                    self._routine_source_code = file.read()

                self._routine_source_code_lines = self._routine_source_code.split("\n")

                ok = self._get_placeholders()
                if not ok:
                    return False

                ok = self._get_designation_type()
                if not ok:
                    return False

                ok = self._get_name()
                if not ok:
                    return False

                self._load_routine_file()

                if self._designation_type == 'bulk_insert':
                    self.get_bulk_insert_table_columns_info()

                self._get_routine_parameters_info()

                self._update_metadata()

            return self._pystratum_metadata

        except Exception as e:
            print('Error', e, file=sys.stderr)
            return False

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _must_reload(self):
        """
        Returns True if the source file must be load or reloaded. Otherwise returns False.

        :rtype: bool
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    def _get_placeholders(self):
        """
        Extracts the placeholders from the stored routine source.

        Return True if all placeholders are defined. Returns False otherwise.

        :rtype: bool
        """
        ret = True

        pattern = re.compile('(@[A-Za-z0-9_.]+(%type)?@)')
        matches = pattern.findall(self._routine_source_code)

        placeholders = []

        if len(matches) != 0:
            for tmp in matches:
                placeholder = tmp[0]
                if placeholder.lower() not in self._replace_pairs:
                    print("Error: Unknown placeholder '%s' in file '%s'." % (placeholder, self._source_filename),
                          file=sys.stderr)
                    ret = False
                if placeholder not in placeholders:
                    placeholders.append(placeholder)
        if ret:
            for placeholder in placeholders:
                if placeholder not in self._replace:
                    self._replace[placeholder] = self._replace_pairs[placeholder.lower()]

        return ret

    # ------------------------------------------------------------------------------------------------------------------
    def _get_designation_type(self):
        """
        Extracts the designation type of the stored routine.

        Returns True on success. Otherwise returns False.

        :rtype: bool
        """
        pass

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _get_name(self):
        """
        Extracts the name of the stored routine and the stored routine type (i.e. procedure or function) source.

        Returns True on success. Returns False otherwise.

        :rtype: bool
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _load_routine_file(self):
        """
        Loads the stored routine into the RDBMS instance.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def get_bulk_insert_table_columns_info(self):
        """
        Gets the column names and column types of the current table for bulk insert.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _get_routine_parameters_info(self):
        """
        Retrieves information about the stored routine parameters from the meta data of the RDBMS.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    def _update_metadata(self):
        """
        Updates the metadata of the stored routine.
        """
        self._pystratum_metadata['routine_name'] = self._routine_name
        self._pystratum_metadata['designation'] = self._designation_type
        self._pystratum_metadata['table_name'] = self._table_name
        self._pystratum_metadata['parameters'] = self._parameters
        self._pystratum_metadata['columns'] = self._columns
        self._pystratum_metadata['fields'] = self._fields
        self._pystratum_metadata['column_types'] = self._columns_types
        self._pystratum_metadata['timestamp'] = self._m_time
        self._pystratum_metadata['replace'] = self._replace

    # ------------------------------------------------------------------------------------------------------------------
    @abc.abstractmethod
    def _drop_routine(self):
        """
        Drops the stored routine if it exists.
        """
        raise NotImplementedError()

    # ------------------------------------------------------------------------------------------------------------------
    def _set_magic_constants(self):
        """
        Adds magic constants to replace list.
        """
        real_path = os.path.realpath(self._source_filename)

        self._replace['__FILE__'] = "'%s'" % real_path
        self._replace['__ROUTINE__'] = "'%s'" % self._routine_name
        self._replace['__DIR__'] = "'%s'" % os.path.dirname(real_path)

    # ------------------------------------------------------------------------------------------------------------------
    def _unset_magic_constants(self):
        """
        Removes magic constants from current replace list.
        """
        if '__FILE__' in self._replace:
            del self._replace['__FILE__']

        if '__ROUTINE__' in self._replace:
            del self._replace['__ROUTINE__']

        if '__DIR__' in self._replace:
            del self._replace['__DIR__']

        if '__LINE__' in self._replace:
            del self._replace['__LINE__']

# ----------------------------------------------------------------------------------------------------------------------
