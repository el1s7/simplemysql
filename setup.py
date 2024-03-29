#!/usr/bin/env python

from setuptools import setup

setup(
	name="simplemysql",
	version="2.0.0",
	description="An ultra simple wrapper for Python MySQLdb with very basic functionality",
	author="Elis",
	author_email="github@elis.cc",
	packages=['simplemysql'],
	download_url="http://github.com/elis-k/simplemysql",
	license="GPLv2",
	classifiers=[
		"Development Status :: 3 - Alpha",
		"Intended Audience :: Developers",
		"Programming Language :: Python",
		"Natural Language :: English",
		"License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
		"Programming Language :: Python :: 3.5",
		"Topic :: Software Development :: Libraries :: Python Modules",
		"Topic :: Database",
		"Topic :: Software Development :: Libraries"
	],
	install_requires=["mysqlclient"]
)
