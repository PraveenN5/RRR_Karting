import streamlit as st
import mysql.connector
import hashlib
import os
import re
from datetime import datetime
from PIL import Image
import io
import validators

# Database connection
def connect_db():
    try:
        conn = mysql.connector.connect(
            host="mysql-1f1fce20-pgsbssnk-fae1.e.aivencloud.com",
            port=18570,
            user="avnadmin",
            password="AVNS_Ghcy45yDjyQY0YlA9dM",
            database="defaultdb"
        )
        return conn
    except mysql.connector.Error as err:
        st.error(f"Database connection error: {err}")
        return None

# Create table
def create_table_if_not_exists():
    conn = connect_db()
    if not conn:
        return False

    cursor = conn.cursor()
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Driver (
            driver_id INT PRIMARY KEY,
            driver_name VARCHAR(100) NOT NULL,
            user_name VARCHAR(50) UNIQUE NOT NULL,
            country VARCHAR(50),
            dob DATE,
            insta_id VARCHAR(50),
            website VARCHAR(100),
            password_salt VARCHAR(128) NOT NULL,
            email VARCHAR(100),
            phone_number VARCHAR(20),
            dp LONGBLOB
        )
        ''')
        conn.commit()
        return True
    except mysql.connector.Error as err:
        st.error(f"Error creating table: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

# Check username uniqueness
def is_username_unique(username):
    conn = connect_db()
    if not conn:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM Driver WHERE user_name = %s", (username,))
        return cursor.fetchone()[0] == 0
    finally:
        cursor.close()
        conn.close()

# Hash password (salt not needed)
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Validation functions
def validate_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email)

def validate_phone(phone):
    return re.match(r"^[0-9]{10}$", phone)

def validate_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Include an uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Include a lowercase letter"
    if not re.search(r"\d", password):
        return False, "Include a digit"
    if not re.search(r"[!@#$%^&*]", password):
        return False, "Include a special character"
    return True, "Valid password"

def validate_website(url):
    return validators.url(url) if url else True

# Insert driver
def register_driver(driver_data, profile_pic):
    conn = connect_db()
    if not conn:
        return False, "DB connection failed"

    cursor = conn.cursor()

    dp_data = None
    if profile_pic:
        try:
            image = Image.open(profile_pic)
            buf = io.BytesIO()
            image.save(buf, format="JPEG")
            dp_data = buf.getvalue()
        except Exception as e:
            return False, f"Image processing failed: {e}"

    password_hashed = hash_password(driver_data['password'])

    query = """
    INSERT INTO Driver
    (driver_id, driver_name, user_name, country, dob, insta_id, website,
     password_salt, email, phone_number, dp)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        driver_data['driver_id'], driver_data['driver_name'], driver_data['user_name'],
        driver_data['country'], driver_data['dob'], driver_data['insta_id'],
        driver_data['website'], password_hashed, driver_data['email'],
        driver_data['phone_number'], dp_data
    )

    try:
        cursor.execute(query, values)
        conn.commit()
        return True, "Driver registered successfully"
    except mysql.connector.Error as err:
        return False, f"MySQL error: {err}"
    finally:
        cursor.close()
        conn.close()

# Test DB connection
def test_db_connection():
    try:
        conn = connect_db()
        if conn and conn.is_connected():
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            return True, "DB connection successful"
        return False, "Connection failed"
    except mysql.connector.Error as err:
        return False, f"Error: {err}"

# Main app
def main():
    st.set_page_config("Driver Registration", "🏎️")
    db_ok, db_msg = test_db_connection()
    if not db_ok:
        st.error(db_msg)
        st.stop()
    else:
        st.success(db_msg)

    if not create_table_if_not_exists():
        st.error("Table setup failed.")
        st.stop()

    st.title("🏁 Racing Driver Registration")
    st.write("Fill the form to register.")

    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            driver_id = st.number_input("Driver ID", min_value=1, step=1)
            driver_name = st.text_input("Driver Name")
            user_name = st.text_input("Username")
            country = st.text_input("Country")
            dob = st.date_input("Date of Birth", min_value=datetime(1900, 1, 1))
        with col2:
            insta_id = st.text_input("Instagram ID (optional)")
            website = st.text_input("Website (optional)")
            email = st.text_input("Email")
            phone_number = st.text_input("Phone Number")
            password = st.text_input("Password", type="password")

        profile_pic = st.file_uploader("Profile Picture", type=["jpg", "jpeg", "png"])
        submit = st.form_submit_button("Register")

        if submit:
            errors = []
            if not driver_name:
                errors.append("Driver name required")
            if not user_name or not is_username_unique(user_name):
                errors.append("Username taken or empty")
            valid_pwd, pwd_msg = validate_password(password)
            if not valid_pwd:
                errors.append(pwd_msg)
            if not validate_email(email):
                errors.append("Invalid email")
            if not validate_phone(phone_number):
                errors.append("Phone number must be 10 digits")
            if not validate_website(website):
                errors.append("Invalid website URL")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                data = {
                    'driver_id': driver_id,
                    'driver_name': driver_name,
                    'user_name': user_name,
                    'country': country,
                    'dob': dob,
                    'insta_id': insta_id,
                    'website': website,
                    'password': password,
                    'email': email,
                    'phone_number': phone_number
                }
                with st.spinner("Registering..."):
                    success, msg = register_driver(data, profile_pic)
                if success:
                    st.success(msg)
                    st.balloons()
                    st.subheader("🎉 Registration Summary")
                    st.write(f"**ID:** {driver_id}")
                    st.write(f"**Name:** {driver_name}")
                    st.write(f"**Username:** {user_name}")
                    st.write(f"**DOB:** {dob}")
                    st.write(f"**Email:** {email}")
                    st.write(f"**Phone:** {phone_number}")
                    st.write(f"**Instagram:** {insta_id}")
                    st.write(f"**Website:** {website}")
                else:
                    st.error(msg)

if __name__ == "__main__":
    main()
