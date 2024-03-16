#Password module test code completed
from basecode2.authenticate import hash_password
import streamlit as st


def change_password(username, new_password):
    """Updates the password for the given username in MongoDB."""
    hashed_pw = hash_password(new_password)
    
    # MongoDB update operation
    result = st.session_state.u_collection.update_one(
        {"username": username}, 
        {"$set": {"password": hashed_pw}}
    )
    
    # Update password in session state if the operation was successful
    if result.modified_count > 0:
        st.session_state.user['password'] = hashed_pw
        st.success("Password changed successfully!")
    else:
        st.error("Failed to change the password.")

def password_settings(username):
    # Form to change password
    with st.form(key='change_password_form'):
        st.write("Username: ", username)
        new_password = st.text_input("New Password", type="password", max_chars=16)
        repeat_new_password = st.text_input("Repeat New Password", type="password", max_chars=16)
        submit_button = st.form_submit_button("Change Password")

        # On submit, check if new passwords match and then update the password.
        if submit_button:
            if new_password != repeat_new_password:
                st.error("New password and repeat new password do not match.")
                return False
            else:
                change_password(username, new_password)
                return True