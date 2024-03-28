#Prompt designs for different applications
from openai import OpenAI
import streamlit as st
from basecode2.authenticate import return_openai_key, return_cohere_key, return_google_key, return_claude_key
import streamlit_antd_components as sac
import configparser
import ast
import cohere
import google.generativeai as genai
import anthropic
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

# Retrieve variables from the 'Prompt_Design_Templates' section
SUMMARY = config_handler.get_config_values('Prompt_Design_Templates', 'SUMMARY')
EXTRACTION = config_handler.get_config_values('Prompt_Design_Templates', 'EXTRACTION')
ANSWER = config_handler.get_config_values('Prompt_Design_Templates', 'ANSWER')
TEXT_CLASSIFICATION = config_handler.get_config_values('Prompt_Design_Templates', 'TEXT_CLASSIFICATION')
CONVERSATION_ROLE = config_handler.get_config_values('Prompt_Design_Templates', 'CONVERSATION_ROLE')
CODE_GENERATION = config_handler.get_config_values('Prompt_Design_Templates', 'CODE_GENERATION')
MATH_FORMULA = config_handler.get_config_values('Prompt_Design_Templates', 'MATH_FORMULA')
DEFAULT_TEXT = config_handler.get_config_values('constants', 'DEFAULT_TEXT')

def prompt_designs_llm():
	st.subheader("Prompt Designs for different applications")
	
	# Define a dictionary mapping options to their corresponding prompt designs
	prompt_designs = {
		'Summarise Content': SUMMARY,
		'Info Extraction': EXTRACTION,
		'Answer in specific format': ANSWER,
		'Text Classification': TEXT_CLASSIFICATION,
		'Conversation Role': CONVERSATION_ROLE,
		'Code Generation': CODE_GENERATION,
		'Math Problem': MATH_FORMULA,
	}

	options = sac.chip(items=[
								sac.ChipItem(label='Summarise Content', icon='body-text'),
								sac.ChipItem(label='Info Extraction', icon='blockquote-left'),
								sac.ChipItem(label='Answer in specific format', icon='question-circle'),
								sac.ChipItem(label='Text Classification', icon='filter'),
								sac.ChipItem(label='Conversation Role', icon='person-circle'),
								sac.ChipItem(label='Code Generation', icon='code-slash'),
								sac.ChipItem(label='Math Problem', icon='calculator'),
								sac.ChipItem(label='COSTAR Prompt Framework', icon='star'),
							], format_func='title', radius='sm', size='sm', align='left', variant='light')
	
	# Assume that `options` returns the label of the selected chip
	selected_option = options  # Update this based on how options are returned from sac.chip
	selected_prompt_design = prompt_designs.get(selected_option, DEFAULT_TEXT)

	if st.checkbox("Configure Chatbot parameters"):
		chatbot_settings()

	if options != 'COSTAR Prompt Framework':
		st.subheader(options)
		prompt_design = st.text_area("Enter your the prompt design for the API call:", value=selected_prompt_design, max_chars=4000, height=300)
		prompt_query = st.text_area("Enter your user input:", value="I want to know about AI in 100 words", max_chars=4000, height=300)
		select_model = st.selectbox("Select a model", ["gpt-3.5-turbo","gpt-4-turbo-preview", "cohere", "gemini-pro","claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"])	
		if st.button("Submit Prompt Design and Query to LLM"):
			if prompt_design and prompt_query:
				# Replace the placeholder with the actual user input
				full_prompt = prompt_design.format(user_input=prompt_query)

				if select_model == "cohere":
					call_cohere_api(full_prompt)
				elif select_model == "gemini-pro":
					call_google_api(full_prompt)
				elif select_model.startswith("claude"):
					claude_bot(full_prompt, select_model)
				else:
					api_call(full_prompt, select_model)
			else:
				st.warning("Please enter a prompt design and user input.")
	else:
		st.subheader(options)
		part1 = costar_prompt_framework()
		
		if st.checkbox("Include Chain of Thought"):
			part2 = chain_of_thought()
			prompt_design = part1 + part2
		else:
			prompt_design = part1
		# select_model = st.selectbox("Select a model", ["gpt-3.5-turbo", "gpt-4-1106-preview", "cohere", "gemini-pro"])
		# prompt_query = st.text_area("Enter your user input:", value="I want to know about AI in 100 words.", max_chars=4000, height=300)	
		if st.button("Submit Prompt Design"):
			if prompt_design:
				# Replace the placeholder with the actual user input
				st.divider()
				st.success("Prompt design template for chatbot")
				st.write(prompt_design)

			else:
				st.warning("Please enter a prompt design")
		

def costar_prompt_framework():
	context = st.text_area("Context (C)", value="You are an educator facilitating a discussion", help="Provide essential background information or setting for the task. This helps the LLM understand the specific scenario or domain it is dealing with, leading to more relevant responses.")
	objective = st.text_area("Objective (O)",value="Your goal is to scaffold understanding by asking the following questions on the topic...", help="Clearly articulate the goal or purpose of the prompt. Specify what you want the LLM to accomplish, ensuring that its focus remains on achieving this particular aim.")
	style = st.text_input("Style (S)",value="professional and clear", help="Define the desired style of the response. This could range from imitating the writing style of a specific profession, like a scientist or journalist, to emulating the narrative tone of certain genres, such as formal reports or creative fiction.")
	tone_voice= st.text_input("Tone (T)", value="friendly", help="Determine the emotional or attitudinal coloring of the response. Whether it’s formal, casual, enthusiastic, or empathetic, setting the tone ensures the LLM's response aligns with the intended sentiment.")
	audience = st.text_input("Audience (A)",value="students", help="Identify the target audience for whom the response is intended. Tailoring the content and complexity of the LLM's response to suit the audience, such as experts, beginners, or a general readership, ensures better comprehension and engagement.")
	response_format = st.text_input("Response Format (R)", value="points or list", help="Specify the format in which you want the response. This could be a list, a structured report, a JSON object, a narrative, etc. Defining the format helps in generating responses that are suitable for your subsequent use, whether it be for analysis, presentation, or further processing.")
	# Construct the output string
	output_string = (f"Context (C): {context}\n\n"
					 f"Objective (O): {objective}\n\n"
					 f"Style (S): {style}\n\n"
					 f"Tone (T): {tone_voice}\n\n"
					 f"Audience (A): {audience}\n\n"
					 f"Response Format (R): {response_format}\n")
	
	return output_string

def chain_of_thought():
	st.subheader("Chain of Thought Approach")

	# Primer Step
	primer_step = st.text_area("Primer Step", value="As a facilitator, your first task is to ask the user for their name, up to two times.")

	# Outline Step
	outline_step = st.text_area("Outline Step", value="Once the name is obtained, proceed to ask the questions about AI in the order listed. Pay attention to the user's responses.")

	# Optimization Step
	optimization_step = st.text_area("Optimization Step", value="Ensure the conversation remains friendly, casual, and informative. If a question seems to perplex the user, offer a brief explanation or example.")

	# Final Step
	final_step = st.text_area("Final Step", value="After discussing all points, thank the user for their input and gracefully end the conversation.")

	 # Construct the output string
	output_string = (f"\n\nChain of Thought Approach\n\n"
					 f"Primer Step: {primer_step}\n\n"
					 f"Outline Step: {outline_step}\n\n"
					 f"Optimization Step: {optimization_step}\n\n"
					 f"Final Step: {final_step}")
	
	return output_string

def call_google_api(full_prompt):
	# Initialize the Cohere client
	genai.configure(api_key = return_google_key())

	with st.status("Calling the Google API..."):
		# Call the Cohere API
		
		chat_model = genai.GenerativeModel('gemini-pro')
		response = chat_model.generate_content(full_prompt)
		# Check if the response has the expected structure
		
		st.write(response.text)


def call_cohere_api(full_prompt):
	# Initialize the Cohere client
	co = cohere.Client(return_cohere_key())

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

def claude_bot(full_prompt, model):
    client = anthropic.Anthropic(api_key=return_claude_key())
    
    response = client.messages.create(
        max_tokens=1024,
        system="Please follow the instructions below:",  
        messages=[
            {"role": "user", "content": full_prompt}
        ],
        model=model,
    )

    # Correcting access method for 'Message' object attributes
    if response:
        # Initialize an empty string to accumulate message text
        message_text = ""
        # Iterate through each content block in the response's content attribute
        for content_block in response.content:
            # Append the text content if the block type is 'text'
            if content_block.type == 'text':
                message_text += content_block.text + "\n"  # Add a newline for readability

        # Display the concatenated message text
        st.write("Message Text:")
        st.write(message_text.strip())
        # Access and display input and output tokens from the 'usage' attribute
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        st.write(f"Input Tokens: {input_tokens}, Output Tokens: {output_tokens}")


def api_call(full_prompt, model):
	client = OpenAI(api_key=return_openai_key())
	st.title("Api Call")
	#MODEL = "gpt-3.5-turbo"
	with st.status("Calling the OpenAI API..."):
		response = client.chat.completions.create(
			model=model,
			messages=[
				{"role": "system", "content": "Please follow the instructions below:"},
				{"role": "user", "content": full_prompt},
			],
			temperature=st.session_state.default_temp, #settings option
			presence_penalty=st.session_state.default_presence_penalty, #settings option
			frequency_penalty=st.session_state.default_frequency_penalty, #settings option
		)
		st.markdown("**This is the extracted response:**")
		st.write(response.choices[0].message.content)
		completion_tokens = response.usage.completion_tokens
		prompt_tokens = response.usage.prompt_tokens
		total_tokens = response.usage.total_tokens

		st.write(f"Completion Tokens: {completion_tokens}")
		st.write(f"Prompt Tokens: {prompt_tokens}")
		st.write(f"Total Tokens: {total_tokens}")

def chatbot_settings():
	default_temp = float(st.session_state.default_temp) if 'default_temp' in st.session_state and st.session_state.default_temp else 0.5
	temp = st.slider("Temp", min_value=0.0, max_value=1.0, value=default_temp, step=0.01)
	presence_penalty = st.number_input("Presence Penalty", value=st.session_state.default_presence_penalty, min_value=-2.0, max_value=2.0, step=0.1)
	frequency_penalty = st.number_input("Frequency Penalty", value=st.session_state.default_frequency_penalty, min_value=-2.0, max_value=2.0, step=0.1)
	if st.button("Update Chatbot Settings", key = 1):
		st.session_state.default_temp = temp
		st.session_state.default_presence_penalty = presence_penalty
		st.session_state.default_frequency_penalty = frequency_penalty