
import streamlit as st
import os
from supabase import create_client

# Debug secrets fetch
st.write("Supabase URL from secrets:", st.secrets.get("SUPABASEURL"))
st.write("Supabase KEY from secrets:", st.secrets.get("SUPABASEKEY"))

SUPABASE_URL = st.secrets.get("SUPABASEURL") or os.getenv("SUPABASEURL")
SUPABASE_KEY = st.secrets.get("SUPABASEKEY") or os.getenv("SUPABASEKEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase credentials are missing! Check your secrets.")
else:
    st.success("Supabase credentials found!")
    st.write("SUPABASE_URL:", SUPABASE_URL)
    st.write("SUPABASE_KEY:", SUPABASE_KEY)

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        st.success("Supabase client created successfully!")
    except Exception as e:
        st.error(f"Error creating Supabase client: {e}")

    st.title("Debug Registration Screen")
    st.markdown("### Test registration and inspect errors")

    with st.form("register_form"):
        email = st.text_input("Email")
        full_name = st.text_input("Full name")
        password = st.text_input("Password", type="password")
        password_confirm = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Register (debug)")

        if submitted:
            st.write("Attempting registration with:",{"email":email,"full_name":full_name,"password":password})
            if password != password_confirm:
                st.error("Passwords do not match!")
            elif len(password)< 6:
                st.error("Password must be at least 6 characters!")
            else:
                try:
                    response = supabase.auth.sign_up({"email": email, "password": password, "options": {"data": {"full_name": full_name}}})
                    st.write("Raw response:", response)
                    if hasattr(response, "user") and response.user:
                        st.success("User created! Data:")
                        st.write(response.user)
                    else:
                        st.error("Registration error:")
                        if hasattr(response, "error"):
                            st.write("Error object:", response.error)
                        else:
                            st.write("No error attribute, inspect response above.")
                except Exception as ex:
                    st.error(f"Exception during registration: {ex}")
