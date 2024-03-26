import streamlit as st
from basecode2.authenticate import return_openai_key
from langchain.memory import ConversationBufferWindowMemory
from langchain.memory import ConversationSummaryBufferMemory
from basecode2.rag_mongodb import load_rag
from workshop_code.k_map import map_prompter_with_plantuml, generate_plantuml_mindmap, render_diagram
from datetime import datetime
from langchain.chat_models import ChatOpenAI
#from st_audiorec import st_audiorec
import os
import PIL
import openai
import google.generativeai as genai
import requests
import base64
import tempfile
import io
from openai import OpenAI
import streamlit_antd_components as sac
import requests
from Markdown2docx import Markdown2docx
import configparser
# import spacy_streamlit
# import spacy
import ast

#nlp = spacy.load("en_core_web_sm")

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

START_BOT = config_handler.get_value('constants', 'START_BOT')
CONNECT_BOT = config_handler.get_value('constants', 'CONNECT_BOT')
LANGUAGE_BOT = config_handler.get_value('constants', 'LANGUAGE_BOT')
LINKING_BOT = config_handler.get_value('constants', 'LINKING_BOT')
START_PROMPT1 = config_handler.get_value('Prompt_Design_Templates', 'START_PROMPT1')
START_PROMPT2 = config_handler.get_value('Prompt_Design_Templates', 'START_PROMPT2')
START_PROMPT3 = config_handler.get_value('Prompt_Design_Templates', 'START_PROMPT3')
START_PROMPT4 = config_handler.get_value('Prompt_Design_Templates', 'START_PROMPT4')

cwd = os.getcwd()
AUDIO_DIRECTORY = os.path.join(cwd, "audio_files")
if not os.path.exists(AUDIO_DIRECTORY):
	os.makedirs(AUDIO_DIRECTORY)


# Function to encode the image
def encode_image(image_path):
	with open(image_path, "rb") as image_file:
		return base64.b64encode(image_file.read()).decode('utf-8')

# Function to get file extension
def get_file_extension(file_name):
	return os.path.splitext(file_name)[-1]


def clear_session_states():
	st.session_state.msg = []
	if "memory" not in st.session_state:
		pass
	else:
		del st.session_state["memory"]
		

def starting_bot(): #this bot helps the students to start from nothing  using visual and image tools
	if "starting_bot" in st.session_state:
		st.session_state.chatbot = st.session_state.starting_bot

	with st.expander("Chatbot Settings"):
		c1,c2 = st.columns([2,2])
		with c2:
			if "voice_image_file_exist" not in st.session_state:
				st.session_state.voice_image_file_exist = None
			if "vision_model" not in st.session_state:
				st.session_state.vision_model = "gpt-vision"
			if "start_prompt" not in st.session_state:
				st.session_state.start_prompt = None
			
			if st.toggle("Gemini Vision (Default: GPT-3 Vision)"):
				st.session_state.vision_model = "gemini-vision"
			else:
				st.session_state.vision_model = "gpt-vision"
		with c1:
			load_rag()
		#new options --------------------------------------------------------
	if st.button("Clear Chat"):
		clear_session_states()

	b1, b2 = st.columns([3,2])

	with b1:

		if st.session_state.vs:#chatbot with knowledge base
			base_bot(START_BOT, True, True) #chatbot with knowledge base and memory
		else:#chatbot with no knowledge base
			base_bot(START_BOT, True, False) #chatbot with no knowledge base but with memory
	with b2:
		with st.container(border=True):
			st.write("Take a picture to start learning!")
			detect_file_upload()
			
		with st.container(border=True):
			st.write("Help me get started! 👌")
			if "memory" not in st.session_state:
				st.session_state.memory = ConversationBufferWindowMemory(k=st.session_state.default_k_memory)
			c1,c2 = st.columns([1,1])
			with c1:
				if st.button("How to get started on this topic"):
					with st.spinner("Please be patient, I am thinking..."):
						st.session_state.start_prompt = START_PROMPT1
						if st.session_state.voice_image_file_exist:
							if st.session_state.vision_model == "gpt-vision":
								response = analyse_image_chat(st.session_state.voice_image_file_exist, st.session_state.start_prompt)
							else:
								response = analyse_image_chat_gemini(st.session_state.voice_image_file_exist, st.session_state.start_prompt)
							st.session_state.msg.append({"role": "assistant", "content": response})
							st.session_state["memory"].save_context({"input": START_PROMPT1},{"output": response})
							st.rerun()
						pass
				if st.button("What are the key concepts in this topic?"):
					with st.spinner("Please be patient, I am thinking..."):
						st.session_state.start_prompt = START_PROMPT2
						if st.session_state.voice_image_file_exist:
							if st.session_state.vision_model == "gpt-vision":
								response = analyse_image_chat(st.session_state.voice_image_file_exist, st.session_state.start_prompt)
							else:
								response = analyse_image_chat_gemini(st.session_state.voice_image_file_exist, st.session_state.start_prompt)
							st.session_state.msg.append({"role": "assistant", "content": response})
							st.session_state["memory"].save_context({"input": START_PROMPT2},{"output": response})
							st.rerun()
					
			with c2:
				if st.button("Can you explain this topic to me?"):
					with st.spinner("Please be patient, I am thinking..."):
						st.session_state.start_prompt = START_PROMPT3
						if st.session_state.voice_image_file_exist:
							if st.session_state.vision_model == "gpt-vision":
								response = analyse_image_chat(st.session_state.voice_image_file_exist, st.session_state.start_prompt)
							else:
								response = analyse_image_chat_gemini(st.session_state.voice_image_file_exist, st.session_state.start_prompt)
							st.session_state.msg.append({"role": "assistant", "content": response})
							st.session_state["memory"].save_context({"input": START_PROMPT3},{"output": response})
							st.rerun()
				if st.button("What is this topic about?"):
					with st.spinner("Please be patient, I am thinking..."):
						st.session_state.start_prompt = START_PROMPT4
						if st.session_state.voice_image_file_exist:
							if st.session_state.vision_model == "gpt-vision":
								response = analyse_image_chat(st.session_state.voice_image_file_exist, st.session_state.start_prompt)
							else:
								response = analyse_image_chat_gemini(st.session_state.voice_image_file_exist, st.session_state.start_prompt)
							st.session_state.msg.append({"role": "assistant", "content": response})
							st.session_state["memory"].save_context({"input": START_PROMPT4},{"output": response})
							st.rerun()
			


def detect_file_upload():
	
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
			st.session_state.voice_image_file_exist = temp_file_path
			st.success("Image uploaded successfully")
	else:
		st.session_state.voice_image_file_exist = None
		



def analyse_image_chat_gemini(temp_file_path, prompt):
	genai.configure(api_key = st.secrets["google_key"])
	image = PIL.Image.open(temp_file_path)
	vision_model = genai.GenerativeModel('gemini-pro-vision')
	response = vision_model.generate_content([prompt,image])
	if response:
		os.remove(temp_file_path)
		return response.text
	else:
		os.remove(temp_file_path)
		return False



def analyse_image_chat(temp_file_path, prompt):
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
	
#================================== image chatbot ========================================	


def prompt_template_function(prompt, memory_flag, rag_flag):
	#check if there is kb loaded
	if st.session_state.vs:
		docs = st.session_state.vs.similarity_search(prompt)
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


def base_bot(bot_name, memory_flag, rag_flag):
	#set st.session_state.chatbot = something
	client = OpenAI(api_key=return_openai_key())
	full_response = ""
	greetings_str = f"Hi, I am {bot_name}"
	help_str = "How can I help you today?"
	img_str = "At any time, if you have an uploaded image, use this starting prompt to ask about your image: 'From this image'"
	if "image_prompt" not in st.session_state:
		st.session_state.image_prompt = "Enter your query or question here..."

	# Check if st.session_state.msg exists, and if not, initialize with greeting and help messages
	if 'msg' not in st.session_state:
		st.session_state.msg = [
			{"role": "assistant", "content": greetings_str},
			{"role": "assistant", "content": help_str},
			{"role": "assistant", "content": img_str}
		]
	elif st.session_state.msg == []:
		st.session_state.msg = [
			{"role": "assistant", "content": greetings_str},
			{"role": "assistant", "content": help_str},
			{"role": "assistant", "content": img_str}
		]
	messages = st.container(border=True)
	# Showing the history of the chatbots
	for message in st.session_state.msg:
		with messages.chat_message(message["role"]):
			st.markdown(message["content"])

	if st.session_state.voice_image_file_exist:
		st.session_state.image_prompt = "From this image, I would like to know about the following"
	else:
		st.session_state.image_prompt = "Enter your query or question here..."

	# Chat bot input
	try:
		if prompt := st.chat_input(placeholder=st.session_state.image_prompt):
			st.session_state.msg.append({"role": "user", "content": prompt})
			with messages.chat_message("user"):
				st.markdown(prompt)

			image_analysis_required = prompt.lower().startswith("from this image")

			if st.session_state.voice_image_file_exist and image_analysis_required:
				with st.spinner("Please be patient, I am processing your image and question..."):
					with messages.chat_message("assistant"):
						if st.session_state.vision_model == "gpt-vision":
							response = analyse_image_chat(st.session_state.voice_image_file_exist, prompt)
						else:
							response = analyse_image_chat_gemini(st.session_state.voice_image_file_exist, prompt)
						st.write(response)
						
			else:
				with messages.chat_message("assistant"):
					prompt_template = prompt_template_function(prompt, memory_flag, rag_flag)
					stream = client.chat.completions.create(
						model=st.session_state.openai_model,
						messages=[
							{"role": "system", "content": prompt_template},
							{"role": "user", "content": prompt},
						],
						temperature=st.session_state.default_temp,  # settings option
						presence_penalty=st.session_state.default_presence_penalty,  # settings option
						frequency_penalty=st.session_state.default_frequency_penalty,  # settings option
						stream=True  # settings option
					)
					response = st.write_stream(stream)
			st.session_state.msg.append({"role": "assistant", "content": response})
			st.session_state["memory"].save_context({"input": prompt}, {"output": response})

	except Exception as e:
		st.exception(e)

#================================== Network Bot =====================================
def generate_image(i_prompt):
	if "image_url" not in st.session_state:
		st.session_state.image_url = None
	if st.button("Generate"):
		with st.spinner("Please wait, I am generating the image..."):
			if i_prompt is not None:
				client = OpenAI(api_key=return_openai_key())
				response = client.images.generate(
				model="dall-e-3",
				prompt=i_prompt,
				size="1024x1024",
				quality="standard",
				n=1,
				)

				st.session_state.image_url = response.data[0].url
				st.image(st.session_state.image_url)

def network_bot():
	if "kg_text" not in st.session_state:
		st.session_state.kg_text = ""
	
	if "mindmap_bot" in st.session_state:
		st.session_state.chatbot = st.session_state.mindmap_bot

	with st.expander("Chatbot RAG Settings"):
		load_rag()


	if st.button("Clear Chat"):
		clear_session_states()
		st.session_state.kg_summary = None
		st.session_state.kg_text = ""
		st.session_state.image_url = None

	d1, d2 = st.columns([3,2])


	with d1:
		if st.session_state.vs:#chatbot with knowledge base
			network_base_bot(CONNECT_BOT, True, True) #chatbot with knowledge base and memory
		else:#chatbot with no knowledge base
			network_base_bot(CONNECT_BOT, True, False) #chatbot with no knowledge base but with memory
	with d2:
		with st.container(border=True):
			st.write(":blue[Knowledge Map]")
			if "kg_text" not in st.session_state:
				st.session_state.kg_text = ""
			if st.session_state.kg_text != "":
				if st.button("Render Knowledge Map"):
					st.image(render_diagram(st.session_state.kg_text))
					st.session_state.kg_text = ""
			else:
				st.write("Please generate a knowledge map syntax first")
		with st.container(border=True):
			st.write(":red[Knowledge Graph Information]")
			if st.session_state.kg_summary != None:
				if st.button("Generate Knowledge Map Syntax"):
					with st.spinner("Please wait, I am processing your request..."):
						kb_prompt = map_prompter_with_plantuml(st.session_state.kg_summary)
						if kb_prompt:
							kb_syntax = generate_plantuml_mindmap(kb_prompt)
							st.session_state.kg_text = kb_syntax
							update_syntax = st.text_area("Knowledge Map Syntax (Editable)", value=kb_syntax, height=300)
							if st.button("Update Knowledge Map"):
								st.session_state.kg_text = update_syntax
								st.success("Knowledge Map updated successfully")
			else:
				st.write("To generate a knowlegde map, start a conversation with the chatbot and then click on the 'Generate Knowledge Map Syntax' button when you have a response that you want to see in a knowledge map")
		with st.container(border=True):
			st.write(":green[Image Generation]")
			if st.session_state.kg_summary != None:
				i_prompt = "Based on this response given by a chatbot :" + st.session_state.kg_summary + "Generate a pictographic representation of the response to help me understand better"
				generate_image(i_prompt)
			else:
				st.write("To generate an image, start a conversation with the chatbot and then click on the 'Generate' button when you have a response that you want to see in an image")
			
		
def prompt_template_function_network(prompt, memory_flag, rag_flag):
	#check if there is kb loaded
	if st.session_state.vs:
		docs = st.session_state.vs.similarity_search(prompt)
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




def network_base_bot(bot_name, memory_flag, rag_flag):

	client = OpenAI(api_key=return_openai_key())
	full_response = ""
	greetings_str = f"Hi, I am {bot_name}"
	help_str = "How can I help you today?"
	if "kg_summary" not in st.session_state:
		st.session_state.kg_summary = None
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
				prompt_template = prompt_template_function_network(prompt, memory_flag, rag_flag)
				stream = client.chat.completions.create(
					model=st.session_state.openai_model,
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
			st.session_state.kg_summary = response
			st.session_state.msg.append({"role": "assistant", "content": response})
			st.session_state["memory"].save_context({"input": prompt},{"output": response})

			
	except Exception as e:
		st.exception(e)


#================================== Language Bot =====================================
def language_bot():

	if "language_bot" in st.session_state:
		st.session_state.chatbot = st.session_state.language_bot

	if "voice_audio_file_path" not in st.session_state:
		st.session_state.voice_audio_file_path = None

	with st.expander("Chatbot Settings"):
		load_rag()

	if st.button("Clear Chat"):
		clear_session_states()
			
		
	l1, l2 = st.columns([3,2])

	with l1:
		if st.session_state.vs:
			language_base_bot(LANGUAGE_BOT, True, True) #chatbot with knowledge base and memory
		else:
			language_base_bot(LANGUAGE_BOT, True, False) #chatbot with no knowledge base but with memory
	with l2:
		with st.container(border=True):
			if "translated_response" not in st.session_state:
				st.session_state.translated_response = ""
			st.write(":blue[Text to Speech]")
			if st.toggle("Translated Text"):
				st.write(st.session_state.translated_response)
				if st.session_state.translated_response != "":
					if st.button("Generate Speech"):
						with st.spinner("Please wait, I am generating the audio..."):
							audio_file_path = generate_audio(st.session_state.translated_response)
							st.session_state.voice_audio_file_path = audio_file_path
							st.success("Audio generated and stored successfully.")
							st.audio(st.session_state.voice_audio_file_path )
				else:
					st.write("Create a translated text to generate speech")
			else:
				st.write(st.session_state.translate_msg)
				if st.session_state.translate_msg != "":
					if st.button("Generate Speech"):
						with st.spinner("Please wait, I am generating the audio..."):
							audio_file_path = generate_audio(st.session_state.translate_msg)
							st.session_state.voice_audio_file_path = audio_file_path
							st.success("Audio generated and stored successfully.")
							st.audio(st.session_state.voice_audio_file_path )
				else:
					st.write("Talk to the chatbot to create a text to generate speech")
		with st.container(border=True):
			st.write(":red[Translation]")
			language = st.selectbox("Choose a language to translate to: ",["English", "Chinese", "Malay", "Tamil"])
			if st.button("Translate"):
				client = OpenAI(api_key=return_openai_key())
				stream = client.chat.completions.create(
						model=st.session_state.openai_model,
						messages=[
							{"role": "system", "content": f"Translate the following to {language} as accurately as possible"},
							{"role": "user", "content": st.session_state.translate_msg},
						],
						temperature=st.session_state.default_temp,  # settings option
						presence_penalty=st.session_state.default_presence_penalty,  # settings option
						frequency_penalty=st.session_state.default_frequency_penalty,  # settings option
						stream=True  # settings option
					)
				response = st.write_stream(stream)
				st.session_state.translated_response = response

				

def prompt_template_function_language(prompt, memory_flag, rag_flag):
	#check if there is kb loaded
	if st.session_state.vs:
		docs = st.session_state.vs.similarity_search(prompt)
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




def language_base_bot(bot_name, memory_flag, rag_flag):

	client = OpenAI(api_key=return_openai_key())
	full_response = ""
	greetings_str = f"Hi, I am {bot_name}"
	help_str = "How can I help you today?"
	if "translate_msg" not in st.session_state:
		st.session_state.translate_msg = None
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
				prompt_template = prompt_template_function_language(prompt, memory_flag, rag_flag)
				stream = client.chat.completions.create(
					model=st.session_state.openai_model,
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
			st.session_state.translate_msg = response
			st.session_state.msg.append({"role": "assistant", "content": response})
			st.session_state["memory"].save_context({"input": prompt},{"output": response})		
			
	except Exception as e:
		st.exception(e)



def generate_audio(text):
	# Generate audio from text
	client = OpenAI(api_key=return_openai_key())
	response = client.audio.speech.create(
		model="tts-1",
		voice="alloy",
		input=text
	)
	
	# Store the audio in a temporary file
	with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
		response.stream_to_file(temp_file.name)
		return temp_file.name
	


#===============================Linking Bot===========================================

def linking_bot():
	
	if "linking_bot" in st.session_state:
		st.session_state.chatbot = st.session_state.linking_bot

	with st.expander("Chatbot Settings"):
		load_rag()


	if st.button("Clear Chat"):
		clear_session_states()
		if st.session_state.concept1:
			st.session_state.concept1 = ""
		if st.session_state.concept2:
			st.session_state.concept2 = ""

	j1, j2 = st.columns([3,2])

	with j1:
		if st.session_state.vs:
			linking_base_bot(LINKING_BOT, True, True)
		else:
			linking_base_bot(LINKING_BOT, True, False)
	with j2:
		if "concept1" not in st.session_state:
			st.session_state.concept1 = ""
		with st.container(border=True):
			st.session_state.concept1 = st.text_area("Concept 1", max_chars=1000)
			pass
		if "concept2" not in st.session_state:
			st.session_state.concept2 = ""
		with st.container(border=True):
			st.session_state.concept2 = st.text_area("Concept 2", max_chars=1000)
			pass
		with st.container(border=True):
			if "memory" not in st.session_state:
				st.session_state.memory = ConversationBufferWindowMemory(k=st.session_state.default_k_memory)
			if st.button("Link Concepts"):
				if st.session_state.concept1 != "" and st.session_state.concept2 != "":
					client = OpenAI(api_key=return_openai_key())
					stream = client.chat.completions.create(
						model=st.session_state.openai_model,
						messages=[
							{"role": "user", "content": f"""Link the following concepts together concept 1 : {st.session_state.concept1} and concept 2 : {st.session_state.concept2} , 
								explain in simple sentences how the concepts can be linked together and generate the complete response that link both concepts together, however should the concepts are not linked, 
								please let the user know that both concepts cannot be linked, explain why and provide a response that can be used to link the concepts together in the future."""},	
						],
						temperature=st.session_state.default_temp,  # settings option
						presence_penalty=st.session_state.default_presence_penalty,  # settings option
						frequency_penalty=st.session_state.default_frequency_penalty,  # settings option
						stream=True  # settings option
					)
				response = st.write_stream(stream)
				st.session_state.msg.append({"role": "assistant", "content": response})
				st.session_state["memory"].save_context({"input": START_PROMPT1},{"output": response})
				st.rerun()

def prompt_template_function_linking(prompt, memory_flag, rag_flag):
	#check if there is kb loaded
	if st.session_state.vs:
		docs = st.session_state.vs.similarity_search(prompt)
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


def linking_base_bot(bot_name, memory_flag, rag_flag):

	client = OpenAI(api_key=return_openai_key())
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
				prompt_template = prompt_template_function_linking(prompt, memory_flag, rag_flag)
				stream = client.chat.completions.create(
					model=st.session_state.openai_model,
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
			st.session_state["memory"].save_context({"input": prompt},{"output": response})
			
	except Exception as e:
		st.exception(e)