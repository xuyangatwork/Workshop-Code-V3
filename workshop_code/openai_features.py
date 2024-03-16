import streamlit as st
from basecode.authenticate import return_api_key
from basecode.users_module import vectorstore_selection_interface
from langchain.memory import ConversationBufferWindowMemory
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
from nocode_workshop.k_map import map_creation_form, map_prompter_with_plantuml_form, generate_plantuml_mindmap, render_diagram
import requests

cwd = os.getcwd()
AUDIO_DIRECTORY = os.path.join(cwd, "audio_files")

if not os.path.exists(AUDIO_DIRECTORY):
	os.makedirs(AUDIO_DIRECTORY)

openai.api_key = return_api_key()

client = OpenAI(
	# defaults to os.environ.get("OPENAI_API_KEY")
	api_key=return_api_key(),
)

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


def images_features():
	options = sac.chip(items=[
								sac.ChipItem(label='Image Generator', icon='image'),
								sac.ChipItem(label='Knowledge Map Generator', icon='diagram-3'),
								sac.ChipItem(label='Image analyser with chat', icon='clipboard-data'),
							], format_func='title', radius='sm', size='sm', align='left', variant='light')
	if options == 'Image Generator':
		st.subheader("Image Generator using DALL-E 3")
		generate_image()
	elif options == 'Knowledge Map Generator':
		st.subheader("Knowledge Map Generator using PlantUML")
		subject, topic, levels = map_creation_form()
		if subject and topic and levels:
			kb_prompt = map_prompter_with_plantuml_form(subject, topic, levels)
			if kb_prompt:
				with st.spinner("Generating knowledge map..."):
					kb_syntax = generate_plantuml_mindmap(kb_prompt)
					st.write(kb_syntax)
					st.image(render_diagram(kb_syntax))

	elif options == 'Image analyser with chat':
		if "voice_image_file_exist" not in st.session_state:
			st.session_state.voice_image_file_exist = None
		if "vision_model" not in st.session_state:
			st.session_state.vision_model = "gpt-vision"
		st.subheader("Image analyser with chat")
		with st.expander("Image input"):
			vectorstore_selection_interface(st.session_state.user["id"])
			if st.toggle("Gemini Vision"):
				st.session_state.vision_model = "gemini-vision"
			detect_file_upload()
			pass
		if st.button("Clear chat"):
			clear_session_states()
		visual_basebot_memory("VISUAL BOT")


def voice_features():
	options = sac.chip(items=[
								sac.ChipItem(label='Conversation Helper', icon='mic'),
								sac.ChipItem(label='Call Agent', icon='headset'),
							], format_func='title', radius='sm', size='sm', align='left', variant='light')
	if options == 'Conversation Helper':
		st.subheader("Conversation Helper")
		if st.toggle("Upload Audio"):
			transcript = upload_audio()
		else:
			transcript = record_myself()
		if transcript:
			st.write("Providing conversation feedback")
			with st.spinner("Constructing feedback"):
				analyse_audio(transcript)
				pass
	elif options == 'Call Agent':
		st.subheader("Call Agent")
		phone = st.text_input("Enter your phone number")
		st.write("Call Agent - work in progress")



def analyse_audio(prompt):
	prompt_design = """You are listening to the student's speech and you are giving feedback in the content and the way the sentences are structured to the student.
					provide feedback to the student on the following speech, tell the student what is good and what can be improved as well as provide guidance and pointers:"""
	if prompt_design and prompt:
		try:
			prompt = prompt_design + "\n" + prompt
			os.environ["OPENAI_API_KEY"] = return_api_key()
			# Generate response using OpenAI API
			response = client.chat.completions.create(
											model=st.session_state.openai_model, 
											messages=[{"role": "user", "content": prompt}],
											temperature=st.session_state.default_temp, #settings option
											presence_penalty=st.session_state.default_presence_penalty, #settings option
											frequency_penalty=st.session_state.default_frequency_penalty #settings option
											)
			if response.choices[0].message.content != None:
				st.write(response.choices[0].message.content)
	
		except Exception as e:
			st.error(e)
			st.error("Please type in a new topic or change the words of your topic again")
			return False


		

def analyse_image():
	st.subheader("Analyse an image")
	api_key = return_api_key()
	# Streamlit: File Uploader
	uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
	img_file_buffer = st.camera_input("Take a picture")
	prompt = st.text_input("Enter a prompt", value="This is a photo of a")
	if st.button("Analyse"):
		if uploaded_file is not None or img_file_buffer is not None:
			# Save the file to a temporary file
			if img_file_buffer is not None:
				uploaded_file = img_file_buffer
			extension = get_file_extension(uploaded_file.name)
			with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
				temp_file.write(uploaded_file.getvalue())
				temp_file_path = temp_file.name

			# Encode the image
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
				st.write(response.json())
				st.write(response.json()["choices"][0]["message"]["content"])
			else:
				st.error("Failed to get response")

			# Clean up the temporary file
			os.remove(temp_file_path)

# def detect_file_upload():
# 	uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
# 	img_file_buffer = st.camera_input("Take a picture")
# 	if uploaded_file is not None or img_file_buffer is not None:
# 		# Save the file to a temporary file
# 		if img_file_buffer is not None:
# 			uploaded_file = img_file_buffer
# 		extension = get_file_extension(uploaded_file.name)
# 		with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
# 			temp_file.write(uploaded_file.getvalue())
# 			temp_file_path = temp_file.name
# 			st.session_state.voice_image_file_exist = temp_file_path
# 			#st.write(st.session_state.voice_image_file_exist)
# 			#return True

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
		st.info("Please enter a prompt to ask me how to analyse the image or click X to clear the image or upload")



def analyse_image_chat_gemini(temp_file_path, prompt):
	genai.configure(api_key = st.secrets["google_key"])
	image = PIL.Image.open(temp_file_path)
	vision_model = genai.GenerativeModel('gemini-pro-vision')
	response = vision_model.generate_content([prompt,image])
	if response:
		os.remove(temp_file_path)
		return response



def analyse_image_chat(temp_file_path, prompt):
	# Encode the image
	api_key = return_api_key()
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


#below ------------------------------ base bot , K=2 memory for short term memory---------------------------------------------
#faster and more precise but no summary
def memory_buffer_component(prompt):
	if st.session_state.vs:
		docs = st.session_state.vs.similarity_search(prompt)
		resource = docs[0].page_content
		source = docs[0].metadata
	# if "memory" not in st.session_state:
	# 	st.session_state.memory = ConversationBufferWindowMemory(k=st.session_state.default_k_memory)
	mem = st.session_state.memory.load_memory_variables({})
	#st.write(resource)

	if st.session_state.vs:
	
		prompt_template = st.session_state.vision_chatbot + f"""
							Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. 
							Search Result:
							{resource}
							{source}
							History of conversation:
							{mem}
							You must quote the source of the Search Result if you are using the search result as part of the answer"""
	else:
		prompt_template = st.session_state.vision_chatbot + f"""
							History of conversation:
							{mem}
							"""
	
	return prompt_template


#chat completion memory for streamlit using memory buffer
def chat_completion_memory(prompt):
	openai.api_key = return_api_key()
	os.environ["OPENAI_API_KEY"] = return_api_key()	
	prompt_template = memory_buffer_component(prompt)
	#st.write("Prompt Template ", prompt_template)
	response = client.chat.completions.create(
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
	return response




#integration API call into streamlit chat components with memory
def visual_basebot_memory(bot_name):
	full_response = ""
	greetings_str = f"Hi, I am {bot_name}"
	help_str = "How can I help you today?"
	file_upload_str = "We noticed that you have uploaded an image, would you like to analyse it?"
	analyse_image_str = "Please enter a prompt to ask me how to analyse the image or click X to clear the image or upload"
	if "memory" not in st.session_state:
		st.session_state.memory = ConversationBufferWindowMemory(k=st.session_state.default_k_memory)
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
		if st.session_state.voice_image_file_exist != None:
			if os.path.exists(st.session_state.voice_image_file_exist):
			#st.image(st.session_state.voice_image_file_exist)
			# if st.button("Cancel", key=3):
			# 	os.remove(st.session_state.voice_image_file_exist)
			# 	st.session_state.voice_image_file_exist = None
			# 	st.rerun()
				if prompt := st.chat_input("Please analyse this image and...", key=1):
					with st.spinner("Analysing image..."):
						if st.session_state.vision_model == "gemini-vision":
							response = analyse_image_chat_gemini(st.session_state.voice_image_file_exist, prompt).text
						else:
							response = analyse_image_chat(st.session_state.voice_image_file_exist, prompt)
					st.session_state.msg.append({"role": "user", "content": prompt})
					with st.chat_message("user"):
						st.markdown(prompt)
					with st.chat_message("assistant"):
						message_placeholder = st.empty()
						message_placeholder.markdown(response)
						st.session_state.msg.append({"role": "assistant", "content": response})
						st.session_state["memory"].save_context({"input": prompt},{"output": response})
			else:
				st.session_state.voice_image_file_exist = None
				st.rerun()
		elif prompt := st.chat_input("What is up?", key=2):
			st.session_state.msg.append({"role": "user", "content": prompt})
			with st.chat_message("user"):
				st.markdown(prompt)

			with st.chat_message("assistant"):
				message_placeholder = st.empty()
				full_response = ""
				for response in chat_completion_memory(prompt):
					full_response += (response.choices[0].delta.content or "")
					message_placeholder.markdown(full_response + "▌")
				message_placeholder.markdown(full_response)
		
			st.session_state.msg.append({"role": "assistant", "content": full_response})
			st.session_state["memory"].save_context({"input": prompt},{"output": full_response})
			
	except Exception as e:
		st.error(e)


#==== image generator ===================


def generate_image():
	st.subheader("Generate an image")
	i_prompt = st.text_input("Enter a prompt", value="Generate a photo of a")
	if st.button("Generate"):
		if i_prompt is not None or i_prompt != "Generate a photo of a":
			response = client.images.generate(
			model="dall-e-3",
			prompt=i_prompt,
			size="1024x1024",
			quality="standard",
			n=1,
			)

			image_url = response.data[0].url
			st.image(image_url)
		else:
			st.write("Please enter a prompt")

#=======voice================
def text_speech(input_text):
	# Create a temporary file within the 'audio_files' directory
	temp_file = tempfile.NamedTemporaryFile(delete=False, dir=AUDIO_DIRECTORY, suffix='.mp3')
	
	# Generate speech
	response = client.audio.speech.create(
		model="tts-1",
		voice="alloy",
		input=input_text
	)

	# Write the response content to the temporary file
	with open(temp_file.name, 'wb') as file:
		file.write(response.content)

	# Return the path of the temporary file
	return temp_file.name


def text_to_speech():
	st.subheader("Text to Speech")
	if 'audio_file_path' not in st.session_state:
		st.session_state.audio_file_path = None

	user_input = st.text_area("Enter your text here:")

	if user_input and st.button("Generate Speech from Text"):
		st.session_state.audio_file_path = text_speech(user_input)
		st.audio(st.session_state.audio_file_path)

	if st.session_state.audio_file_path and st.button("Reset"):
		# Remove the temporary file
		os.remove(st.session_state.audio_file_path)
		st.session_state.audio_file_path = None
		st.experimental_rerun()

def transcribe_audio(file_path):
	with open(file_path, "rb") as audio_file:
		transcript = client.audio.transcriptions.create(
			model="whisper-1", 
			file=audio_file, 
			response_format="text"
		)
	return transcript

def translate_audio(file_path):
	with open(file_path, "rb") as audio_file:
		transcript = client.audio.translations.create(
		model="whisper-1", 
		file=audio_file
		)
		return transcript


def upload_audio():
	# Streamlit: File Uploader
	st.subheader("Transcribe an audio file")
	uploaded_file = st.file_uploader("Upload an audio file", type=["wav", "mp3"])

	if uploaded_file is not None:
		# Save the file to a temporary file
		extension = os.path.splitext(uploaded_file.name)[-1]
		with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
			temp_file.write(uploaded_file.getvalue())
			temp_file_path = temp_file.name

		# Transcribe the audio
		if st.button("Transcribe"):
			with st.spinner("Transcribing..."):
				transcription_result = transcribe_audio(temp_file_path)
				st.write(transcription_result)

		# Clean up the temporary file
		os.remove(temp_file_path)

def record_myself():
	# Audio recorder
	st.subheader("Record and Transcribe an audio file")
	wav_audio_data = st_audiorec()

	if st.button("Transcribe (Maximum: 30 Seconds)") and wav_audio_data is not None:
		memory_file = io.BytesIO(wav_audio_data)
		memory_file.name = "recorded_audio.wav"

		with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
			tmpfile.write(wav_audio_data)

		with st.spinner("Transcribing..."):
			transcription_result = transcribe_audio(tmpfile.name)
			os.remove(tmpfile.name)  # Delete the temporary file manually after processing
			st.write(transcription_result)
			return transcription_result
		


			