from .exceptions import DatabaseError
from .helpers import run_once
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .simplemysql import SimpleMysql

class Model:

	__protected__ = [
		'db',
		'table',
		'columns',
		'keys',
		'select_error_msg',
		'update_error_msg',
		'insert_error_msg',
		'commit',
		'all',
		'count',
		'insert',
		'save',
		'load',
		'load_args',
		'loaded',
		'isLoaded',
		'unsaved',
		'__create_table__',
		'__create',
		'__doesTableExist'
	]

	__create_table__ = True

	db: SimpleMysql = None

	'''	
		Configuration
	'''
	table = '' # Table Name
	
	columns = [] # Table Columns

	keys = [] # Table Index Keys

	select_error_msg = ""
	update_error_msg = ""
	insert_error_msg = ""

	def __init__(self, *args, **kwargs):
		self.__create()
		self.load(*args, **kwargs)
		pass
	
	def __setattr__(self, name, value):				
		if name == 'columns' or name == 'keys':
			if not isinstance(value, list):
				raise DatabaseError("Model columns should be a list")

			for column in value:
				if column in self.__protected__:
					raise DatabaseError("Reserved key '{}' cannot be used as column name".format(column))

		if name in self.columns and (not hasattr(self, name) or getattr(self, name) != value):
			self.unsaved[name] = value
			return True

		return object.__setattr__(self, name, value)

	def __doesTableExist(self):
		try:
			get = self.db.execute("SELECT * FROM {} LIMIT 1".format(self.db.escape(self.table)))
			if not get:
				return False
			return True
		except Exception as e:
			return False

	@run_once
	def __create(self):
		allowed_types = [
			"INT", "VARCHAR", "TEXT", "DATE", "TINYINT", "SMALLINT", "MEDIUMINT", "INT", "BIGINT", "DECIMAL", "FLOAT", "DOUBLE", "REAL","BIT","BOOLEAN","SERIAL","DATE","DATETIME","TIMESTAMP", "TIME", "YEAR", "CHAR", "VARCHAR", 
			"TINYTEXT", "TEXT", "MEDIUMTEXT", "LONGTEXT", "BINARY", "VARBINARY", "TINYBLOB", "MEDIUMBLOB", "BLOB", "LONGBLOB", "ENUM", "SET", "GEOMETRY", "POINT", "LINESTRING", "POLYGON", "MULTIPOINT", "MULTILINESTRING", "MULTIPOLYGON", "GEOMETRYCOLLECTION"
		]
		
		if isinstance(self.columns, dict) and not self.__doesTableExist() and self.__create_table__:
			fields = []
			primary_keys = []
			unique_keys = []

			for column, options in self.columns.items():

				if not options['type'] or options['type'] not in allowed_types:
					raise DatabaseError("Invalid type column type '%s'" % options['type'])
				
				if options.get('primary') and column not in primary_keys and column not in unique_keys:
					primary_keys.append(column)
				
				if options.get('unique') and column not in primary_keys and column not in unique_keys:
					unique_keys.append(column)

				parseOptions = [
					options['type'] + (
						'(%s)' % options.get('length') if options.get('length') else ''
					),
					'NULL' if options.get('null') else 'NOT NULL',
					'on update CURRENT_TIMESTAMP' if options.get('onUpdateTime') else '',
					'DEFAULT ' + (
						options.get('default') if (
							options.get('default') in ['CURRENT_TIMESTAMP', 'NULL'] or isinstance(options.get('default'), int)
							) else ("'%s'" % self.db.escape(options.get('default')))
					) if options.get('default') else '',
					'AUTO_INCREMENT' if options.get('autoIncrement') else '',
				]

				fields.append(
					'`{}` {}'.format(self.db.escape(column), ' '.join(parseOptions))
				)
				
			fields.extend([
				'PRIMARY KEY (`%s`)' % self.db.escape(pk) for pk in primary_keys
			])

			fields.extend([
				'UNIQUE (`%s`)' % self.db.escape(uk) for uk in unique_keys
			])

			if not isinstance(self.keys, list) or not len(self.keys):
				object.__setattr__(self, 'keys', [
					*primary_keys,
					*unique_keys
				])

			table_query = """
			CREATE TABLE {}. ({})
			ENGINE = InnoDB;
			""".format(self.db.escape(self.table), ',\r\n'.join(fields))

			return self.db.execute(table_query)
		
		return False
	
	def __parse_loaders(self, *args, **kwargs):
		self.load_args = [args, kwargs]

		if len(args) and args[0] and isinstance(args[0], str):
			params = args[1] if len(args) == 2 and args[1] and isinstance(args[1], list) else []
			return (args[0], params)

		if self.keys and isinstance(self.keys, list):
			keys = []
			params = []
			for key in self.keys:
				if kwargs.get(key):
					keys.append(
						'{} = %s'.format(self.db.escape(key))
					)
					params.append(
						kwargs.get(key)
					)
			
			if not len(keys):
				return False
			
			return (' AND '.join(keys), params)

		return False

	def isLoaded(self):
		return hasattr(self, 'keys') and isinstance(self.keys, list) and hasattr(self, self.keys[0]) and self.loaded


	def reload(self):
		if not self.loaded:
			return False
		
		args, kwargs = self.load_args

		return self.load(*args, **kwargs)

	def load(self, *args, **kwargs):
		self.raise_for_load = kwargs.get('raise_for_load', True)
		where = self.__parse_loaders(*args,**kwargs)

		if not where:
			if self.raise_for_load:
				raise DatabaseError(self.__dict__.get('select_error_msg',"This entry doesn't exist"))
			return False

		get_query= self.db.getOne(self.table, '*', where)

		if not get_query:
			raise DatabaseError(self.__dict__.get('select_error_msg',"This entry doesn't exist"))
		
		for name, value in get_query._asdict().items():
			object.__setattr__(self, name, value)
		
		self.unsaved = {}
		self.loaded = True

		return self

	def save(self):
		if not len(self.unsaved):
			return False
		
		args, kwargs = self.load_args

		where = self.__parse_loaders(*args, **kwargs)

		if not where:
			return False

		do_update = self.db.update(self.table, self.unsaved, where)

		if not do_update:
			raise DatabaseError(self.__dict__.get('update_error_msg',"Failed updating this entry"))

		for name, value in self.unsaved.items():
			object.__setattr__(self, name, value)
		
		return self

	@classmethod
	def commit(cls):
		return cls.db.commit()
	
	@classmethod 
	def all(cls, where=None, params=[]):
		return cls.db.getAll(cls.table,'*',
			(where, params) if where else None
		)
	
	@classmethod
	def count(cls, where=None, params=[]):
		get_count = cls.db.getOne(cls.table, 'count(*) as total_count', 
			(where, params) if where else None
		)
		if not get_count:
			raise DatabaseError(cls.__dict__.get('select_error_msg',"No entries found"))
		return get_count.total_count

	@classmethod
	def insert(cls, data):
		return cls.db.insert(cls.table, data)

	@classmethod
	def insertAll(cls, data):
		return cls.db.insertBatch(cls.table, data)

	@classmethod
	def insertOrUpdate(cls,data, update):
		return cls.db.insertOrUpdate(cls.table, data, update)