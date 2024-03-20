import openai
from openai import OpenAI
import streamlit as st
from basecode2.authenticate import return_openai_key
import os
import streamlit_antd_components as sac
import configparser
import ast
import pandas as pd
import cohere
import google.generativeai as genai
import json



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

RUBRICS = config_handler.get_config_values('Prompt_Design_Templates', 'RUBRICS')
SUBJECTS = config_handler.get_config_values('menu_lists', 'SUBJECTS_SINGAPORE')
LEVELS = config_handler.get_config_values('menu_lists', 'CLASS_LEVELS_SINGAPORE')

def chatbot_settings():
	temp = st.number_input("Temperature", value=st.session_state.default_temp, min_value=0.0, max_value=1.0, step=0.1)
	presence_penalty = st.number_input("Presence Penalty", value=st.session_state.default_presence_penalty, min_value=-2.0, max_value=2.0, step=0.1)
	frequency_penalty = st.number_input("Frequency Penalty", value=st.session_state.default_frequency_penalty, min_value=-2.0, max_value=2.0, step=0.1)
	top_p = st.number_input("Top P", value=st.session_state.default_top_p, min_value=0.0, max_value=1.0, step=0.1)
	max_tokens = st.number_input("Max Tokens", value=st.session_state.default_max_tokens, min_value=0, max_value=4000, step=10)

	if st.button("Update Chatbot Settings", key = 3):
		st.session_state.default_temp = temp
		st.session_state.default_presence_penalty = presence_penalty
		st.session_state.default_frequency_penalty= frequency_penalty
		st.session_state.default_top_p = top_p
		st.session_state.default_max_tokens = max_tokens

def leniency_settings():
	#lieniency settings low medium high
	leniency = st.selectbox("Select Leniency", ["Low", "Medium", "High"])
	#if st.button("Update Leniency Settings", key = 4):
	if leniency == "Low":
		st.session_state.default_temp = 0.1
		st.session_state.default_presence_penalty = 0.0
		st.session_state.default_frequency_penalty= 0.0
		st.session_state.default_top_p = 0.0
		st.session_state.default_max_tokens = 4000
	elif leniency == "Medium":
		st.session_state.default_temp = 0.2
		st.session_state.default_presence_penalty = 0.0
		st.session_state.default_frequency_penalty= 0.0
		st.session_state.default_top_p = 0.0
		st.session_state.default_max_tokens = 4000
	elif leniency == "High":
		st.session_state.default_temp = 0.3
		st.session_state.default_presence_penalty = 0.0
		st.session_state.default_frequency_penalty= 0.0
		st.session_state.default_top_p = 0.0
		st.session_state.default_max_tokens = 4000

def api_call(full_prompt, model):
	client = OpenAI(
	# defaults to os.environ.get("OPENAI_API_KEY")
	api_key=return_openai_key(),
	)
	openai.api_key = return_openai_key()
	os.environ["OPENAI_API_KEY"] = return_openai_key()
	st.title("Api Call")
	#MODEL = "gpt-3.5-turbo"
	with st.status("Calling the OpenAI API..."):
		response = client.chat.completions.create(
			model=model,
			messages=[
				{"role": "user", "content": full_prompt},
			],
			temperature=st.session_state.default_temp, #settings option
			presence_penalty=st.session_state.default_presence_penalty, #settings option
			frequency_penalty=st.session_state.default_frequency_penalty, #settings option
			top_p = st.session_state.default_top_p, #settings option
		)
		st.markdown("**This is the extracted response:**")
		st.write(response.choices[0].message.content)
		completion_tokens = response.usage.completion_tokens
		prompt_tokens = response.usage.prompt_tokens
		total_tokens = response.usage.total_tokens

		st.write(f"Completion Tokens: {completion_tokens}")
		st.write(f"Prompt Tokens: {prompt_tokens}")
		st.write(f"Total Tokens: {total_tokens}")

def api_batch_call(full_prompt, model):
	openai.api_key = return_openai_key()
	os.environ["OPENAI_API_KEY"] = return_openai_key()
	#st.title("Api Call")
	#MODEL = "gpt-3.5-turbo"
	client = OpenAI(
	# defaults to os.environ.get("OPENAI_API_KEY")
	api_key=return_openai_key(),
	)
	response = client.chat.completions.create(
		model=model,
		messages=[
			{"role": "user", "content": full_prompt},
		],
		temperature=st.session_state.default_temp, #settings option
		presence_penalty=st.session_state.default_presence_penalty, #settings option
		frequency_penalty=st.session_state.default_frequency_penalty, #settings option
		top_p = st.session_state.default_top_p, #settings option
	)
	#st.markdown("**This is the extracted response:**")
	completion_tokens = prompt_tokens = total_tokens = 0

	response_str = response.choices[0].message.content
		# Check for token counts
	if hasattr(response.usage, 'completion_tokens'):
		completion_tokens = response.usage.completion_tokens
	if hasattr(response.usage, 'prompt_tokens'):
		prompt_tokens = response.usage.prompt_tokens
	if hasattr(response.usage, 'total_tokens'):
		total_tokens = response.usage.total_tokens
	
	return response_str, completion_tokens, prompt_tokens, total_tokens


def parse_json_rubrics_data(data):
	# Assuming data is an instance of ChatCompletion with an attribute 'choices' that is a list
	try:
		for choice in getattr(data, 'choices', []):
			# Assuming message is an attribute of choice which is an instance with an attribute 'tool_calls'
			for tool_call in getattr(choice.message, 'tool_calls', []):
				# Assuming function is an attribute of tool_call which is an instance with an attribute 'name'
				if getattr(tool_call.function, 'name', '') == 'get_marks_feedback_and_rubrics':
					# Now, assuming arguments is a JSON string stored in an attribute of function
					arguments = json.loads(getattr(tool_call.function, 'arguments', '{}'))
					marks = arguments.get('marks')
					feedback = arguments.get('feedback')
					rubrics = arguments.get('rubrics')
					return marks, feedback, rubrics
	except:
		st.error("No information available to display.")
		return None, None, None



def parse_json_data(data):
	try:
		# Navigate through the nested structure to find the relevant information
		for choice in getattr(data, 'choices', []):
			for tool_call in getattr(choice.message, 'tool_calls', []):
				function = getattr(tool_call, 'function', {})
				if getattr(function, 'name', '') == 'get_marks_feedback_and_rubrics':
					# Parsing the 'arguments' attribute from the function
					arguments = json.loads(getattr(function, 'arguments', '{}'))
					marks = arguments.get('marks')
					feedback = arguments.get('feedback')
					return marks, feedback

		# Return None if the required information is not found
		return None, None
	except json.JSONDecodeError:
		st.error("Invalid JSON format.")
		return None, None
	except Exception as e:
		st.error(f"An error occurred: {e}")
		return None, None

def api_call_json(full_prompt, model, tools, rubrics):
	client = OpenAI(
	# defaults to os.environ.get("OPENAI_API_KEY")
	api_key=return_openai_key(),
	)
	openai.api_key = return_openai_key()
	os.environ["OPENAI_API_KEY"] = return_openai_key()
	st.title("Api Call with JSON")
	#MODEL = "gpt-3.5-turbo"
	with st.status("Calling the OpenAI API..."):
		response = client.chat.completions.create(
			model=model,
			messages=[
			#{"role": "system", "content": "You are a helpful assistant designed to output JSON."}, #system prompt
			{"role": "user", "content": full_prompt},
			],
			#response_format={ "type": "json_object" }, #response format
			tools = tools,
			tool_choice = {"type": "function", "function": {"name": "get_marks_feedback_and_rubrics"}},
			temperature=st.session_state.default_temp, #settings option
			presence_penalty=st.session_state.default_presence_penalty, #settings option
			frequency_penalty=st.session_state.default_frequency_penalty, #settings option
			top_p = st.session_state.default_top_p, #settings option
			max_tokens=st.session_state.default_max_tokens, #settings option
		)
		st.markdown("**This is the extracted response:**")
		st.write(response)

		if rubrics != None:
			marks, feedback, rubrics = parse_json_rubrics_data(response)
			if marks is not None and feedback is not None and rubrics is not None:
				
				c1, c2, c3 = st.columns(2,1,3)
				
				with c1:
					st.subheader('Feedback')
					st.write(feedback)
				
				with c2:
					st.subheader('Marks')
					st.write(marks)

				with c3:
					st.subheader('Rubrics Feedback')
					d1, d2, d3 = st.columns([1,1,4])
					for rubric in rubrics:
						with d1:
							st.write(f"Dimension: {rubric['dimension']}")
						with d2:	
							st.write(f"Marks: {rubric['marks']}")
						with d3:
							st.write(f"Feedback: {rubric['feedback']}")
			else:
				st.write('No data available to display.')
		else: #no rubrics
			marks, feedback = parse_json_data(response)
			if marks is not None and feedback is not None:
				e1, e2 = st.columns([1,3])
				with e1:
					st.subheader('Marks')
					st.write(marks)
				with e2:
					st.subheader('Feedback')
					st.write(feedback)
				pass

		completion_tokens = response.usage.completion_tokens
		prompt_tokens = response.usage.prompt_tokens
		total_tokens = response.usage.total_tokens
		st.divider()
		st.write(f"Completion Tokens: {completion_tokens}")
		st.write(f"Prompt Tokens: {prompt_tokens}")
		st.write(f"Total Tokens: {total_tokens}")


def api_batch_call_json(full_prompt, model, tools, rubrics):
	openai.api_key = return_openai_key()
	os.environ["OPENAI_API_KEY"] = return_openai_key()
	#st.title("Api Call with JSON")
	client = OpenAI(
	# defaults to os.environ.get("OPENAI_API_KEY")
	api_key=return_openai_key(),
	)
	response = client.chat.completions.create(
		model=model,
		messages=[
			#{"role": "system", "content": "You are a helpful assistant designed to output JSON."}, #system prompt
			{"role": "user", "content": full_prompt},
		],
		#response_format={ "type": "json_object" }, #response format
		tools=tools,
		tool_choice={"type": "function", "function": {"name": "get_marks_feedback_and_rubrics"}},
		temperature=st.session_state.default_temp,
		presence_penalty=st.session_state.default_presence_penalty,
		frequency_penalty=st.session_state.default_frequency_penalty,
		top_p=st.session_state.default_top_p,
		max_tokens=st.session_state.default_max_tokens,
	)

	# Initialize variables with NA or None
	marks = feedback = extracted_rubrics = 'NA'
	completion_tokens = prompt_tokens = total_tokens = 0

	# Extract response data
	if response:  # Check if response is valid
		if rubrics is not None:
			marks, feedback, extracted_rubrics = parse_json_rubrics_data(response)
		else:
			marks, feedback = parse_json_data(response)
		
		# Ensure extracted_rubrics is always a list
		# if not isinstance(extracted_rubrics, list):
		# 	extracted_rubrics = [extracted_rubrics] if extracted_rubrics else []  

		# Check for token counts
		if hasattr(response.usage, 'completion_tokens'):
			completion_tokens = response.usage.completion_tokens
		if hasattr(response.usage, 'prompt_tokens'):
			prompt_tokens = response.usage.prompt_tokens
		if hasattr(response.usage, 'total_tokens'):
			total_tokens = response.usage.total_tokens
	
	response_str = str(response)

	return response_str, marks, feedback, extracted_rubrics, completion_tokens, prompt_tokens, total_tokens

def prompt_template(prompt_design, level, subject, question, suggested_answer, student_answer, final_rubrics, total_marks): #without rubrics
	variables = {"Model answer": suggested_answer, "Question":question, "Student's response": student_answer, "Marks": total_marks}
	if final_rubrics is not None:
		variables["Rubrics"] = final_rubrics
	if level != "":
		variables["Level"] = level
	if subject != "":
		variables["Subject"] = subject
	return prompt_design.format(**variables)


def short_answer(json_call):
	final_rubrics = None
	question = None
	suggested_answer = None
	total_marks = None
	student_answer = None
	

	level = st.selectbox("Enter your Level:", options=LEVELS, index=st.session_state.level)
	subject = st.selectbox("Enter your Subject:", options=SUBJECTS, index=st.session_state.subject)
	question = st.text_input("Enter your Question:", value=st.session_state.question_prompt, max_chars=250)
	suggested_answer = st.text_area("Enter your Suggested Answer:", value=st.session_state.suggested_answer_prompt, max_chars=2000, height=200)
	if st.checkbox("Rubrics"):
		# calling the rubrics function
		#rubrics = """\nDimension: Grammar – 3 to 5 – Grammar does not have mistakes or minor mistakes, Maximum mark for this dimension: 5. Id for this dimension: 21056.\nDimension: Completeness – 3 to 4 – Answer has expressed details, Maximum mark for this dimension: 4. Id for this dimension: 21057.\n\n"""
		st.session_state.rubrics_prompt = create_rubric_interface()			
		final_rubrics = st.text_area("Enter your rubrics:", value=st.session_state.rubrics_prompt, max_chars=2000, height=300)
	total_marks = st.number_input("Enter the total marks for this question:", value=2, max_value=100, step=1)
	student_answer = st.text_area("Enter your Student's response:", value=st.session_state.student_answer_prompt, max_chars=2000, height=300)
	st.divider()
	if st.button("Clear and reset above text fields"):
		clear_question_cache()
	st.divider()
	# Create a mapping between prompt names and their corresponding session state values
	prompt_options = {
		"Production Prompt": st.session_state.production_prompt,
		"Development Prompt 1": st.session_state.development_prompt_1,
		"Development Prompt 2": st.session_state.development_prompt_2,
		"Development Prompt 3": st.session_state.development_prompt_3,
		"Development Prompt 4": st.session_state.development_prompt_4,
	}

	# Let the user select a prompt by name
	selected_prompt_name = st.selectbox("Select your prompt design:", tuple(prompt_options.keys()))

	# Set the select_prompt to the corresponding session state value based on the selected name
	select_prompt = prompt_options[selected_prompt_name]

	# Display the selected prompt
	st.markdown(select_prompt, unsafe_allow_html=True)
	# select_prompt = st.selectbox("Select your prompt design:", (st.session_state.production_prompt, st.session_state.development_prompt_1, st.session_state.development_prompt_2, st.session_state.development_prompt_3, st.session_state.development_prompt_4, ))
	# st.write(select_prompt)
	st.divider()
	st.write("Preview of your content prompt:")
	
	if question and suggested_answer and total_marks:
		complete_prompt = prompt_template(select_prompt, level, subject, question, suggested_answer, student_answer, final_rubrics, total_marks)
		prompt_design = st.text_area("Edit or Enter your prompt design:", value=complete_prompt, max_chars=4000, height=300)
	else:
		st.error("Content prompt cannot be generated without the question, suggested answer, student answer and total marks")

	st.divider()
	st.session_state.j_tools_format = tool_function()

	if json_call:
		if st.button("Submit Content Prompt for JSON call", key = 1):
			if not prompt_design:
				st.error("Content prompt cannot be empty")
				return False
			else:
				st.session_state.level = LEVELS.index(level)
				st.session_state.subject = SUBJECTS.index(subject)
				st.session_state.question_prompt = question
				st.session_state.suggested_answer_prompt = suggested_answer
				st.session_state.rubrics_prompt = final_rubrics
				st.session_state.total_marks_prompt = total_marks
				st.session_state.student_answer_prompt = student_answer
				return final_rubrics, prompt_design
	else:
		if st.button("Submit Content Prompt for API call", key = 2):
			if not prompt_design:
				st.error("Content prompt cannot be empty")
				return False
			else:
				st.session_state.level = LEVELS.index(level)
				st.session_state.subject = SUBJECTS.index(subject)
				st.session_state.question_prompt = question
				st.session_state.suggested_answer_prompt = suggested_answer
				st.session_state.rubrics_prompt = final_rubrics
				st.session_state.total_marks_prompt = total_marks
				st.session_state.student_answer_prompt = student_answer
				return final_rubrics, prompt_design

def batch_call(model, df, json_call):
	st.divider()
	st.subheader("Please select your content prompt:")
	# Create a mapping between prompt names and their corresponding session state values
	prompt_options = {
		"Production Prompt": st.session_state.production_prompt,
		"Development Prompt 1": st.session_state.development_prompt_1,
		"Development Prompt 2": st.session_state.development_prompt_2,
		"Development Prompt 3": st.session_state.development_prompt_3,
		"Development Prompt 4": st.session_state.development_prompt_4,
	}

	# Let the user select a prompt by name
	selected_prompt_name = st.selectbox("Select your prompt design:", tuple(prompt_options.keys()))

	# Set the select_prompt to the corresponding session state value based on the selected name
	select_prompt = prompt_options[selected_prompt_name]

	# Display the selected prompt
	st.write(select_prompt)
	# select_prompt = st.selectbox("Select your prompt design:", (st.session_state.production_prompt, st.session_state.development_prompt_1, st.session_state.development_prompt_2, st.session_state.development_prompt_3, st.session_state.development_prompt_4, ))
	# st.write(select_prompt)
	
	if json_call:
		st.divider()
		st.session_state.j_tools_format = tool_function()
		tools = json.loads(st.session_state.j_tools_format)

	if st.button("Execute Batch Call"):
		with st.status("Batch processing Prompts with OpenAI API..."):
			progress_bar = st.progress(0)
			total_rows = len(df)
			result_rows = []
			for index, row in df.iterrows():
				# Update the progress bar
				progress = (index + 1) / total_rows
				progress_bar.progress(min(progress, 1.0))
				subject = row['subject']
				level = row['level']
				question = row['question']
				suggested_answer = row['suggested_answer']
				student_answer = row['student_answer']
				total_marks = row['total_marks']
				final_rubrics = row['rubrics'] if pd.notna(row['rubrics']) else None

				if question and suggested_answer and total_marks:
					complete_prompt = prompt_template(select_prompt, level, subject, question, suggested_answer, student_answer, final_rubrics, total_marks)

				if json_call:
					if complete_prompt:
				
						#api_call_json(complete_prompt, model, tools, final_rubrics)
						response, marks, feedback, rubrics, completion_tokens, prompt_tokens, total_tokens = api_batch_call_json(complete_prompt, model, tools, final_rubrics)
						rubrics_str = json.dumps(rubrics) if isinstance(rubrics, (list, dict)) else str(rubrics)
						row['generated_response'] = response
						row['generated_feedback'] = feedback
						row['generated_marks'] = marks
						row['rubrics'] = rubrics_str
						row['completion_tokens'] = completion_tokens
						row['prompt_tokens'] = prompt_tokens
						row['total_tokens'] = total_tokens
						# Including session state values in the row
						row['session_temp'] = st.session_state.default_temp
						row['session_presence_penalty'] = st.session_state.default_presence_penalty
						row['session_frequency_penalty'] = st.session_state.default_frequency_penalty
						row['session_top_p'] = st.session_state.default_top_p
						row['session_max_tokens'] = st.session_state.default_max_tokens
						result_rows.append(row)
				else:
					if complete_prompt:
						response_str, completion_tokens, prompt_tokens, total_tokens = api_batch_call(complete_prompt, model)
						row['generated_response'] = response_str
						row['completion_tokens'] = completion_tokens
						row['prompt_tokens'] = prompt_tokens
						row['total_tokens'] = total_tokens
						# Including session state values in the row
						row['session_temp'] = st.session_state.default_temp
						row['session_presence_penalty'] = st.session_state.default_presence_penalty
						row['session_frequency_penalty'] = st.session_state.default_frequency_penalty
						row['session_top_p'] = st.session_state.default_top_p
						row['session_max_tokens'] = st.session_state.default_max_tokens
						result_rows.append(row)
					
			updated_df = pd.DataFrame(result_rows)
			st.session_state.prompt_df = updated_df

def clear_question_cache():
	st.session_state.level = 0
	st.session_state.subject = 0
	st.session_state.question_prompt = "Enter your question"
	st.session_state.suggested_answer_prompt = "Enter your suggested answer"
	st.session_state.rubrics_prompt = RUBRICS
	st.session_state.total_marks_prompt = 0
	st.session_state.student_answer_prompt = "Enter your student's answer"

#main function call for prompt analyser
def prompt_analyser():
	if "level" not in st.session_state:
		st.session_state.level = 0
	if "subject" not in st.session_state:
		st.session_state.subject = 0
	if "question_prompt" not in st.session_state:
		st.session_state.question_prompt = "Enter your question"
	if "suggested_answer_prompt" not in st.session_state:
		st.session_state.suggested_answer_prompt = "Enter your suggested answer"
	if "rubrics_prompt" not in st.session_state:
		st.session_state.rubrics_prompt = RUBRICS
	if "total_marks_prompt" not in st.session_state:
		st.session_state.total_marks_prompt = 2
	if "student_answer_prompt" not in st.session_state:
		st.session_state.student_answer_prompt = "Enter your student's answer"

	options = sac.chip(items=[
									sac.ChipItem(label='Single API call (Text)', icon='body-text'),
									sac.ChipItem(label='Single API call (JSON)', icon='code-slash'),
									sac.ChipItem(label='Mass API call (Text)', icon='body-text'),
									sac.ChipItem(label='Mass API call (JSON)', icon='code-slash'),
								], index=[0],format_func='title', radius='sm', size='sm', align='left', variant='light')
		
		# Assume that `options` returns the label of the selected chip
	selected_option = options  # Update this based on how options are returned from sac.chip
	st.divider()
	a1, a2, a3 = st.columns(3)
	with a1:
		select_model = st.selectbox("Select a model", ["gpt-3.5-turbo-1106", "gpt-4-turbo-preview"])
	with a2:
		leniency_settings()
	with a3:
		pass
	with st.expander("Configure Chatbot parameters"):
		st.warning("This Chabot parameters will overide the leniency settings")
		chatbot_settings()

	if selected_option == 'Single API call (Text)':
		st.subheader(":blue[Single API call (Text)]")
		st.write(":red[Prompt Content creation:]")
		content_prompt = short_answer(False)
		st.divider()
		if content_prompt:
			api_call(content_prompt[1], select_model)
	elif selected_option == 'Single API call (JSON)':
		st.subheader(":blue[Single API call (JSON)]")
		st.write(":red[Prompt Content creation:]")
		content_prompt = short_answer(True)
		if content_prompt:
			st.success("Content prompt generated successfully")
		
		st.divider()
		if content_prompt and st.session_state.j_tools_format:
			tools = json.loads(st.session_state.j_tools_format)
			st.write(content_prompt[0])
			api_call_json(content_prompt[1], select_model, tools, content_prompt[0])
	elif selected_option == 'Mass API call (Text)':
		st.write("Mass API call (Text)")
		st.write(":red[Ensure your CSV file has the following columns: subject, level, question, suggested_answer, student_answer, total_marks, rubrics]")
		if upload_csv():
			if st.button("Cancel Upload"):
				st.session_state.prompt_df = None
			pass_test = check_column_values(st.session_state.prompt_df , ['subject', 'level','question', 'suggested_answer', 'student_answer', 'total_marks', 'rubrics'])
			if not pass_test:
				st.error("Please upload a CSV file with the required columns or modify the dataframe")
			if pass_test:
				batch_call(select_model,st.session_state.prompt_df, False)
				st.data_editor(st.session_state.prompt_df)
	elif selected_option == 'Mass API call (JSON)':
		st.subheader(":blue[Batch API call (JSON)]")
		st.write(":red[Ensure your CSV file has the following columns: question, suggested_answer, student_answer, total_marks, rubrics]")
		st.write(":red[All the cells in all the columns (except rubrics) must have a content or else the row will be dropped]")
		if upload_csv():
			if st.button("Cancel Upload"):
				st.session_state.prompt_df = None
			pass_test = check_column_values(st.session_state.prompt_df , ['subject', 'level','question', 'suggested_answer', 'student_answer', 'total_marks', 'rubrics'])
			if not pass_test:
				st.error("Please upload a CSV file with the required columns or modify the dataframe")
			if pass_test:
				batch_call(select_model,st.session_state.prompt_df, True)
				st.data_editor(st.session_state.prompt_df)

def standardize_rubrics(value):
	# If the value is NaN or None, return an empty list
	if pd.isna(value) or value is None:
		return []
	# If the value is not a list, return it as a single-item list
	elif not isinstance(value, list):
		return [value]
	# If the value is already a list, return it as is
	return value



def tool_function():
	st.write(":red[Functional tools for JSON function calling:]")

	if "j_tools_format" not in st.session_state:
		st.session_state.j_tools_format = st.session_state.tools_format_1

	# Create a mapping between format names and their corresponding session state values
	tools_format_options = {
		"Production Format": st.session_state.tools_format_1,
		"Development Format 1": st.session_state.tools_format_2,
		"Development Format 2": st.session_state.tools_format_3,
	}

	
	# Let the user select a tools format by name
	selected_format_name = st.selectbox("Select your functional tools format: (JSON)", tuple(tools_format_options.keys()))

	# Set the j_tools_format to the corresponding session state value based on the selected name
	j_tools_format = tools_format_options[selected_format_name]

	# Display the selected tools format in a text area for editing
	st.markdown(j_tools_format, unsafe_allow_html=True)
	st.divider()
	return j_tools_format


def create_rubric_interface():
	# Set the starting ID for dimensions
	dimension_id_start = 21000

	# Set the title for the page
	st.title("Rubrics Creator")

	# Initialize a form for the rubric
	with st.container(border=True):
		# Input for the overall title of the rubric
		title = st.text_input("Title")

		# Get the number of dimensions from the user
		number_of_dimensions = st.number_input("Number of Dimensions", min_value=1, value=2, step=1)

		# Initialize an empty list to hold dimension data
		dimensions_data = []

		# Loop to create input fields for each dimension
		for i in range(number_of_dimensions):
			dimension_id = dimension_id_start + i
			with st.expander(f"Dimension {i + 1} Details (ID: {dimension_id})"):
				dimension_criteria = st.text_input(f"Dimension {i + 1} Criteria", key=f"dimension_{i+1}_criteria")
				
				# Initialize variables to handle descriptions and marks
				descriptions = []
				total_marks = 0  # This will be updated but ultimately set to the mark of the last description
				
				# Dynamic input fields for descriptions and their marks
				number_of_descriptions = st.number_input(f"Number of Descriptions for Dimension {i + 1}", min_value=1, value=3, step=1, key=f"dimension_{i+1}_num_descriptions")
				for j in range(number_of_descriptions):
					mark = st.number_input(f"Mark for Description {j + 1} of Dimension {i + 1}", min_value=1, step=1, key=f"dimension_{i+1}_mark_{j+1}")
					description = st.text_area(f"Description for Mark {mark}", key=f"dimension_{i+1}_description_{j+1}")
					descriptions.append(f"up to {mark} – {description}")
					total_marks = mark  # Set total_marks to the current mark, which will end up being the last one's mark

				# Add dimension data to dimensions_data list here (assuming the rest of the code follows)

				
				dimensions_data.append({
					"id": dimension_id,
					"criteria": dimension_criteria,
					"descriptions": descriptions,
					"total_marks": total_marks
				})

		# Button to submit form
		submitted = st.button("Submit Rubric")
		if submitted:
			st.write("Rubric Submitted!")
			# Process and display the input data
			rubrics_output = ""
			for dimension in dimensions_data:
				dimension_output = f"Id for this dimension: {dimension['id']}. Dimension Criteria: {dimension['criteria']} – " + ", ".join(dimension['descriptions']) + f". Maximum mark for this dimension: {dimension['total_marks']}."
				rubrics_output += dimension_output + "\n"
			return rubrics_output


def upload_csv():
	# Upload CSV file using st.file_uploader
	uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
	#st.session_state.prompt_history = []
	if "prompt_df" not in st.session_state:
		st.session_state.prompt_df = None

	if uploaded_file is not None:
		try:
			df = pd.read_csv(uploaded_file)

			# Check if the number of rows is greater than 300
			if len(df) > 300:
				# Truncate the DataFrame to 300 rows
				df = df.head(300)

				# Display a warning
				st.warning("The uploaded CSV file contains more than 300 rows. It has been truncated to the first 300 rows.")

			st.session_state.prompt_df = df

		except Exception as e:
			st.write("There was an error processing the CSV file.")
			st.write(e)

	# Check if the DataFrame exists before calling st.data_editor
	if st.session_state.prompt_df is not None:
		st.session_state.prompt_df.columns = st.session_state.prompt_df.columns.str.lower()
		st.session_state.prompt_df = st.data_editor(st.session_state.prompt_df, num_rows="dynamic", height=500)
		return True
	else:
		return False
	


def check_column_values(df, required_columns):
	 # Convert required columns to lowercase
	required_columns = [col.lower() for col in required_columns]
	
	missing_columns = [col for col in required_columns if col not in df.columns]
	if missing_columns:
		st.error(f"Missing columns: {', '.join(missing_columns)}")
		return False
	else:
		st.session_state.prompt_df = df.dropna(subset=[col for col in required_columns if col != 'rubrics'])
		return True

def call_google_api(full_prompt):
	# Initialize the Cohere client
	genai.configure(api_key = st.secrets["google_key"])

	with st.status("Calling the Google API..."):
		# Call the Cohere API
		
		chat_model = genai.GenerativeModel('gemini-pro')
		response = chat_model.generate_content(full_prompt)
		# Check if the response has the expected structure
		
		st.write(response.text)


def call_cohere_api(full_prompt):
	# Initialize the Cohere client
	co = cohere.Client(st.secrets["cohere_key"])

	with st.status("Calling the Cohere API..."):
		# Call the Cohere API
		response = co.generate(prompt=full_prompt, max_tokens=1000, temperature=st.session_state.default_temp, presence_penalty=st.session_state.default_presence_penalty, frequency_penalty=st.session_state.default_frequency_penalty)
		
		# Check if the response has the expected structure
		if response and response.generations:
			# Extract the text of the first generation
			generation_text = response.generations[0].text

			# Display the raw response (optional)
			st.markdown("**This is the raw response:**")
			st.write(response)

			# Display the extracted response
			st.markdown("**This is the extracted response:**")
			st.write(generation_text)

			# Display token usage information
			# Display token usage information
			if 'meta' in response and 'billed_units' in response['meta']:
				completion_tokens = response['meta']['billed_units']['output_tokens']
				prompt_tokens = response['meta']['billed_units']['input_tokens']
				st.write(f"Completion Tokens: {completion_tokens}")
				st.write(f"Prompt Tokens: {prompt_tokens}")
		else:
			st.error("No response or unexpected response format received from the API.")