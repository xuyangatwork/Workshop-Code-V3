import duckdb
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
conn = duckdb.connect(SQL_DB)

def initialise_duckdb():
    # Create the app_config_table if it doesn't exist
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_config_table (
            condition VARCHAR,
            value VARCHAR
        );
    """)
    
def check_condition_value(condition, value):
    """Checks if a given condition and its value exist in the app_config_table."""
    query_result = conn.execute("""
        SELECT EXISTS (
            SELECT 1 FROM app_config_table WHERE condition = ? AND value = ?
        );
    """, (condition, value)).fetchone()
    return query_result[0] == 1


def insert_condition_value(condition, value):
    """Inserts a new condition and its value into the app_config_table."""
    conn.execute("""
        INSERT INTO app_config_table (condition, value) VALUES (?, ?)
    """, (condition, value))


def get_value_by_condition(condition):
    """Retrieves the value for a given condition from the app_config_table."""
    query_result = conn.execute("""
        SELECT value FROM app_config_table WHERE condition = ?
    """, (condition,)).fetchone()
    return query_result[0] if query_result else None