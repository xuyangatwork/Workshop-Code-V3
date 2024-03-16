import streamlit as st
from basecode2.authenticate import return_openai_key
from basecode2.rag_mongodb import load_rag
from langchain.memory import ConversationBufferWindowMemory
from datetime import datetime
import openai
import pandas as pd
import google.generativeai as genai
from Markdown2docx import Markdown2docx
import base64
from sqlalchemy import create_engine
import streamlit_antd_components as sac
import requests
from sqlalchemy import create_engine
from typing import Dict, Any
import os
import pandas as pd
import sqlite3
from llama_index.core import SimpleDirectoryReader
from llama_index.core import SQLDatabase, ServiceContext, KnowledgeGraphIndex
from llama_index.core.query_engine import NLSQLTableQueryEngine
import ast
import configparser
from openai import OpenAI
from transformers import AutoModel, AutoTokenizer
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.core import StorageContext
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile

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


# Function to encode the image
def encode_image(image_path):
	with open(image_path, "rb") as image_file:
		return base64.b64encode(image_file.read()).decode('utf-8')

# Function to get file extension
def get_file_extension(file_name):
	return os.path.splitext(file_name)[-1]

def rag_bot():
	if "graph_bot" in st.session_state:
		st.session_state.chatbot = st.session_state.graph_bot
  
	with st.expander("Chatbot Settings"):
		st.write(f"Currently Loaded KB (RAG): {st.session_state.current_kb_model}")
		vs, rn = load_rag()
		d1,d2,d3 = st.columns([2,2,3])
		with d1:
			if st.button("Load RAG"):
				st.session_state.vs = vs
				st.session_state.current_kb_model = rn
				st.rerun()
		with d2:
			if st.button("Unload RAG"):
				st.session_state.vs = None
				st.session_state.current_kb_model = ""
				st.rerun()
	
	k1, k2 = st.columns([2,2])

	with k1:
		if st.session_state.vs:#chatbot with knowledge base
			rag_base_bot(RAG_BOT, True, True) #chatbot with knowledge base and memory
		else:#chatbot with no knowledge base
			rag_base_bot(RAG_BOT, True, False) #chatbot with no knowledge base but with memory
	with k2:
		with st.container(border=True, height=500):
			st.write(":red[Knowledge Graph]")
			if st.button("Clear Graph"):
				st.session_state.k_graph_index = None
				st.rerun()
			networkx_graph()
		with st.container(border=True):
			st.write(":green[Knowledge Graph Query Response]")
			st.write(st.session_state.query_response)
		with st.container(border=True):
			st.write(":blue[Upload References]")
			rag_kb()
			pass

def prompt_template_function_rag(prompt, memory_flag, rag_flag):
	#check if there is kb loaded
	if st.session_state.vs:
		docs = st.session_state.vs.similarity_search(prompt)
		resource = docs[0].page_content
		source = docs[0].metadata
		st.session_state.rag_response = resource, source
	else:
		resource = ""
		source = ""

	if memory_flag:
		if "memory" not in st.session_state:
			st.session_state.memory = ConversationBufferWindowMemory(k=st.session_state.default_k_memory)
		mem = st.session_state.memory.load_memory_variables({})
	if rag_flag and memory_flag: #rag and memory only
		prompt_template = st.session_state.chatbot + f"""
							Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. 
							Search Result:
							{resource}
							{source}
							History of conversation:
							{mem}
							You must quote the source of the Search Result if you are using the search result as part of the answer"""
	
		return prompt_template
	
	elif rag_flag and not memory_flag: #rag kb only
		prompt_template = st.session_state.chatbot + f"""
						Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer. 
						Search Result:
						{resource}
						{source}
						You must quote the source of the Search Result if you are using the search result as part of the answer"""
		return prompt_template
	
	elif not rag_flag and memory_flag: #memory only
		prompt_template = st.session_state.chatbot + f""" 
						History of conversation:
						{mem}"""
		return prompt_template
	else: #base bot nothing
		return st.session_state.chatbot

def rag_base_bot(bot_name, memory_flag, rag_flag):

	if "query_response" not in st.session_state:
		st.session_state.query_response = "No query response"

	client = OpenAI(api_key=return_openai_key())
	full_response = ""
	greetings_str = f"Hi, I am {bot_name}"
	help_str = "How can I help you today?"
	g_str = "At any time, if you have a knowledge graph, use this starting prompt to ask about your image: From the graph"
	# Check if st.session_state.msg exists, and if not, initialize with greeting and help messages
	if 'msg' not in st.session_state:
		st.session_state.msg = [
			{"role": "assistant", "content": greetings_str},
			{"role": "assistant", "content": help_str},
			{"role": "assistant", "content": g_str}
		]
	elif st.session_state.msg == []:
		st.session_state.msg = [
			{"role": "assistant", "content": greetings_str},
			{"role": "assistant", "content": help_str},
			{"role": "assistant", "content": g_str}
		]
	messages = st.container(border=True)
		#showing the history of the chatbots
	for message in st.session_state.msg:
		with messages.chat_message(message["role"]):
			st.markdown(message["content"])
	#chat bot input
	try:
		if prompt := st.chat_input("Enter your query"):
			st.session_state.msg.append({"role": "user", "content": prompt})
			with messages.chat_message("user"):
				st.markdown(prompt)
			
			image_required = prompt.lower().startswith("from the graph")
			if image_required and st.session_state.k_graph_index:
				with st.spinner("Thinking..."):
					q_engine = query_graph()
					response = q_engine.query(
						prompt,
					)
					st.session_state.query_response = response.response
					prompt = response.response

			with messages.chat_message("assistant"):
				prompt_template = prompt_template_function_rag(prompt, memory_flag, rag_flag)
				stream = client.chat.completions.create(
					model=st.session_state.openai_model,
					messages=[
						{"role": "system", "content":prompt_template },
						{"role": "user", "content": prompt},
					],
					temperature=st.session_state.default_temp, #settings option
					presence_penalty=st.session_state.default_presence_penalty, #settings option
					frequency_penalty=st.session_state.default_frequency_penalty, #settings option
					stream=True #settings option
				)
				response = st.write_stream(stream)
			
			st.session_state.msg.append({"role": "assistant", "content": response})
			st.session_state["memory"].save_context({"input": prompt},{"output": response})

			
	except Exception as e:
		st.exception(e)

@st.cache_resource
def embedding_function():
	model_name = "sentence-transformers/all-MiniLM-L6-v2"
	tokenizer_name = model_name  # usually the same as model_name

	model = AutoModel.from_pretrained(model_name)
	tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

	embedding = HuggingFaceEmbedding(
		model_name=model_name,
		tokenizer_name=tokenizer_name,
		model=model,
		tokenizer=tokenizer,	
	)
	return embedding


def rag_kb():

	# if "kb_doc" not in st.session_state:
	# 	st.session_state.kb_doc = None
	
	if "k_graph_index" not in st.session_state:
		st.session_state.k_graph_index = None
	# File uploader widget for multiple files
	uploaded_files = st.file_uploader("Upload files", accept_multiple_files=True, type = ['docx', 'txt', 'pdf'])
	if uploaded_files:
	# Check if files were uploaded
		if st.button("Process Knowledge Base"):
			with st.spinner("Processing Knowledge Base..."):
				# Create a temporary directory and ensure it's automatically cleaned up
				with tempfile.TemporaryDirectory() as temp_dir:
					# Process each uploaded file
					for uploaded_file in uploaded_files:
						# Read bytes data from the uploaded file
						bytes_data = uploaded_file.getvalue()
						
						# Construct a file path in the temporary directory
						temp_file_path = os.path.join(temp_dir, uploaded_file.name)
						
						# Write bytes data to a new file in the temp directory
						with open(temp_file_path, 'wb') as temp_file:
							temp_file.write(bytes_data)
					
					reader = SimpleDirectoryReader(input_dir=temp_dir)
					document= reader.load_data()
						# Display the file path and name in Streamlit
					#st.write(f"File saved to temporary directory: {temp_file_path}")

					if document is not None:
						openai.api_key = return_openai_key()
						os.environ["OPENAI_API_KEY"] = return_openai_key()
						from llama_index.llms.openai import OpenAI
						llm3 = OpenAI(temperature=0.1, model="gpt-3.5-turbo-1106")

						service_context = ServiceContext.from_defaults(
							llm=llm3, 
							embed_model=embedding_function(),
							chunk_size=512,
							chunk_overlap=128
						)
						graph_store = SimpleGraphStore()
						storage_context = StorageContext.from_defaults(graph_store=graph_store)

						st.session_state.k_graph_index = KnowledgeGraphIndex.from_documents(
							document,
							max_triplets_per_chunk=3, #need to check this
							storage_context=storage_context,
							service_context=service_context,
							show_progress=True,
							include_embeddings=True
						)
						st.success("Knowledge Base processed successfully.")
						st.rerun()
	
def networkx_graph():
	if "k_graph_index" not in st.session_state:
		st.session_state.k_graph_index = None

	if st.session_state.k_graph_index is not None:
		g = st.session_state.k_graph_index.get_networkx_graph()
		net = Network(notebook=True, cdn_resources="in_line", directed=True, bgcolor="#222222", font_color="white")
		#net.toggle_physics(True)
		net.from_nx(g)
		#net.show_buttons(filter_=['nodes'])
		
		# Create a temporary file to save the graph HTML
		with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode='w+', encoding='utf-8') as tmpfile:
			net.show(tmpfile.name)
			tmpfile.seek(0)  # Go to the beginning of the file
			source_code = tmpfile.read()  # Read the content of the file
			components.html(source_code, height=360, width=650)

			

def query_graph():
	if "k_graph_index" not in st.session_state:
		st.session_state.k_graph_index = None

	if st.session_state.k_graph_index is not None:
		query_engine = st.session_state.k_graph_index.as_query_engine(
		include_text=True,
		response_mode="tree_summarize",
		embedding_mode="hybrid",
		similarity_top_k=5,
	)
	
		return query_engine
	else:
		return False