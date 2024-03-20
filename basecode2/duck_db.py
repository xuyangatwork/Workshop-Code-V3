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
    
def create_config_table(table_name):
    """
    Creates a configuration table in DuckDB.
    """
    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            sch_name VARCHAR,
            key VARCHAR,
            value VARCHAR,
            PRIMARY KEY (sch_name, key)
        );
    """
    conn.execute(create_table_sql)

    
def insert_or_update_config(table_name, sch_name, config):
    """
    Inserts or updates configuration settings in the specified table.
    """
    for key, value in config.items():
        # Convert value to a string to store in the VARCHAR column
        value_str = str(value)
        
        # Insert or update the setting
        conn.execute(f"""
            INSERT INTO {table_name} (sch_name, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT (sch_name, key) DO UPDATE SET value = EXCLUDED.value
        """, (sch_name, key, value_str))
        
    
def modify_config_setting(operation, table_name, sch_name, key, value=None):
    """
    Modifies a configuration setting in the specified table.
    
    Parameters:
    - operation: The type of operation to perform ('insert', 'edit', 'remove').
    - table_name: The name of the table containing the configuration.
    - sch_name: The school name or identifier for the configuration setting.
    - key: The configuration key to modify.
    - value: The new value for the configuration setting (required for 'insert' and 'edit').
    """
    if operation in ['insert', 'edit']:
        if value is None:
            raise ValueError("Value is required for insert and edit operations.")
        # Insert or update the setting
        conn.execute(f"""
            INSERT INTO {table_name} (sch_name, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT (sch_name, key) DO UPDATE SET value = EXCLUDED.value
        """, (sch_name, key, str(value)))
    elif operation == 'remove':
        # Delete the setting
        conn.execute(f"""
            DELETE FROM {table_name} WHERE sch_name = ? AND key = ?
        """, (sch_name, key))
    else:
        raise ValueError("Unsupported operation. Use 'insert', 'edit', or 'remove'.")
  
def remove_all_settings_by_sch_name(table_name, sch_name):
    """
    Removes all configuration settings for a given school name or identifier.
    
    Parameters:
    - table_name: The name of the table containing the configuration.
    - sch_name: The school name or identifier whose settings are to be removed.
    """
    conn.execute(f"""
        DELETE FROM {table_name} WHERE sch_name = ?
    """, (sch_name,))


#to check if a variable exists in the app_config_table

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