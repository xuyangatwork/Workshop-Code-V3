#No need SQLite
import nltk
import streamlit as st
from streamlit_antd_components import menu, MenuItem
import streamlit_antd_components as sac
from basecode2.app_management import load_app_settings, load_sa_app_settings, propagate_prompts
from basecode2.authenticate import login_function
from basecode2.personal_prompt import set_prompt_settings, manage_prompt_templates
from basecode2.rag_mongodb import rag_creator_mongodb
from basecode2.app_management import set_app_settings, delete_app_settings, delete_prompt_settings
from basecode2.org_module import (
	setup_users, 
	manage_app_access, 
	manage_organisation, 
	initialise_admin_account, 
	create_school, 
	load_user_profile, 
	set_function_access_for_user, 
	sa_delete_profile_from_school,
	manage_students_school,
	manage_teachers_school,
	)
from basecode2.sqlite_db import create_sql_db
from basecode2.chatbot import main_chatbot_functions
from basecode2.pwd_module import password_settings
from basecode2.class_dash import class_dash
from workshop_code.discussion_bot import main_discussion_bot
from workshop_code.rule_based_bot import main_rule_based
from workshop_code.faq_bot import main_faq_bot
from workshop_code.api_calls import call_api
from workshop_code.prompt_designs import prompt_designs_llm 
from workshop_code.prototype_application import my_first_app, my_first_app_advance, prototype_settings
from workshop_code.educational_bots import starting_bot, network_bot, language_bot, linking_bot
from workshop_code.assistant_bot import assistant_demo
# from workshop_code.knowledge_bot import rag_bot
# from workshop_code.analytics_bot import basic_analysis_bot
from workshop_code.agent import agent_bot, agent_management
import configparser
import os
import ast
import ssl
import time
			  
try:
	_create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
	pass
else:
	ssl._create_default_https_context = _create_unverified_https_context

class ConfigHandler:
	def __init__(self):
		self.config = configparser.ConfigParser()
		self.config.read('config.ini')

	def get_value(self, section, key):
		value = self.config.get(section, key)
		try:
			# Convert string value to a Python data structure
			return ast.literal_eval(value)
		except (SyntaxError, ValueError):
			# If not a data structure, return the plain string
			return value

# Initialization
config_handler = ConfigHandler()

# Setting Streamlit configurations
st.set_page_config(layout="wide")

MENU_FUNCS = config_handler.get_value('menu_lists', 'MENU_FUNCS')
SA = config_handler.get_value('constants', 'SA')
AD = config_handler.get_value('constants', 'AD')
ACK = config_handler.get_value('application_agreement', 'ACK')
PROTOTYPE = config_handler.get_value('constants', 'PROTOTYPE')
PROMPT_CONFIG = config_handler.get_value('menu_lists', 'PROMPT_CONFIG')
APP_CONFIG = config_handler.get_value('menu_lists', 'APP_CONFIG')
os.environ['TIKTOKEN_CACHE_DIR'] = st.secrets["NLTK_DATA"]
os.environ['NLTK_DATA'] = st.secrets["NLTK_DATA"]


#function for menu options
def is_function_disabled(function_name):
	return st.session_state.func_options.get(function_name, True)

#change option name in the st.sidebar	
def return_function_name(function_name, default_name = ""):
	if st.session_state.func_options.get(function_name, True):
		return "-"
	else:
		if default_name == "":
			return function_name
		else:
			return default_name
		
#set the menu options for the user where SA is all visible and other users are not 
def initialize_session_state( menu_funcs, default_value):
	st.session_state.func_options = {key: default_value for key in menu_funcs.keys()}


def load_app_session_states():
	#initialize session state for the application
	if "title_page" not in st.session_state:
		st.session_state.title_page = st.secrets["default_title"]

	if "func_options" not in st.session_state:
			st.session_state.func_options = {}
			initialize_session_state(MENU_FUNCS, True)
	
	if "acknowledgement" not in st.session_state:
		st.session_state.acknowledgement = False
	
	if "login" not in st.session_state:
		st.session_state.login = False
	
	if "user" not in st.session_state:
		st.session_state.user = {}
	
	if "username" not in st.session_state:
		st.session_state.username = ""

	if "start" not in st.session_state:
		st.session_state.start = 0
  
	

	# if "load_templates" not in st.session_state:
	# 	st.session_state.load_templates = False
	
#Base chabot settings and chatbot session states
def load_chatbot_session_states():
	if "msg" not in st.session_state:
		st.session_state.msg = []
	
	if "memoryless" not in st.session_state:
		st.session_state.memoryless = False

	if "chatbot" not in st.session_state:
		st.session_state.chatbot = "You are a helpful assistant"
	
	#Vectorstore aka RAG KB 
	if "vs" not in st.session_state:
		st.session_state.vs = None

	# if "vs2" not in st.session_state:
	# 	st.session_state.vs2 = None

	# if "vs3" not in st.session_state:
	# 	st.session_state.vs3 = None

	if "current_kb_model" not in st.session_state:
		st.session_state.current_kb_model = ""

	if "button_text" not in st.session_state:
		st.session_state.button_text = "Cancel"

	if "data_doc" not in st.session_state:
		st.session_state.data_doc = ""
		
	if "download_response_flag" not in st.session_state:
		st.session_state.download_response_flag = False
	
	if "chat_response" not in st.session_state:
		st.session_state.chat_response = ""

	if "rag_response" not in st.session_state:
		st.session_state.rag_response = None
  
def load_mongo_db():
	pass	


def load_safa_session_states():
	#initialize session state for JSON Tools in Short Answer
	if "tools" not in st.session_state:
		st.session_state.tools = []

def main():
	try:
		#initialize the application settings
		create_sql_db()
		#start_time = time.time()
		load_app_session_states()
		initialise_admin_account()
		st.title(st.session_state.title_page)
		sac.divider(label='Artificial Intelligence by Joe Tay', icon='house', align='center')
  
			# Define the NLTK data directory
		nltk_data_dir = st.secrets["NLTK_DATA"]

		# Ensure the NLTK data directory exists
		if not os.path.exists(nltk_data_dir):
			os.makedirs(nltk_data_dir, exist_ok=True)

		# Update the NLTK data path to include the custom directory
		nltk.data.path.append(nltk_data_dir)

		def download_nltk_data_if_absent(package_name):
			try:
				# Try loading the package to see if it exists in the custom directory
				nltk.data.find("tokenizers/" + package_name)
			except LookupError:
				# If the package doesn't exist, download it to the specified directory
				nltk.download(package_name, download_dir=nltk_data_dir)
		#print(f"Iteration: {st.session_state.iterate + 1}")
		# Example usage
		download_nltk_data_if_absent('punkt')
		download_nltk_data_if_absent('stopwords')
			
		#initialize session state options for side menubar for the application
		if "options" not in st.session_state:
			st.session_state.options = False
   

		with st.sidebar: #options for sidebar
			if st.session_state.login == False:
				
				st.image("app_logo/aied_logo.png")
				st.session_state.option = menu([MenuItem('Users login', icon='people')])
			else:
				#can do a test if user is school is something show a different logo and set a different API key
				if st.session_state.user['profile_id'] == SA: #super admin login feature
					# Initialize the session state for function options	
					initialize_session_state(MENU_FUNCS, False)
				else:
					#if user has not acknowledged the use of AI, then the user cannot access the application
					if st.session_state.acknowledgement == False:
						initialize_session_state(MENU_FUNCS, True)
					else:
						#setting the menu options for the user
						set_function_access_for_user()
				#menu options for the application	
				st.session_state.option = sac.menu([
					sac.MenuItem('Home', icon='house', children=[
						sac.MenuItem(return_function_name('Personal Dashboard'), icon='person-circle', disabled=is_function_disabled('Personal Dashboard')),
					]),
					#workshop_activities
					sac.MenuItem('GenAI Capabilities', icon='book', children=[
						#sac.MenuItem(return_function_name('Machine Learning and Neural Network'), icon='stack'),
						#sac.MenuItem(return_function_name('AI Analytics'), icon='graph-up'),
						#sac.MenuItem(return_function_name('Knowledge Graph Bot'), icon='diagram-3'),
						#sac.MenuItem(return_function_name('Teacher Assistant Bot'), icon='chat-heart'),
					]),	

					sac.MenuItem('Educational Chatbots', icon='book', children=[
						sac.MenuItem(return_function_name('Discussion Chatbot'), icon='people'),
						sac.MenuItem(return_function_name('Starting Bot'), icon='skip-start'), #visual image
						sac.MenuItem(return_function_name('Connecting Bot'), icon='diagram-3'), #Graph agent lang graph
						sac.MenuItem(return_function_name('Language Support Bot'), icon='chat'), #Language
						sac.MenuItem(return_function_name('Linking Bot'), icon='emoji-smile'), #Image generator and voice
					]),	

					sac.MenuItem('Chatbots Activities', icon='person-fill-gear', children=[
						sac.MenuItem(return_function_name('Rule Based Chatbot'), icon='chat-dots'),
						sac.MenuItem(return_function_name('FAQ AI Chatbot'), icon='chat-dots'),
						sac.MenuItem(return_function_name('LLM API Call'), icon='chat-dots'),
						sac.MenuItem(return_function_name('Prompt Designs'), icon='arrow-left-right'),
						sac.MenuItem(return_function_name('AI Chatbot'), icon='chat-dots'),
						sac.MenuItem(return_function_name('Prototype Application'), icon='star-fill'),
						sac.MenuItem(return_function_name('Prototype Settings'), icon='wrench'),
						sac.MenuItem(return_function_name('Agent Chatbot'), icon='chat-dots'),
						
					]),

					sac.MenuItem('ChatBots, RAG & Prompts', icon='person-fill-gear', children=[
						#sac.MenuItem(return_function_name('AI Chatbot'), icon='chat-dots', disabled=is_function_disabled('AI Chatbot')),
						sac.MenuItem(return_function_name('KB management', 'KB (RAG) Management'), icon='database-fill-up',disabled=is_function_disabled('KB management')),
						sac.MenuItem(return_function_name('Prompt Management'), icon='wrench', disabled=is_function_disabled('Prompt Management')),						
					]),
					sac.MenuItem('Organisation Settings', icon='buildings', children=[
						sac.MenuItem(return_function_name( 'Organisation Management','Org Management'), icon='building-gear', disabled=is_function_disabled('Organisation Management')),
					]),
					sac.MenuItem(type='divider'),
					sac.MenuItem('Profile Settings', icon='gear'),
					sac.MenuItem('Application Info', icon='info-circle'),
					sac.MenuItem('Logout', icon='box-arrow-right'),
				], index=st.session_state.start, format_func='title', open_all=True)
		
		if st.session_state.option == 'Users login':
				col1, col2 = st.columns([3,4])
				placeholder = st.empty()
				with placeholder:
					with col1:
						#can make login faster - optimise code here
						if login_function() == True:
							load_user_profile()
							st.session_state.login = True
							# if st.session_state.user['profile_id'] != SA:
							st.rerun()

					with col2:
						pass
		elif st.session_state.option == 'Home':
			#st.subheader(f":green[Please select a school below to proceed if there is any]")
			load_chatbot_session_states()
			col1, col2 = st.columns([3,1])
			with col1:
				st.subheader("Acknowledgement on the use of Generative AI with Large Language Models")
				initialize_session_state(MENU_FUNCS, True)
				st.write(ACK)
				ack = st.checkbox("I acknowledge the above information")
				if ack:
					st.session_state.acknowledgement = True
					set_function_access_for_user()
					load_app_settings("prompt_templates", PROMPT_CONFIG)
					load_app_settings("app_settings", APP_CONFIG)
					st.session_state.start = 1
					st.rerun()
				else:
					st.warning("Please acknowledge the above information before you proceed")
					initialize_session_state(MENU_FUNCS, True)
					st.stop()
				pass
			with col2:
				pass
		
		#Personal Dashboard
		elif st.session_state.option == 'Personal Dashboard':
			st.subheader(f":green[{st.session_state.option}]")
			class_dash()
		#workshop_activities
			if st.session_state.user['profile_id'] == SA:
				load_sa_app_settings()
		elif st.session_state.option == 'Discussion Chatbot':
			st.subheader(f":green[{st.session_state.option}]")
			main_discussion_bot()
		elif st.session_state.option == 'Machine Learning and Neural Network':
			st.subheader(f":green[{st.session_state.option}]")
			#machine_learning()
		elif st.session_state.option == 'Rule Based Chatbot':
			st.subheader(f":green[{st.session_state.option}]")
			main_rule_based()
		elif st.session_state.option == 'FAQ AI Chatbot':
			st.subheader(f":green[{st.session_state.option}]")
			main_faq_bot()
		elif st.session_state.option == 'LLM API Call':
			st.subheader(f":green[{st.session_state.option}]")
			call_api()
		elif st.session_state.option == 'Prompt Designs':
			st.subheader(f":green[{st.session_state.option}]")
			prompt_designs_llm()
		elif st.session_state.option == 'AI Chatbot':
			
			st.subheader(f":green[{st.session_state.option}]")
			main_chatbot_functions()
		elif st.session_state.option == 'Prototype Application':
			st.subheader(f":green[{st.session_state.option}]")
			if st.toggle("Form Prototype", False):
				my_first_app()
			else:
				my_first_app_advance()
		elif st.session_state.option == 'Prototype Settings':
			st.subheader(f":green[{st.session_state.option}]")
			prototype_settings()
			pass
		elif st.session_state.option == 'Starting Bot':
			st.subheader(f":green[{st.session_state.option}]")
			starting_bot()
		elif st.session_state.option == 'Connecting Bot':
			st.subheader(f":green[{st.session_state.option}]")
			network_bot()
		elif st.session_state.option == 'Language Support Bot':
			st.subheader(f":green[{st.session_state.option}]")
			language_bot()
		elif st.session_state.option == 'Linking Bot':
			st.subheader(f":green[{st.session_state.option}]")
			linking_bot()
		elif st.session_state.option == 'AI Analytics':
			st.subheader(f":green[{st.session_state.option}]")
			#basic_analysis_bot()
			pass
		elif st.session_state.option == 'Agent Chatbot':
			st.subheader(f":green[{st.session_state.option}]")
			agent_bot()
		elif st.session_state.option == 'Knowledge Graph Bot':
			st.subheader(f":green[{st.session_state.option}]")
			#rag_bot()             
		elif st.session_state.option == 'Teacher Assistant Bot':
			st.subheader(f":green[{st.session_state.option}]")
			st.write("### Feature not available yet")
			#assistant_demo()
		elif st.session_state.option == "KB (RAG) Management":
			st.subheader(f":green[{st.session_state.option}]") 
			rag_creator_mongodb()
		elif st.session_state.option == 'Prompt Management':
			st.subheader(f":green[{st.session_state.option}]")
			set_prompt_settings()
			st.divider()
			manage_prompt_templates()
		#workshop tools
		
			
		#Organisation Tools
		elif st.session_state.option == "Org Management":
			if st.session_state.user['profile_id'] == SA or st.session_state.user['profile_id'] == AD:
				create_flag = True
				if st.session_state.user['profile_id'] == SA:
					create_flag = False
				steps_options = sac.steps(
									items=[
										sac.StepsItem(title='Create new school', disabled=create_flag),
										sac.StepsItem(title='Manage Users'),
										sac.StepsItem(title='Manage School'),
										sac.StepsItem(title='Function Access'),
										sac.StepsItem(title='User Assignments'),
										sac.StepsItem(title='App configuration'),
									]
								)
				if steps_options == "Create new school":
					create_school()
				elif steps_options == "Manage School":
					manage_organisation()
				elif steps_options == "Manage Users":
					setup_users()
				elif steps_options == "Function Access":
					manage_app_access()
					st.divider()
					sa_delete_profile_from_school()
				elif steps_options == "User Assignments":
	
					#select teachers or students
					action = st.selectbox("Select action", ["Select", "Manage Teachers", "Manage Students"])
					if action == "Manage Teachers":
						manage_teachers_school()
					elif action == "Manage Students":
						manage_students_school()
				elif steps_options == "App configuration":
					set_app_settings()
					st.divider()
					delete_app_settings()
					st.divider()
					delete_prompt_settings()
					st.divider()
					propagate_prompts()
				else:
					st.subheader(f":red[This option is accessible only to administrators only]")	
				pass

		elif st.session_state.option == "Profile Settings":
			st.subheader(f":green[{st.session_state.option}]") 
			#direct_vectorstore_function()
			password_settings(st.session_state.user["id"])

		elif st.session_state.option == 'Application Info':
			st.subheader(f":green[{st.session_state.option}]") 
			col1, col2 = st.columns([3,1])
			with col1:
				st.subheader("Acknowledgement on the use of Generative AI with Large Language Models")
				initialize_session_state(MENU_FUNCS, True)
				st.write(ACK)
				if st.session_state.acknowledgement == True:
					st.success("You have acknowledged the above information")
				else:
					ack = st.checkbox("I acknowledge the above information")
					if ack:
						st.session_state.acknowledgement = True
						set_function_access_for_user()
						st.session_state.start = 1
						st.rerun()
					else:
						st.warning("Please acknowledge the above information before you proceed")
						initialize_session_state(MENU_FUNCS, True)
						st.stop()
					pass
			with col2:
				pass

		elif st.session_state.option == 'Logout':
		
			for key in st.session_state.keys():
				del st.session_state[key]
			st.rerun()
   
		# end_time = time.time()
		# execution_time = end_time - start_time
		# st.write(f"Execution time: {execution_time} seconds")

					
	except Exception as e:
		st.exception(e)

if __name__ == "__main__":
	main()
