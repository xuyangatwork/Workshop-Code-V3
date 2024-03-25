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
TCH = config_handler.get_config_values('constants', 'TCH')
APP_CONFIG = config_handler.get_config_values('menu_lists', 'APP_CONFIG')
PROMPT_CONFIG = config_handler.get_config_values('menu_lists', 'PROMPT_CONFIG')
APP_SETTINGS_LIST = config_handler.get_config_values('menu_lists', 'APP_SETTINGS_LIST')



def initialize_app_settings():
	if "app_config" not in st.session_state:
		st.session_state.app_config = {}
	if "u_collection" not in st.session_state:
		st.session_state.u_collection = None
		
	if "URI" in st.secrets["MONGO"]:
		MONGO_URI = st.secrets["MONGO"]["URI"]
		DATABASE_NAME = st.secrets["MONGO"]["DATABASE"]
	else:
		pass

	client = MongoClient(MONGO_URI, tls=True,tlsAllowInvalidCertificates=True)
	db = client[DATABASE_NAME]
	st.session_state.u_collection = db["users"]    


def load_document(username, field_name=None, dict_input=None):
	# Try to find the document by school name
	document = st.session_state.u_collection.find_one({"username": username})

	# If the document doesn't exist and both field_name and dict_input are provided,
	# create a new document with these details
	if not document and field_name and dict_input is not None:
		new_document = {"username": username, field_name: dict_input}
		st.session_state.u_collection.insert_one(new_document)
		st.write(f"Added {field_name} to {username} settings for the first time")
		return dict_input  # Return the newly added data

	# If the document exists but doesn't contain the field_name, handle the missing key
	if document and field_name and document.get(field_name) is None:
		if dict_input is not None:
			# If dict_input is provided, update the document with this new field and value
			st.session_state.u_collection.update_one(
				{"username": username},
				{"$set": {field_name: dict_input}}
			)
			st.write(f"Added {field_name} to {username} settings")
			return dict_input  # Return the newly added data
		else:
			# If dict_input is not provided, just return None or a default value
			return None

	# If the document and field_name exist, return its value
	#st.write(f"Loaded {field_name} from {username} settings")
	return document.get(field_name)

def app_load_document(sch, field_name=None, dict_input=None):
	# Try to find the document by school name
	document = st.session_state.a_collection.find_one({"sch_name": sch})

	# If the document doesn't exist and both field_name and dict_input are provided,
	# create a new document with these details
	if not document and field_name and dict_input is not None:
		new_document = {"sch_name": sch, field_name: dict_input}
		st.session_state.a_collection.insert_one(new_document)
		st.write(f"Added {field_name} to {sch} settings for the first time")
		return dict_input  # Return the newly added data

	# If the document exists but doesn't contain the field_name, handle the missing key
	if document and field_name and document.get(field_name) is None:
		if dict_input is not None:
			# If dict_input is provided, update the document with this new field and value
			st.session_state.a_collection.update_one(
				{"sch_name": sch},
				{"$set": {field_name: dict_input}}
			)
			st.write(f"Added {field_name} to {sch} settings")
			return dict_input  # Return the newly added data
		else:
			# If dict_input is not provided, just return None or a default value
			return None

	# If the document and field_name exist, return its value
	#st.write(f"Loaded {field_name} from {username} settings")
	return document.get(field_name)



def load_user_settings(field_name, dict): #load_prompt setting
	initialize_app_settings()
	excluded_fields = ['_id', 'username']
	doc = load_document(st.session_state.user['id'], field_name, dict)
	if doc == False:
		st.error(f"No {field_name} settings found")
		return False
		# Initialize session state for each field in the document, excluding certain fields
	for key, value in doc.items():
		if key not in st.session_state and key not in excluded_fields:
			session_key = key.replace(" ", "_").lower()
			st.session_state[session_key] = value
			print(key, value)
	return True
		#load all app settings flag to true

def reset_app_settings(default_dict):
	# Place the button to reset settings
	if st.button("Reset Settings"):
		# Temporarily store the reset request in session state to persist across reruns
		st.session_state.pending_reset = True

	# Check if there was a pending reset request and confirm it
	if st.session_state.get('pending_reset', False):
		# Use a checkbox for confirmation
		if st.checkbox("Are you sure you want to reset your prompt settings?"):
			# Perform the reset
			st.session_state.u_collection.update_one(
				{"username": st.session_state.user['id']},
				{"$set": {"prompt_templates": default_dict}}
			)
			st.write("Settings reset successfully.")
			# Clear the pending reset request from session state
			del st.session_state['pending_reset']
		elif st.checkbox("Cancel Reset"):
			# Clear the pending reset if user cancels
			del st.session_state['pending_reset']


def set_prompt_settings():
	initialize_app_settings()
	if "app_pdf" not in st.session_state:
		st.session_state.app_pdf = None
	excluded_fields = ['_id', 'username']
	doc = load_document(st.session_state.user['id'], "prompt_templates", PROMPT_CONFIG)

	doc_for_df = {k: v for k, v in doc.items() if k not in excluded_fields}
	st.session_state.app_pdf = pd.DataFrame(list(doc_for_df.items()), columns=['Field', 'Values'])
	st.write("Current Settings : ", "prompt_templates")
	st.dataframe(st.session_state.app_pdf)

	action = st.selectbox("Select Action", ["Edit", "Add", "Remove"], key='app_edit_action')
	new_key = ""
	new_value = ""
	field = ""
	if action == "Add":
		new_key = st.text_input("Enter new key", key='app_new_key')
		new_value = st.text_area("Enter new value", key='app_new_value', height=400)
	else:
		field = st.selectbox("Select field", ["-"] + st.session_state.app_pdf['Field'].tolist(), key='app_action')
		if action == "Edit" and field != "-":
			existing_value = st.session_state.app_pdf.loc[st.session_state.app_pdf['Field'] == field, 'Values'].iloc[0]
			new_value = st.text_area("Enter new value", value=existing_value, key='app_edit_value', height=400)

	if st.button("Submit Action"):
		# Perform the action (Add, Edit, Remove)
		perform_modification_and_update_session_state(action, field, new_key, new_value, st.session_state.user['id'], excluded_fields)

		st.write("Action completed successfully.")
	st.divider()
	st.write("### :red[Warning - Reset Settings]")
	reset_app_settings(PROMPT_CONFIG)

def perform_modification_and_update_session_state(action, field, new_key, new_value, username, excluded_fields):
	if action == "Add" and new_key:
		new_row = pd.DataFrame([[new_key, new_value]], columns=['Field', 'Values'])
		st.session_state.app_pdf = pd.concat([st.session_state.app_pdf, new_row], ignore_index=True)
	elif action == "Edit" and field and field != "-":
		st.session_state.app_pdf.loc[st.session_state.app_pdf['Field'] == field, 'Values'] = new_value
	elif action == "Remove" and field and field != "-":
		st.session_state.app_pdf = st.session_state.app_pdf[st.session_state.app_pdf['Field'] != field]
	updated_doc = {row['Field']: row['Values'] for index, row in st.session_state.app_pdf.iterrows()}
	st.session_state.u_collection.update_one({"username": username},{"$set": {"prompt_templates": updated_doc}})
	
	# Directly update session_state to reflect changes without re-querying
	for key in updated_doc.keys():
		if key not in excluded_fields:
			session_key = key.replace(" ", "_").lower()
			st.session_state[session_key] = updated_doc[key]
   
   
def manage_prompt_templates():
	if "current_prompt" not in st.session_state:
		st.session_state.current_prompt = "School Prompt Templates"
	st.write(f"### :green[Current Prompt Templates: {st.session_state.current_prompt}]")
	prompt_select = st.selectbox("Select Prompt Templates", ["School Prompt Templates", "Personal Prompt Templates"])
	if prompt_select == "School Prompt Templates":
		#st.session_state.current_prompt = prompt_select
		excluded_fields = ['_id', 'sch_name']
		doc = app_load_document(st.session_state.user['school_id'], "prompt_templates", PROMPT_CONFIG)
		doc_for_df = {k: v for k, v in doc.items() if k not in excluded_fields}
		st.session_state.app_pdf = pd.DataFrame(list(doc_for_df.items()), columns=['Field', 'Values'])
		st.write("Current Settings : ", "prompt_templates")
		st.dataframe(st.session_state.app_pdf)
		if doc == False:
			st.error("No prompt_templates settings found")
			return False
			# Initialize session state for each field in the document, excluding certain fields
		if st.button("Load School Prompt Templates"):
			st.session_state.current_prompt = prompt_select
			for key, value in doc.items():
				if key not in st.session_state and key not in excluded_fields:
					session_key = key.replace(" ", "_").lower()
					st.session_state[session_key] = value
			for key in doc.keys():
				if key not in excluded_fields:
					session_key = key.replace(" ", "_").lower()
					st.session_state[session_key] = doc[key]
			st.success("School Prompt Templates loaded successfully")
			#st.rerun()
			return True
	
	else:
		doc = load_document(st.session_state.user['id'], "prompt_templates", PROMPT_CONFIG)
		#st.session_state.current_prompt = prompt_select
		excluded_fields = ['_id', 'username']
		doc_for_df = {k: v for k, v in doc.items() if k not in excluded_fields}
		st.session_state.app_pdf = pd.DataFrame(list(doc_for_df.items()), columns=['Field', 'Values'])
		st.write("Current Settings : ", "prompt_templates")
		st.dataframe(st.session_state.app_pdf)
		if doc == False:
			st.error("No prompt_templates settings found")
			return False
			# Initialize session state for each field in the document, excluding certain fields
		if st.button("Load Personal Prompt Templates"):
			st.session_state.current_prompt = prompt_select
			for key, value in doc.items():
				if key not in st.session_state and key not in excluded_fields:
					session_key = key.replace(" ", "_").lower()
					st.session_state[session_key] = value
		
			for key in doc.keys():
					if key not in excluded_fields:
						session_key = key.replace(" ", "_").lower()
						st.session_state[session_key] = doc[key]
			st.success("Personal Prompt Templates loaded successfully")
			return True
			
   
def load_templates_class():
	if st.session_state.user['profile_id'] == SA:
		return
	my_class  = load_my_class()
	if my_class == None:
		st.error("Class not allocated to you. Please contact the admin.")
		return
	if isinstance(my_class, list):
	# Convert list to a nicely formatted string
		class_str = ', '.join(my_class)
		st.write(f"#### :blue_book: My assigned class: {class_str}")
	else:
		# If 'my_class' is not a list, display it directly
		st.write(f"#### :blue_book: My current class: {my_class}")
	if st.session_state.user['profile_id'] == TCH:
		return
	else:
		teachers = list_teachers_for_student(my_class)
		selected_teacher_username = st.selectbox("Select my teacher to load templates", ['School Default'] + teachers)
		if selected_teacher_username == 'School Default':
			st.success("Loading School Default Templates")
			return
		else:
			teacher_doc = st.session_state.u_collection.find_one({"username": selected_teacher_username})
			templates = teacher_doc.get('prompt_templates')

			for key, value in templates.items():
				if key not in st.session_state:
					session_key = key.replace(" ", "_").lower()
					st.session_state[session_key] = value
			
			for key in templates.keys():
					session_key = key.replace(" ", "_").lower()
					st.session_state[session_key] = templates[key]
			st.success(f"Teacher {selected_teacher_username} Prompt Templates loaded successfully")
			st.write(templates)
		
		pass
	#load personal templates or school templates to students
	

def load_my_class():
	student_document = st.session_state.u_collection.find_one(
	{"username": st.session_state.user['id']},
	{"class": 1, "_id": 0}
	)
	if student_document:
		student_class = student_document.get('class', 'Class not specified')
		return student_class
 
def list_teachers_for_student(student_class):
	# Since 'student_class' is now a single class (not a list),
	# the query looks for teachers who teach this specific class.
	teachers = st.session_state.u_collection.find({
		"profile": "Teacher",
		"class": student_class  # Direct comparison to the single class string
	}).distinct("username")  # Assuming 'username' uniquely identifies a teacher

	return teachers

def load_teacher_templates_for_student(sch_name, student_class):
	teachers = list_teachers_for_student(student_class)
	
	# Streamlit UI for teacher selection
	selected_teacher_username = st.selectbox("Select a Teacher", teachers)
	
	if selected_teacher_username:
		# Mock retrieval of teacher document - replace with your actual database query
		teacher_document = {"username": selected_teacher_username, "profile": "Teacher", "templates": ["Template 1", "Template 2"]}  # Mock data
		
		if teacher_document:
			templates = teacher_document.get('templates')
			return templates
	return None