import streamlit as st
from openai import OpenAI
import sqlite3
from basecode2.authenticate import return_openai_key
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chat_models import ChatOpenAI
import configparser
import os
import pandas as pd
import ast



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
DISCUSSION = config_handler.get_config_values('constants', 'DISCUSSION')
SA = config_handler.get_config_values('constants', 'SA')
SQL_DB = config_handler.get_config_values('DATABASE', 'SQL_DB')

cwd = os.getcwd()
WORKING_DIRECTORY = os.path.join(cwd, "database")
WORKING_DATABASE = os.path.join(WORKING_DIRECTORY , SQL_DB	)

def clear_session_states():                
	st.session_state.msg = []
	if "memory" not in st.session_state:
		pass
	else:
		del st.session_state["memory"]

def extract_and_combine_responses():
	# Connect to the SQLite database
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()

	# SQL query to select all responses for discussion_bot
	query = f"SELECT response FROM Chatbot_Training_Records WHERE chatbot_type = '{DISCUSSION}'"
	

	cursor.execute(query)
	responses = cursor.fetchall()
	
	# Combine all responses into a single string
	combined_responses = ' '.join([response[0] for response in responses if response[0]])
	#st.write("Combined Responses: ", combined_responses)
	conn.close()
	return combined_responses

		

#below ------------------------------ base bot , summary memory for long conversation---------------------------------------------
#summary of conversation , requires another LLM call for every input, useful for feedback and summarising what was spoken
def memory_summary_component(prompt, prompt_design): #currently not in use
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()
	os.environ["OPENAI_API_KEY"] = return_openai_key()
	if "memory" not in st.session_state:
		llm = ChatOpenAI(model_name=st.session_state.default_llm_model,temperature=st.session_state.default_temp)
		st.session_state.memory = ConversationSummaryBufferMemory(llm=llm, max_token_limit=2000)
	messages = st.session_state["memory"].chat_memory.messages
	previous_summary = ""
	mem = st.session_state["memory"].predict_new_summary(messages, previous_summary)
	#vectorstore available
	prompt_template = prompt_design + f"""
						Summary of current conversation:
						{mem}"""
	chatbot_name = "chatbot" + str(st.session_state.user['id'])
	user_id = st.session_state.user['id']
	school_id = st.session_state.user['school_id']

	# Check if a record exists
	cursor.execute("SELECT COUNT(*) FROM Chatbot_Training_Records WHERE user_id = ? AND school_id = ?",
				   (user_id, school_id))
	record_exists = cursor.fetchone()[0] > 0

	if record_exists:
		# Update the existing record
		cursor.execute("UPDATE Chatbot_Training_Records SET response = ? WHERE user_id = ? AND school_id = ?",
					   (mem, user_id, school_id))
	else:
		# Insert a new record
		cursor.execute("INSERT INTO Chatbot_Training_Records (chatbot_type, chatbot_name, prompt, response, user_id, school_id) VALUES (?, ?, ?, ?, ?, ?)",
					   (DISCUSSION, chatbot_name, "NIL", mem, user_id, school_id))
	conn.commit()
	conn.close()
	return prompt_template


#chat completion memory for streamlit using memory buffer
def chat_completion_qa_memory(prompt, prompt_design):
	client = OpenAI(api_key=return_openai_key())	
	prompt_template = memory_summary_component(prompt, prompt_design)
	response = client.chat.completions.create(
		model=st.session_state.default_llm_model,
		messages=[
			{"role": "system", "content":prompt_template },
			{"role": "user", "content": prompt},
		],
		temperature=st.session_state.default_temp, #settings option
		presence_penalty=st.session_state.default_presence_penalty, #settings option
		frequency_penalty=st.session_state.default_frequency_penalty, #settings option	
		stream=True #settings option
	)
	return response

#integration API call into streamlit chat components with memory and qa

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
		df['chatbot_type'] = 'rule_base'
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


def discussion_bot(bot_name, prompt_design):
	if st.button("Clear Chat"):
		clear_session_states()
	full_response = ""
	greetings_str = st.session_state.greetings_prompt
	#st.write(greetings_str)
	# Check if st.session_state.msg exists, and if not, initialize with greeting and help messages
	if 'msg' not in st.session_state:
		st.session_state.msg = [
			
			{"role": "assistant", "content": greetings_str}
		]
	elif st.session_state.msg == []:
		st.session_state.msg = [
			
			{"role": "assistant", "content": greetings_str}
		]
	#lesson collaborator
	for message in st.session_state.msg:
		with st.chat_message(message["role"]):
			st.markdown(message["content"])

	try:
		if prompt := st.chat_input("Enter your thoughts"):
			st.session_state.msg.append({"role": "user", "content": prompt})
			with st.chat_message("user"):
				st.markdown(prompt)

			with st.chat_message("assistant"):
				message_placeholder = st.empty()
				full_response = ""
				for response in chat_completion_qa_memory(prompt, prompt_design):
					full_response += (response.choices[0].delta.content or "")
					message_placeholder.markdown(full_response + "▌")
				message_placeholder.markdown(full_response)
				#Response Rating
				
			st.session_state.msg.append({"role": "assistant", "content": full_response})
			st.session_state["memory"].save_context({"input": prompt},{"output": full_response})
			
			
			
	except Exception as e:
		st.exception(e)

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
	cursor.execute("SELECT * FROM Chatbot_Training_Records")
	rows = cursor.fetchall()
	column_names = [description[0] for description in cursor.description]
	
	conn.close()
	return rows, column_names



def main_discussion_bot():
	# Code for FAQ AI chatbot
	if "extract_data" not in st.session_state:
		st.session_state.extract_data = ""
	if "analyse_discussion" not in st.session_state:
		st.session_state.analyse_discussion = False
	#fetch_and_create_session_states()
	if st.session_state.user['profile_id'] == SA:
		with st.expander("Discussion Bot Settings"):
			analyse_responses = st.toggle('Switch on to analyse responses')
			if analyse_responses:
				if st.button("Extract Responses"):
					st.session_state.extract_data = extract_and_combine_responses()
					st.write("Discussion Data: ", st.session_state.extract_data)
				st.session_state.analyse_discussion = True
				#st.write("Discussion Data: ", st.session_state.extract_data)
				#d, c  = fetch_all_data()
				#display_data(d, c)
			else:
				st.session_state.analyse_discussion = False
	
			dis_bot = st.checkbox("I will delete and initialise training data for discussion bot")
			if st.button("Initialise Training Data") and dis_bot:
				init_training_data()
			pass

	if st.session_state.analyse_discussion:
		prompt = st.session_state.extraction_prompt + "/n" + st.session_state.extract_data  + "/n" + "Please analyse the response and answer the questions below"
	else:		
		prompt = st.session_state.discussion_prompt

	discussion_bot(DISCUSSION, prompt)