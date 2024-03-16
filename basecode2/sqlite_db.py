import sqlite3
import streamlit as st
import os
#clear no error in creating schema

# Create or check for the 'database' directory in the current working directory

	
def create_sql_db():
    cwd = os.getcwd()
    WORKING_DIRECTORY = os.path.join(cwd, "database")
    WORKING_DATABASE = os.path.join(WORKING_DIRECTORY , "default.db")

    if not os.path.exists(WORKING_DIRECTORY):
        os.makedirs(WORKING_DIRECTORY)
    
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
