import openai
from openai import OpenAI
import streamlit as st
from basecode2.authenticate import return_openai_key, return_cohere_key, return_google_key
import google.generativeai as genai
import os
import pandas as pd
import sqlite3
import string
import cohere
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

def clear_session_states():
	st.session_state.messages = []
	if "memory" not in st.session_state:
		pass
	else:
		del st.session_state["memory"]


def call_api():
	st.subheader("Calling the LLM API")
	prompt_design = st.text_input("Enter your the prompt design for the API call:", value="You are a helpful assistant.")
	prompt_query = st.text_input("Enter your user input:", value="Tell me about Singapore in the 1970s in 50 words.")
	select_model = st.selectbox("Select a model", ["gpt-4-turbo-preview", "gpt-3.5-turbo", "cohere", "gemini-pro"])	
	if st.button("Call the API"):
		if prompt_design and prompt_query:
			if select_model == "cohere":
				call_cohere_api(prompt_design, prompt_query)
			elif select_model == "gemini-pro":
				call_google_api(prompt_design, prompt_query)
			else:
				api_call(prompt_design, prompt_query, select_model)
		else:
			st.warning("Please enter a prompt design and user input.")


def call_google_api(prompt_design, prompt_query):
	# Initialize the Cohere client
	genai.configure(api_key = return_google_key())

	with st.status("Calling the Google API..."):
		# Call the Cohere API
		
		chat_model = genai.GenerativeModel('gemini-pro')
		response = chat_model.generate_content(prompt_design + prompt_query)
		# Check if the response has the expected structure
		
		st.write(response.text)

def call_cohere_api(prompt_design, prompt_query):
	# Initialize the Cohere client
	co = cohere.Client(return_cohere_key())

	with st.status("Calling the Cohere API..."):
		# Call the Cohere API
		response = co.generate(prompt=prompt_design + "\n" + prompt_query, max_tokens=1000)
		
		# Check if the response has the expected structure
		if response and response.generations:
			# Extract the text of the first generation
			generation_text = response.generations[0].text

			# Display the raw response (optional)
			st.markdown("**This is the raw response:**")
			st.write(response)

			# Display the extracted response
			st.markdown("**This is the extracted response:**")
			st.write(generation_text)

			# Display token usage information
			# Display token usage information
			if 'meta' in response and 'billed_units' in response['meta']:
				completion_tokens = response['meta']['billed_units']['output_tokens']
				prompt_tokens = response['meta']['billed_units']['input_tokens']
				st.write(f"Completion Tokens: {completion_tokens}")
				st.write(f"Prompt Tokens: {prompt_tokens}")
		else:
			st.error("No response or unexpected response format received from the API.")

def api_call(p_design, p_query, model):

	st.title("Api Call")
	#MODEL = "gpt-3.5-turbo"
	client = OpenAI(api_key=return_openai_key())
	with st.status("Calling the OpenAI API..."):
		response = client.chat.completions.create(
			model=model,
			messages=[
				{"role": "system", "content": p_design},
				{"role": "user", "content": p_query},
			],
			temperature=0,
		)

		st.markdown("**This is the raw response:**") 
		st.write(response)
		st.markdown("**This is the extracted response:**")
		st.write(response.choices[0].message.content)
		completion_tokens = response.usage.completion_tokens
		prompt_tokens = response.usage.prompt_tokens
		total_tokens = response.usage.total_tokens

		st.write(f"Completion Tokens: {completion_tokens}")
		st.write(f"Prompt Tokens: {prompt_tokens}")
		st.write(f"Total Tokens: {total_tokens}")




