from .exceptions import DatabaseError
from .helpers import run_once

class Model:

	__protected__ = [
		'db',
		'table',
		'columns',
		'keys',
		'select_error_msg',
		'update_error_msg',
		'insert_error_msg',
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

	db = None

	'''	
		Configuration
	'''
	table = '' # Table Name
	
	columns = [] # Table Columns

	keys = [] # Table Index Keys

	select_error_msg = ""
	update_error_msg = ""
	insert_error_msg = ""


	def __init__(self, **kwargs):
		self.__create()
		self.load(**kwargs)
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
	
	def __parse_loaders(self, **kwargs):
		self.load_args = kwargs
		self.loaders = []
		if self.keys and isinstance(self.keys, list):
			for key in self.keys:
				if kwargs.get(key):
					escaped_value = kwargs.get(key) if isinstance(kwargs.get(key), int) else (
						"'%s'" % self.db.escape(kwargs.get(key))
					)
					self.loaders.append(
						'`{}` = {}'.format(self.db.escape(key), escaped_value)
					)

		return self.loaders

	def isLoaded(self):
		return hasattr(self, 'keys') and isinstance(self.keys, list) and hasattr(self, self.keys[0]) and self.loaded

	def load(self, **kwargs):
		self.raise_for_load = kwargs.get('raise_for_load', True)
		self.loaders = self.__parse_loaders(**kwargs)

		if not len(self.loaders):
			if self.raise_for_load:
				raise DatabaseError(self.__dict__.get('select_error_msg',"This entry doesn't exist"))
			return False

		query_selector = "SELECT * FROM {} WHERE {}".format(
			self.table, 
			' AND '.join(self.loaders)
		)

		get_query = self.db.query(query_selector)
		if not get_query:
			raise DatabaseError(self.__dict__.get('select_error_msg',"This entry doesn't exist"))
		
		fetch_one = get_query.fetchone()
		
		if not fetch_one:
			raise DatabaseError(self.__dict__.get('select_error_msg',"This entry doesn't exist"))
		
		for n in range(len(fetch_one)):
			name = self.db.cur.description[n]
			value = fetch_one[n]
			object.__setattr__(self, name, value)
		
		self.unsaved = {}
		self.loaded = True

		return True

	def save(self):
		if not len(self.unsaved):
			return False

		self.loaders = self.__parse_loaders(self.load_args)

		if not len(self.loaders):
			return False

		do_update = self.db.update(self.table, self.unsaved, [' AND '.join(self.loaders)])

		if not do_update:
			raise DatabaseError(self.__dict__.get('update_error_msg',"Failed updating this entry"))

		for name, value in self.unsaved.items():
			object.__setattr__(self, name, value)
		
		return True

	@classmethod
	def commit(cls):
		return cls.db.commit()
	
	@classmethod 
	def all(cls, where=None):
		return cls.db.getAll(cls.table,'*',where)
	
	@classmethod
	def count(cls, where=None):
		get_count = cls.db.getOne(cls.table, 'count(*) as total_count', where)
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