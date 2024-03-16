import streamlit as st
from basecode2.org_module import sa_select_school
import pandas as pd
import configparser
import ast
from pymongo import MongoClient

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
APP_CONFIG = config_handler.get_config_values('menu_lists', 'APP_CONFIG')


def initialize_app_settings():
	if "app_config" not in st.session_state:
		st.session_state.app_config = {}
	if "a_collection" not in st.session_state:
		st.session_state.a_collection = None
		
	if "URI" in st.secrets["MONGO"]:
		MONGO_URI = st.secrets["MONGO"]["URI"]
		DATABASE_NAME = st.secrets["MONGO"]["DATABASE"]
	else:
		pass

	client = MongoClient(MONGO_URI, tls=True,tlsAllowInvalidCertificates=True)
	db = client[DATABASE_NAME]
	st.session_state.a_collection = db["app_settings"]    


# Function to load or create a new document
def load_document(sch_name):
	document = st.session_state.a_collection.find_one({"sch_name": sch_name})
	if not document:
		# Create a new document if it doesn't exist
		document = {"sch_name": sch_name}
		document = {**document, **APP_CONFIG}
		st.session_state.a_collection.insert_one(document)
	return document

def load_app_settings(): #load_prompt settings
	initialize_app_settings()
	excluded_fields = ['_id', 'sch_name']
	doc = load_document(st.session_state.user['school_id'])
		# Initialize session state for each field in the document, excluding certain fields
	for key, value in doc.items():
		if key not in st.session_state and key not in excluded_fields:
			st.session_state[key] = value
	return True
		#load all app settings flag to true
	
def load_sa_app_settings():
	initialize_app_settings()
	excluded_fields = ['_id', 'sch_name']
	"Load all app settings for SA user, you need to select to run this application"
	sch_names = sa_select_school()
	if sch_names == []:
		st.error("No schools found")
		return True
	else:
		school = st.selectbox('Select School', ["Select School"] + sch_names, key='app_school')
		if school != "Select School" and school != None:
			st.session_state.user['school_id'] = school
			doc = load_document(school)
			# Initialize session state for each field in the document, excluding certain fields
			for key, value in doc.items():
				if key not in st.session_state and key not in excluded_fields:
					st.session_state[key] = value
			return True	

def set_app_settings():
	initialize_app_settings()
	if "app_pdf" not in st.session_state:
		st.session_state.app_pdf = None
	if st.session_state.user['profile_id'] == SA:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', sch_names, key='app_school')
		excluded_fields = ['_id', 'sch_name']
		if school:
			doc = load_document(school)
			# Initialize session state for each field in the document, excluding certain fields
			for key, value in doc.items():
				if key not in st.session_state and key not in excluded_fields:
					st.session_state[key] = value
		
		# Convert the document (excluding specified keys) to a DataFrame for display
			doc_for_df = {k: v for k, v in doc.items() if k not in excluded_fields}
			st.session_state.app_pdf  = pd.DataFrame(list(doc_for_df.items()), columns=['Field', 'Values'])
			#data_pd = st.data_editor(st.session_state.app_pdf, num_rows="dynamic", width=300, height=300)
			# Update the document with the edited values
			st.write("Current settings")
			st.dataframe(st.session_state.app_pdf)

		field = st.selectbox("Select field to edit", st.session_state.app_pdf['Field'].tolist(), key='app_action')
		if field:
			new_value = st.text_input(f"Enter new value for {field}", key='app_value')
			if st.button("Update"):
				st.session_state.app_pdf[field] = new_value
				st.session_state.a_collection.update_one({"sch_name": school}, {"$set": {field: new_value}})
				st.write("Updated successfully")
	else:
		st.write("You are not authorized to perform this action")

def return_openai_key():
	return st.secrets["api_key"]


def delete_app_settings():
	st.subheader(":red[Delete App Configuration]")
	if st.session_state.user['profile_id'] != SA:
		st.write("You are not authorized to perform this action")
		return
	else:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', ["Select School"] + sch_names, key='app_school_delete')
		if school:
			if st.checkbox("Are you sure you want to delete this school's settings?"):
				if st.button("Delete"):
					st.session_state.a_collection.delete_one({"sch_name": school})
					st.write(f"{school} settings deleted successfully")
