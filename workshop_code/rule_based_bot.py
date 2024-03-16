import streamlit as st
import os
import pandas as pd
import sqlite3
import string
import ast
import configparser

cwd = os.getcwd()
WORKING_DIRECTORY = os.path.join(cwd, "database")
WORKING_DATABASE = os.path.join(WORKING_DIRECTORY , "default.db")

class ConfigHandler:
	def __init__(self):
		self.config = configparser.ConfigParser()
		self.config.read('config.ini')

	def get_config_values(self, section, key):
		value = self.config.get(section, key)
		try:
			# Convert string value to a Python data structure
			return ast.literal_eval(value)
		except (SyntaxError, ValueError):
			# If not a data structure, return the plain string
			return value

# Initialization
config_handler = ConfigHandler()
SA = config_handler.get_config_values('constants', 'SA')
RULE_BASED = config_handler.get_config_values('constants', 'RULE_BASED')


def clear_session_states():
	st.session_state.messages = []
	if "memory" not in st.session_state:
		pass
	else:
		del st.session_state["memory"]


def rule_based():
	st.write("Rules for the chatbot:")
	df = pd.DataFrame(
		[
			{"prompt": "Hello", "response": "Hi there what can I do for you"},
			{
				"prompt": "What is your name?",
				"response": "My name is EAI , an electronic artificial being"
			},
			{"prompt": "How old are you?", "response": "Today is my birthday!"},
		]
	)

	edited_df = st.data_editor(df, num_rows="dynamic")
	st.divider()
	# Initialize chat history
	if "messages" not in st.session_state:
		st.session_state.messages = []

	# Display chat messages from history on app rerun
	for message in st.session_state.messages:
		with st.chat_message(message["role"]):
			st.markdown(message["content"])

	# React to user input
	if prompt := st.chat_input("Enter your prompt"):
		if prompt in edited_df["prompt"].values:
			reply = edited_df.loc[edited_df["prompt"] == prompt]["response"].values[0]
		else:
			reply = "I don't understand"

		with st.chat_message("user"):
			st.write(prompt)
			st.session_state.messages.append({"role": "user", "content": prompt})
		with st.chat_message("assistant"):
			st.write(reply)
			st.session_state.messages.append({"role": "assistant", "content": reply})

def init_training_data():
	# Base data for initialization
	initial_data = [
		{"prompt": "Hello", "response": "Hi there what can I do for you"},
		{"prompt": "What is your name?", "response": "My name is EAI, an electronic artificial being"},
		{"prompt": "How old are you?", "response": "Today is my birthday!"}
	]

	# Creating a list of 10 DataFrames for each chatbot
	global_dfs = []
	for i in range(1, 16):
		chatbot_name = f"rb_chatbot{i}"
		df = pd.DataFrame(initial_data)
		df['chatbot_type'] = RULE_BASED
		df['chatbot_name'] = chatbot_name
		global_dfs.append(df)

	with sqlite3.connect(WORKING_DATABASE) as conn:
		cursor = conn.cursor()

		# Delete existing data
		cursor.execute('DELETE FROM Chatbot_Training_Records')

		# Insert data into Chatbot_Training_Records
		for df in global_dfs:
			for _, row in df.iterrows():
				cursor.execute('''
					INSERT INTO Chatbot_Training_Records (chatbot_type, chatbot_name, prompt, response, user_id, school_id) 
					VALUES (?, ?, ?, ?, ?, ?)
				''', (row['chatbot_type'], row['chatbot_name'], row['prompt'], row['response'], 0, 0))

		conn.commit()

def clean_string(input_str):
	return input_str.strip(string.punctuation + string.whitespace).lower()

def group_rule_based():
	# Database connection
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()

	st.write("Rules for the chatbot:")

	# Select the chatbot from rb_chatbot1 to rb_chatbot10
	chatbot_selection = st.selectbox("Select a Chatbot", [f"rb_chatbot{i}" for i in range(1, 16)])

	# Extract the data from the database
	# Extract the data from the database and join with Users table to get the username
	cursor.execute("""
		SELECT id, user_id, chatbot_name, prompt, response 
		FROM Chatbot_Training_Records
		WHERE chatbot_name = ?
	""", (chatbot_selection,))
	rows = cursor.fetchall()
	df = pd.DataFrame(rows, columns=['id', 'user_id', 'chatbot_name', 'prompt', 'response'])
	with st.expander("Enter Rules"):
		# Display and edit data
		st.write(df)

		# Adding new rules
		new_prompt = st.text_input("Enter new prompt")
		new_response = st.text_input("Enter new response")
		if st.button("Add Rule"):
			if new_prompt and new_response:
				cursor.execute("INSERT INTO Chatbot_Training_Records (chatbot_type, chatbot_name, prompt, response, user_id, school_id) VALUES (?, ?, ?, ?, ?, ?)",
							(RULE_BASED, chatbot_selection, new_prompt, new_response, st.session_state.user['id'], st.session_state.user['school_id']))
				conn.commit()
				st.success("New rule added")
				st.rerun()

		# Select a row ID to delete
		if not df.empty:
			delete_id = st.selectbox("Select a row ID to delete", df['id'])
			if st.button("Delete Row"):
				cursor.execute("DELETE FROM Chatbot_Training_Records WHERE id = ?", (delete_id,))
				conn.commit()
				st.success(f"Row with ID {delete_id} deleted successfully!")
				st.rerun()

		conn.close()
	
	if st.button("Clear Chat"):
		clear_session_states()

	st.divider()
	st.subheader("Rule based Chatbot")

	# Initialize chat history
	if "messages" not in st.session_state:
		st.session_state.messages = []

	# Display chat messages from history on app rerun
	for message in st.session_state.messages:
		with st.chat_message(message["role"]):
			st.markdown(message["content"])

	# React to user input
	if prompt := st.chat_input("Enter your prompt"):
		cleaned_prompt = clean_string(prompt)

		# Find a matching response by comparing cleaned prompts
		matching_responses = df[df['prompt'].apply(clean_string) == cleaned_prompt]['response']
		reply = matching_responses.iloc[0] if not matching_responses.empty else "I don't understand"

		with st.chat_message("user"):
			st.write(prompt)
			st.session_state.messages.append({"role": "user", "content": prompt})
		with st.chat_message("assistant"):
			st.write(reply)
			st.session_state.messages.append({"role": "assistant", "content": reply})

	# Close the database connection
	conn.close()

def main_rule_based():
    # Code for Rule Based Chatbot - Zerocode
    if st.session_state.user['profile_id'] == SA:
        with st.expander("Rule Based Chatbot Settings"):
            rb_chatbot = st.checkbox("I will delete and initialise training data for rule based chatbot")
            if st.button("Initialise Training Data") and rb_chatbot:
                init_training_data()
            pass

    personal = st.toggle('Switch on to access the Personal Chatbot')
    if personal:
        rule_based()
    else:
        group_rule_based()