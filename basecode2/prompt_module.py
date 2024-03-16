from basecode2.authenticate import hash_password
import streamlit as st
import configparser
import ast
import pandas as pd
from basecode2.org_module import sa_select_school

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
AD = config_handler.get_config_values('constants', 'AD')
STU = config_handler.get_config_values('constants', 'STU')
ALL_ORG = config_handler.get_config_values('constants', 'ALL_ORG')


def display_prompt_templates(title, prompt_dict):
	st.markdown(f'##### :blue[{title} Prompt Templates:]')
	if prompt_dict:
		# Convert the dictionary to a DataFrame for a nicer table display
		prompt_df = pd.DataFrame(list(prompt_dict.items()), columns=['Prompt Name', 'Prompt Text'])
		st.dataframe(prompt_df)  # Display the DataFrame as a table
	else:
		st.write(f'No {title} Prompt Templates found.')
	
def valid_key(key):
	return len(key) <= 30 and not key.isnumeric()


def add_new_prompt(prompt_dict, personal_flag, sch_name=None):
	# Text area for adding or editing values
	key_input = st.text_input('Enter prompt template name (Key)', '').strip()
	value_input = st.text_area('Enter prompt design (Value)', value="You are a helpful assistant", height=500).strip()
	if st.button('Add Prompt'):
		if valid_key(key_input):
			if len(prompt_dict) < 20 or key_input in prompt_dict:
				prompt_dict[key_input] = value_input
				st.success('Prompt added successfully!')
				if personal_flag:
					user_prompt_templates_to_mongodb(st.session_state.user['id'], prompt_dict, "prompt_templates")
				else:
					sch_prompt_templates_to_mongodb(sch_name, prompt_dict, "prompt_templates")
				# Update the session state after addition
			else:
				st.error('Maximum limit of 20 entries reached.')
		else:
			st.error('Invalid key. Ensure it has no more than 20 characters, no spaces, no special characters, and is not purely numeric.')


def remove_prompt(prompt_dict, personal_flag, sch_name=None):
	if prompt_dict == None or len(prompt_dict) == 0:
		st.warning('No prompts to remove.')
	else:
		# Multiselect for removing keys
		keys_to_remove = st.multiselect('Select keys to remove', list(prompt_dict.keys()))
		if st.button('Remove Selected'):
			for key in keys_to_remove:
				if key in prompt_dict:
					del prompt_dict[key]
			if len(keys_to_remove) > 0:
				st.success('Selected keys removed successfully.')
			if len(prompt_dict) == 0:
				st.warning('No prompts left after removal.')
				prompt_dict = {}
			if personal_flag:
				user_prompt_templates_to_mongodb(st.session_state.user['id'], prompt_dict, "prompt_templates")
			else:
				sch_prompt_templates_to_mongodb(sch_name, prompt_dict, "prompt_templates")
			
			
		
def edit_prompt(prompt_dict, personal_flag, sch_name=None):
	if prompt_dict == None or len(prompt_dict) == 0:
		st.warning('No prompts to edit.')
	else:
		user_inputs = {}
		# Display the current dictionary for review
		for key, value in prompt_dict.items():
			# Use unique keys for input fields to avoid conflicts
			edited_key = st.text_input(f'Key: {key}', key, key=f"key_{key}").strip()
			edited_value = st.text_area(f'Value for {key}', value, key=f"value_{key}", height=500).strip()
			user_inputs[edited_key] = edited_value

		if st.button('Update All Edits'):
			# Validate and update all edits at once
			updated_dict = {}
			error_flag = False
			for key, value in user_inputs.items():
				if valid_key(key):
					if len(updated_dict) < 20:
						updated_dict[key] = value
					else:
						st.error('Maximum limit of 20 entries reached.')
						error_flag = True
				else:
					st.error('Invalid key. Ensure it has no more than 20 characters, no spaces, no special characters, and is not purely numeric.')
					error_flag = True

			if not error_flag:
				prompt_dict = updated_dict
				st.success('All changes updated successfully!')
				if personal_flag:
					user_prompt_templates_to_mongodb(st.session_state.user['id'], prompt_dict, "prompt_templates")
				else:
					sch_prompt_templates_to_mongodb(sch_name, prompt_dict, "prompt_templates")
				# Update the session state after edit
		

# Function to update the prompt_templates field in MongoDB
def fetch_sch_templates(sch_name):
	# Assuming MongoDB connection and s_collection are already set up in st.session_state
	# Replace 's_collection' with the actual variable you use to access the schools collection
	
	# Fetch the school document by school name
	sch_doc = st.session_state.s_collection.find_one({"sch_name": sch_name})
	
	if sch_doc:
		# Check if the 'prompt_templates' field exists
		if "prompt_templates" in sch_doc:
			# Extract and return the prompt_templates dictionary
			#fetch_and_create_session_states(sch_doc[field_name])
			return sch_doc["prompt_templates"]
		else:
			# prompt_templates field does not exist
			st.warning(f"The document for '{sch_name}' exists, inserting a 'prompt_templates' field.")
			st.session_state.s_collection.update_one(
				{"sch_name": sch_name},
				{"$set": {f"prompt_templates": {}}}
			)
			return {}

def fetch_user_templates(username):
	# Assuming MongoDB connection and s_collection are already set up in st.session_state
	# Replace 's_collection' with the actual variable you use to access the schools collection
	
	# Fetch the school document by school name
	person_doc = st.session_state.u_collection.find_one({"username": username})
	
	if person_doc:
		# Check if the 'prompt_templates' field exists
		if "prompt_templates" in person_doc:
			# Extract and return the prompt_templates dictionary
			return person_doc["prompt_templates"]
		else:
			# prompt_templates field does not exist
			st.warning(f"The document for '{username}' exists , inserting a 'prompt_templates' field.")
			st.session_state.u_collection.update_one(
				{"username": username},
				{"$set": {"prompt_templates": {}}}
			)
			return {}

def manage_prompt_org(): #field_name needs to change for different apps
	personal_flag = False
	prompt_templates = None
	st.subheader("Manage Prompt Templates")
	#check if administrators or super administrators want to edit their own prompt templates
	if st.session_state.user["profile_id"]	== SA or st.session_state.user["profile_id"] == AD:
		if st.toggle("Personal Prompt Templates", False):
			personal_flag = True
		else:
			personal_flag = False
	else: #all other users can only see their own prompt templates
		personal_flag = True
	if personal_flag:
		# Fetch the prompt_templates dictionary from MongoDB
		prompt_templates = fetch_user_templates(st.session_state.user['id'])
		#st.write(prompt_templates)
		# Display the prompt_templates dictionary and manage its contents
		display_prompt_templates(st.session_state.user['id'], prompt_templates)

	else:
		#fetch schools for SA and school for AD
		if st.session_state.user["profile_id"] == SA:
			sch_names = sa_select_school()
			school = st.selectbox('Select School', ["Select School"] + sch_names, key='app_school')
			if school != "Select School" and school != None:
				# Fetch the prompt_templates dictionary from MongoDB
				prompt_templates = fetch_sch_templates(school)
				# Display the prompt_templates dictionary and manage its contents
				display_prompt_templates(school, prompt_templates)
				sch_name = school
		else:
			# Fetch the prompt_templates dictionary from MongoDB
			prompt_templates = fetch_sch_templates(st.session_state.user['school_id'])
			# Display the prompt_templates dictionary and manage its contents
			display_prompt_templates(st.session_state.user['school_id'], prompt_templates)
			sch_name = st.session_state.user['school_id']

	#st.write(prompt_templates)
	action = st.selectbox("Select Action", ["Select Action","Add Prompt", "Remove Prompt", "Edit Prompt"])
	if prompt_templates != None:
		if action == "Add Prompt":
			if personal_flag:
				add_new_prompt(prompt_templates, personal_flag)
			else:
				add_new_prompt(prompt_templates, personal_flag, sch_name)
		elif action == "Remove Prompt":
			if personal_flag:
				remove_prompt(prompt_templates, personal_flag)
			else:
				remove_prompt(prompt_templates, personal_flag, sch_name)
		elif action == "Edit Prompt":
			if personal_flag:
				edit_prompt(prompt_templates, personal_flag)
			else:
				edit_prompt(prompt_templates, personal_flag, sch_name)
	else:
		st.warning("No prompt templates found")
	


	
def sch_prompt_templates_to_mongodb(sch_name, prompt_templates, field_name):
	#st.write("Hello")
	update_result = st.session_state.s_collection.update_one(
		{"sch_name": sch_name},
		{"$set": {field_name: prompt_templates}}
	)
	if update_result.modified_count > 0:
		st.success("Prompt templates updated successfully in MongoDB.")
		#st.rerun()
	else:
		st.error("No changes detected, prompt templates in MongoDB not updated.")


def user_prompt_templates_to_mongodb(username, prompt_templates, field_name):
	#st.write("Hello")
	update_result = st.session_state.u_collection.update_one(
		{"username": username},
		{"$set": {field_name: prompt_templates}}
	)
	if update_result.modified_count > 0:
		st.success("Prompt templates updated successfully in MongoDB.")
		#st.rerun()
	else:
		st.error("No changes detected, prompt templates in MongoDB not updated.")

def fetch_and_create_session_states():
	# Fetch the prompt_templates dictionary from MongoDB
	if st.session_state.user["profile_id"]	!= STU:
		if st.toggle("Personal Prompt Templates", False):
			personal_flag = True
		else:
			personal_flag = False
	else:
		personal_flag = False
	
	if personal_flag:
		prompt_templates = fetch_user_templates(st.session_state.user['id'])
	else:
		prompt_templates = fetch_sch_templates(st.session_state.user['school_id'])
	# Check if prompt_templates is not empty
	if prompt_templates:
		# Iterate over each key-value pair in the prompt_templates
		for key, value in prompt_templates.items():
			# Create a session_state variable for each key, assigning its corresponding value
			session_key = key.replace(" ", "_").lower()  # Format the key to be suitable for session_state
			st.session_state[session_key] = value
			print(session_key, value)
	else:
		print("No prompt templates found.")
		# Optionally, inform the user that session states have been created/updated


def display_prompts(): #field_name needs to change for different apps
	personal_flag = False
	prompt_templates = None
	st.divider()
	#check if administrators or super administrators want to edit their own prompt templates
	if st.session_state.user["profile_id"]	== SA or st.session_state.user["profile_id"] == AD:
		if st.toggle("Load Personal Prompt Templates", False):
			personal_flag = True
		else:
			personal_flag = False
	else: #all other users can only see their own prompt templates
		personal_flag = True
	if personal_flag:
		# Fetch the prompt_templates dictionary from MongoDB
		prompt_templates = fetch_user_templates(st.session_state.user['id'])
		#st.write(prompt_templates)
		# Display the prompt_templates dictionary and manage its contents
		display_prompt_templates(st.session_state.user['id'], prompt_templates)

	else:
		#fetch schools for SA and school for AD
		if st.session_state.user["profile_id"] == SA:
			sch_names = sa_select_school()
			school = st.selectbox('Select School', ["Select School"] + sch_names, key='app_school')
			if school != "Select School" and school != None:
				# Fetch the prompt_templates dictionary from MongoDB
				prompt_templates = fetch_sch_templates(school)
				# Display the prompt_templates dictionary and manage its contents
				display_prompt_templates(school, prompt_templates)
		else:
			# Fetch the prompt_templates dictionary from MongoDB
			prompt_templates = fetch_sch_templates(st.session_state.user['school_id'])
			# Display the prompt_templates dictionary and manage its contents
			display_prompt_templates(st.session_state.user['school_id'], prompt_templates)

	return prompt_templates


def select_and_set_prompt(prompt_templates, select): #need to rethink this
    # Create a list of keys that start with 'chatbot_'
    chatbot_keys = [key for key in prompt_templates.keys() if key.startswith('chatbot_')]

    options_to_display = chatbot_keys if chatbot_keys else list(prompt_templates.keys())

    # If options_to_display is empty, show a message instead
    if not options_to_display:
        st.write("No prompt templates available.")
        return

    # Check if 'chatbot_default' exists, select is False, and there are 'chatbot_' keys
    if 'chatbot_default' in prompt_templates and not select and chatbot_keys:
        st.session_state.chatbot = prompt_templates['chatbot_default']
    else:
        # Allow the user to select a prompt, prioritizing chatbot_keys if available
        prompt_selection = st.selectbox('Select a Prompt', options_to_display)

        # Set the selected prompt to st.session_state.chatbot
        if prompt_selection:
            st.session_state.chatbot = prompt_templates[prompt_selection]
    
    st.write("Current prompt: ", st.session_state.chatbot)

def set_default_template(default_template):
	# Fetch the prompt_templates dictionary from MongoDB for school
	prompt_templates = fetch_sch_templates(st.session_state.user['school_id'])
	if 'chatbot_default' in prompt_templates:
		st.session_state.chatbot = prompt_templates['chatbot_default']
	else:
		st.error("Using default prompt template as 'chatbot_default' is not set.")
		st.session_state.chatbot = default_template