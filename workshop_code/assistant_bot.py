import streamlit as st
from basecode2.authenticate import return_openai_key, return_assistant_id_1
import openai
from openai import OpenAI
import json
import time




#######################################
# PREREQUISITES
#######################################
assistant_id = return_assistant_id_1()
assistant_state = "assistant"
thread_state = "thread"
conversation_state = "conversation"
last_openai_run_state = "last_openai_run"
user_msg_input_key = "input_user_msg"

#######################################
# SESSION STATE SETUP
#######################################
def init_session_state():
	openai.api_key = return_openai_key()

	client = OpenAI(
		# defaults to os.environ.get("OPENAI_API_KEY")
		api_key=return_openai_key(),
	)
	if (assistant_state not in st.session_state) or (thread_state not in st.session_state):
		st.session_state[assistant_state] = client.beta.assistants.retrieve(assistant_id)
		st.session_state[thread_state] = client.beta.threads.create()

	if conversation_state not in st.session_state:
		st.session_state[conversation_state] = []

	if last_openai_run_state not in st.session_state:
		st.session_state[last_openai_run_state] = None
		
	#update the map markers and state
	if "key_points" not in st.session_state:
		st.session_state["key_points"] = {
			"point1": "",
			"point2": "",
			"point3": "",
		}
	if "reflection" not in st.session_state:
		st.session_state["reflection"] = {
			"question1": "",
			"question2": "",
			"question3": "",
		}
	if "learning_plan" not in st.session_state:
		st.session_state["learning_plan"] = {
			"step1": "",
			"step2": "",
			"step3": "",
			"hint": "",
			"feedback": "",
		}


#######################################
# TOOLS SETUP
#######################################

def update_topic_key_points(point1, point2, point3):
	"""Update session state with topic key points."""
	st.session_state["key_points"] = {
		"point1": point1,
		"point2": point2,
		"point3": point3,
	}
	return "Key points updated"

def update_reflection(question1, question2, question3):
	"""Update session state with reflection questions."""
	st.session_state["reflection"] = {
		"question1": question1,
		"question2": question2,
		"question3": question3,
	}
	return "Reflection questions updated"

def update_learning_plan(step1, step2, step3, hint, feedback):
	"""Update session state with a learning plan, including steps, a hint, and feedback."""
	st.session_state["learning_plan"] = {
		"step1": step1,
		"step2": step2,
		"step3": step3,
		"hint": hint,
		"feedback": feedback,
	}
	return "Learning plan updated"


tool_to_function = {
	"update_topic_key_points": update_topic_key_points,
	"update_reflection": update_reflection,
	"update_learning_plan": update_learning_plan,
}

#######################################
# HELPERS
#######################################


def get_assistant_id():
	return st.session_state[assistant_state].id


def get_thread_id():
	return st.session_state[thread_state].id


def get_run_id():
	return st.session_state[last_openai_run_state].id


def on_text_input(status_placeholder):
	"""Callback method for any chat_input value change
	"""
	openai.api_key = return_openai_key()

	client = OpenAI(
		# defaults to os.environ.get("OPENAI_API_KEY")
		api_key=return_openai_key(),
	)
	
	if st.session_state[user_msg_input_key] == "":
		return

	client.beta.threads.messages.create(
		thread_id=get_thread_id(),
		role="user",
		content=st.session_state[user_msg_input_key],
	)
	st.session_state[last_openai_run_state] = client.beta.threads.runs.create(
		assistant_id=get_assistant_id(),
		thread_id=get_thread_id(),
	)
	completed = False

	# Polling
	
	
	with status_placeholder.status("Computing Assistant answer") as status_container:
		st.write(f"Launching run {get_run_id()}")

		while not completed:
			run = client.beta.threads.runs.retrieve(
				thread_id=get_thread_id(),
				run_id=get_run_id(),
			)

			if run.status == "requires_action":
				tools_output = []
				for tool_call in run.required_action.submit_tool_outputs.tool_calls:
					f = tool_call.function
					print(f)
					f_name = f.name
					f_args = json.loads(f.arguments)

					st.write(f"Launching function {f_name} with args {f_args}")
					tool_result = tool_to_function[f_name](**f_args)
					tools_output.append(
						{
							"tool_call_id": tool_call.id,
							"output": tool_result,
						}
					)
				st.write(f"Will submit {tools_output}")
				client.beta.threads.runs.submit_tool_outputs(
					thread_id=get_thread_id(),
					run_id=get_run_id(),
					tool_outputs=tools_output,
				)

			if run.status == "completed":
				st.write(f"Completed run {get_run_id()}")
				status_container.update(label="Assistant is done", state="complete")
				completed = True

			else:
				time.sleep(0.1)

	st.session_state[conversation_state] = [
	    (m.role, m.content[0].text.value)
	    for m in client.beta.threads.messages.list(get_thread_id()).data
	]
	
	# new_messages = client.beta.threads.messages.list(get_thread_id()).data
	
	# # Process and append new messages to st.session_state.msg
	# for m in new_messages:
	# 	st.session_state['msg'].append({
	# 		"role": m.role,
	# 		"content": m.content[0].text.value  # Assuming this is the structure of your message content
	# 	})


def on_reset_thread():
	openai.api_key = return_openai_key()

	client = OpenAI(
		# defaults to os.environ.get("OPENAI_API_KEY")
		api_key=return_openai_key(),
	)
	client.beta.threads.delete(get_thread_id())
	st.session_state[thread_state] = client.beta.threads.create()
	st.session_state[conversation_state] = []
	st.session_state[last_openai_run_state] = None


#######################################
# DEBUG
#######################################
def debug():
	st.header("Debug")
	st.write(st.session_state.to_dict())
	st.button("Reset Thread", on_click=on_reset_thread)

#######################################
# MAIN
#######################################

def assistant_demo():
	left_col, right_col = st.columns(2)
	init_session_state()

	with left_col:
		with st.container(border=True):
			for role, message in st.session_state[conversation_state]:
				with st.chat_message(role):
					st.write(message)
			status_placeholder = st.empty()
			
			st.chat_input(
			placeholder="Ask your question here",
			key=user_msg_input_key,
			on_submit=on_text_input,
			args=(status_placeholder,),
			)
			# assistant_bot(status_placeholder)

	with right_col:
	# Display Topic Key Points
		with st.container(border=True):
			st.write("### :green[Topic Key Points]")
			if "key_points" in st.session_state:
				for key, value in st.session_state["key_points"].items():
					st.write(f"{key}: {value}")
			else:
				st.write("No key points defined.")
		
		# Display Reflection
		with st.container(border=True):
			st.write("#### :red[Reflection]")
			if "reflection" in st.session_state:
				for key, value in st.session_state["reflection"].items():
					st.write(f"{key}: {value}")
			else:
				st.write("No reflection questions defined.")
		
		# Display Learning Plan
		with st.container(border=True):
			st.write("#### :blue[Learning Plan]")
			if "learning_plan" in st.session_state:
				for key, value in st.session_state["learning_plan"].items():
					# Customizing display for learning plan to differentiate steps, hint, and feedback
					if key in ["step1", "step2", "step3"]:
						st.write(f"Step {key[-1]}: {value}")
					else:
						st.write(f"{key.capitalize()}: {value}")
			else:
				st.write("No learning plan defined.")
				
# def assistant_bot(status_placeholder):
	
# 	# Check if 'msg' key exists in session_state, if not initialize it
# 	if 'msg' not in st.session_state:
# 		st.session_state.msg = [
# 			{"role": "assistant", "content": "Greetings!"},  # Example greeting
# 			{"role": "assistant", "content": "How can I help you today?"}  # Example help offer
# 		]

# 	# Displaying messages
# 	messages_container = st.container()
# 	with messages_container:
# 		for message in st.session_state.msg:
# 			with st.chat_message(message["role"]):
# 				st.markdown(message["content"])

# 	# Chat input for new messages
# 	user_input = st.chat_input("Enter your query",  key=user_msg_input_key, on_submit=on_text_input,args=(status_placeholder))
# 	with st.chat_message("user"):
# 		st.markdown(user_input)
