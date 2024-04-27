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
DV = config_handler.get_config_values('constants', 'DV')
APP_CONFIG = config_handler.get_config_values('menu_lists', 'APP_CONFIG')
PROMPT_CONFIG = config_handler.get_config_values('menu_lists', 'PROMPT_CONFIG')
APP_SETTINGS_LIST = config_handler.get_config_values('menu_lists', 'APP_SETTINGS_LIST')
SCH_PROFILES = config_handler.get_config_values('menu_lists', 'SCH_PROFILES')



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


def load_document(sch_name, field_name=None, dict_input=None):
	# Try to find the document by school name
	document = st.session_state.a_collection.find_one({"sch_name": sch_name})

	# If the document doesn't exist and both field_name and dict_input are provided,
	# create a new document with these details
	if not document and field_name and dict_input is not None:
		new_document = {"sch_name": sch_name, field_name: dict_input}
		st.session_state.a_collection.insert_one(new_document)
		#st.write(f"Added {field_name} to {sch_name} settings for the first time")
		return dict_input  # Return the newly added data

	# If the document exists but doesn't contain the field_name, handle the missing key
	if document and field_name and document.get(field_name) is None:
		if dict_input is not None:
			# If dict_input is provided, update the document with this new field and value
			st.session_state.a_collection.update_one(
				{"sch_name": sch_name},
				{"$set": {field_name: dict_input}}
			)
			#st.write(f"Added {field_name} to {sch_name} settings")
			return dict_input  # Return the newly added data
		else:
			# If dict_input is not provided, just return None or a default value
			return None

	# If the document and field_name exist, return its value
	#st.write(f"Loaded {field_name} from {sch_name} settings")
	return document.get(field_name)


def load_app_settings(field_name, dict): #load_prompt setting
	initialize_app_settings()
	if st.session_state.user['profile_id'] == SA:
		#st.warning("Super Administrator must select a school to load settings")
		return False
	excluded_fields = ['_id', 'sch_name']
	doc = load_document(st.session_state.user['school_id'], field_name, dict)
	if doc == False:
		st.error(f"No {field_name} settings found")
		return False
		# Initialize session state for each field in the document, excluding certain fields
	for key, value in doc.items():
		if key not in st.session_state and key not in excluded_fields:
			session_key = key.replace(" ", "_").lower()
			st.session_state[session_key] = value
			#print(key, value)
	return True
		#load all app settings flag to true


def load_sa_app_settings():
	if "school_sa_selected" not in st.session_state:
		st.session_state.school_sa_selected = ""
	st.warning("Super Administrator must select a school to load settings")
	initialize_app_settings()
	excluded_fields = ['_id', 'sch_name']
	"Load all app settings for SA user, you need to select to run this application"
	sch_names = sa_select_school()
	if sch_names == []:
		st.error("No schools found")
		return True
	else:
		st.write(f"####  :blue[Current Super Admin School: {st.session_state.school_sa_selected}]")
		school = st.selectbox('Select School', ["Select School"] + sch_names, key='sa_app_school')
		if school != "Select School" and school != None:
			st.session_state.user['school_id'] = school
			doc1 = load_document(school, "prompt_templates", PROMPT_CONFIG)
			doc2 = load_document(school, "app_settings", APP_CONFIG)
			doc = {**doc1, **doc2}
			# Initialize session state for each field in the document, excluding certain fields
			for key, value in doc.items():
				if key not in st.session_state and key not in excluded_fields:
					session_key = key.replace(" ", "_").lower()
					st.session_state[session_key] = value
					#st.write(key, value)
			st.success(f"{school} settings loaded successfully")
			st.session_state.school_sa_selected = school
			return True



def delete_app_settings():
	st.subheader(":red[Reset App Configuration]")
	if st.session_state.user['profile_id'] != SA:
		st.write("You are not authorized to perform this action")
		return
	else:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', ["Select School"] + sch_names, key='app_school_delete')
		if school:
			if st.checkbox("Are you sure you want to reset app settings?"):
					if st.button("Reset App Configuration"):
						st.session_state.a_collection.update_one(
							{"sch_name": school},
							{"$set": {"app_settings": APP_CONFIG}}
						)
						st.write(f"{school} settings deleted successfully")
	  
def delete_prompt_settings():
	st.subheader(":red[Reset Prompt Templates Configuration]")
	if st.session_state.user['profile_id'] != SA:
		st.write("You are not authorized to perform this action")
		return
	else:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', ["Select School"] + sch_names, key='prompt_school_delete')
		if school:
			if st.checkbox("Are you sure you want to reset the prompts settings?"):
				if st.button("Reset Templates Configuration"):
					st.session_state.a_collection.update_one(
						{"sch_name": school},
						{"$set": {"prompt_templates": PROMPT_CONFIG}}
					)
					st.write(f"{school} settings deleted successfully")
	 

def set_app_settings():
	initialize_app_settings()
	if "app_pdf" not in st.session_state:
		st.session_state.app_pdf = None
	if st.session_state.user['profile_id'] == SA:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', sch_names, key='app_school')
	elif st.session_state.user['profile_id'] == AD:
		school = st.session_state.user['school_id']
		
	field_name = st.selectbox('Select Field', APP_SETTINGS_LIST, key='app_field')
	if field_name == "prompt_templates":
		dict_input = PROMPT_CONFIG
	else:
		dict_input = APP_CONFIG
	excluded_fields = ['_id', 'sch_name']
	if school:
		doc = load_document(school, field_name, dict_input)
		doc_for_df = {k: v for k, v in doc.items() if k not in excluded_fields}
		st.session_state.app_pdf = pd.DataFrame(list(doc_for_df.items()), columns=['Field', 'Values'])
		st.write("Current Settings : ", field_name)
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

		if field_name == "prompt_templates" and st.session_state.user['profile_id'] == SA or st.session_state.user['profile_id'] == DV:
			auto_pro = st.checkbox("Auto Propagate Settings to all schools")
		else:
			auto_pro = False
		if st.button("Submit Action"):
			# Perform the action (Add, Edit, Remove)
			perform_modification_and_update_session_state(action, field, new_key, new_value, school, excluded_fields, field_name)
			if auto_pro:
				auto_propagate_prompts(field, new_value)
	
			st.write("Action completed successfully.")

def perform_modification_and_update_session_state(action, field, new_key, new_value, school, excluded_fields, field_name):
	if action == "Add" and new_key:
		new_row = pd.DataFrame([[new_key, new_value]], columns=['Field', 'Values'])
		st.session_state.app_pdf = pd.concat([st.session_state.app_pdf, new_row], ignore_index=True)
	elif action == "Edit" and field and field != "-":
		st.session_state.app_pdf.loc[st.session_state.app_pdf['Field'] == field, 'Values'] = new_value
	elif action == "Remove" and field and field != "-":
		st.session_state.app_pdf = st.session_state.app_pdf[st.session_state.app_pdf['Field'] != field]

	updated_doc = {row['Field']: row['Values'] for index, row in st.session_state.app_pdf.iterrows()}
	st.session_state.a_collection.update_one({"sch_name": school}, {"$set": {field_name: updated_doc}})
	
	# Directly update session_state to reflect changes without re-querying
	for key in updated_doc.keys():
		if key not in excluded_fields:
			session_key = key.replace(" ", "_").lower()
			st.session_state[session_key] = updated_doc[key]

def auto_propagate_prompts(key, prompt_template):
    if not key or not prompt_template:
        st.error("Key or prompt template cannot be empty.")
        return
    
    try:
        # Fetch all school names except the user's own school
        sch_names = sa_select_school()
        #st.write(sch_names)
        #sch_names.remove(st.session_state.user['school_id'])

        # Generate the MongoDB update statement specific to the key passed into the function
        update_statement = {
            "$set": {
                f"prompt_templates.{key}": prompt_template
            }
        }

        # Update the document for each target school
        for school in sch_names:
            result = st.session_state.a_collection.update_one(
                {"sch_name": school},
                update_statement
            )
            if result.modified_count == 0:
                st.write(f"No changes made to {school}.")
            else:
                st.write(f"Updated {school} successfully.")

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")


	

def propagate_prompts():
	st.subheader(":blue[Propagate Prompt Templates to Schools]")
	if st.session_state.user['profile_id'] == SA:
		# Fetch school names
		sch_names = sa_select_school()
		
		# Select the source school for prompt templates
		source_sch = st.selectbox('Select Source School for Prompts', sch_names, key='source_school')
		
		# Fetch the prompt templates from the selected source school
		if source_sch:
			source_prompts = fetch_prompts_for_school(source_sch)  # You need to define this function
			
			if source_prompts:
				# Now, select target schools for propagation
				selected_schs = st.multiselect('Select Target Schools', [sch for sch in sch_names if sch != source_sch], key='target_schools')
				
				# List keys from the source prompts for selection
				prompt_keys = list(source_prompts.keys())
				selected_keys = st.multiselect('Select Prompts to Propagate', prompt_keys, key='propagate_prompts')
				
				if selected_schs and selected_keys:
					if st.button("Propagate Prompts"):
						for school in selected_schs:
							# Construct the update statement to only modify selected prompts
							update_statement = {"$set": {}}
							for key in selected_keys:
								# Only add the prompts that are selected to be updated
								prompt_path = f"prompt_templates.{key}"
								update_statement["$set"][prompt_path] = source_prompts[key]
							
							# Update the document for each selected target school
							st.session_state.a_collection.update_one(
								{"sch_name": school},
								update_statement
							)
						
						st.write("Prompts propagated successfully")

def fetch_prompts_for_school(sch_name):
	"""
	Fetch the prompt templates for a given school.
	
	Parameters:
	- sch_name: The name of the school for which to fetch the prompt templates.
	
	Returns:
	- A dictionary of the prompt templates if found, or None if not found.
	"""
	# Query the database for the document with the matching sch_name
	school_doc = st.session_state.a_collection.find_one({"sch_name": sch_name})
	
	# Check if the document and the prompt_templates field exist
	if school_doc and "prompt_templates" in school_doc:
		return school_doc["prompt_templates"]
	else:
		# Return None if the document or prompt_templates field doesn't exist
		return None


		
def propagate_settings():
	st.subheader(":blue[Propagate App Settings to Schools]")
	if st.session_state.user['profile_id'] == SA:
		# Fetch school names
		sch_names = sa_select_school()
		
		# Select the source school for prompt templates
		source_sch = st.selectbox('Select Source School for Settings', sch_names, key='source_app_school')
		
		# Fetch the prompt templates from the selected source school
		if source_sch:
			source_prompts = fetch_settings_for_school(source_sch)  # You need to define this function
			
			if source_prompts:
				# Now, select target schools for propagation
				selected_schs = st.multiselect('Select Target Schools', [sch for sch in sch_names if sch != source_sch], key='target_app_schools')
				
				# List keys from the source prompts for selection
				prompt_keys = list(source_prompts.keys())
				selected_keys = st.multiselect('Select Settings to Propagate', prompt_keys, key='propagate_settings')
				
				if selected_schs and selected_keys:
					if st.button("Propagate Settings"):
						for school in selected_schs:
							# Construct the update statement to only modify selected prompts
							update_statement = {"$set": {}}
							for key in selected_keys:
								# Only add the settings that are selected to be updated
								prompt_path = f"app_settings.{key}"
								update_statement["$set"][prompt_path] = source_prompts[key]
							
							# Update the document for each selected target school
							st.session_state.a_collection.update_one(
								{"sch_name": school},
								update_statement
							)
						
						st.write("Settings propagated successfully")

def fetch_settings_for_school(sch_name):
	"""
	Fetch the prompt templates for a given school.
	
	Parameters:
	- sch_name: The name of the school for which to fetch the prompt templates.
	
	Returns:
	- A dictionary of the prompt templates if found, or None if not found.
	"""
	# Query the database for the document with the matching sch_name
	school_doc = st.session_state.a_collection.find_one({"sch_name": sch_name})
	
	# Check if the document and the prompt_templates field exist
	if school_doc and "app_settings" in school_doc:
		return school_doc["app_settings"]
	else:
		# Return None if the document or prompt_templates field doesn't exist
		return None
	
	
def propagate_user_prompts():
	st.subheader(":blue[Propagate Prompt Templates to Users]")
	
	if st.session_state.user['profile_id'] == SA:  # Assuming 'SA' is a constant representing a specific profile ID
		# Fetch school names
		sch_names = sa_select_school()
		
		# Select the source school for prompt templates
		source_sch = st.selectbox('Select Source School for Prompts', sch_names, key='source_school_u')
		
		# Fetch the prompt templates from the selected source school
		if source_sch:
			source_prompts = fetch_prompts_for_school(source_sch)  # Assuming this function is defined elsewhere
			
			if source_prompts:
				# Now, select target schools for propagation
				selected_schs = st.multiselect('Select Target Schools', [sch for sch in sch_names if sch != source_sch], key='target_schools_u')
				
				# Select target profiles
				selected_profile = st.selectbox('Select Profile', SCH_PROFILES, key='target_profile_u')
				
				# Checkbox to decide if prompts should be updated for all users with the selected profile
				update_all = st.checkbox('Update for all users with this profile', False)
				
				selected_usernames = []
				if not update_all:
					# Fetch usernames based on school and profile only if not updating all users with the profile
					usernames = fetch_usernames_for_school_and_profile(selected_schs, selected_profile)
					selected_usernames = st.multiselect('Select Usernames', usernames, key='target_usernames_u')
				
				# List keys from the source prompts for selection
				prompt_keys = list(source_prompts.keys())
				selected_keys = st.multiselect('Select Prompts to Propagate', prompt_keys, key='propagate_prompts_u')
				
				if selected_schs and selected_keys and (selected_usernames or update_all):
					if st.button("Propagate Prompts"):
						for school in selected_schs:
							# Construct the update statement to only modify selected prompts
							update_statement = {"$set": {}}
							for key in selected_keys:
								prompt_path = f"prompt_templates.{key}"
								update_statement["$set"][prompt_path] = source_prompts[key]
							
							# Define the filter for update query
							if update_all:
								# Update all users with the selected profile in the school
								filter_criteria = {"sch_name": {"$in": selected_schs}, "profile": selected_profile}
							else:
								# Update only selected usernames with the selected profile in the school
								filter_criteria = {"sch_name": {"$in": selected_schs}, "username": {"$in": selected_usernames}, "profile": selected_profile}
							
							# Update the documents based on the filter criteria
							st.session_state.u_collection.update_many(
								filter_criteria,
								update_statement
							)
						
						st.success("Prompts propagated successfully")



def fetch_usernames_for_school_and_profile(selected_schs, selected_profile):
	"""
	Fetch usernames for a given profile within selected schools.

	Parameters:
	- selected_schs: List of selected school names.
	- selected_profile: The selected profile.

	Returns:
	- List of usernames matching the criteria.
	"""
	# Make sure selected_schs is a list, even if it contains only one item, to prevent query errors.
	if not isinstance(selected_schs, list):
		selected_schs = [selected_schs]

	# Query the MongoDB collection to find users who match the selected schools and profile.
	# This uses the $in operator to find documents where sch_name matches any value in the selected_schs list.
	query_result = st.session_state.u_collection.find(
		{"sch_name": {"$in": selected_schs}, "profile": selected_profile},
		{"username": 1, "_id": 0}  # Projection: Include only the username field and exclude the _id field
	)

	# Extract usernames from the query results.
	usernames = [user['username'] for user in query_result]

	return usernames
