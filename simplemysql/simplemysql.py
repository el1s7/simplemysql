#!/usr/bin/env python
# vim: fileencoding=utf-8: noexpandtab

"""
	A very simple wrapper for MySQLdb

	Methods:
		getOne() - get a single row
		getAll() - get all rows
		lastId() - get the last insert id
		lastQuery() - get the last executed query
		insert() - insert a row
		insertBatch() - Batch Insert
		insertOrUpdate() - insert a row or update it if it exists
		update() - update rows
		delete() - delete rows
		query()  - run a raw sql query
		leftJoin() - do an inner left join query and get results

	License: GNU GPLv2

	Kailash Nadh, http://nadh.in
	May 2013
"""

import MySQLdb, sqlite3
from collections import namedtuple
from itertools import repeat
import re

from .helpers import mysql_escape_string
from .model import Model

class SimpleMysql:
	conn = None
	cur = None
	conf = None

	def __init__(self, **kwargs):
		self.conf = kwargs
		self.conf["keep_alive"] = kwargs.get("keep_alive", False)
		self.conf["charset"] = kwargs.get("charset", "utf8")
		self.conf["file"] = kwargs.get("file", False)
		self.conf["read_only"] = kwargs.get("read_only", False)
		self.conf["host"] = kwargs.get("host", "localhost")
		self.conf["port"] = kwargs.get("port", 3306)
		self.conf["autocommit"] = kwargs.get("autocommit", False)
		self.conf["read_timeout"] = kwargs.get("read_timeout",60)
		self.conf["ssl"] = kwargs.get("ssl", False)
		self.conf["table_escape"] = kwargs.get("table_escape", '`')
		self.connect()

		class ModelExtend(Model):
			pass

		ModelExtend.db = self

		self.Model = ModelExtend

	def connect(self):
		if self.conf['file']:
			return self.connect_file()
		
		return self.connect_server()

	def connect_server(self):
		"""Connect to the mysql server"""

		try:
			if not self.conf["ssl"]:
			    self.conn = MySQLdb.connect(db=self.conf['db'], host=self.conf['host'],
										port=self.conf['port'], user=self.conf['user'],
										passwd=self.conf['passwd'],
										charset=self.conf['charset'],read_timeout=self.conf["read_timeout"])
			else:
			    self.conn = MySQLdb.connect(db=self.conf['db'], host=self.conf['host'],
										port=self.conf['port'], user=self.conf['user'],
										passwd=self.conf['passwd'],
										ssl=self.conf['ssl'],
										charset=self.conf['charset'],read_timeout=self.conf["read_timeout"])
			self.cur = self.conn.cursor()
			self.conn.autocommit(self.conf["autocommit"])
		except:
			print ("MySQL connection failed")
			raise
	
	def connect_file(self):
		"""Connect to a local file or a :memory: database"""
		kwarg = {
			'database': self.conf['file'],
			'timeout': self.conf['read_timeout']
		}
		
		if self.conf['autocommit']:
			kwarg['isolation_level']=None

		try:
			self.conn = sqlite3.connect(**kwarg)
			# self.conn.set_autocommit(self.conf["autocommit"])
			self.cur = self.conn.cursor()
		except:
			print ("MySQL connection failed")
			raise


	def getOne(self, table=None, fields='*', where=None, order=None, limit=(0, 1)):
		"""Get a single result

			table = (str) table_name
			fields = (field1, field2 ...) list of fields to select
			where = ("parameterizedstatement", [parameters])
					eg: ("id=%s and name=%s", [1, "test"])
			order = [field, ASC|DESC]
			limit = [limit1, limit2]
		"""

		cur = self._select(table, fields, where, order, limit)
		result = cur.fetchone()

		row = None
		if result:
			Row = namedtuple("Row", [f[0] for f in cur.description])
			row = Row(*result)

		return row


	def getAll(self, table=None, fields='*', where=None, order=None, limit=None):
		"""Get all results

			table = (str) table_name
			fields = (field1, field2 ...) list of fields to select
			where = ("parameterizedstatement", [parameters])
					eg: ("id=%s and name=%s", [1, "test"])
			order = [field, ASC|DESC]
			limit = [limit1, limit2]
		"""

		cur = self._select(table, fields, where, order, limit)
		result = cur.fetchall()

		rows = None
		if result:
			Row = namedtuple("Row", [f[0] for f in cur.description])
			rows = [Row(*r) for r in result]

		return rows

	def lastId(self):
		"""Get the last insert id"""
		return self.cur.lastrowid

	def lastQuery(self):
		"""Get the last executed query"""
		try:
			return self.cur.statement
		except AttributeError:
			return self.cur._last_executed

	def leftJoin(self, tables=(), fields=(), join_fields=(), where=None, order=None, limit=None):
		"""Run an inner left join query

			tables = (table1, table2)
			fields = ([fields from table1], [fields from table 2])  # fields to select
			join_fields = (field1, field2)  # fields to join. field1 belongs to table1 and field2 belongs to table 2
			where = ("parameterizedstatement", [parameters])
					eg: ("id=%s and name=%s", [1, "test"])
			order = [field, ASC|DESC]
			limit = [limit1, limit2]
		"""

		cur = self._select_join(tables, fields, join_fields, where, order, limit)
		result = cur.fetchall()

		rows = None
		if result:
			Row = namedtuple("Row", [f[0] for f in cur.description])
			rows = [Row(*r) for r in result]

		return rows


	def insert(self, table, data):
		"""Insert a record"""

		query = self._serialize_insert(data)

		sql = "INSERT INTO %s (%s) VALUES(%s)" % (table, query[0], query[1])

		return self.query(sql, list(data.values())).rowcount

	def insertBatch(self, table, data):
		"""Insert multiple record"""

		query = self._serialize_batch_insert(data)
		sql = "INSERT INTO %s (%s) VALUES %s" % (table, query[0], query[1])
		flattened_values = [v for sublist in data for k,v in sublist.items()]
		return self.query(sql,flattened_values).rowcount

	def update(self, table, data, where = None):
		"""Insert a record"""

		query = self._serialize_update(data)

		sql = "UPDATE %s SET %s" % (table, query)

		if where and len(where) > 0:
			sql += " WHERE %s" % where[0]

		return self.query(sql, list(data.values()) + where[1] if where and len(where) > 1 else list(data.values())
						).rowcount


	def insertOrUpdate(self, table, data, keys):
		insert_data = data.copy()

		data = {k: data[k] for k in data if k not in keys}

		insert = self._serialize_insert(insert_data)

		update = self._serialize_update(data)

		sql = "INSERT INTO %s (%s) VALUES(%s) ON DUPLICATE KEY UPDATE %s" % (table, insert[0], insert[1], update)

		return self.query(sql, list(insert_data.values()) + list(data.values()) ).rowcount

	def delete(self, table, where = None):
		"""Delete rows based on a where condition"""

		sql = "DELETE FROM %s" % table

		if where and len(where) > 0:
			sql += " WHERE %s" % where[0]

		return self.query(sql, where[1] if where and len(where) > 1 else None).rowcount


	def query(self, sql, params = []):
		"""Run a raw query"""
		params = params if params and len(params) > 0 else None

		# check if connection is alive. if not, reconnect
		try:
			self.cur.execute(sql, params)
		except MySQLdb.OperationalError as e:
			# mysql timed out. reconnect and retry once
			if e.args[0] == 2006 or e.args[0] == 2013:
				self.connect()
				self.cur.execute(sql, params)
			else:
				raise
		except:
			print("Query failed")
			raise

		return self.cur
		
	
	def execute(self, sql, params=[]):
		return self.query(sql, params)

	def escape_string(self, s):
		return mysql_escape_string(s)

	def escape(self, s):
		return self.escape_string(s)

	def executemany(self, sql, params=[]):
		"""Run a raw query"""

		# check if connection is alive. if not, reconnect
		try:
			self.cur.executemany(sql, params)
		except MySQLdb.OperationalError as e:
			# mysql timed out. reconnect and retry once
			if e.args[0] == 2006 or e.args[0] == 2013:
				self.connect()
				self.executemany(sql, params)
			else:
				raise
		except:
			print("Query failed")
			raise

		return self.cur

	def commit(self):
		"""Commit a transaction (transactional engines like InnoDB require this)"""
		return self.conn.commit()

	def is_open(self):
		"""Check if the connection is open"""
		return self.conn.open

	def end(self):
		"""Kill the connection"""
		self.cur.close()
		self.conn.close()

	# ===

	def _serialize_insert(self, data):
		"""Format insert dict values into strings"""
		keys = ",".join( list(data.keys()) )
		vals = ",".join(["%s" for k in data])

		return [keys, vals]

	def _serialize_batch_insert(self, data):
		"""Format insert dict values into strings"""
		keys = ",".join( list(data[0].keys()) )
		v = "(%s)" % ",".join(tuple("%s".rstrip(',') for v in range(len(data[0]))))
		l = ','.join(list(repeat(v,len(data))))
		return [keys, l]

	def _serialize_update(self, data):
		"""Format update dict values into string"""
		return "=%s,".join( list(data.keys()) ) + "=%s"


	def _select(self, table=None, fields=(), where=None, order=None, limit=None):
		"""Run a select query"""

		sql = "SELECT %s FROM %s%s%s" % (
			",".join(fields) if isinstance(fields, list) or isinstance(fields, tuple) else fields, 
			self.conf["table_escape"], table, self.conf["table_escape"]
		)

		# where conditions
		if where and len(where) > 0:
			is_not_where = re.match(r"^(\s+)?(limit [0-9]+|order by)", where[0])
			sql += " %s" % where[0] if is_not_where else " WHERE %s" % where[0]

		# order
		if order:
			sql += " ORDER BY %s" % order[0]

			if len(order) > 1:
				sql+= " %s" % order[1]

		# limit
		if limit:
			sql += " LIMIT %s" % limit[0]

			if len(limit) > 1:
				sql+= ", %s" % limit[1]

		return self.query(sql, where[1] if where and len(where) > 1 else None)

	def _select_join(self, tables=(), fields=(), join_fields=(), where=None, order=None, limit=None):
		"""Run an inner left join query"""

		fields = [tables[0] + "." + f for f in fields[0]] + \
				 [tables[1] + "." + f for f in fields[1]]

		sql = "SELECT %s FROM %s LEFT JOIN %s ON (%s = %s)" % \
				( 	",".join(fields) if isinstance(fields, list) or isinstance(fields, tuple) else fields,
					tables[0],
					tables[1],
					tables[0] + "." + join_fields[0], \
					tables[1] + "." + join_fields[1]
				)

		# where conditions
		if where and len(where) > 0:
			sql += " WHERE %s" % where[0]

		# order
		if order:
			sql += " ORDER BY %s" % order[0]

			if len(order) > 1:
				sql+= " " + order[1]

		# limit
		if limit:
			sql += " LIMIT %s" % limit[0]

			if len(limit) > 1:
				sql+= ", %s" % limit[1]

		return self.query(sql, where[1] if where and len(where) > 1 else None)

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.end()
