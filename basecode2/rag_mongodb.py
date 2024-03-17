
from basecode2.authenticate import hash_password
from basecode2.org_module import sa_select_school
from bson.binary import Binary
import tempfile
import streamlit_antd_components as sac
import streamlit as st
import time
import pandas as pd
import configparser
from langchain_community.vectorstores import FAISS
import tempfile
import pickle
import os
import shutil
import ast
from pymongo import MongoClient
import pymongo
#from bson import ObjectId
import certifi
import botocore 
import botocore.session
from langchain_community.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import CharacterTextSplitter
from basecode2.authenticate import return_openai_key

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
SA = config_handler.get_value('constants', 'SA')
AD = config_handler.get_value('constants', 'AD')

def initialise_rag_collection():
	if "r_collection" not in st.session_state:
		# Connect to MongoDB
		if "URI" in st.secrets["MONGO"]:
			MONGO_URI = st.secrets["MONGO"]["URI"]
			DATABASE_NAME = st.secrets["MONGO"]["DATABASE"]
		else:
			#AWS manager
			pass
		client = MongoClient(MONGO_URI, tls=True,tlsAllowInvalidCertificates=True)
		db = client[DATABASE_NAME]
		st.session_state.r_collection = db["rag"]

def rag_creator_mongodb():
	initialise_rag_collection()
	if st.session_state.user['profile_id'] == SA:
		if st.toggle("Personal RAG"):
			action = st.selectbox("Select action", ["Create RAG", "Display RAG", "Delete RAG"])
			if action == "Create RAG":
				#create_rag_mongodb(st.session_state.user['id'], False)
				create_rag_mongodb("super_admin", False)
			elif action == "Delete RAG":
				#delete_rag_mongodb(st.session_state.user['id'], False)
				delete_rag_mongodb("super_admin", False)
				pass
			elif action == "Display RAG":
				display_documents_as_dataframe("super_admin")
		else:
			sch_names = sa_select_school()
			school = st.selectbox('Select School', sch_names, key='app_school')
			action = st.selectbox("Select action", ["Create RAG", "Display RAG", "Delete RAG"])
			if action == "Create RAG":
				create_rag_mongodb(school, True)
			elif action == "Delete RAG":
				delete_rag_mongodb(school, True)
				st.divider()
				delete_rag_direct()
				pass
			elif action == "Display RAG":
				display_documents_as_dataframe(school)
	elif st.session_state.user['profile_id'] == AD:
		if st.toggle("Personal RAG"):
			action = st.selectbox("Select action", ["Create RAG", "Display RAG", "Delete RAG"])
			if action == "Create RAG":
				create_rag_mongodb(st.session_state.user['id'], False)
			elif action == "Delete RAG":
				delete_rag_mongodb(st.session_state.user['id'], False)
				pass
			elif action == "Display RAG":
				display_documents_as_dataframe(st.session_state.user['id'])
		else:
			action = st.selectbox("Select action", ["Create RAG", "Display RAG", "Delete RAG"])
			if action == "Create RAG":
				create_rag_mongodb(st.session_state.user['school_id'], True)
			elif action == "Delete RAG":
				delete_rag_mongodb(st.session_state.user['school_id'], True)
				pass
			elif action == "Display RAG":
				display_documents_as_dataframe(st.session_state.user['school_id'])
	else:
		action = st.selectbox("Select action", ["Create RAG", "Display RAG", "Delete RAG"])
		if action == "Create RAG":
			create_rag_mongodb(st.session_state.user['id'], False)
		elif action == "Delete RAG":
			delete_rag_mongodb(st.session_state.user['id'], False)
			pass
		elif action == "Display RAG":
			display_documents_as_dataframe(st.session_state.user['id'])
		

def delete_rag_mongodb(var, school_flag):
	if school_flag:
		rag_list = sch_check_and_get_rag_list(var)
	else:
		rag_list = u_check_and_get_rag_list(var)

	if rag_list == []:
		st.error("No RAGs to delete.")
	else:
		rag_to_delete = st.selectbox("Select RAG to delete", rag_list)
		if st.button("Delete"):
			rag_list.remove(rag_to_delete)
			st.session_state.s_collection.update_one({"sch_name": var}, {"$set": {"rag_list": rag_list}})
			st.session_state.u_collection.update_one({"username": var}, {"$set": {"rag_list": rag_list}})
			st.session_state.r_collection.delete_one({"owner": var, "name": rag_to_delete})
			st.success(f"RAG {rag_to_delete} deleted successfully!")

def delete_rag_direct():
	st.warning("Use above first, as this action will delete the RAG from the database directly.")
	documents = st.session_state.r_collection.find({}, {'owner': 1, 'name': 1, '_id': 0})
	docs_list = list(documents)
	df = pd.DataFrame(docs_list)
	st.dataframe(df)

	owner = st.text_input("Enter the owner of the RAG to delete")
	if st.button("Delete", key="delete_rag"):
		st.session_state.r_collection.delete_many({"owner": owner})
		st.success(f"All RAGs owned by {owner} deleted successfully!")


def display_documents_as_dataframe(owner):
	# Assuming st.session_state.r_collection is your MongoDB collection
	documents = st.session_state.r_collection.find({"owner": owner})
	
	# Convert MongoDB documents to a list of dictionaries, excluding '_id' and 'rag_data'
	docs_list = []
	for doc in documents:
		# Remove '_id' and 'rag_data' fields
		doc.pop('_id', None)
		doc.pop('rag_data', None)
		docs_list.append(doc)
	
	# Create a DataFrame from the list of dictionaries
	df = pd.DataFrame(docs_list)
	
	# Display the DataFrame in Streamlit
	st.dataframe(df)

def create_rag_mongodb(var,school_flag):
	#st.write(return_openai_key())	
	os.environ["OPENAI_API_KEY"] = return_openai_key()
	st.subheader("Create Knowledge Base for RAG")
	uploaded_files = st.file_uploader("Choose a file", type=['docx', 'txt', 'pdf'], accept_multiple_files=True)
	new_rag = st.text_input("Enter new RAG name")
	meta = st.text_input("Please enter your document source (Default is MOE):", max_chars=50)
	if meta == "":
		meta = "MOE"
	description = st.text_area("Please enter a brief description of the document:", max_chars=200)
	if description == "":
		description = "No description available"
	if st.checkbox("KB Sharing"):
		sharing = True
		st.write("KB Sharing is enabled")
	else:
		sharing = False
		st.write("KB Sharing is disabled")
	if uploaded_files:
		if st.button("Create RAG"):
			if new_rag == "":
				st.error("Please enter a name for the RAG.")
				return
			if school_flag:
				rag_list = sch_check_and_get_rag_list(var)
			else:
				rag_list = u_check_and_get_rag_list(var)
			st.write(f"Current RAG list : {rag_list}")
			if new_rag in rag_list:
				st.error("Already exists in the list.")
				return
			else:
				if school_flag:
					sch_update_rag_list(var, new_rag)
				else:
					u_update_rag_list(var, new_rag)
			
			list_of_files = []
			for uploaded_file in uploaded_files:

				with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
					# Write the uploaded file's content to the temporary file
					shutil.copyfileobj(uploaded_file, tmp_file)
					# Get the path of the temporary file
					temp_file_path = tmp_file.name
				
				list_of_files.append(temp_file_path)
			
			#st.write(list_of_files)
			with st.spinner("Creating RAG..."):
				os.environ["OPENAI_API_KEY"] = return_openai_key()
				embeddings = OpenAIEmbeddings()
				docs = split_docs(list_of_files, meta)
				st.write(docs)
				db = FAISS.from_documents(docs, embeddings)
				pkl = db.serialize_to_bytes() 
				#serialized_index = serialize_faiss_index(db.index)
				#serialized_binary = Binary(pickle.dumps(serialized_index))
				index_document = {
					'name': new_rag,
					'description': description,
					'sharing': sharing,
					'owner': var,
					'rag_data': pkl
				}
				st.session_state.r_collection.insert_one(index_document)

				st.success(f"RAG {new_rag} created successfully!")
	

def split_docs(file_path,meta):
#def split_meta_docs(file, source, tch_code):
	loader = UnstructuredFileLoader(file_path)
	documents = loader.load()
	text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
	docs = text_splitter.split_documents(documents)
	metadata = {"source": meta}
	for doc in docs:
		doc.metadata.update(metadata)
	return docs


# Example function to fetch the serialized FAISS object from the database
def fetch_serialized_faiss(db_collection, rag_name, owner):
	# Adjust the query to include both 'name' and 'owner' fields
	document = db_collection.find_one({'name': rag_name, 'owner': owner})
	if document:
		return document['rag_data']
	else:
		return None

def list_rags_for_owner(db_collection, owner):
	# Query the database for documents with the specified owner
	documents = db_collection.find({'owner': owner})
	# Collect the 'name' (RAG name) from each document
	rag_names = [doc['name'] for doc in documents]
	return rag_names



def sch_check_and_get_rag_list(sch_name):
	school_doc = st.session_state.s_collection.find_one({"sch_name": sch_name},{"rag_list": 1})
	if school_doc and "rag_list" in school_doc:
		return school_doc["rag_list"]
	else:
		return []

def sch_update_rag_list(sch_name, new_value):
	rag_list = sch_check_and_get_rag_list(sch_name)
	if rag_list == []:
		st.session_state.s_collection.update_one({"sch_name": sch_name}, {"$set": {"rag_list": [new_value]}})
	elif len(rag_list) < 10:
		rag_list.append(new_value)
		st.session_state.s_collection.update_one({"sch_name": sch_name}, {"$set": {"rag_list": rag_list}})
		st.success("Updated successfully!")
	else:
		st.error("No more than 10 items allowed in the list.")

def u_check_and_get_rag_list(u_name):
	school_doc = st.session_state.u_collection.find_one({"username": u_name},{"rag_list": 1})
	if school_doc and "rag_list" in school_doc:
		return school_doc["rag_list"]
	else:
		return []

def u_update_rag_list(u_name, new_value):
	rag_list = u_check_and_get_rag_list(u_name)
	if rag_list == []:
		st.session_state.u_collection.update_one({"username": u_name}, {"$set": {"rag_list": [new_value]}})
	if len(rag_list) < 10:
		rag_list.append(new_value)
		st.session_state.u_collection.update_one({"username": u_name}, {"$set": {"rag_list": rag_list}})
		st.success("Updated successfully!")
	else:
		st.error("No more than 10 items allowed in the list.")


def load_rag():
	os.environ["OPENAI_API_KEY"] = return_openai_key()
	initialise_rag_collection()
	# Fetch all RAGs for the current user
	if st.toggle("Load Personal RAG"):
		display_documents_as_dataframe(st.session_state.user['id'])
		rag_list = list_rags_for_owner(st.session_state.r_collection, st.session_state.user['id'])
		if rag_list == []:
			st.error("No RAGs found.")
		else:
			rag_name = st.selectbox("Select RAG", rag_list)
			# Fetch the serialized FAISS object from the database
			serialized_faiss = fetch_serialized_faiss(st.session_state.r_collection, rag_name, st.session_state.user['id'])
			# Unserialize the FAISS object
			#faiss_obj = unserialize_faiss_object(serialized_faiss)
			embeddings_instance = OpenAIEmbeddings()
			faiss_obj = FAISS.deserialize_from_bytes(embeddings=embeddings_instance, serialized=serialized_faiss)

			if faiss_obj is not None:
				# Proceed with using the deserialized FAISS index
				print("FAISS index deserialized successfully.")
			else:
				print("Failed to deserialize FAISS index.")
			# Return the FAISS object
			return faiss_obj, rag_name
	else:
		if st.session_state.user["profile_id"] == SA:
			sch_names = sa_select_school()
			school = st.selectbox('Select School', ["Select School"] + sch_names, key='rag_school')
			st.write("School RAG Display")
			display_documents_as_dataframe(school)
			if school != "Select School" and school != None:
				rag_list = list_rags_for_owner(st.session_state.r_collection, school)
				if rag_list == []:
					st.error("No RAGs found.")
				else:
					rag_name = st.selectbox("Select RAG", rag_list)
					# Fetch the serialized FAISS object from the database
					serialized_faiss = fetch_serialized_faiss(st.session_state.r_collection, rag_name, st.session_state.user['school_id'])
					embeddings_instance = OpenAIEmbeddings()
					faiss_obj = FAISS.deserialize_from_bytes(embeddings=embeddings_instance, serialized=serialized_faiss)
					if faiss_obj is not None:
						# Proceed with using the deserialized FAISS index
						print("FAISS index deserialized successfully.")
					else:
						print("Failed to deserialize FAISS index.")
					# Return the FAISS object
					return faiss_obj, rag_name
		else:
			st.write("School RAG Display")
			display_documents_as_dataframe(st.session_state.user['school_id'])
			rag_list = list_rags_for_owner(st.session_state.r_collection, st.session_state.user['school_id'])
			if rag_list == []:
				st.error("No RAGs found.")
			else:
				rag_name = st.selectbox("Select RAG", rag_list)
				# Fetch the serialized FAISS object from the database
				serialized_faiss = fetch_serialized_faiss(st.session_state.r_collection, rag_name, st.session_state.user['school_id'])
				embeddings_instance = OpenAIEmbeddings()
				faiss_obj = FAISS.deserialize_from_bytes(embeddings=embeddings_instance, serialized=serialized_faiss)
				if faiss_obj is not None:
					# Proceed with using the deserialized FAISS index
					print("FAISS index deserialized successfully.")
				else:
					print("Failed to deserialize FAISS index.")
				# Return the FAISS object
				return faiss_obj, rag_name
	return None, None



