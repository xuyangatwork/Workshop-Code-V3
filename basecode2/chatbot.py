import streamlit as st
from basecode2.org_module import sa_select_school
from basecode2.rag_mongodb import load_rag
from langchain_community.vectorstores import FAISS
from basecode2.prompt_module import display_prompts, select_and_set_prompt, set_default_template
import pandas as pd
import configparser
import ast
from pymongo import MongoClient
import streamlit as st
import openai
from openai import OpenAI
import sqlite3
from basecode2.authenticate import return_openai_key, return_claude_key
from datetime import datetime
from langchain.memory import ConversationSummaryBufferMemory
from langchain.memory import ConversationBufferWindowMemory
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
import streamlit_antd_components as sac
import os
from Markdown2docx import Markdown2docx
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
import anthropic


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
# Fetching constants from config.ini
SA = config_handler.get_config_values('constants', 'SA')
AD = config_handler.get_config_values('constants', 'AD')
STU = config_handler.get_config_values('constants', 'STU')
DEFAULT_TEXT = config_handler.get_config_values('constants', 'DEFAULT_TEXT')
CHATBOT = config_handler.get_config_values('constants', 'CHATBOT')
SUMMARY_MODEL = config_handler.get_config_values('constants', 'SUMMARY_MODEL')
SQL_DB = config_handler.get_config_values('DATABASE', 'SQL_DB')



def bot_settings():
	with st.form(key='sliders_form'):
		# Sliders for settings
		st.write("Current User Bot Settings")
		temp = st.slider("Temp", min_value=0.0, max_value=1.0, value=st.session_state.default_temp, step=0.01)
		presence_penalty = st.slider("Presence Penalty", min_value=-2.0, max_value=2.0, value=st.session_state.default_presence_penalty, step=0.01)
		frequency_penalty = st.slider("Frequency Penalty", min_value=-2.0, max_value=2.0, value=st.session_state.default_frequency_penalty, step=0.01)
		chat_memory = st.slider("Chat Memory", min_value=0, max_value=10, value=st.session_state.default_k_memory, step=1)	
		top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=st.session_state.top_p, step=0.01)
		seed_num = st.slider("Seed Number", min_value=1, max_value=100, value=st.session_state.seed_num, step=1)
		# Submit button for the form
		submit_button = st.form_submit_button(label='Submit')

		# If the form is successfully submitted, assign values to session state
		if submit_button:
			st.session_state.default_temp = temp
			st.session_state.default_presence_penalty = presence_penalty
			st.session_state.default_frequency_penalty= frequency_penalty
			st.session_state.default_k_memory = chat_memory
			st.session_state.default_top_p = top_p
			st.session_state.seed_num = seed_num
			st.success("Parameters saved!")


def insert_into_data_table(date, chatbot_ans,user_prompt, tokens, function_name):
	cwd = os.getcwd()
	WORKING_DIRECTORY = os.path.join(cwd, "database")
	WORKING_DATABASE = os.path.join(WORKING_DIRECTORY , SQL_DB)
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()

	# Insert data into Data_Table using preloaded session state value
	cursor.execute('''
		INSERT INTO Data_Table (date, user_id, profile_id, school_id, chatbot_ans, user_prompt, function_name, tokens)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	''', (date, st.session_state.user["id"], st.session_state.user["profile_id"], st.session_state.user['school_id'], chatbot_ans, user_prompt, function_name, tokens))

	conn.commit()
	conn.close()

def response_download():
	docx_name = "crp" + st.session_state.user['id'] + ".docx"
	docx_path = os.path.join("chatbot_response", docx_name)
	
	if os.path.exists(docx_path):
# Provide the docx for download via Streamlit
		with open(docx_path, "rb") as docx_file:
			docx_bytes = docx_file.read()
			st.success("File is ready for downloading")
			st.download_button(
				label="Download document as DOCX",
				data=docx_bytes,
				file_name=docx_name,
				mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
			)
		os.remove(docx_path)
		st.session_state.button_text = 'Reset'
	else:
		st.warning("There is no lesson plan available for download.")


def complete_my_lesson():
	plan_action = sac.buttons([sac.ButtonsItem(label='Preview Responses', icon='eye', color='#00BFFF'),
							sac.ButtonsItem(label='Download Responses', icon='file-earmark-arrow-down', color='#40826D'),
							sac.ButtonsItem(label='Clear Responses', icon='file-earmark-arrow-down', color='#FF7F50')
								], index=None, format_func='title', size='small')
	
	
	if plan_action == 'Preview Responses':
		st.write(st.session_state.data_doc)

	elif plan_action == 'Download Responses':
		st.write("Downloading your lesson plan")
		md_filename = "crp" + st.session_state.user['id'] + ".md"
		md_filepath = os.path.join("chatbot_response", md_filename)
		if not os.path.exists("chatbot_response"):
			os.makedirs("chatbot_response")
		with open(md_filepath, 'w', encoding='utf-8') as file:
			file.write(st.session_state.data_doc)
		# Convert the markdown file to a docx
		base_filepath = os.path.join("chatbot_response", "crp" + st.session_state.user['id'])
		project = Markdown2docx(base_filepath)
		project.eat_soup()
		project.save()  # Assuming it saves the file with the same name but a .docx extension
		response_download()
	elif plan_action == 'Clear Responses':
		if st.checkbox("Clear Responses"):
			st.session_state.data_doc = ""
			st.success("Responses cleared")

def add_response(response):
	# add_response = sac.buttons([sac.ButtonsItem(label='Ignore Response', icon='plus-circle', color='#40826D'), [sac.ButtonsItem(label='Add Response', icon='plus-circle', color='#25C3B0')]
	# 							], index=None, format_func='title', size='small',type='primary')
	opt = sac.buttons([sac.ButtonsItem(label='Save Response', color='#40826D')], format_func='title', index=None, size='small')
	
	# st.write(response)
	if add_response:
		st.session_state.data_doc = st.session_state.data_doc + "\n\n" + response
	
	return opt

def clear_session_states():
	st.session_state.msg = []
	if "memory" not in st.session_state:
		pass
	else:
		del st.session_state["memory"]

def prompt_template_function(prompt, memory_flag, rag_flag):
	#check if there is kb loaded
	if st.session_state.vs:
		docs = st.session_state.vs.similarity_search(query=prompt, k=4)
		resource = docs[0].page_content
		source = docs[0].metadata
		st.session_state.rag_response = resource, source
	else:
		resource = ""
		source = ""

	if memory_flag:
		if "memory" not in st.session_state:
			st.session_state.memory = ConversationBufferWindowMemory(k=st.session_state.default_k_memory)
		mem = st.session_state.memory.load_memory_variables({})

	if rag_flag and memory_flag: #rag and memory only
		prompt_template = st.session_state.chatbot + f"""
							Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. 
							Search Result:
							{resource}
							{source}
							History of conversation:
							{mem}
							You must quote the source of the Search Result if you are using the search result as part of the answer"""
	
		return prompt_template
	
	elif rag_flag and not memory_flag: #rag kb only
		prompt_template = st.session_state.chatbot + f"""
						Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. 
						Search Result:
						{resource}
						{source}
						You must quote the source of the Search Result if you are using the search result as part of the answer"""
		return prompt_template
	
	elif not rag_flag and memory_flag: #memory only
		prompt_template = st.session_state.chatbot + f""" 
						History of conversation:
						{mem}"""
		return prompt_template
	else: #base bot nothing
		return st.session_state.chatbot


def openai_base_bot(bot_name, c_model, memory_flag, rag_flag):
	client = OpenAI(
	api_key=return_openai_key(),)	
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
	messages = st.container(border=True)
		#showing the history of the chatbots
	for message in st.session_state.msg:
		with messages.chat_message(message["role"]):
			st.markdown(message["content"])
	#chat bot input
	try:
		if prompt := st.chat_input("Enter your query"):
			st.session_state.msg.append({"role": "user", "content": prompt})
			with messages.chat_message("user"):
				st.markdown(prompt)
			with messages.chat_message("assistant"):
				prompt_template = prompt_template_function(prompt, memory_flag, rag_flag)
				stream = client.chat.completions.create(
					model=c_model,
					messages=[
						{"role": "system", "content":prompt_template },
						{"role": "user", "content": prompt},
					],
					temperature=st.session_state.default_temp, #settings option
					presence_penalty=st.session_state.default_presence_penalty, #settings option
					frequency_penalty=st.session_state.default_frequency_penalty, #settings option
					stream=True #settings option
				)
				response = st.write_stream(stream)
			st.session_state.msg.append({"role": "assistant", "content": response})
			if memory_flag:
				st.session_state["memory"].save_context({"input": prompt},{"output": response})
			# Insert data into the table
			now = datetime.now() # Using ISO format for date
			num_tokens = len(full_response + prompt)*1.3
			insert_into_data_table(now.strftime("%d/%m/%Y %H:%M:%S"),  response, prompt, num_tokens, bot_name)
			if st.session_state.download_response_flag == True:
				st.session_state.chat_response = add_response(response)
			
			
	except Exception as e:
		st.exception(e)
	
 
def claude_bot(bot_name, c_model, memory_flag, rag_flag):
	client = anthropic.Anthropic(api_key=return_claude_key())
	greetings_str = f"Hi, I am Claude {bot_name}"
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
		if prompt := st.chat_input("Enter your query"):
			st.session_state.msg.append({"role": "user", "content": prompt})
			with st.chat_message("user"):
				st.markdown(prompt)

			with st.chat_message("assistant"):
				prompt_template = prompt_template_function(prompt, memory_flag, rag_flag)
				with client.messages.stream(
						max_tokens=1024,
	  					system=prompt_template,	
						messages=[
		  					{"role": "user", "content": prompt}
			   			],
						model=c_model,
					) as stream:
        
						response = st.write_stream(stream.text_stream)
			st.session_state.msg.append({"role": "assistant", "content": response})
			st.session_state["memory"].save_context({"input": prompt},{"output": response})
			 # Insert data into the table
			now = datetime.now() # Using ISO format for date
			response_str = str(response)
			prompt_str = str(prompt)
			# Now concatenate and calculate the length as intended.
			num_tokens = len(response_str + prompt_str) * 1.3
			#st.write(num_tokens)
			insert_into_data_table(now.strftime("%d/%m/%Y %H:%M:%S"),  response_str, prompt_str, num_tokens, bot_name)
			
	except Exception as e:
		st.exception(e)

 
 
def store_summary_chatbot_response():
	all_messages_string = " ".join(message["content"] for message in st.session_state.msg)
	client = OpenAI(
	api_key=return_openai_key(),)	
	summary= client.chat.completions.create(
					model=SUMMARY_MODEL,
					messages=[
						{"role": "system", "content":"Summarise key points of the conversation in no more than 200 words" },
						{"role": "user", "content": all_messages_string},
					],
					temperature=0.0, #settings option
				)
	return summary.choices[0].message.content

def main_chatbot_functions():
#check if prompt_template is in session state the default is the chatbot_key
	#check the school settings for chatbot settings
	with st.expander("Chatbot Settings"):
		c1, c2 = st.columns([1,1])
		with c1:
			memory = st.checkbox("Memory Enabled", value=True)
			rag = st.checkbox("RAG Enabled", value=True)
			if st.session_state.user['profile_id'] == STU:
				set_default_template(DEFAULT_TEXT)
			else:
				chat_bot = st.selectbox("Select Chatbot", ["gpt-4-turbo-preview", "gpt-3.5-turbo"])	
				prompt_templates = display_prompts()
				if st.checkbox("Select Prompt", value=False):
					if prompt_templates:
						select_and_set_prompt(prompt_templates, True)
		
		with c2:
			if rag:
				st.write(f"Currently Loaded KB (RAG): {st.session_state.current_kb_model}")
				vs, rn = load_rag()
				d1,d2,d3 = st.columns([2,2,3])
				with d1:
					if st.button("Load RAG"):
						st.session_state.vs = vs
						st.session_state.current_kb_model = rn
						st.rerun()
				with d2:
					if st.button("Unload RAG"):
						st.session_state.vs = None
						st.session_state.current_kb_model = ""
						st.rerun()
			#show the templates for chatbot
	with st.expander("Download Chatbot Responses"):
		complete_my_lesson()
	
	b1, b2 = st.columns([3,1])
	with b1:
		
		if st.button("Clear Chat"):
			clear_session_states()
	
			#if chat_bot.startswith("claude"):
			#claude_bot(CHATBOT, chat_bot, memory, rag)
			#else:
		openai_base_bot(CHATBOT, chat_bot, memory, rag)
	with b2:
		with st.container(border=True):
			if rag:
				st.write("RAG Results")
				if st.session_state.rag_response == None  or st.session_state.rag_response == "":
					resource = ""
					source = ""
				else:
					resource, source = st.session_state.rag_response
				st.write("Resource: ", resource)
				st.write("Source : ", source)
			else:
				st.write("RAG is not enabled")
		with st.container(border=True):
			if memory:
				st.write("Chat Memory")
				if "memory" not in st.session_state:
					st.write("No memory")
				else:
					st.write(st.session_state.memory.load_memory_variables({}))
			else:
				st.write("Memory is not enabled")
