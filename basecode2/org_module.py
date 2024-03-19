from basecode2.authenticate import hash_password
import streamlit as st
import pandas as pd
import configparser
import ast
from pymongo import MongoClient
#from bson import ObjectId
import time


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
TCH = config_handler.get_config_values('constants', 'TCH')
NUM_TCH = config_handler.get_config_values('constants', 'NUM_TCH')
NUM_STU = config_handler.get_config_values('constants', 'NUM_STU')
ALL_ORG = config_handler.get_config_values('constants', 'ALL_ORG')
SCH_PROFILES = config_handler.get_config_values('menu_lists', 'SCH_PROFILES')
MENU_FUNCS = config_handler.get_config_values('menu_lists', 'MENU_FUNCS')

def aws_secret_manager():
	pass
	
def load_user_profile():
	"""Loads the user profile from the database and updates session state."""
	user_document = st.session_state.u_collection.find_one({"username": st.session_state.username})
	if user_document:
		# Initialize a new dictionary for user profile information
		user_profile = {
			'id': user_document['username'],
			'profile_id': user_document['profile'],
			'school_id': user_document['sch_name'],
		}
		# Update the session state with the loaded user profile
		st.session_state.user = user_profile
		return True
	else:
		return False

def initialise_admin_account():
	start_time = time.time()

	if "s_collection" in st.session_state:
		st.session_state.s_collection = None
	if "u_collection" in st.session_state:
		st.session_state.u_collection = None
	#this portion can either be in st.secrets or password manager in AWS
		
	if "URI" in st.secrets["MONGO"]:
		MONGO_URI = st.secrets["MONGO"]["URI"]
		DATABASE_NAME = st.secrets["MONGO"]["DATABASE"]
		
	else:
		aws_secret_manager()
		
	
	# Connect to MongoDB
	client = MongoClient(MONGO_URI, tls=True,tlsAllowInvalidCertificates=True)
	db = client[DATABASE_NAME]
	st.session_state.s_collection = db["schools"]
	st.session_state.u_collection = db["users"]

	super_admin_exists = st.session_state.u_collection.find_one({"username": st.secrets["super_admin_username"]})
	end_time = time.time()

	# Calculate and print execution time
	execution_time = end_time - start_time
	st.write(f"Execution time: {execution_time} seconds")
	if super_admin_exists:
		#st.success("Super admin account already exists!")
		return
	else:
		st.session_state.u_collection.insert_one({
				"username": st.secrets["super_admin_username"],
				"user_id": 0,
				"password": hash_password(st.secrets["super_admin_password"]), #hash_password(SUPER_PWD) 
				"profile": SA,
				"sch_name": ALL_ORG
			})
		st.success(f"Super Administrator created successfully!")


def sa_select_school():
	documents = st.session_state.s_collection.find({}, { "sch_name": 1, "_id": 0 })
	sch_names = [doc["sch_name"] for doc in documents]
	if not sch_names:
		st.error("No schools found. Please add a school first.")
		return []
	#school = st.selectbox('Select School', sch_names, key='school')
	return sch_names


#-------------------------------------------------------------------------------- Users Function --------------------------------------------------------------------------------
def create_users(sch_name, num_users, default_password, profile="", username_prefix=None):
	"""Create user accounts with incremental usernames and a hashed password, ensuring unique usernames."""
	
	# Find the user with the highest user_id for the given school
	highest_user_doc = st.session_state.u_collection.find_one(
		{"sch_name": sch_name},
		sort=[("user_id", -1)]  # Sort in descending order and get the first document
	)
	
	# If no users exist for the school, start with user_id 1; otherwise, increment the highest user_id by 1
	starting_user_id = 1 if highest_user_doc is None else highest_user_doc["user_id"] + 1

	if username_prefix:
		# If a custom username prefix is provided, use it; otherwise, use the first 3 characters of the school name
		user_prefix = username_prefix
	else:
		user_prefix = sch_name[:3]

	for i in range(starting_user_id, starting_user_id + num_users):
		username = f"{user_prefix}_{i}"  # Adjust username format to use the updated starting index
		hashed_pwd = hash_password(default_password)  # Assume hash_password is a function you've defined to hash passwords
		
		user_doc = {
			"username": username,
			"user_id": i,  # Using user_id for incremental numbering
			"password": hashed_pwd,  # Store the hashed password
			"profile": profile,
			"sch_name": sch_name,
		}
		
		# Insert the user document into MongoDB
		st.session_state.u_collection.insert_one(user_doc)
	
	st.success(f"Successfully created {num_users} user(s) for {username}.")

def edit_user(username, new_password=None, new_profile=None):
	"""Edit an existing user's details, only updating fields where non-None values are provided."""
	update_data = {}
	
	# Update password only if a new, non-empty password is provided
	if new_password is not None and new_password != "":
		hashed_pwd = hash_password(new_password)  # Hash the new password
		update_data['password'] = hashed_pwd  # Add hashed password to update_data
	
	# Update profile if a new profile is provided
	if new_profile:
		update_data['profile'] = new_profile  # Add new profile to update_data
	
	if update_data:
		# Check if the user exists before attempting update
		user_exists = st.session_state.u_collection.find_one({"username": username})
		if not user_exists:
			st.error(f"User '{username}' does not exist.")
			return
		
		# Proceed with the update
		result = st.session_state.u_collection.update_one({"username": username}, {"$set": update_data})
		if result.modified_count > 0:
			st.success(f"User '{username}' updated successfully.")
	else:
		st.warning("No changes specified.")


def remove_user(username):
	"""Remove a user from the database."""
	result = st.session_state.u_collection.delete_one({"username": username})
	if result.deleted_count > 0:
		st.success(f"User '{username}' removed successfully.")
	else:
		st.error("Failed to remove the user. Please check the username.")

def fetch_users_for_school(school_name):
	"""
	Fetches all users associated with the specified school name.

	Args:
	- school_name (str): The name of the school to fetch users for.

	Returns:
	- List[Dict]: A list of user documents associated with the school.
	"""
	# Ensure the school exists
	sch_doc = st.session_state.s_collection.find_one({"sch_name": school_name})
	if not sch_doc:
		# If the school does not exist in the database, return an empty list
		st.error("School not found")
		return []

	# Fetch all users associated with this school
	# This query assumes there's a 'school_name' field in the user documents that matches the school's name
	# You may need to adjust the field name based on your actual database schema
	users = st.session_state.u_collection.find({"sch_name": school_name}, {"username": 1, "password": 1, "profile": 1})


	# Convert the cursor to a list of dictionaries (if you want to work with it directly) or just usernames
	users_list = [user['username'] for user in users]

	return users_list


def fetch_users_for_school(school_name):
	# Check if the school exists
	sch_doc = st.session_state.s_collection.find_one({"sch_name": school_name})
	if not sch_doc:
		st.error("School not found.")
		return []
	
	# Fetch users associated with this school
	users_cursor = users_cursor = st.session_state.u_collection.find({"sch_name": school_name}, {"username": 1, "password": 1, "profile": 1})

	users = list(users_cursor)
	return users

def is_unique_username_within_school(new_username, school_name, exclude_user_id=None):
	# Check for existing username within the same school, excluding the current user being edited
	existing_user = st.session_state.u_collection.find_one({
		"username": new_username, 
		"_id": {"$ne": exclude_user_id},
		"sch_name": school_name
	})
	return existing_user is None

def update_username(user_id, new_username):
	# Update the user's username in the database
	st.session_state.u_collection.update_one({"_id": user_id}, {"$set": {"username": new_username}})

def edit_usernames(school_name):
	users = fetch_users_for_school(school_name)
	new_usernames = {}

	for user in users:
		user_key = f"username_{user['_id']}"
		new_username = st.text_input(f"Edit Username for {user['username']}", value=user['username'], key=user_key)
		new_usernames[user['_id']] = new_username

	if st.button("Update Usernames"):
		# Check for duplicate usernames in the new_usernames list
		if len(new_usernames.values()) != len(set(new_usernames.values())):
			st.error("Usernames must be unique. Please correct the duplicates.")
			return

		# Check for "super_admin" and uniqueness in the database
		for user_id, new_username in new_usernames.items():
			if new_username == "super_admin":
				st.error("The username 'super_admin' is reserved and cannot be used.")
				return
			if not is_unique_username_within_school(new_username, school_name, exclude_user_id=user_id):
				st.error(f"Username '{new_username}' is already taken. Please choose a different username.")
				return

		# All checks passed, proceed to update usernames
		for user_id, new_username in new_usernames.items():
			update_username(user_id, new_username)

		st.success("Usernames updated successfully!")


def setup_mass_edit_users(school_name):
	users_in_school = fetch_users_for_school(school_name)
	user_changes = {}  # This will hold the changes pending submission
	
	with st.form("user_edit_form"):
		for user in users_in_school:
			username = user['username']
			current_profile = user.get('profile', 'No Profile')
			
			st.markdown(f"### Editing Username: {username}")
			new_password = st.text_input("Enter New Password", type="password", max_chars=16, key=f"password_{username}")
			new_profile = st.selectbox("Select New Profile (Existing profile shown below)", SCH_PROFILES, index=SCH_PROFILES.index(current_profile) if current_profile in SCH_PROFILES else 0, key=f"profile_{username}")
			
			# Collect changes without applying them immediately
			user_changes[username] = {"new_password": new_password, "new_profile": new_profile}
		
		# Submit button for the form
		submit_changes = st.form_submit_button("Update All Users")

	if submit_changes:
		# Apply changes after submission
		for username, changes in user_changes.items():
			if changes["new_password"] or changes["new_profile"] != current_profile:  # Check if there are actual changes
				edit_user(username, changes["new_password"], changes["new_profile"])
		
		st.success("All selected users updated successfully!")


def setup_users():
	st.subheader("Manage Users")
	#st.write(SCH_PROFILES)
	if st.session_state.user['profile_id'] == SA:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', sch_names, key='user_school')
		st.write(f":green[School Selected: {school}]")
		action = st.selectbox('Select Action', ['Edit User', 'Remove User','Create Users', 'Edit Usernames'], key='u_action')
		if action == 'Edit User':
			setup_mass_edit_users(school)
		elif action == 'Remove User':
			remove_username = st.text_input("Enter Username", max_chars=20)
			if st.button("Remove User"):
				remove_user(remove_username)
		elif action == 'Create Users':# Step 1: Create a copy of the SCH_PROFILES list to avoid modifying the original
				sch_profiles_copy = SCH_PROFILES.copy()
				# Step 2: Remove "No Profile" from the copy if it exists
				if "No Profile" in sch_profiles_copy:
					sch_profiles_copy.remove("No Profile")
				num_users = st.number_input("Number of Users to Create", min_value=1, value=1, step=1)
				default_profile = st.selectbox("Select Profile", sch_profiles_copy, key='profile')
				default_password = st.text_input("Default Password", value=st.session_state.default_password, type="password")
				if st.checkbox("Customise Usernames"):
					username_prefix = st.text_input("Username Prefix", value=school[:3], max_chars=10)
				else:
					username_prefix = school[:3]
				if st.button("Create Users"):
					if school and default_password:
						create_users(school, num_users, default_password, default_profile, username_prefix)
					else:
						st.error("Please provide both a school name and a default password.")

		elif action == 'Edit Usernames':
			edit_usernames(school)
	elif st.session_state.user['profile_id'] == AD:
		st.write(f":green[School Selected: {st.session_state.user['sch_name']}]")
		school = st.session_state.user['sch_name']
		action = st.selectbox('Select Action', ['Edit User', 'Remove User', 'Create Users'], key='u_action')
		if action == 'Edit User':
			setup_mass_edit_users(school)
		elif action == 'Remove User':
			remove_username = st.text_input("Enter Username", max_chars=20)
			if st.button("Remove User"):
				remove_user(remove_username)
		elif action == 'Create Users':
		
				num_users = st.number_input("Number of Users to Create", min_value=1, value=1, step=1)
				default_profile = st.selectbox("Select Profile", SCH_PROFILES.remove("No Profile"), key='profile')
				default_password = st.text_input("Default Password", value=st.session_state.default_password, type="password")
				if st.button("Create Users"):
					if school and default_password:
						create_users(school, num_users, default_password, default_profile)
					else:
						st.error("Please provide both a school name and a default password.")
		elif action == 'Edit Usernames':
			edit_usernames(school)

	else:
		st.warning('You do not have the required permissions to perform this action')
	

#--------------------------------------------------------------------------------App Function --------------------------------------------------------------------------------
def create_school():
	if st.session_state.user['profile_id'] == SA:
		st.subheader("Add School")
		sch_name = st.text_input("Enter School Name")
		if st.button("Add School"):
			if sch_name:
				sch_doc = st.session_state.s_collection.find_one({"sch_name": sch_name})
				if sch_doc:
					st.error(f"School '{sch_name}' already exists. Please try a different name.")
				else:
					st.session_state.s_collection.insert_one({"sch_name": sch_name, "sch_levels": []})
					st.session_state.user['school_id'] = sch_name
					st.success(f"School '{sch_name}' added successfully.")
			else:
				st.error("Please enter a school name.")


def set_function_access_for_user():
	"""Set the function access for the user."""
	# Fetch the current user document
	user_doc = st.session_state.u_collection.find_one({"username": st.session_state.user['id']})
	if not user_doc:
		st.error("User not found. Please add the user first.")
		return

	# Fetch the current school document
	sch_doc = st.session_state.s_collection.find_one({"sch_name": st.session_state.user['school_id']})
	if not sch_doc:
		st.error("School not found. Please add the school first.")
		return

	# Fetch the user's profile functions from the user document
	profile_name = user_doc.get("profile", "")

	# Fetch the user's profile functions from the school document
	function_list = sch_doc.get(profile_name, {})

	# Initialize or update function options
	if not function_list:  # If the profile doesn't exist or has no functions
		st.session_state.func_options = {key: True for key in MENU_FUNCS.keys()}  # Assume all functions are enabled if not explicitly disabled
	else:  # If the profile exists and has functions
		# Load existing function options, defaulting to True (enabled) for functions not mentioned
		# and reversing the boolean since we're now treating True as enabled
		st.session_state.func_options = {func: not function_list.get(func, True) for func in MENU_FUNCS.keys()}


def manage_app_access():
	st.subheader("Manage App Functions")
	if st.session_state.user['profile_id'] == SA:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', sch_names, key='app_school')
		st.write(f":green[School Selected: {school}]")
		edit_function(school)
		
	elif st.session_state.user['profile_id'] == AD:
		st.write(f":green[School Selected: {st.session_state.user['sch_name']}]")
		edit_function(st.session_state.user['sch_name'])
	else:
		st.warning('You do not have the required permissions to perform this action')

def edit_function(sch_name):
	sch_doc = st.session_state.s_collection.find_one({"sch_name": sch_name})
	if not sch_doc:
		st.error(f"School '{sch_name}' not found. Please add the school first.")
		return

	# Fetch the current school document
	profile_name = st.selectbox("Select Profile", SCH_PROFILES, key="profile")
	if profile_name == "No Profile":
		st.warning("Please select a valid profile.")
		return

	function_list = sch_doc.get(profile_name, {})

	# Initialize or update function options
	# Note: Now, False means enabled (checked), True means disabled (unchecked)
	if not function_list:  # If the profile doesn't exist or has no functions
		st.session_state.func_options = {key: True for key in MENU_FUNCS.keys()}  # All functions disabled by default
	else:
		# Invert the logic when loading existing function options
		st.session_state.func_options = {func: not function_list.get(func, True) for func in MENU_FUNCS.keys()}

	with st.container():
		st.write("Select the functions to enable for this profile:")
		for func, desc in MENU_FUNCS.items():
			# Invert the value to display correctly. Checked means enabled (stored as False).
			current_value = not st.session_state.func_options.get(func, True)
			st.session_state.func_options[func] = not st.checkbox(f"{func}: {desc}", value=current_value, key=func)

	if st.button("Save Profile Functions"):
		# Invert the values back before saving to database
		func_options_to_save = {func: not value for func, value in st.session_state.func_options.items()}
		st.session_state.s_collection.update_one(
			{"sch_name": sch_name},
			{"$set": {profile_name: func_options_to_save}},
			upsert=True
		)
		st.success(f"Profile '{profile_name}' functions updated in '{sch_name}'.")

		# Retrieve the updated profile functions for the given profile from the school document
		updated_school_doc = st.session_state.s_collection.find_one({"sch_name": sch_name})
		updated_profile_functions = updated_school_doc.get(profile_name, {})

		# Find all user documents with the matching sch_name and profile, then update them
		matching_users = st.session_state.u_collection.find({"sch_name": sch_name, "profile": profile_name})

		for user in matching_users:
			# Also, invert the profile functions for consistency
			user_profile_functions_to_save = {func: not value for func, value in updated_profile_functions.items()}
			st.session_state.u_collection.update_one(
				{"_id": user["_id"]},
				{"$set": {"profile_functions": user_profile_functions_to_save}}
			)

		st.success(f"All matching user documents for profile '{profile_name}' in school '{sch_name}' have been updated with new profile functions.")



#-------------------------------------------------------------------------------- Edit class --------------------------------------------------------------------------------

def manage_organisation():
	st.subheader("Add/Edit Levels and Classes")
	if st.session_state.user['profile_id'] == SA:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', sch_names, key='m_school')
		st.write(f":green[School Selected: {school}]")
		manage_levels_classes(school)
	elif st.session_state.user['profile_id'] == AD:
		st.write(f":green[School Selected: {st.session_state.user['sch_name']}]")
		manage_levels_classes(st.session_state.user['sch_name'])
	else:
		st.warning('You do not have the required permissions to perform this action')


def manage_levels_classes(sch_name):
	st.subheader("Add/Edit Levels and Classes")
	action = st.selectbox('Select Action', ['Add Level', 'Remove Level', 'Add/Remove Classes'], key='c_action')
	if action == 'Add Level':
		add_level(sch_name)
	elif action == 'Remove Level':
		remove_level(sch_name)
	else:
		add_remove_classes(sch_name)

def add_level(sch_name):
	st.subheader("Add Level")
	# Input for level name
	level_name = st.text_input("Level Name", "lvl_", key="level_name")

	if level_name:
		# Ensure level_name starts with 'lvl_' and doesn't contain invalid characters
		if not level_name.startswith("lvl_") or not all(char.isalnum() or char == '_' for char in level_name[4:]):
			st.error("Invalid level name. It must start with 'lvl_' and contain only alphanumeric characters or underscores.")
			return
		
		# Fetch the school document
		sch_doc = st.session_state.s_collection.find_one({"sch_name": sch_name})

		if not sch_doc:
			st.error(f"School '{sch_name}' not found. Please add the school first.")
			return
		
		# Check if the level already exists
		if level_name in sch_doc:
			st.error(f"Level '{level_name}' already exists in '{sch_name}'. Consider editing the classes or removing the level.")
			# Optionally, display existing classes for the level
			existing_classes = sch_doc.get(level_name, [])
			st.write(f"Existing classes for {level_name}: {', '.join(existing_classes)}")
			return

		# Button to add the new level
		if st.button("Add Level"):
			# Update operation to append the new level_name to sch_levels and create an empty list for the level
			update_action = {
				"$addToSet": {"sch_levels": level_name},
				"$set": {level_name: []}
			}
			st.session_state.s_collection.update_one({"sch_name": sch_name}, update_action, upsert=True)
			st.success(f"Level '{level_name}' added to '{sch_name}'.")


def add_remove_classes(sch_name):
	st.subheader(f"Manage Classes in {sch_name}")

	# Fetch the current school document
	sch_doc = st.session_state.s_collection.find_one({"sch_name": sch_name})
	if not sch_doc:
		st.error("School not found. Please add the school first.")
		return
	
	# Get list of levels, if any
	levels = sch_doc.get("sch_levels", [])
	if not levels:
		st.error("No levels found for this school. Please add levels first.")
		return

	# Allow the user to select a level_name
	level_name = st.selectbox("Select Level", levels)
	if not level_name:
		st.warning("Please select a level.")
		return

	# Proceed with the rest of the function for adding/removing classes
	classes = sch_doc.get(level_name, [])

	# Input for adding a new class
	new_class = st.text_input("Add New Class", key="new_class")
	if st.button("Add Class", key="add_class") and new_class:
		if new_class not in classes:
			classes.append(new_class)
			st.session_state.s_collection.update_one({"sch_name": sch_name}, {"$set": {level_name: classes}})
			st.success(f"Added '{new_class}' to '{level_name}' in '{sch_name}'.")
		else:
			st.error("This class already exists in the level.")

	# Option to remove a class
	class_to_remove = st.selectbox("Remove Class", [""] + classes, key="remove_class")
	if st.button("Remove Class", key="remove_btn") and class_to_remove:
		classes.remove(class_to_remove)
		st.session_state.s_collection.update_one({"sch_name": sch_name}, {"$set": {level_name: classes}})
		st.success(f"Removed '{class_to_remove}' from '{level_name}' in '{sch_name}'.")




def remove_level(sch_name):
	st.subheader("Remove an Entire Level from a School")
	if sch_name:
		# Fetch the current school document to get the levels
		sch_doc = st.session_state.s_collection.find_one({"sch_name": sch_name})
		
		if sch_doc and "sch_levels" in sch_doc:
			levels = sch_doc["sch_levels"]
			
			# Allow the user to select a level to remove
			level_to_remove = st.selectbox("Select Level to Remove", ["Choose a level"] + levels)
			
			if level_to_remove != "Choose a level":
				# Confirm before removing
				if st.button(f"Remove '{level_to_remove}' Level"):
					# Update the document to remove the level
					update_action = {
						"$pull": {"sch_levels": level_to_remove},  # Remove from sch_levels list
						"$unset": {level_to_remove: ""}  # Remove the level field
					}
					st.session_state.s_collection.update_one({"sch_name": sch_name}, update_action)
					st.success(f"Level '{level_to_remove}' successfully removed from '{sch_name}'.")
		else:
			st.error("No levels found for this school, or school does not exist. Please check the school name.")
	else:
		# If no school has been selected yet or if there are no schools to select
		st.error("Please select a school first.")


def sa_delete_profile_from_school():
	st.subheader("Delete Profile from School")

	if st.session_state.user['profile_id'] == SA:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', sch_names, key='del_profile_school')
		st.write(f":green[School Selected: {school}]")
		if school:
			profile_to_delete = st.selectbox("Select Profile to Delete", SCH_PROFILES, key="profile_to_delete")
			if st.button("Delete Profile"):
				delete_profile(school, profile_to_delete)
		else:
			st.warning("Please select a school first.")
	else:
		st.warning('You do not have the required permissions to perform this action')


def delete_profile(sch_name, profile_var):
	# Search for the school document in s_collection
	sch_doc = st.session_state.s_collection.find_one({"sch_name": sch_name})
	if not sch_doc:
		st.error(f"School '{sch_name}' not found. Please add the school first.")
		return
	
	# Check if the profile_var exists in the document
	if profile_var in sch_doc:
		# Use $unset to delete the profile_var field from the document
		result = st.session_state.s_collection.update_one(
			{"sch_name": sch_name},
			{"$unset": {profile_var: ""}}
		)
		
		if result.modified_count > 0:
			st.success(f"Profile '{profile_var}' deleted successfully from '{sch_name}'.")
		else:
			st.warning(f"Profile '{profile_var}' could not be deleted or did not exist in '{sch_name}'.")
	else:
		st.warning(f"Profile '{profile_var}' does not exist in '{sch_name}'.")

def manage_teachers_school():
	# Fetch the current user's school_id
	school_id = st.session_state.user['school_id']
	st.subheader("Add Teachers to School")
	if st.session_state.user['profile_id'] == SA:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', sch_names, key='add_teacher_school')
		st.write(f":green[School Selected: {school}]")
		if school:
			manage_teachers(school)
		else:
			st.warning("Please select a school first.")
	elif st.session_state.user['profile_id'] == AD:
		st.write(f":green[School Selected: {st.session_state.user['sch_name']}]")
		manage_teachers(st.session_state.user['sch_name'])
	else:
		st.warning('You do not have the required permissions to perform this action')

def fetch_my_students_from_class(teacher_username):
    # Fetch the teacher's document
    teacher_doc = st.session_state.u_collection.find_one({"username": teacher_username})
    
    # Fetch the teacher's school
    sch_name = teacher_doc['sch_name']

    # Assuming the teacher might have multiple levels and classes assigned, let them choose
    level_name = st.selectbox("Select Level", teacher_doc['level'])
    class_name = st.selectbox("Select Class", teacher_doc['class'])
    
    # Once a level and class are selected, fetch all students in that class
    if level_name and class_name:
        students_cursor = st.session_state.u_collection.find(
            {
                "sch_name": sch_name,
                "level": {"$in": [level_name]},  # Check if 'level_name' is in the list of levels
                "class": {"$in": [class_name]},  # Check if 'class_name' is in the list of classes
                "profile": STU  # Assuming "STU" is a constant representing the student profile
            },
            {"_id": 0, "username": 1}  # Project only the username
        )
        students = [student["username"] for student in students_cursor]
        if not students:
            st.warning("No students found for this class.")
            return []
        else:
            return students
    else:
        # If level or class is not selected, return an empty list (or you may handle this case differently)
        return []

def manage_teachers(sch_name):
	st.subheader("Manage Teachers")
	# Fetch the current school document
	sch_doc = st.session_state.s_collection.find_one({"sch_name": sch_name})
	if not sch_doc:
		st.error("School not found. Please add the school first.")
		return
	
	# Get list of levels, if any
	levels = sch_doc.get("sch_levels", [])
	if not levels:
		st.error("No levels found for this school. Please add levels first.")
		return
	
	# Allow the user to select a level_name
	level_name = st.selectbox("Select Level", levels, key="level_name")
	if not level_name:
		st.warning("Please select a level.")
		return
	
	# Proceed with the rest of the function for adding/removing teachers
	classes = sch_doc.get(level_name, [])
	if not classes:
		st.error(f"No classes found for {level_name}. Please add classes first.")
		return
	
	# Allow the user to select a class
	class_name = st.selectbox("Select Class", classes, key="class_name")
	if not class_name:
		st.warning("Please select a class.")
		return
	
	st.write(f":green[Selected: {level_name} - {class_name}]")
	action = st.selectbox('Select Action', ['Add Teachers', 'Remove Teachers'], key='teacher_action')
	if action == 'Add Teachers':
		#display all teachers in the current class
		teachers = fetch_teachers_for_class(sch_name, level_name, class_name)
		st.write(f"Teachers in {level_name} - {class_name}")
		display_teachers(teachers)
		add_teachers_to_class(sch_name, level_name, class_name)
	elif action == 'Remove Teachers':
		teachers = fetch_teachers_for_class(sch_name, level_name, class_name)
		st.write(f"Teachers in {level_name} - {class_name}")
		display_teachers(teachers)
		remove_teachers(teachers, sch_name, level_name, class_name)

def fetch_teachers_for_class(sch_name, level_name, class_name):
	# Adjusted query for 'level' and 'class' as separate lists
	teachers_cursor = st.session_state.u_collection.find(
		{
			"sch_name": sch_name,
			"level": {"$in": [level_name]},  # Check if 'level_name' is in the list of levels
			"class": {"$in": [class_name]},  # Check if 'class_name' is in the list of classes
			"profile": TCH
		},
		{"_id": 0 ,"username": 1}
	)
	# Extract the usernames from the query results
	teachers = [teacher["username"] for teacher in teachers_cursor]

	if not teachers:
		st.warning(f"No teachers found for {sch_name}. Please add teachers from classes first.")
		return []
	else:
		return teachers
	
def remove_teachers(teachers, sch_name, level_name, class_name):
	# Multiselect teachers to remove from the class
	if not teachers:
		st.warning("No teachers found for the selected class.")
		return
	else:
		# Select teachers to remove from class
		selected_teachers = st.multiselect("Select Teachers to Remove", teachers)
		if not selected_teachers:
			st.warning("Please select teachers to remove from the class.")
			return
		else:
			if st.button("Remove Teachers"):
				for teacher in selected_teachers:
					# Fetch the teacher's document
					teacher_doc = st.session_state.u_collection.find_one({"username": teacher})
					
					# Manually remove one instance of level_name and class_name
					if level_name in teacher_doc['level']:
						teacher_doc['level'].remove(level_name)
					if class_name in teacher_doc['class']:
						teacher_doc['class'].remove(class_name)
					
					# Update the document in the database
					update_result = st.session_state.u_collection.update_one(
						{"username": teacher},
						{"$set": {"class": teacher_doc['class'], "level": teacher_doc['level']}}
					)
					
					# Check if the update was successful
					if update_result.modified_count > 0:
						st.success(f"Removed one instance of '{level_name}' and '{class_name}' from '{teacher}'.")
					else:
						st.error("Failed to update the teacher's information. Please try again.")



def add_teachers_to_class(sch_name, level_name, class_name):
	#fetch all teachers from the school regardless of class assignment
	all_teachers = fetch_all_teachers(sch_name)
	if all_teachers == []:
		st.warning(f"No teachers found for {sch_name}. Please add teachers from classes first.")
		return
	else:
		#check how many teachers can be added to the class by subtract
		num_teachers = NUM_TCH - len(fetch_teachers_for_class(sch_name, level_name, class_name))
		if num_teachers == 0:
			st.warning(f"No more teachers can be added to {level_name} - {class_name}.")
			return
		else:
			selected_teachers = st.multiselect("Select Teachers to Add", all_teachers)
			if not selected_teachers:
				st.warning("Please select teachers to add to the class.")
				return
			else:
				if st.button("Add Teachers"):
					if num_teachers < len(selected_teachers):
						st.warning(f"Number of teachers to add ({len(selected_teachers)}) exceeds the available slots ({num_teachers}).")
						return
					for teacher in selected_teachers:
						# First, check if the 'level' field exists and is an array.
						# If it does not exist or is not an array, set it to an empty array first.
						st.session_state.u_collection.update_one(
							{"username": teacher, "$or": [{"level": {"$exists": False}}, {"level": {"$type": "array"}}]},
							{"$setOnInsert": {"level": []}},
							upsert=True
						)
						
						# Then, push the new level_name to the 'level' array.
						# This ensures that 'level' is always treated as an array.
						st.session_state.u_collection.update_one(
							{"username": teacher},
							{"$push": {"level": {"$each": [level_name]}}}
						)

						# First, check if the 'class' field exists and is an array.
						# If it does not exist or is not an array, set it to an empty array first.
						st.session_state.u_collection.update_one(
							{"username": teacher, "$or": [{"class": {"$exists": False}}, {"class": {"$type": "array"}}]},
							{"$setOnInsert": {"class": []}},
							upsert=True
						)

						# Then, push the new class_name to the 'class' array.
						# This ensures that 'class' is always treated as an array.
						st.session_state.u_collection.update_one(
							{"username": teacher},
							{"$push": {"class": {"$each": [class_name]}}}
						)							

						
					st.success(f"Successfully added {len(selected_teachers)} teachers to the class.")

def fetch_all_teachers(sch_name):
	# Fetch all teachers from the school
	teachers_cursor = st.session_state.u_collection.find(
		{"sch_name": sch_name, "profile": TCH},
		 {"_id": 0, "username": 1} 
	)

	# Extract the usernames from the query results
	teachers = [teacher["username"] for teacher in teachers_cursor]

	if not teachers:
		st.warning(f"No teachers found for {sch_name}. Please add teachers from classes first.")
		return []
	else:
		return teachers


def display_teachers(teachers):
	#display teachers in a dataframe with row numbers
	if teachers:
		df = pd.DataFrame(teachers)
		#remove the _id field
		st.dataframe(df)
	else:
		st.warning("No teachers found for the selected class.")

def manage_students_school():
	# Fetch the current user's school_id
	school_id = st.session_state.user['school_id']
	st.subheader("Add Students to Class")
	if st.session_state.user['profile_id'] == SA:
		sch_names = sa_select_school()
		school = st.selectbox('Select School', sch_names, key='add_student_school')
		st.write(f":green[School Selected: {school}]")
		if school:
			manage_students(school)
		else:
			st.warning("Please select a school first.")
	elif st.session_state.user['profile_id'] == AD:
		st.write(f":green[School Selected: {st.session_state.user['sch_name']}]")
		manage_students(st.session_state.user['sch_name'])
	else:
		st.warning('You do not have the required permissions to perform this action')

def manage_students(sch_name):
	st.subheader("Manage Students")
	# Fetch the current school document
	sch_doc = st.session_state.s_collection.find_one({"sch_name": sch_name})
	if not sch_doc:
		st.error("School not found. Please add the school first.")
		return
	
	# Get list of levels, if any
	levels = sch_doc.get("sch_levels", [])
	if not levels:
		st.error("No levels found for this school. Please add levels first.")
		return
	
	# Allow the user to select a level_name
	level_name = st.selectbox("Select Level", levels, key="level_name")
	if not level_name:
		st.warning("Please select a level.")
		return
	
	# Proceed with the rest of the function for adding/removing students
	classes = sch_doc.get(level_name, [])
	if not classes:
		st.error(f"No classes found for {level_name}. Please add classes first.")
		return
	
	# Allow the user to select a class
	class_name = st.selectbox("Select Class", classes, key="class_name")
	if not class_name:
		st.warning("Please select a class.")
		return
	
	st.write(f":green[Selected: {level_name} - {class_name}]")
	action = st.selectbox('Select Action', ['Add Students', 'Remove Students'], key='student_action')
	if action == 'Add Students':
		#display all students in the current class
		students = fetch_students_for_class(sch_name, level_name, class_name)
		st.write(f"Students in {level_name} - {class_name}")
		if students == []:
			st.warning("No students found for the selected class.")
		else:	
			display_students(students)
		add_students_to_class(sch_name, level_name, class_name)
	elif action == 'Remove Students':
		students = fetch_students_for_class(sch_name, level_name, class_name)
		st.write(f"Students in {level_name} - {class_name}")
		display_students(students)
		remove_students(students)

def remove_students(students):
	# Remove students from the class
	if students == []:
		st.warning("No students found for the selected class.")
		return
	else:
		selected_students = st.multiselect("Select Students to Remove", students)
		if not selected_students:
			st.warning("Please select students to remove from the class.")
			return
		else:
			if st.button("Remove Students"):
				result = st.session_state.u_collection.update_many(
					{"username": {"$in": selected_students}},
					{"$unset": {"level": None, "class": None}}
				)
				st.success(f"Successfully removed {len(selected_students)} students from the class.")


def display_students(students):
	#display students in a dataframe with row numbers
	if students:
		df = pd.DataFrame(students)
		#remove the _id field
		st.dataframe(df)

def fetch_students_for_class(sch_name, level_name, class_name):
	# Fetch the students in the specified class
	students_cursor = st.session_state.u_collection.find(
		{"sch_name": sch_name, "level": level_name, "class": class_name, "profile": STU},
		{"_id" : 0, "username": 1}
	)

	students = [student["username"] for student in students_cursor]
	if not students:
		return []
	else:
		return students
	
def add_students_to_class(sch_name, level_name, class_name):
	# Fetch all the students from the school
	all_students = fetch_students_no_class(sch_name)
	if not all_students:
		st.warning(f"No unassigned students found for {sch_name}. Please add or remove students from classes first.")
		return
	else:
		#check how many students can be added to the class by subtracting the number of students in the class from the total number of students
		num_students = NUM_STU - len(fetch_students_for_class(sch_name, level_name, class_name))
		st.write(f"Number of students that can be added to {level_name} - {class_name} is {num_students}")
		display_students(all_students)
		#multiselect the students to add to the class
		selected_students = st.multiselect("Select Students to Add", all_students)
		if not selected_students:
			st.warning("Please select students to add to the class.")
			return
		else:
			if st.button("Add Students"):
				len_selected_students = len(selected_students)
				if len_selected_students > num_students:
					st.error(f"Number of students selected ({len_selected_students}) exceeds the available slots ({num_students}).")
					return
				else:
					# Update the selected students with the specified level and class
					result = st.session_state.u_collection.update_many(
						{"sch_name": sch_name, "username": {"$in": selected_students}},
						{"$set": {"level": level_name, "class": class_name}}
					)
					st.success(f"Successfully added {len_selected_students} students to {level_name} - {class_name}.")


def fetch_students_no_class(sch_name):
	# Fetch all students associated with the specified school name with profile "Student" without any class or level or students witout any fields of level or class
	#students_cursor = st.session_state.u_collection.find(
	students_cursor = st.session_state.u_collection.find(
	{
		"sch_name": sch_name,
		"profile": STU,
		"$or": [
			{"level": None, "class": None},
			{"level": {"$exists": False}, "class": {"$exists": False}}
		]
	},
	{"username": 1}
	)
	students = [student["username"] for student in students_cursor]
	if not students_cursor:
		st.warning(f"No students found for {sch_name}.")
		return []
	else:
		return students

