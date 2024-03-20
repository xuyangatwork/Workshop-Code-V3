import openai
from openai import OpenAI
import streamlit as st
from basecode2.authenticate import return_openai_key
import os
import streamlit_antd_components as sac
import configparser
import os
import ast
import pandas as pd
import cohere
import google.generativeai as genai
import json


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
SUBJECTS = config_handler.get_config_values('menu_lists', 'SUBJECTS_SINGAPORE')
CLASS_LEVELS = config_handler.get_config_values('menu_lists', 'CLASS_LEVELS_SINGAPORE')
COLS_NAME = config_handler.get_config_values('menu_lists', 'COLUMNS_NAME')


def chatbot_settings():
	temp = st.number_input("Temperature", value=st.session_state.default_temp, min_value=0.0, max_value=1.0, step=0.1)
	presence_penalty = st.number_input("Presence Penalty", value=st.session_state.default_presence_penalty, min_value=-2.0, max_value=2.0, step=0.1)
	frequency_penalty = st.number_input("Frequency Penalty", value=st.session_state.default_frequency_penalty, min_value=-2.0, max_value=2.0, step=0.1)
	top_p = st.number_input("Top P", value=st.session_state.default_top_p, min_value=0.0, max_value=1.0, step=0.1)
	max_tokens = st.number_input("Max Tokens", value=st.session_state.default_max_tokens, min_value=0, max_value=4000, step=10)

	if st.button("Update Chatbot Settings", key = 1):
		st.session_state.default_temp = temp
		st.session_state.default_presence_penalty = presence_penalty
		st.session_state.default_frequency_penalty= frequency_penalty
		st.session_state.default_top_p = top_p
		st.session_state.default_max_tokens = max_tokens
	


def generated_app():
	st.title("Data Generation Form")

	select_model = st.selectbox("Select a model", ["gpt-4-turbo-preview","gpt-3.5-turbo-1106"])

	if st.checkbox("Configure Chatbot parameters"):
		chatbot_settings()

	# Form for input
	with st.form("data_gen_form"):
		num_rows = st.number_input("Number of Rows to Generate", min_value=1, value=5)
		selected_subjects = st.multiselect("Select Subjects", SUBJECTS)
		selected_levels = st.multiselect("Select Class Levels", CLASS_LEVELS)
		selected_columns = st.multiselect("Select Column Names", COLS_NAME, default=COLS_NAME)
		number_of_words_questions = st.number_input("Number of words for the question", min_value=1, value=30)
		number_of_words_suggest = st.number_input("Number of words for the suggested answer", min_value=1, value=30)
		number_of_words_student = st.number_input("Number of words for the student answer", min_value=1, value=30)
		other_prompts = st.text_area("Other Prompts", "")
		submit_button = st.form_submit_button("Generate Data")

		if submit_button:
			# Call function to generate data
			generated_prompt = f"""Generate {num_rows} rows of data for {selected_subjects} at {selected_levels} with columns {selected_columns}.
			You are going to generate about {number_of_words_questions} for the questions, about {number_of_words_suggest} for the suggested answer and about {number_of_words_student} for the student answer. \n\n 
			{other_prompts}
			If the subject is a language subject, you are suppose to generate the question and the suggested answer in the language of the subject. \n\n
			You are supppose to use column names  as references to help you generate a table of data. \n\nColumn names: {selected_columns}\n\n"""
			empty_data = [[None for _ in range(len(selected_columns))] for _ in range(num_rows)]
			df = pd.DataFrame(empty_data, columns=selected_columns)
			st.data_editor(df,num_rows="dynamic")
			lesson_bot(generated_prompt, select_model)


def lesson_bot(prompt, model):
	try:
		if prompt:
			with st.status("Calling the OpenAI API..."):

				client = OpenAI(
					# defaults to os.environ.get("OPENAI_API_KEY")
					api_key=return_openai_key(),
)
				response = client.chat.completions.create(
					model=model,
					messages=[
						{"role": "user", "content": prompt},
					],
					temperature=st.session_state.default_temp, #settings option
					presence_penalty=st.session_state.default_presence_penalty, #settings option
					frequency_penalty=st.session_state.default_frequency_penalty, #settings option
					top_p = st.session_state.default_top_p, #settings option
				)
				st.write(response.choices[0].message.content)
	except Exception as e:
		st.error(e)