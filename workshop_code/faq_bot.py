import streamlit as st
from openai import OpenAI
import sqlite3
from basecode2.authenticate import return_openai_key, return_cohere_key
import configparser
import os
import pandas as pd
import cohere
import ast

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
		
config_handler = ConfigHandler()
SA = config_handler.get_config_values('constants', 'SA')
FAQ_BOT = config_handler.get_config_values('constants', 'FAQ_BOT')
SQL_DB = config_handler.get_config_values('DATABASE', 'SQL_DB')

cwd = os.getcwd()
WORKING_DIRECTORY = os.path.join(cwd, "database")
WORKING_DATABASE = os.path.join(WORKING_DIRECTORY , SQL_DB)

def clear_session_states():
	st.session_state.msg = []
	if "memory" not in st.session_state:
		pass
	else:
		del st.session_state["memory"]

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
		df['chatbot_type'] = FAQ_BOT
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


def retrieve_faqs(chatbot_selection):
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()
	cursor.execute("""
			SELECT chatbot_name, prompt, response 
			FROM Chatbot_Training_Records 
			WHERE chatbot_name = ?
		""", (chatbot_selection,))
	rows = cursor.fetchall()
	df = pd.DataFrame(rows, columns=['chatbot_name', 'prompt', 'response'])
	all_records_string = "\n".join([f"Prompt: {row['prompt']}, Response: {row['response']}" for index, row in df.iterrows()])
	conn.close()
	return all_records_string 

def faq_bot():
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()

	st.write("Rules for the chatbot:")

	# Select the chatbot from rb_chatbot1 to rb_chatbot10
	chatbot_selection = st.selectbox("Select a Chatbot", [f"faq_chatbot{i}" for i in range(1, 16)])
	
	# Extract the data from the database
	# Extract the data from the database and join with Users table to get the username
	cursor.execute("""
		SELECT id, user_id, chatbot_name, prompt, response 
		FROM Chatbot_Training_Records
		WHERE chatbot_name = ?
	""", (chatbot_selection,))
	rows = cursor.fetchall()
	df = pd.DataFrame(rows, columns=['id', 'user_id', 'chatbot_name', 'prompt', 'response'])

	with st.expander("Enter FAQ"):
		# Display and edit data
		st.write(df)

		# Adding new rules
		new_prompt = st.text_input("Enter new prompt")
		new_response = st.text_input("Enter new response")
		if st.button("Add Rule"):
			if new_prompt and new_response:
				cursor.execute("INSERT INTO Chatbot_Training_Records (chatbot_type, chatbot_name, prompt, response, user_id, school_id) VALUES (?, ?, ?, ?, ?, ?)",
							(FAQ_BOT, chatbot_selection, new_prompt, new_response, st.session_state.user['id'], st.session_state.user['school_id']))
				conn.commit()
				st.success("New rule added")
				conn.close()
				st.rerun()

		# Select a row ID to delete
		if not df.empty:
			delete_id = st.selectbox("Select a row ID to delete", df['id'])
			if st.button("Delete Row"):
				cursor.execute("DELETE FROM Chatbot_Training_Records WHERE id = ?", (delete_id,))
				conn.commit()
				st.success(f"Row with ID {delete_id} deleted successfully!")
				conn.close()
				st.rerun()

	
	if st.button("Clear Chat"):
		clear_session_states()

	st.divider()
	st.subheader("FAQ Chatbot with AI")
	if st.toggle("Use Cohere"):
		st.write("Using Cohere Model")
		cohere_bot(FAQ_BOT, chatbot_selection)
	else:
		st.write("Using OpenAI Model GPT-3.5 Turbo")
		basebot(FAQ_BOT, chatbot_selection)
	

	# Concatenate all records into a string


#below ------------------------------ base bot , no memory ---------------------------------------------
#chat completion for streamlit function
def chat_completion(prompt, faq):
	client = OpenAI(api_key=return_openai_key())
	faq = "You are an FAQ BOT, these are the faq information given to you:" + faq + "You must use only the information given to you in the faq informatio to answer the user query, do not provide your own information\n This the user query: "
	response = client.chat.completions.create(
		model="gpt-3.5-turbo-1106",
		messages=[
			{"role": "system", "content":faq},
			{"role": "user", "content": prompt},
		],
		stream=True #settings option
	)
	return response

#integration API call into streamlit chat components
def basebot(bot_name, chatbot_selection):
	full_response = ""
	greetings_str = f"Hi, I am {bot_name}"
	help_str = "How can I help you today?"
	# Check if st.session_state.msg exists, and if not, initialize with greeting and help messages
	if 'msg' not in st.session_state:
		st.session_state.msg = [
			{"role": "assistant", "content": greetings_str},
			{"role": "assistant", "content": help_str}
		]
	elif st.session_state.msg == []:
		st.session_state.msg = [
			{"role": "assistant", "content": greetings_str},
			{"role": "assistant", "content": help_str}
		]
	for message in st.session_state.msg:
		with st.chat_message(message["role"]):
			st.markdown(message["content"])
	try:
		if prompt := st.chat_input("Enter a query"):
			faq = retrieve_faqs(chatbot_selection)

			st.session_state.msg.append({"role": "user", "content": prompt})
			with st.chat_message("user"):
				st.markdown(prompt)

			with st.chat_message("assistant"):
				message_placeholder = st.empty()
				full_response = ""
				for response in chat_completion(prompt, faq):
					full_response += (response.choices[0].delta.content or "")
					message_placeholder.markdown(full_response + "▌")
				message_placeholder.markdown(full_response)
			
			st.session_state.msg.append({"role": "assistant", "content": full_response})
				
	except Exception as e:
		st.error(e)


def cohere_bot(bot_name, chatbot_selection):
	full_response = ""
	greetings_str = f"Hi, I am {bot_name}"
	help_str = "How can I help you today?"
	co = cohere.Client(return_cohere_key())
	#co = cohere.Client(st.secrets["cohere_key"])
	# Check if st.session_state.msg exists, and if not, initialize with greeting and help messages
	if 'msg' not in st.session_state:
		st.session_state.msg = [
			{"role": "assistant", "content": greetings_str},
			{"role": "assistant", "content": help_str}
		]
	elif st.session_state.msg == []:
		st.session_state.msg = [
			{"role": "assistant", "content": greetings_str},
			{"role": "assistant", "content": help_str}
		]
	for message in st.session_state.msg:
		with st.chat_message(message["role"]):
			st.markdown(message["content"])
	try:
		if prompt := st.chat_input("Enter a query"):
			faq = retrieve_faqs(chatbot_selection)

			st.session_state.msg.append({"role": "user", "content": prompt})
			with st.chat_message("user"):
				st.markdown(prompt)

			with st.chat_message("assistant"):
				message_placeholder = st.empty()
				full_response = ""
				#response = 
				#if response and response.generations:
				#for response in co.chat(prompt=faq + "\n" + prompt, max_tokens=1000, stream = True):
				response_stream = co.chat(message="You are an FAQ BOT, these are the faq information given to you:" + faq + "You must use only the information given to you in the faq informatio to answer the user query, do not provide your own information\n This the user query: " + prompt, max_tokens=1000, stream=True)
    
				for response_object in response_stream:
				# Check if response_object has a 'text' attribute
					if hasattr(response_object, 'text'):
						# Append the text to full_response
						full_response += response_object.text

							# Update the placeholder with the current state of full_response
					message_placeholder.markdown(full_response + "▌")

				# Final update to the placeholder after streaming is complete
				message_placeholder.markdown(full_response)
						
			st.session_state.msg.append({"role": "assistant", "content": full_response})
				
	except Exception as e:
		st.error(e)


def main_faq_bot():
	if st.session_state.user['profile_id'] == SA:
		with st.expander("FAQ Bot Settings"):
			faq = st.checkbox("I will delete and initialise training data for FAQ bot")
			if st.button("Initialise Training Data") and faq:
				init_training_data()
			pass
		# Code for FAQ AI chatbot
	faq_bot()
