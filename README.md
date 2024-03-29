## SimpleMysql

An simple MySQL wrapper and ORM for Python3

## Reference
- [Installation](#installation)
- [Usage](#usage)
- [API](#api)
- [ORM Model](#model)

## Installation
```pip3 install git+https://github.com/elis-k/simplemysql```


# Usage

## For normal connection
```python
from simplemysql import SimpleMysql

db = SimpleMysql(
	host="127.0.0.1",
	db="mydatabase",
	user="username",
	passwd="password",
	keep_alive=True # try and reconnect timedout mysql connections?
)
```

## For SSL Connection
```python
from simplemysql import SimpleMysql

db = SimpleMysql(
    host="127.0.0.1",
    db="mydatabase",
    user="username",
    passwd="password",
    ssl = {'cert': 'client-cert.pem', 'key': 'client-key.pem'},
    keep_alive=True # try and reconnect timedout mysql connections?
)

```
## For SQLite Connection
```python
from simplemysql import SimpleMysql

db = SimpleMysql(
	file='./data.db' # Or :memory: for memory
)

```

Then after you've connected you can start using the API just like this
```python
# insert a record to the <em>books</em> table
db.insert("books", {"type": "paperback", "name": "Time Machine", "price": 5.55, year: "1997"})

book = db.getOne("books", ["name"], ["year = 1997"])

print "The book's name is " + book.name
```


# API
insert(), update(), delete(), getOne(), getAll(), lastId(), query()

## insert(table, record{})
Inserts a single record into a table.

```python
db.insert("food", {"type": "fruit", "name": "Apple", "color": "red"})
db.insert("books", {"type": "paperback", "name": "Time Machine", "price": 5.55})
```

## update(table, row{}, condition[])
Update one more or rows based on a condition (or no condition).

```python
# update all rows
db.update("books", {"discount": 0})

# update rows based on a simple hardcoded condition
db.update("books",
	{"discount": 10},
	["id=1"]
)

# update rows based on a parametrized condition
db.update("books",
	{"discount": 10},
	("id=%s AND year=%s", [id, year])
)
```
## insertBatch(table, rows{})
Insert Multiple values into table.

```python
# insert multiple values in table
db.insertBatch("books", [{"discount": 0},{"discount":1},{"discount":3}])
```

## insertOrUpdate(table, row{}, keys)
Insert a new row, or update if there is a primary key conflict.

```python
# insert a book with id 123. if it already exists, update values
db.insertOrUpdate("books",
		{"id": 123, type": "paperback", "name": "Time Machine", "price": 5.55},
		["id"]
)
```

## getOne(table, fields[], where[], order[], limit[])
## getAll(table, fields[], where[], order[], limit[])
Get a single record or multiple records from a table given a condition (or no condition). The resultant rows are returned as namedtuples. getOne() returns a single namedtuple, and getAll() returns a list of namedtuples.

```python
book = db.getOne("books", ["id", "name"])
```

```python
# get a row based on a simple hardcoded condition
book = db.getOne("books", ["name", "year"], ("id=1"))
```

```python
# get multiple rows based on a parametrized condition
books = db.getAll("books",
	["id", "name"],
	("year > %s and price < %s", [year, 12.99])
)
```

```python
# get multiple rows based on a parametrized condition with an order and limit specified
books = db.getAll("books",
	["id", "name", "year"],
	("year > %s and price < %s", [year, 12.99]),
	["year", "DESC"],	# ORDER BY year DESC
	[0, 10]			# LIMIT 0, 10
)
```
## lastId()
Get the last insert id
```python
# get the last insert ID
db.lastId()
```

## lastQuery()
Get the last query executed
```python
# get the SQL of the last executed query
db.lastQuery()
```

## delete(table, fields[], condition[], order[], limit[])
Delete one or more records based on a condition (or no condition)

```python
# delete all rows
db.delete("books")

# delete rows based on a condition
db.delete("books", ("price > %s AND year < %s", [25, 1999]))
```

## query(table)
Run a raw SQL query. The MySQLdb cursor is returned.

```python
# run a raw SQL query
db.query("DELETE FROM books WHERE year > 2005")
```

## commit()
Insert, update, and delete operations on transactional databases such as innoDB need to be committed

```python
# Commit all pending transaction queries
db.commit()
```

## Model

A light-weight ORM class 

```python
from SimpleMysql import Model

class Users(Model):

	table='users'
	
	'''
		You can either set columns as a list or a specify column dict schema.
		By using dict schema (like example below), table will get auto-created if it doesn't exist.
	'''
	columns={
		'id':{
			'type': 'INT',
			'primary': True,
			'autoInrement':True,
		},
		'email':{
			'type': 'VARCHAR',
			'length': '255',
			'unique': True
		},
		'username':{
			'type': 'VARCHAR',
			'length': '100',
			'unique': True
		},
		'full_name':{
			'type': 'VARCHAR',
			'null': True,
		},
		'age':{
			'type': 'INT',
		},
		'date_added':{
			'type': 'DATETIME',
			'default': 'CURRENT_TIMESTAMP'
		}
	}


# Load an user | Using the index keys only
user = Users(id=5)
print(user.full_name)

# Load with multiple Index Keys (Joined with AND)
user = Users(username='jack', email='jack1@email.com')
print(user.full_name)

# Load with custom WHERE SQL
user = Users("username = %s AND age > 21 AND (date_added > NOW() - INTERVAL 12 DAYS)", ['jack'])
print(user.full_name)

# Update user
user.age = user.age + 1
user.email = "update@email.com"
user.save()
# user.commit() if autocommit is turned off
```

Base version forked from https://github.com/knadh/simplemysql :)

