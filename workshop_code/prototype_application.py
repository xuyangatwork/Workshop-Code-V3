import streamlit as st
from basecode2.rag_mongodb import load_rag
from datetime import datetime
import sqlite3
import openai
from openai import OpenAI
import os
from basecode2.authenticate import return_cohere_key, return_openai_key, return_google_key
from datetime import datetime
from langchain.memory import ConversationSummaryBufferMemory
from langchain.memory import ConversationBufferWindowMemory
from langchain.chat_models import ChatOpenAI
import configparser
import cohere
import google.generativeai as genai
import ast


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
MY_APP = config_handler.get_config_values('Prompt_Design_Templates', 'MY_APP')
MY_FORM = config_handler.get_config_values('Prompt_Design_Templates', 'MY_FORM')
MY_APP_ADVANCE = config_handler.get_config_values('Prompt_Design_Templates', 'MY_APP_ADVANCE')
PROTOTYPE = config_handler.get_config_values('constants', 'PROTOTYPE')
FORM_PROTOTYPE = config_handler.get_config_values('constants', 'FORM_PROTOTYPE')

def insert_into_data_table(date, chatbot_ans,user_prompt, tokens, function_name):
	cwd = os.getcwd()
	WORKING_DIRECTORY = os.path.join(cwd, "database")
	WORKING_DATABASE = os.path.join(WORKING_DIRECTORY , "default.db")
	conn = sqlite3.connect(WORKING_DATABASE)
	cursor = conn.cursor()

	# Insert data into Data_Table using preloaded session state value
	cursor.execute('''
		INSERT INTO Data_Table (date, user_id, profile_id, school_id, chatbot_ans, user_prompt, function_name, tokens)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	''', (date, st.session_state.user["id"], st.session_state.user["profile_id"], st.session_state.user['school_id'], chatbot_ans, user_prompt, function_name, tokens))

	conn.commit()
	conn.close()



def init_settings():
	# Initialize original session state variables if they don't exist
	if "form_title" not in st.session_state:
		st.session_state.form_title = "Message Generator"
	if "question_1" not in st.session_state:
		st.session_state.question_1 = "Name"
	if "question_2" not in st.session_state:
		st.session_state.question_2 = "Occupation"
	if "question_3" not in st.session_state:
		st.session_state.question_3 = "Subject"
	if "question_4" not in st.session_state:
		st.session_state.question_4 = "Message"
	if "question_5" not in st.session_state:
		st.session_state.question_5 = "Number of words"

def default_settings():
	st.session_state.form_title = "Message Generator"
	st.session_state.question_1 = "Name"
	st.session_state.question_2 = "Occupation"
	st.session_state.question_3 = "Subject"
	st.session_state.question_4 = "Message"
	st.session_state.question_5 = "Number of words"



def form_input():
		
	with st.form("my_form"):
		st.subheader(st.session_state.form_title)
		q1 = st.text_input(f"Question 1: {st.session_state.question_1}")
		q2 = st.text_input(f"Question 2: {st.session_state.question_2}")
		q3 = st.text_input(f"Question 3: {st.session_state.question_3}")
		q4 = st.text_input(f"Question 4: {st.session_state.question_4}")
		q5 = st.text_input(f"Question 5: {st.session_state.question_5}")

		# Every form must have a submit button.
		submitted = st.form_submit_button("Submit")
		if submitted:
			return q1, q2, q3, q4, q5
		
	return False

def update_session_state(title, question_1, question_2, question_3, question_4, question_5):
	st.session_state.form_title = title
	st.session_state.question_1 = question_1
	st.session_state.question_2 = question_2
	st.session_state.question_3 = question_3
	st.session_state.question_4 = question_4
	st.session_state.question_5 = question_5

def set_session_state():
	for i in range(1, 6):
		st.write(st.session_state[f"question_{i}"])


	 
def form_settings():
	if st.checkbox("Use default form settings", key = 0):
		default_settings()
	with st.form("form_settings"):
		st.write("These are the current questions for the form, do not leave a blank (Enter NA for non applicable questions)")
		title = st.text_input("Form Title", value=st.session_state.form_title)
		question_1 = st.text_input("Question 1:", value=st.session_state.question_1)
		question_2 = st.text_input("Question 2:", value=st.session_state.question_2)
		question_3 = st.text_input("Question 3:", value=st.session_state.question_3)
		question_4 = st.text_input("Question 4:", value=st.session_state.question_4)
		question_5 = st.text_input("Question 5:", value=st.session_state.question_5)
		
		submitted = st.form_submit_button("Update Questions")
		if submitted:
			if not all([title, question_1, question_2, question_3, question_4, question_5]):
				st.error("Please fill in all fields or enter 'NA' if not applicable.")
			else:
				update_session_state(title, question_1, question_2, question_3, question_4, question_5)
				st.success("Questions updated successfully!")

def chatbot_settings():
	temp = st.number_input("Temperature", value=st.session_state.default_temp, min_value=0.0, max_value=1.0, step=0.1)
	k_memory = st.number_input("K Memory", value=st.session_state.default_k_memory, min_value=0, max_value=5, step=1)
	presence_penalty = st.number_input("Presence Penalty", value=st.session_state.default_presence_penalty, min_value=-2.0, max_value=2.0, step=0.1)
	frequency_penalty = st.number_input("Frequency Penalty", value=st.session_state.default_frequency_penalty, min_value=-2.0, max_value=2.0, step=0.1)
	if st.button("Update Chatbot Settings", key = 6):
		st.session_state.default_temp = temp
		st.session_state.default_k_memory = k_memory
		st.session_state.default_presence_penalty = presence_penalty
		st.session_state.default_frequency_penalty = frequency_penalty


def prompt_template_settings():
	st.info("You can use the following variables which is link to your first 5 questions in your form prompt inputs: {q1}, {q2}, {q3}, {q4}, {q5}")
	if st.checkbox("Use form design default template", key = 2):
		st.session_state.my_app_template = MY_APP
	form_input = st.text_area("Enter your form prompt:", value = st.session_state.my_app_template, height=300 )
	if st.checkbox("Use default app template", key = 3):
		st.session_state.my_form_template = MY_FORM
	st.info("Enter your app prompt template here, you can add the following variables: {source}, {resource} ")
	prompt_template = st.text_area("Enter your application prompt design", value = st.session_state.my_form_template, height=300)
	if st.button("Update Prompt Template", key = 1):
		st.session_state.my_app_template = form_input
		st.session_state.my_form_template = prompt_template

def advance_prompt_template_settings():
	st.info("You can use the following variables in your prompt template: {mem}, {source}, {resource}")
	if st.checkbox("Use default app template", key=4):
		st.session_state.my_app_template_advance = MY_APP_ADVANCE
	prompt_template = st.text_area("Enter your prompt template here:", value = st.session_state.my_app_template_advance, height=300)
	if st.button("Update Prompt Template", key = 5):
		st.session_state.my_app_template_advance = prompt_template

def advance_prompt_template(memory, source, resource):
	text = st.session_state.my_app_template_advance
	return text.format( mem=memory, source=source, resource=resource)

def prompt_template(results):
	text = st.session_state.my_app_template
	return text.format(q1=results[0], q2=results[1], q3=results[2], q4=results[3], q5=results[4])

def form_template(source, resource):
	text = st.session_state.my_form_template
	return text.format(source=source, resource=resource)

def my_first_app(bot_name=PROTOTYPE):
	if "prototype_model" not in st.session_state:
		st.session_state.prototype_model = "gpt-3.5-turbo"
	if "my_app_template" not in st.session_state:
		st.session_state.my_app_template = MY_APP
	if "my_form_template" not in st.session_state:
		st.session_state.my_form_template = MY_FORM
	init_settings()
	st.subheader("Protyping a chatbot")
	with st.expander("Prototype Settings"):
		st.write("Current Form Template: ", st.session_state.my_form_template)
		st.write("Current Prompt Template: ", st.session_state.my_app_template)
	results = ""
	results = form_input()
	if results != False:
		form_output = prompt_template(results)
		basic_bot(form_output , bot_name)

def clear_session_states():
	st.session_state.msg = []
	if "memory" not in st.session_state:
		pass
	else:
		del st.session_state["memory"]

def my_first_app_advance(bot_name=PROTOTYPE):
	init_settings()
	if "prototype_model" not in st.session_state:
		st.session_state.prototype_model = "gpt-3.5-turbo"
	if "my_app_template_advance" not in st.session_state:
		st.session_state.my_app_template_advance = MY_APP_ADVANCE

	st.subheader("Protyping a chatbot")
	with st.expander("Prototype Settings"):
		st.write("Current Prompt Template: ", st.session_state.my_app_template_advance)
	if st.button("Clear Chat"):
		clear_session_states()
	if st.session_state.prototype_model == "gemini-pro":
		prototype_gemini_bot(bot_name)
	elif st.session_state.prototype_model == "cohere":
		prototype_cohere_bot(bot_name)
	else:
		prototype_advance_bot(bot_name)

def prototype_settings():
	if "my_app_template" not in st.session_state:
		st.session_state.my_app_template = MY_APP
	
	if "my_form_template" not in st.session_state:
		st.session_state.my_form_template = MY_FORM
		
	init_settings()
	tab1, tab2, tab3, tab4 = st.tabs([ "Chatbot Prompt Settings", "Chatbot Parameter Settings", "KB settings", "Form Prompt Settings"])


	with tab1:
		st.subheader("Chatbot Prompt Settings")
		advance_prompt_template_settings()
		
	with tab2:
		st.subheader("Chatbot Parameter Settings")
		if "prototype_model" not in st.session_state:
			st.session_state.prototype_model = "gpt-3.5-turbo"
		
		st.write("Current Model: ",st.session_state.prototype_model)
		model_settings = st.selectbox("Select a model", ["gpt-4-turbo-preview", "gpt-3.5-turbo", "cohere", "gemini-pro"])
		if st.button("Update Model"):
			st.session_state.prototype_model = model_settings
		chatbot_settings()

	with tab3:
		st.subheader("KB settings")
		st.write("KB settings")
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

	with tab4:
		st.subheader("Form Prompt Settings")
		form_settings()
		prompt_template_settings()


#below ========================================================= OPENAI BOT =========================================================
#using the query from lanceDB and vector store , combine with memory
def prompt_template_prototype(prompt):
	#st.write(type(st.session_state.vs))
	if st.session_state.vs:
		docs = st.session_state.vs.similarity_search(prompt)
		resource = docs[0].page_content
		source = docs[0].metadata
	else:
		source = ""
		resource = ""

	if "memory" not in st.session_state:
		st.session_state.memory = ConversationBufferWindowMemory(k=st.session_state.default_k_memory)
	mem = st.session_state.memory.load_memory_variables({})

	#st.write(resource)
	prompt = advance_prompt_template(mem, source, resource)
	
	return prompt


#chat completion memory for streamlit using memory buffer
def chat_completion_prototype(prompt):
	client = OpenAI(api_key=return_openai_key())
	prompt_template = prompt_template_prototype(prompt)
	response = client.chat.completions.create(
		model=st.session_state.prototype_model,
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

def prototype_advance_bot(bot_name= PROTOTYPE):
	
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
		if prompt := st.chat_input("Enter your query"):
			st.session_state.msg.append({"role": "user", "content": prompt})
			with st.chat_message("user"):
				st.markdown(prompt)

			with st.chat_message("assistant"):
				message_placeholder = st.empty()
				full_response = ""
				for response in chat_completion_prototype(prompt):
					full_response += (response.choices[0].delta.content or "")
					message_placeholder.markdown(full_response + "▌")
				message_placeholder.markdown(full_response)
				#Response Rating
			st.session_state.msg.append({"role": "assistant", "content": full_response})
			st.session_state["memory"].save_context({"input": prompt},{"output": full_response})
			 # Insert data into the table
			now = datetime.now() # Using ISO format for date
			num_tokens = len(full_response + prompt)*1.3
			#st.write(num_tokens)
			insert_into_data_table(now.strftime("%d/%m/%Y %H:%M:%S"),  full_response, prompt, num_tokens, bot_name)
			
	except Exception as e:
		st.exception(e)
#==================================================== GEMINI PRO BOT =========================================================	
#integration API call into streamlit chat components with memory and qa

def prototype_gemini_bot(bot_name= PROTOTYPE):
	genai.configure(api_key = return_google_key())
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
		if prompt := st.chat_input("Enter your query"):
			st.session_state.msg.append({"role": "user", "content": prompt})
			with st.chat_message("user"):
				st.markdown(prompt)

			with st.chat_message("assistant"):
				message_placeholder = st.empty()
				full_response = ""
				#response = 
				chat_model = genai.GenerativeModel('gemini-pro')
				response_stream = chat_model.generate_content(prompt, stream=True)
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


			st.session_state["memory"].save_context({"input": prompt},{"output": full_response})
			 # Insert data into the table
			now = datetime.now() # Using ISO format for date
			num_tokens = len(full_response + prompt)*1.3
			#st.write(num_tokens)
			insert_into_data_table(now.strftime("%d/%m/%Y %H:%M:%S"),  full_response, prompt, num_tokens, bot_name)
			
	except Exception as e:
		st.exception(e)



#below ========================================================= COHERE BOT =========================================================
#integration API call into streamlit chat components with memory and qa

def prototype_cohere_bot(bot_name= PROTOTYPE):
	co = cohere.Client(return_cohere_key())
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
		if prompt := st.chat_input("Enter your query"):
			st.session_state.msg.append({"role": "user", "content": prompt})
			with st.chat_message("user"):
				st.markdown(prompt)

			with st.chat_message("assistant"):
				message_placeholder = st.empty()
				full_response = ""
				#response = 
				#if response and response.generations:
				#for response in co.chat(prompt=faq + "\n" + prompt, max_tokens=1000, stream = True):
				response_stream = co.chat(message= prompt_template_prototype(prompt) + "\n This is the user query" + prompt, max_tokens=1000, stream=True)
	
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


			st.session_state["memory"].save_context({"input": prompt},{"output": full_response})
			 # Insert data into the table
			now = datetime.now() # Using ISO format for date
			num_tokens = len(full_response + prompt)*1.3
			#st.write(num_tokens)
			insert_into_data_table(now.strftime("%d/%m/%Y %H:%M:%S"),  full_response, prompt, num_tokens, bot_name)
			
	except Exception as e:
		st.exception(e)



#================================FORM TEMPLATE BOT===============================================================================

#chat completion memory for streamlit using memory buffer
def template_prompt(prompt, prompt_template):
	client = OpenAI(api_key=return_openai_key())
	response = client.chat.completions.create(
		model=st.session_state.openai_model,
		messages=[
			{"role": "system", "content":prompt_template},
			{"role": "user", "content": prompt},
		],
		temperature=st.session_state.default_temp, #settings option
		presence_penalty=st.session_state.default_presence_penalty, #settings option
		frequency_penalty=st.session_state.default_frequency_penalty, #settings option
		stream=True #settings option
	)
	return response


def basic_bot(prompt, bot_name= "Prototype"):
	try:
		if prompt:
			# if "memory" not in st.session_state:
			# 	st.session_state.memory = ConversationBufferWindowMemory(k=st.session_state.default_k_memory)
			#st.session_state.msg.append({"role": "user", "content": prompt})
			message_placeholder = st.empty()
			#check if there is any knowledge base
			if st.session_state.vs:
				docs = st.session_state.vs.similarity_search(prompt)
				resource = docs[0].page_content
				source = docs[0].metadata
			else:
				resource = ""
				source = ""
			st.session_state.my_form_template = form_template(source, resource)
			
			full_response = ""
			for response in template_prompt(prompt, st.session_state.my_form_template):
				full_response += (response.choices[0].delta.content or "")
				message_placeholder.markdown(full_response + "▌")
	
			message_placeholder.markdown(full_response)
			now = datetime.now() # Using ISO format for date
			num_tokens = len(full_response + prompt)*1.3
			#st.write(num_tokens)
			insert_into_data_table(now.strftime("%d/%m/%Y %H:%M:%S"),  full_response, prompt, num_tokens, bot_name)
			
	except Exception as e:
		st.error(e)
