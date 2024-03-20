import sqlite3
import streamlit as st
import os
import configparser
import ast
#clear no error in creating schema

# Create or check for the 'database' directory in the current working directory
class ConfigHandler:
	def __init__(self):
		self.config = configparser.ConfigParser()
		self.config.read('config.ini')

	def get_value(self, section, key):
		value = self.config.get(section, key)
		try:
			# Convert string value to a Python data structure
			return ast.literal_eval(value)
		except (SyntaxError, ValueError):
			# If not a data structure, return the plain string
			return value

# Initialization
config_handler = ConfigHandler()
SQL_DB = config_handler.get_value('DATABASE', 'SQL_DB')
	
def create_sql_db():
	cwd = os.getcwd()
	WORKING_DIRECTORY = os.path.join(cwd, "database")
	if not os.path.exists(WORKING_DIRECTORY):
		os.makedirs(WORKING_DIRECTORY)
	WORKING_DATABASE = os.path.join(WORKING_DIRECTORY , SQL_DB)
	
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()

	cursor.execute('''
	CREATE TABLE IF NOT EXISTS Data_Table (
		data_id INTEGER PRIMARY KEY AUTOINCREMENT,
		date TEXT,
		user_id TEXT NOT NULL,
		profile_id TEXT NOT NULL,
		school_id TEXT NOT NULL,
		chatbot_ans TEXT,
		user_prompt TEXT,
		function_name TEXT,
		tokens INTEGER
	)
	
	''')
#not in use if you are not running the workshop
	cursor.execute('''
	CREATE TABLE IF NOT EXISTS Chatbot_Training_Records (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		chatbot_type TEXT NOT NULL,
		chatbot_name TEXT NOT NULL,
		prompt TEXT NOT NULL,
		response TEXT NOT NULL,
		user_id TEXT NOT NULL,
		school_id TEXT NOT NULL
	)
	''')

	conn.commit()
