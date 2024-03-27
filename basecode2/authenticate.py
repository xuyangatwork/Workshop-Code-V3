import streamlit as st
import hashlib
#from st_files_connection import FilesConnection



def login_function():
	with st.form("Student login"):
		username = st.text_input("Enter Username:", max_chars=20)
		password = st.text_input("Enter Password:", type="password", max_chars=16)
		submit_button = st.form_submit_button("Login")
		 # On submit, check if new passwords match and then update the password.
		if submit_button:
			if check_password(username, password):
				st.session_state.username = username
				#st.success("Logged in as: " + username)
				return True
			else:
				st.error("Username and Password is incorrect")
				return False

#can consider bycrypt if need to upgrade higher security
def hash_password(password):
	"""Hashes a password using SHA-256."""
	return hashlib.sha256(password.encode()).hexdigest()

def check_password(username, password):
	"""Checks if the password matches the stored password."""
	hashed_password = hash_password(password)
	user_document = st.session_state.u_collection.find_one({"username": username})
	#conn = st.experimental_connection('s3', type=FilesConnection)
	if user_document:
		if hashed_password == user_document['password']:
			return True
		else:
			return False

#store in duck db 
def return_openai_key():
	return st.session_state.openai_key

def return_cohere_key():
	return st.session_state.cohere_key

def return_google_key():
	return st.session_state.google_key

def return_claude_key():
	return st.session_state.claude_key

def return_serp_key():
	return st.session_state.serp_key

def return_assistant_id_1():
	return st.session_state.assistant_id_1