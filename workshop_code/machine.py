import pandas as pd
import streamlit as st
import os
import zipfile
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.tree import DecisionTreeRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
import cv2
import tempfile
from keras.models import load_model

plt.style.use('bmh')

def machine_learning():
	#choose machine learning or teachable machines
	option = st.selectbox("Choose an option", ["Machine Learning", "Teachable Machines"])
	if option == "Machine Learning":
		machine_learning_section()
	else:
		if st.toggle("Load Default Model"):
			label_file, model_file = load_default_model()
			if label_file is not None and model_file is not None:
				st.write("Default model loaded successfully.")
				load_teachable_machines(label_file, model_file, default=True)
		else:
			
			load_teachable_machines()
	
def machine_learning_section():
	st.title("Machine Learning")
	st.write("In this section, we will explore some machine learning concepts.")
	st.write("Let's start by uploading a dataset.")
	df_btc = upload_csv()
	if df_btc is not None:
		st.write("Great! Now that we have the dataset, let's plot the prices.")
		plot_prices(df_btc)
		st.write("Now, let's prepare the data for training.")
		df_btc_predict, tree, lr, column_name, future_days, X, train = prepare_data_and_train(df_btc)
		if train:
			st.write("Data is ready for training. Let's train the models.")
			st.write("Now, let's plot the predictions.")
			plot_predictions(df_btc_predict, tree, lr, column_name, future_days, X)
			st.write("That's it for the machine learning section!")
	else:
		st.write("Please upload a dataset to continue.")


def upload_csv():
	uploaded_file = st.file_uploader("Choose a file")
	if uploaded_file is not None:
		dataframe = pd.read_csv(uploaded_file)
		if st.checkbox('Pivot Table'):
			dataframe = pd.DataFrame(dataframe.values[::-1], dataframe.index, dataframe.columns)
		edited_df = st.data_editor(dataframe)
		return edited_df


def plot_prices(df_btc):
	title = st.text_input('Enter the title of the plot diagram')
	xlabel = st.text_input('Enter the label of the x-axis', value='Days', key=1)
	ylabel = st.text_input('Enter the label of the y-axis', value='Close Price USD ($)', key=2)
	column_name = st.selectbox("Select the price column:", df_btc.columns)
	st.subheader("Plot Diagram")
	plt.figure(figsize=(16,8))
	plt.title(title, fontsize = 18)
	plt.xlabel(xlabel, fontsize= 18)
	plt.ylabel(ylabel, fontsize = 18)
	plt.plot(df_btc[column_name])
	st.pyplot(plt)
	plt.clf()

def prepare_data_and_train(df_btc_predict):
	column_name = st.selectbox("Select the predictive (e.g., price) column (Warning: float or int only):", df_btc_predict.columns)
	future_days = st.number_input('Enter the number of days to predict', value=25)
	if st.checkbox('Train Test Split'):
		df_btc_predict = df_btc_predict[[column_name]]
		df_btc_predict['Predict'] = df_btc_predict[[column_name]].shift(-future_days)
		
		X = np.array(df_btc_predict.drop(['Predict'], 1))[:-future_days]
		y = np.array(df_btc_predict['Predict'])[:-future_days]
		
		x_train, x_test, y_train, y_test = train_test_split(X, y, test_size = 0.25)
		
		# Train models
		tree = DecisionTreeRegressor().fit(x_train, y_train)
		lr = LinearRegression().fit(x_train, y_train)
		
		return df_btc_predict, tree, lr, column_name, future_days, X, True
	else:
		return None,None,None,None,None,None, False
	
def plot_predictions(df_btc_predict, tree, lr, column_name, future_days, X):
	model_choice = st.selectbox("Select the model to visualize:", ["Linear Regression", "Decision Tree"])
	
	x_future = df_btc_predict.drop(['Predict'], 1)[:-future_days]
	x_future = x_future.tail(future_days)
	x_future = np.array(x_future)
	
	if model_choice == "Linear Regression":
		predictions = lr.predict(x_future)
		title = 'Predictive Linear Regression Model'
		explanation = "Linear Regression models the relationship between two variables by fitting a linear equation to observed data."
	else:
		predictions = tree.predict(x_future)
		title = 'Predictive Tree Decision Model'
		explanation = "A Decision Tree Regressor predicts the target by learning simple decision rules inferred from the training data."
	
	st.write(explanation)
	
	valid = df_btc_predict[X.shape[0]:]
	valid['Predict'] = predictions
	xlabel = st.text_input('Enter the label of the x-axis', value='Days', key=3)
	ylabel = st.text_input('Enter the label of the y-axis', value='Close Price USD ($)', key=4)
	plt.title(title)
	plt.xlabel(xlabel, fontsize=18)
	plt.ylabel(ylabel, fontsize=18)
	plt.plot(df_btc_predict[column_name])
	plt.plot(valid[[column_name, 'Predict']])
	plt.legend(['Train', 'Val', 'Prediction'], loc='lower right')
	st.pyplot(plt)
	plt.clf()
	
def load_default_model():
	st.write("Loading default model...")
	unzip_directory = "workshop_code/samples"
	#sample_model_zip = os.path.join(unzip_directory, 'sample_model.zip')

	#if os.path.exists(sample_model_zip):
		#unzip_file(sample_model_zip, unzip_directory)
	label_file = os.path.join(unzip_directory, 'labels.txt')
	model_file = os.path.join(unzip_directory, 'keras_model.h5')
	return label_file, model_file
	# else:
	# 	st.error("Sample model file not found.")
	# 	return None, None
	
def load_teachable_machines(label_file=None, model_file=None, default=False):
	model = None
	if label_file is not None and model_file is not None:
		#st.write("Model loaded successfully.")
		classes = [x.split(' ')[1].replace('\n', '') for x in open(label_file, 'r').readlines()]
		model = load_model(model_file, compile=False)
	else:
		# Step 1: Streamlit interface for file upload
		uploaded_file = st.file_uploader("Upload a zip file containing labels.txt and keras_model.h5", type="zip")
		label_file_path = None
		model_file_path = None
		# Step 2: Unzip if file uploaded
		if uploaded_file is not None:
			with tempfile.TemporaryDirectory() as tempdir:
				unzip_directory = tempdir
				
				# Unzipping
				unzip_file(uploaded_file, unzip_directory)

				# Determining paths within the temporary directory
				temp_label_file_path = os.path.join(unzip_directory, 'labels.txt')
				temp_model_file_path = os.path.join(unzip_directory, 'keras_model.h5')
				
				# Check if files exist before proceeding
				if os.path.exists(temp_label_file_path) and os.path.exists(temp_model_file_path):
					# Processing must be done within this block
					with open(temp_label_file_path, 'r') as labels:
						classes = [x.split(' ')[1].replace('\n', '') for x in labels.readlines()]
					model = load_model(temp_model_file_path, compile=False)
					
					st.write("Model and labels loaded successfully from uploaded zip.")
	if model is not None:

		#st.write(classes)
		# Continue with the Streamlit interface
		st.title(f'Is it {classes[0]} or {classes[1]}!?')
		img_file_buffer = st.camera_input(f"Take a picture of {classes[0]} or {classes[1]}")

		# Process image and get predictions
		if img_file_buffer is not None:
			bytes_data = img_file_buffer.getvalue()
			cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
			image = cv2.resize(cv2_img, (224, 224), interpolation=cv2.INTER_AREA)
			image = np.asarray(image, dtype=np.float32).reshape(1, 224, 224, 3)
			image = (image / 127.5) - 1
			probabilities = model.predict(image)

			if probabilities[0,0] > 0.8:
				prob = round(probabilities[0,0] * 100,2)
				st.write(f"I'm {prob}% sure that's {classes[0]}!")
			elif probabilities[0,1] > 0.8:
				prob = round(probabilities[0,1] * 100,2)
				st.write(f"I'm {prob}% sure that's {classes[1]}!")
			else:
				st.write("I'm not confident that I know what this is! ")

			st.balloons()
	else:
		st.error("Model and labels not loaded successfully.")

def unzip_file(zip_path, extract_to):
	with zipfile.ZipFile(zip_path, 'r') as zip_ref:
		zip_ref.extractall(extract_to)
