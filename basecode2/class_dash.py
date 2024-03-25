import sqlite3
import streamlit as st
import pandas as pd
from basecode2.org_module import sa_select_school, fetch_my_students_from_class
import os
import configparser
import os
import ast
# Create or check for the 'database' directory in the current working directory

#WORKING DATABASE REMOVED
	
class ConfigHandler:
	def __init__(self):
		self.config = configparser.ConfigParser()
		self.config.read('config.ini')

	def get_config_values(self, section, key):
		value = self.config.get(section, key)
		try:
			# Try converting the string value to a Python data structure
			return ast.literal_eval(value)
		except (SyntaxError, ValueError):
			# If not a data structure, return the plain string
			return value
		
config_handler = ConfigHandler()
TCH = config_handler.get_config_values('constants', 'TCH')
STU = config_handler.get_config_values('constants', 'STU')
SA = config_handler.get_config_values('constants', 'SA')
AD = config_handler.get_config_values('constants', 'AD')
SQL_DB = config_handler.get_config_values('DATABASE', 'SQL_DB')

cwd = os.getcwd()
WORKING_DIRECTORY = os.path.join(cwd, "database")
WORKING_DATABASE = os.path.join(WORKING_DIRECTORY , SQL_DB)


def class_dash():
	if st.session_state.user['profile_id'] == SA:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', sch_names, key='app_school')
		st.write(f"#### :blue[School Selected: {school}]")
		if st.checkbox("Show all schools data"):
			data, columns = fetch_all_data()
			display_data(data, columns)
		else:
			if st.button("Show selected school data"):
				# action = st.selectbox('Select Action', ['All', 'By Function', 'By Username'])
				# if action == 'All':
					data, columns = fetch_data_by_school(school)
					display_data(data, columns)

	elif st.session_state.user['profile_id'] == AD:
		st.write(f"#### :blue[School Selected: {st.session_state.user['school_id']}]")
		if st.button("Show School Data"):
			data, columns = fetch_data_by_school(st.session_state.user['school_id'])
			display_data(data, columns)

	elif st.session_state.user['profile_id'] == STU:
		st.write(f"#### :blue[School Selected: {st.session_state.user['school_id']}]")
		if st.button("Show personal data"):
			data, columns = fetch_data_by_username(st.session_state.user['id'])
			display_data(data, columns)
	else:
		st.write(f"#### :blue[School Selected: {st.session_state.user['school_id']}]")
		action = st.selectbox('Select Action', ['Personal', 'Class'])
		if action == 'Personal':
			if st.button("Show personal data"):
				data, columns = fetch_data_by_username(st.session_state.user['id'])
				display_data(data, columns)
		else:
			if st.button("Show class data"):
				students = fetch_my_students_from_class(st.session_state.user['id']	)
				data, columns = fetch_data_by_students(students)
				display_data(data, columns)
				pass

def display_data(data, columns):
	if len(data) == 0:
		st.write("No data available")
	else:
		df = pd.DataFrame(data, columns=columns)
		st.dataframe(df)

def fetch_all_data():
	# Connect to the specified database
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()

	# Fetch all data from data_table
	cursor.execute("SELECT * FROM Data_Table")
	rows = cursor.fetchall()
	column_names = [description[0] for description in cursor.description]
	
	conn.close()
	return rows, column_names

def fetch_data_by_username(user_id):
	# Connect to the specified database
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()

	# Fetch data from data_table based on the given username
	cursor.execute("SELECT * FROM Data_Table WHERE user_id=?", (user_id,))
	rows = cursor.fetchall()
	column_names = [description[0] for description in cursor.description]
	
	conn.close()
	return rows, column_names

def fetch_data_by_students(list_of_students):
	# Connect to the specified database
	conn = sqlite3.connect(WORKING_DATABASE)  # Ensure to have the correct path to your database
	cursor = conn.cursor()
	
	# Generate placeholders for each item in the list
	placeholders = ','.join('?' for _ in list_of_students)
	
	# Fetch data from data_table based on the given username
	query = "SELECT * FROM Data_Table WHERE user_id IN ({})".format(placeholders)
	cursor.execute(query, list_of_students)
	
	rows = cursor.fetchall()
	column_names = [description[0] for description in cursor.description]
	
	conn.close()
	return rows, column_names

def fetch_data_by_school(sch_id):
	# Connect to the specified database
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()

	# Fetch data from data_table based on the given username
	cursor.execute("SELECT * FROM Data_Table WHERE school_id=?", (sch_id,))
	rows = cursor.fetchall()
	column_names = [description[0] for description in cursor.description]
	
	conn.close()
	return rows, column_names


def fetch_data_by_function(func):
	# Connect to the specified database
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()

	# Fetch data from data_table based on the given username
	cursor.execute("SELECT * FROM Data_Table WHERE function_name=?", (func,))
	rows = cursor.fetchall()
	column_names = [description[0] for description in cursor.description]
	
	conn.close()
	return rows, column_names
