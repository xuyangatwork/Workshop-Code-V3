
import streamlit as st
from basecode2.authenticate import return_openai_key
from datetime import datetime
import openai
import pandas as pd
from llama_index.llms.openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy import create_engine
from typing import Dict, Any
import os
import pandas as pd
import sqlite3
from llama_index.core import SQLDatabase, ServiceContext
from llama_index.core.query_engine import NLSQLTableQueryEngine
import ast
import configparser

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
RAG_BOT = config_handler.get_value('constants', 'RAG_BOT')
SQL_DB = config_handler.get_value('DATABASE', 'SQL_DB')

cwd = os.getcwd()
WORKING_DIRECTORY = os.path.join(cwd, "database")
WORKING_DATABASE = os.path.join(WORKING_DIRECTORY , SQL_DB)



def clear_session_states():
	st.session_state.msg = []
	if "memory" not in st.session_state:
		pass
	else:
		del st.session_state["memory"]
	st.session_state.query_response = "No query response"


class StreamlitChatPack:

	if "my_table" not in st.session_state:
		st.session_state.my_table = "my_table"

	def __init__(
		self,
		page: str = "Natural Language to SQL Query",
		run_from_main: bool = False,
		**kwargs: Any,
	) -> None:
		"""Init params."""
		
		self.page = page

	def get_modules(self) -> Dict[str, Any]:
		"""Get modules."""
		return {}

	def run(self, *args: Any, **kwargs: Any) -> Any:
		"""Run the pipeline."""
		import streamlit as st

		# st.set_page_config(
		#     page_title=f"{self.page}",
		#     layout="centered",
		#     initial_sidebar_state="auto",
		#     menu_items=None,
		# )
		#st.set_page_config(page_title=f"{self.page}", layout="centered")

		

		if "messages" not in st.session_state:
			st.session_state["messages"] = [{"role": "assistant", "content": "Hello. Upload your CSV file to insert into the database."}]

		st.title(f"{self.page}💬")
		st.info("Upload your CSV file to insert its contents into the database. Then, pose any question related to the data.", icon="ℹ️")

		def add_to_message_history(role, content):
			message = {"role": role, "content": str(content)}
			st.session_state["messages"].append(
				message
			)  # Add response to message history
		uploaded_file = st.file_uploader("Choose a CSV file to upload into the database", type="csv")
		if uploaded_file is not None:
			# Read the uploaded CSV file into a DataFrame
			df = pd.read_csv(uploaded_file)
			# Show a preview of the uploaded file
			st.write("Preview of uploaded CSV file:")
			st.dataframe(df.head())

			st.session_state.my_table = "my_table" + str(st.session_state.user['id'])

			# Construct the path to the SQLite database file within the 'database' directory
			database_path = os.path.join(WORKING_DIRECTORY, "workshop.db")

			conn = sqlite3.connect(database_path)
			c = conn.cursor()
			sql_query = f"DROP TABLE IF EXISTS {st.session_state.my_table}"
			c.execute(sql_query)
			conn.commit()

			#insert the df into the database
			conn = sqlite3.connect(database_path)
			df.to_sql(st.session_state.my_table, conn, if_exists='replace', index=False)
			st.success("Successfully inserted the uploaded CSV into the database.")
			conn.close()

			@st.cache_resource
			def load_db_llm():
				# Load the SQLite database
				#engine = create_engine("sqlite:///ecommerce_platform1.db")
				database_path = os.path.join(WORKING_DIRECTORY, "workshop.db")
				engine = create_engine(f"sqlite:///{database_path}?mode=ro", connect_args={"uri": True})

				sql_database = SQLDatabase(engine) #include all tables

				# Initialize LLM
				#llm2 = PaLM(api_key=os.environ["GOOGLE_API_KEY"])  # Replace with your API key
				openai.api_key = return_openai_key()
				os.environ["OPENAI_API_KEY"] = return_openai_key()
				
				llm2 = OpenAI(temperature=0.1, model="gpt-3.5-turbo-1106")

				service_context = ServiceContext.from_defaults(llm=llm2, embed_model="local")
				
				return sql_database, service_context, engine

			sql_database, service_context, engine = load_db_llm()

		# File uploader for CSV files
	 

			if "query_engine" not in st.session_state:  # Initialize the query engine
				st.session_state["query_engine"] = NLSQLTableQueryEngine(
					sql_database=sql_database,
					synthesize_response=True,
					service_context=service_context
				)

			for message in st.session_state["messages"]:
				with st.chat_message(message["role"]):
					st.write(message["content"])

			if prompt := st.chat_input("Enter your natural language query about the database"):
				with st.chat_message("user"):
					st.write(prompt)
				add_to_message_history("user", prompt)

			# If last message is not from assistant, generate a new response
			if st.session_state["messages"][-1]["role"] != "assistant":
				with st.spinner():
					with st.chat_message("assistant"):
						response = st.session_state["query_engine"].query("User Question:"+prompt+". ")
						sql_query = f"```sql\n{response.metadata['sql_query']}\n```\n**Response:**\n{response.response}\n"
						response_container = st.empty()
						response_container.write(sql_query)
						# st.write(response.response)
						add_to_message_history("assistant", sql_query)

def basic_analysis_bot():
	StreamlitChatPack().run()



