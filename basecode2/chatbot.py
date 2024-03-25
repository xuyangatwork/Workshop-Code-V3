import streamlit as st
from basecode2.rag_mongodb import load_rag
import PIL
import tempfile
import configparser
import ast
import streamlit as st
from openai import OpenAI
import sqlite3
from basecode2.authenticate import return_openai_key, return_claude_key, return_google_key, return_cohere_key
from datetime import datetime
from langchain.memory import ConversationBufferWindowMemory
import streamlit_antd_components as sac
import os
from Markdown2docx import Markdown2docx
import anthropic
import google.generativeai as genai
import cohere
import base64
import requests

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

# Function to encode the image
def encode_image(image_path):
	with open(image_path, "rb") as image_file:
		return base64.b64encode(image_file.read()).decode('utf-8')

# Function to get file extension
def get_file_extension(file_name):
	return os.path.splitext(file_name)[-1]

def bot_settings():
	with st.form(key='sliders_form'):
		# Sliders for settings
		st.write("Current User Bot Settings")
		temp = st.slider("Temp", min_value=0.0, max_value=1.0, value=st.session_state.default_temp, step=0.01)
		presence_penalty = st.slider("Presence Penalty", min_value=-2.0, max_value=2.0, value=st.session_state.default_presence_penalty, step=0.01)
		frequency_penalty = st.slider("Frequency Penalty", min_value=-2.0, max_value=2.0, value=st.session_state.default_frequency_penalty, step=0.01)
		chat_memory = st.slider("Chat Memory", min_value=0, max_value=10, value=st.session_state.default_k_memory, step=1)	
		top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=st.session_state.default_top_p, step=0.01)
		seed_num = st.slider("Seed Number", min_value=1.0, max_value=100.0, value=st.session_state.seed_num, step=1.0)
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


def openai_bot(bot_name, c_model, memory_flag, rag_flag):
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
  
  
#----------------Google Gemini Chatbot----------------
def gemini_bot(bot_name, c_model, memory_flag, rag_flag):
	genai.configure(api_key = return_google_key())
	greetings_str = f"Hi, I am Gemini {bot_name}"
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
	
	try:
		if prompt := st.chat_input("Enter your query"):
			st.session_state.msg.append({"role": "user", "content": prompt})
			with messages.chat_message("user"):
				st.markdown(prompt)
			with messages.chat_message("assistant"):
				message_placeholder = st.empty()
				full_response = ""
				#response = 
				chat_model = genai.GenerativeModel(c_model)
				prompt_template = prompt_template_function(prompt, memory_flag, rag_flag)
				prompt = prompt_template + "\n This is the user query" + prompt,
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
			if memory_flag:
				st.session_state["memory"].save_context({"input": prompt},{"output": full_response})
			# Insert data into the table
			now = datetime.now() # Using ISO format for date
			full_response_str = str(full_response)
			prompt_str = str(prompt)

			# Now concatenate and calculate the length as intended.
			num_tokens = len(full_response_str + prompt_str) * 1.3
			#st.write(num_tokens)
			insert_into_data_table(now.strftime("%d/%m/%Y %H:%M:%S"),  full_response_str, prompt_str, num_tokens, bot_name)
			if st.session_state.download_response_flag == True:
				st.session_state.chat_response = add_response(full_response)
			
	except Exception as e:
		st.exception(e)

#------------------ Anthropic Claude Chatbot-------------------
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
			if memory_flag:
				st.session_state["memory"].save_context({"input": prompt},{"output": response})
			 # Insert data into the table
			now = datetime.now() # Using ISO format for date
			response_str = str(response)
			prompt_str = str(prompt)
			# Now concatenate and calculate the length as intended.
			num_tokens = len(response_str + prompt_str) * 1.3
			#st.write(num_tokens)
			insert_into_data_table(now.strftime("%d/%m/%Y %H:%M:%S"),  response_str, prompt_str, num_tokens, bot_name)
			if st.session_state.download_response_flag == True:
				st.session_state.chat_response = add_response(response)
			
	except Exception as e:
		st.exception(e)

#below ========================================================= COHERE BOT =========================================================
#integration API call into streamlit chat components with memory and qa

def cohere_bot(bot_name, c_model, memory_flag, rag_flag):
	co = cohere.Client(return_cohere_key())
	greetings_str = f"Hi, I am Cohere {bot_name}"
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
	
	for message in st.session_state.msg:
		with messages.chat_message(message["role"]):
			st.markdown(message["content"])
	
	try:
		if prompt := st.chat_input("Enter your query"):
			st.session_state.msg.append({"role": "user", "content": prompt})
			with messages.chat_message("user"):
				st.markdown(prompt)
			with messages.chat_message("assistant"):
				message_placeholder = st.empty()
				full_response = ""
				prompt_msg = prompt_template_function(prompt, memory_flag, rag_flag) + "\n This is the user query" + prompt
				#if response and response.generations:
				#for response in co.chat(prompt=faq + "\n" + prompt, max_tokens=1000, stream = True):
				response_stream = co.chat_stream(message= prompt_msg, max_tokens=1000)
	
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
			if memory_flag:
				st.session_state["memory"].save_context({"input": prompt},{"output": full_response})
			 # Insert data into the table
			now = datetime.now() # Using ISO format for date
			num_tokens = len(full_response + prompt)*1.3
			#st.write(num_tokens)
			insert_into_data_table(now.strftime("%d/%m/%Y %H:%M:%S"),  full_response, prompt, num_tokens, bot_name)
			if st.session_state.download_response_flag == True:
				st.session_state.chat_response = add_response(full_response)
			
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
	summary_text = summary.choices[0].message.content
	
	# conversation_doc = {
	# 	"user_id": st.session_state.user['id'],  # Assuming user ID is stored in session state
	# 	"date": datetime.now(),
	# 	"summary": summary_text
	# }
 
	# st.session_state.c_collection.insert_one(conversation_doc)
	

def main_chatbot_functions():
#check if prompt_template is in session state the default is the chatbot_key
	#check the school settings for chatbot settings
	with st.expander("Chatbot Settings"):
		c1, c2 = st.columns([1,1])
		with c2:
			memory = True
			rag = True
			enable_vision = True
			show_rag = True
			chat_bot = "-"
			if st.session_state.user['profile_id'] == SA or st.session_state.user['profile_id'] == AD:
				if st.checkbox("Enable Chatbot Settings"):
					bot_settings()
				memory = st.checkbox("Memory Enabled", value=True)
				rag = st.checkbox("RAG Enabled", value=True)
				enable_vision = st.checkbox("Enable Image Analysis", value=True)
				show_rag = st.checkbox("Show RAG", value=True)
				chat_bot = st.selectbox("OpenAI model", ["-","gpt-4-turbo-preview", "gpt-3.5-turbo", "cohere", "gemini-pro","claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"])
		with c1:
			if rag:
				load_rag()
	with st.expander("Download Chatbot Responses"):
		st.session_state.download_response_flag = st.checkbox("Enable Download Responses")
		complete_my_lesson()
	
	b1, b2 = st.columns([2,1])
	with b1:
		
		if chat_bot == "-":
			chat_bot = st.session_state.default_llm_model
		if chat_bot.startswith("gpt"):
			openai_bot(CHATBOT, chat_bot, memory, rag)
		elif chat_bot.startswith("gemini"):
			gemini_bot(CHATBOT, chat_bot, memory, rag)
		elif chat_bot.startswith("claude"):
			claude_bot(CHATBOT, chat_bot, memory, rag)
		elif chat_bot.startswith("cohere"):
			cohere_bot(CHATBOT, chat_bot, memory, rag)
	with b2:
		if st.button("Clear Chat"):
			# if "msg" in st.session_state and st.session_state.msg != []:
			# 	store_summary_chatbot_response()
			clear_session_states()
			st.rerun()
		if enable_vision:
			with st.container(border=True):
				if "memory" not in st.session_state:
					st.session_state.memory = ConversationBufferWindowMemory(k=st.session_state.default_k_memory)
				detect_file_upload()
				i_prompt = st.text_area("Enter a prompt for the image", value="From the image, I would like to know about this topic...", height=150)
				if st.button("Analyse Image"):
					if st.session_state.voice_image_file_exist:
						with st.spinner("Analysing image..."):
							# Analyse the image
							if chat_bot.startswith("gpt"):
								response = analyse_image_chat_openai(st.session_state.voice_image_file_exist[0], i_prompt)
							elif chat_bot.startswith("claude"):
								response = analyse_image_chat_anthropic(chat_bot, i_prompt)
							else: #default cohere and gemini use free image analysis
								response = analyse_image_chat_gemini(st.session_state.voice_image_file_exist[0], i_prompt)
							st.session_state.msg.append({"role": "assistant", "content": response})
							if memory:
								st.session_state["memory"].save_context({"input": i_prompt},{"output": response})
							st.rerun()
					else:
						st.error("Please upload an image first")
	 
		if show_rag:
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

def detect_file_upload():
	if "voice_image_file_exist" not in st.session_state:
		st.session_state.voice_image_file_exist = None

	uploaded_file = None
	file_uploaded = False  # Flag to indicate if the file is uploaded

	# Toggle button to enable/disable camera input
	if st.toggle('Enable Camera', key=4):
		img_file_buffer = st.camera_input("Take a picture")
		if img_file_buffer is not None:
			uploaded_file = img_file_buffer
	else:
		uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
		if uploaded_file is not None:
			file_uploaded = True  # Set the flag when a file is uploaded


	if uploaded_file is not None:
		if file_uploaded:
			# Display the uploaded image
			st.image(uploaded_file, caption='Uploaded Image', use_column_width=True)

		# Save the file to a temporary file
		extension = get_file_extension(uploaded_file.name)
		with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
			temp_file.write(uploaded_file.getvalue())
			temp_file_path = temp_file.name
			st.session_state.voice_image_file_exist = temp_file_path, extension
			st.success("Image uploaded successfully")
	else:
		st.session_state.voice_image_file_exist = None

def analyse_image_chat_anthropic(c_model,prompt):
	# Open and read the image file in binary format
	client = anthropic.Anthropic(api_key=return_claude_key())
	
	temp_file_path, extension = st.session_state.voice_image_file_exist
	
	with open(temp_file_path, "rb") as image_file:
		image_data = base64.b64encode(image_file.read()).decode("utf-8")
	
	# Assuming the image is JPEG; adjust if necessary
	if extension == ".png":
		image_media_type = "image/png"
	else:
		image_media_type = "image/jpeg"
	
	# Create the message payload for the Anthropic API
	message = client.messages.create(
		model=c_model,
		max_tokens=1024,
		messages=[
			{
				"role": "user",
				"content": [
					{
						"type": "image",
						"source": {
							"type": "base64",
							"media_type": image_media_type,
							"data": image_data,
						},
					},
					{
						"type": "text",
						"text": prompt,
					}
				],
			}
		],
	)
	
	# Clean up by removing the temporary file
	os.remove(temp_file_path)
	
	# Extract and return the response text from the message
	# Note: Adjust this based on how Anthropic structures the response
	if message:
		return message.content[0].text # Adjust according to the actual response structure
	else:
		return False

def analyse_image_chat_gemini(temp_file_path, prompt):
	genai.configure(api_key = return_google_key())
	image = PIL.Image.open(temp_file_path)
	vision_model = genai.GenerativeModel('gemini-pro-vision')
	response = vision_model.generate_content([prompt,image])
	if response:
		os.remove(temp_file_path)
		return response.text
	else:
		os.remove(temp_file_path)
		return False



def analyse_image_chat_openai(temp_file_path, prompt):
	# Encode the image
	api_key = return_openai_key()
	base64_image = encode_image(temp_file_path)

	# Prepare the payload
	headers = {
		"Content-Type": "application/json",
		"Authorization": f"Bearer {api_key}"
	}

	payload = {
		"model": "gpt-4-vision-preview",
		"messages": [
			{
				"role": "user",
				"content": [
					{
						"type": "text",
						"text": prompt
					},
					{
						"type": "image_url",
						"image_url": {
							"url": f"data:image/jpeg;base64,{base64_image}"
						}
					}
				]
			}
		],
		"max_tokens": 500
	}

	# Send the request
	response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

	# Display the response
	if response.status_code == 200:
		#st.write(response.json())
		#st.write(response.json()["choices"][0]["message"]["content"])
		os.remove(temp_file_path)
		return response.json()["choices"][0]["message"]["content"]
	else:
		os.remove(temp_file_path)
		st.session_state.voice_image_file_exist = None
		st.error("Failed to get response")
		return False