import streamlit as st
from langchain.chat_models import ChatOpenAI
import pandas as pd
from basecode.authenticate import return_api_key
import openai
from pandasai import SmartDataframe
from pandasai.llm.openai import OpenAI
import matplotlib.pyplot as plt
import configparser
import ast
import os
from basecode.class_dash import fetch_data_by_username, fetch_data_by_school, fetch_data_by_sa

# Create or check for the 'database' directory in the current working directory
cwd = os.getcwd()
WORKING_DIRECTORY = os.path.join(cwd, "database")

if not os.path.exists(WORKING_DIRECTORY):
	os.makedirs(WORKING_DIRECTORY)

if st.secrets["sql_ext_path"] == "None":
	WORKING_DATABASE= os.path.join(WORKING_DIRECTORY , st.secrets["default_db"])
else:
	WORKING_DATABASE= st.secrets["sql_ext_path"]
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
SA = config_handler.get_config_values('constants', 'SA')
AD = config_handler.get_config_values('constants', 'AD')

def download_data(user_id, sch_id, profile):
	if profile == SA:#super admin
		data, columns = fetch_data_by_sa(sch_id)
		
	elif profile == AD:#administrator or super admin
		data, columns = fetch_data_by_school(sch_id)
	else: 
		data, columns = fetch_data_by_username(user_id)
	df = pd.DataFrame(data, columns=columns)
	return df


# PandasAI- A smart agent that can do visual analytics
def pandas_ai(user_id, sch_id, profile):
	openai.api_key = return_api_key()
	os.environ["OPENAI_API_KEY"] = return_api_key()

	# Upload CSV file using st.file_uploader
	uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
	if "api_key" not in st.session_state:
		st.session_state.api_key = return_api_key()
	st.write("API key: ", st.session_state.api_key)
	st.session_state.prompt_history = []
	st.session_state.df = None

	if uploaded_file is not None:
		try:
			df = pd.read_csv(uploaded_file)
			st.session_state.df = df
		except Exception as e:
			st.write("There was an error processing the CSV file.")
			st.write(e)

	else:
		st.session_state.df = download_data(user_id, sch_id, profile)
		
	# Create a unique directory for each user
	user_chart_dir = os.path.join("exports/charts", str(st.session_state.user['id']))

	if not os.path.exists(user_chart_dir):
		os.makedirs(user_chart_dir)

	def clear_user_images():
		# Function to delete existing images in the user's directory
		for file in os.listdir(user_chart_dir):
			if file.endswith(".png"):
				os.remove(os.path.join(user_chart_dir, file))

	with st.form("Question"):
		question = st.text_input("Question", value="", type="default")
		submitted = st.form_submit_button("Submit")
		if submitted:
			clear_user_images()  # Clear existing images in the user's directory
			with st.spinner():
				llm = OpenAI(api_token=return_api_key())
				df = SmartDataframe(
					st.session_state.df,
					config={
						"llm": llm,
						"save_charts_path": user_chart_dir,
						"save_charts": True,
						"verbose": True,
					},
				)
				response = df.chat(question)

				# Display the textual response (if any):
				if response:
					st.write(response)

				# Assuming the chart is saved in the user_chart_dir
				# Find the latest chart (if any)
				list_of_files = [os.path.join(user_chart_dir, f) for f in os.listdir(user_chart_dir) if f.endswith(".png")]
				if list_of_files:
					latest_chart_path = max(list_of_files, key=os.path.getctime)
					st.image(latest_chart_path, caption="Generated Chart", use_column_width=True)

				st.session_state.prompt_history.append(question)

	if st.session_state.df is not None:
		st.subheader("Data Table:")
		st.write(st.session_state.df)

	st.subheader("Prompt history:")
	st.write(st.session_state.prompt_history)

	if st.button("Clear"):
		st.session_state.prompt_history = []
		st.session_state.df = None
		clear_user_images()  # Clear images when clearing the session