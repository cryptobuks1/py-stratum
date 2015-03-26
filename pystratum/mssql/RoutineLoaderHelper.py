import os
import re
import sys
from pystratum.mssql.StaticDataLayer import StaticDataLayer


# ----------------------------------------------------------------------------------------------------------------------
class RoutineLoaderHelper:
    """
    Class for loading a single stored routine into a MySQL instance from pseudo SQL file.
    """
    # ------------------------------------------------------------------------------------------------------------------
    def __init__(self,
                 routine_filename: str,
                 routine_file_extension: str,
                 metadata: dict,
                 replace_pairs: dict,
                 old_routine_info: dict,
                 sql_mode: str,
                 character_set: str,
                 collate: str):

        self._source_filename = routine_filename
        """
        The source filename holding the stored routine.

        :type : string
        """

        self._routine_file_extension = routine_file_extension
        """
        The source filename extension.

        :type : string
        """

        self._old_metadata = metadata
        """
        The old metadata of the stored routine.  Note: this data comes from the metadata file.

        :type : dict
        """

        self._metadata = {}
        """
        The metadata of the stored routine. Note: this data is stored in the metadata file and is generated by
        pyStratum.

        :type : dict
        """

        self._replace_pairs = replace_pairs
        """
        A map from placeholders to their actual values.

        :type : dict
        """

        self._old_routine_info = old_routine_info
        """
        The old information about the stored routine. Note: this data comes from information_schema.ROUTINES.

        :type : dict
        """

        self._sql_mode = sql_mode
        """
        The SQL mode under which the stored routine will be loaded and run.

        :type : string
        """

        self._character_set = character_set
        """
        The default character set under which the stored routine will be loaded and run.

        :type : string
        """

        self._collate = collate
        """
        The default collate under which the stored routine will be loaded and run.

        :type : string
        """

        self._m_time = 0
        """
        The last modification time of the source file.

        :type : int
        """

        self._routine_name = None
        """
        The name of the stored routine.

        :type : string
        """

        self._routine_source_code = None
        """
        The source code as a single string of the stored routine.

        :type : string
        """

        self._routine_source_code_lines = []
        """
        The source code as an array of lines string of the stored routine.

        :type : list
        """

        self._replace = {}
        """
        The replace pairs (i.e. placeholders and their actual values).

        :type : dict
        """

        self._routine_type = None
        """
        The stored routine type (i.e. procedure or function) of the stored routine.

        :type : string
        """

        self._designation_type = None
        """
        The designation type of the stored routine.

        :type : string
        """

        self._columns_types = None
        """
        The column types of columns of the table for bulk insert of the stored routine.

        :type : list
        """

        self._fields = None
        """
        The keys in the PHP array for bulk insert.

        :type : list
        """

        self._parameters = []
        """
        The information about the parameters of the stored routine.

        :type : list
        """

        self._table_name = None
        """
        If designation type is bulk_insert the table name for bulk insert.

        :type : string
        """

        self._columns = None
        """
        The key or index columns (depending on the designation type) of the stored routine .

        :type : list
        """

    # ------------------------------------------------------------------------------------------------------------------
    def load_stored_routine(self) -> dict:
        """
        Loads the stored routine into the instance of MySQL.
        :return array|bool If the stored routine is loaded successfully the new mata data of the stored routine.
                           Otherwise False.
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

            if self._old_metadata:
                self._metadata = self._old_metadata

            load = self._must_reload()

            if load:
                with open(self._source_filename, 'r') as f:
                    self._routine_source_code = f.read()

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

                # if self._designation_type == 'bulk_insert':
                #    self.get_bulk_insert_table_columns_info()

                self._get_routine_parameters_info()

                self._update_metadata()

            return self._metadata

        except Exception as e:
            print('Error', e, file=sys.stderr)
            return False

    # ------------------------------------------------------------------------------------------------------------------
    def _must_reload(self) -> bool:
        """
        Returns True if the source file must be load or reloaded. Otherwise returns False.
        :return bool
        """
        if not self._old_metadata:
            return True

        if self._old_metadata['timestamp'] != self._m_time:
            return True

        if self._old_metadata['replace']:
            for key, value in self._old_metadata['replace'].items():
                if key.lower() not in self._replace_pairs or self._replace_pairs[key.lower()] != value:
                    return True

        if not self._old_routine_info:
            return True

        # if self._old_routine_info['sql_mode'] != self._sql_mode:
        #    return True

        # if self._old_routine_info['character_set_client'] != self._character_set:
        #    return True

        # if self._old_routine_info['collation_connection'] != self._collate:
        #    return True

        return False

    # ------------------------------------------------------------------------------------------------------------------
    def _get_placeholders(self) -> bool:
        """
        Extracts the placeholders from the stored routine source.
        :return True if all placeholders are defined, False otherwise.
        """
        ret = True

        p = re.compile('(@[A-Za-z0-9_\.]+(%type)?@)')
        matches = p.findall(self._routine_source_code)

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
                self._replace[placeholder] = self._replace_pairs[placeholder.lower()]

        return ret

    # ------------------------------------------------------------------------------------------------------------------
    def _get_designation_type(self) -> bool:
        """
        Extracts the designation type of the stored routine.
        :return True on success. Otherwise returns False.
        """
        ret = True

        key = self._routine_source_code_lines.index('as')

        if key != -1:
            p = re.compile('\s*--\s+type:\s*(\w+)\s*(.+)?\s*')
            matches = p.findall(self._routine_source_code_lines[key - 1])

            if matches:
                self._designation_type = matches[0][0]
                tmp = str(matches[0][1])
                if self._designation_type == 'bulk_insert':
                    n = re.compile('([a-zA-Z0-9_]+)\s+([a-zA-Z0-9_,]+)')
                    info = n.findall(tmp)

                    if not info:
                        print("Error: Expected: -- type: bulk_insert <table_name> <columns> in file '%s'." %
                              self._source_filename, file=sys.stderr)
                    self._table_name = info[0][0]
                    self._columns = str(info[0][1]).split(',')

                elif self._designation_type == 'rows_with_key' or self._designation_type == 'rows_with_index':
                    self._columns = str(matches[0][1]).split(',')
                else:
                    if matches[0][1]:
                        ret = False
        else:
            ret = False

        if not ret:
            print("Error: Unable to find the designation type of the stored routine in file '%s'." %
                  self._source_filename, file=sys.stderr)

        return ret

    # ------------------------------------------------------------------------------------------------------------------
    def _get_name(self) -> bool:
        """
        Extracts the name of the stored routine and the stored routine type (i.e. procedure or function) source.
        :return Returns True on success, False otherwise.
        """
        ret = True
        p = re.compile("create\\s+(procedure|function)\\s+(?:(\w+)\.([a-zA-Z0-9_]+))")
        matches = p.findall(self._routine_source_code)

        if matches:
            self._routine_type = matches[0][0].lower()
            self._routines_schema_name = matches[0][1]

            if self._routine_name != matches[0][2]:
                print("Error: Stored routine name '%s' does not match filename in file '%s'." % (
                    matches[0][2], self._source_filename))
                ret = False
        else:
            ret = False

        if not self._routine_type:
            print("Error: Unable to find the stored routine name and type in file '%s'." % self._source_filename)

        return ret

    # ------------------------------------------------------------------------------------------------------------------
    def _load_routine_file(self):
        """
        Loads the stored routine into the database.
        """
        print("Loading %s %s" % (self._routine_type, self._routine_name))

        self._set_magic_constants()

        routine_source = []
        i = 0
        for line in self._routine_source_code_lines:
            new_line = line
            self._replace['__LINE__'] = "'%d'" % (i + 1)
            for search, replace in self._replace.items():
                tmp = re.findall(search, new_line, re.IGNORECASE)
                if tmp:
                    new_line = new_line.replace(tmp[0], replace)
            routine_source.append(new_line)
            i += 1

        routine_source = "\n".join(routine_source)

        self._unset_magic_constants()
        self._drop_routine()

        # sql = "set sql_mode ='%s'" % self._sql_mode
        # StaticDataLayer.execute_none(sql)

        # sql = "set names '%s' collate '%s'" % (self._character_set, self._collate)
        # StaticDataLayer.execute_none(sql)

        StaticDataLayer.execute_none(routine_source)

    # ------------------------------------------------------------------------------------------------------------------
    def get_bulk_insert_table_columns_info(self):
        """
        Gets the column names and column types of the current table for bulk insert.
        """
        query = """
select 1 from
information_schema.TABLES
where TABLE_SCHEMA = database()
and   TABLE_NAME   = '%s'""" % self._table_name

        # execute row0
        table_is_non_temporary = StaticDataLayer.execute_rows(query)

        if len(table_is_non_temporary) == 0:
            query = 'call %s()' % self._routine_name
            # StaticDataLayer.execute_sp_none(query)

        query = "describe `%s`" % self._table_name
        columns = StaticDataLayer.execute_rows(query)

        tmp_column_types = []
        tmp_fields = []

        n1 = 0
        for column in columns:
            p = re.compile('(\\w+)')
            c_type = p.findall(column['Type'])
            tmp_column_types.append(c_type[0])
            tmp_fields.append(column['Field'])
            n1 += 1

        n2 = len(self._columns)

        if len(table_is_non_temporary) == 0:
            query = "drop temporary table `%s`" % self._table_name
            StaticDataLayer.execute_none(query)

        if n1 != n2:
            raise Exception("Number of fields %d and number of columns %d don't match." % (n1, n2))

        self._columns_types = tmp_column_types
        self._fields = tmp_fields

    # ------------------------------------------------------------------------------------------------------------------
    def _get_routine_parameters_info(self):
        query = """
select par.name      parameter_name
,      typ.name      type_name
,      typ.max_length
,      typ.precision
,      typ.scale
from       sys.schemas        scm
inner join sys.all_objects    prc  on  prc.[schema_id] = scm.[schema_id]
inner join sys.all_parameters par  on  par.[object_id] = prc.[object_id]
inner join sys.types          typ  on  typ.user_type_id = par.system_type_id
where scm.name = '%s'
and   prc.name = '%s'
order by par.parameter_id
;""" % (self._routines_schema_name, self._routine_name)

        routine_parameters = StaticDataLayer.execute_rows(query)

        if len(routine_parameters) != 0:
            for routine_parameter in routine_parameters:
                if routine_parameter['parameter_name']:
                    parameter_name = routine_parameter['parameter_name'][1:]
                    value = routine_parameter['type_name']
                    # if 'character_set_name' in routine_parameter:
                    #    if routine_parameter['character_set_name']:
                    #        value += ' character set %s' % routine_parameter['character_set_name']
                    # if 'collation' in routine_parameter:
                    #    if routine_parameter['character_set_name']:
                    #        value += ' collation %s' % routine_parameter['collation']

                    self._parameters.append({'name': parameter_name,
                                             'data_type': routine_parameter['type_name'],
                                             'data_type_descriptor': value})

    # ------------------------------------------------------------------------------------------------------------------
    def _update_metadata(self):
        """
        Updates the metadata of the stored routine.
        """
        self._metadata.update({'schema_name': self._routines_schema_name})
        self._metadata.update({'routine_name': self._routine_name})
        self._metadata.update({'designation': self._designation_type})
        self._metadata.update({'table_name': self._table_name})
        self._metadata.update({'parameters': self._parameters})
        self._metadata.update({'columns': self._columns})
        self._metadata.update({'fields': self._fields})
        self._metadata.update({'column_types': self._columns_types})
        self._metadata.update({'timestamp': self._m_time})
        self._metadata.update({'replace': self._replace})

    # ------------------------------------------------------------------------------------------------------------------
    def _drop_routine(self):
        """
        Drops the stored routine if it exists.
        """
        if self._old_routine_info:
            sql = """
if exists
    ( select *
      from sys.objects
      where type_desc = 'SQL_STORED_PROCEDURE'
      and name = '%s' )
      DROP PROC %s.%s;
"""
            sql = sql % (self._routine_name,
                         self._old_routine_info['schema_name'],
                         self._routine_name)

            StaticDataLayer.execute_none(sql)

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
            del (self._replace['__FILE__'])

        if '__ROUTINE__' in self._replace:
            del (self._replace['__ROUTINE__'])

        if '__DIR__' in self._replace:
            del (self._replace['__DIR__'])

        if '__LINE__' in self._replace:
            del (self._replace['__LINE__'])


# ----------------------------------------------------------------------------------------------------------------------
