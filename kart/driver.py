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

# Create driver table
def create_driver_table_if_not_exists():
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
            dp LONGBLOB,
            event_id INT,
            FOREIGN KEY (event_id) REFERENCES Event(event_id)
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

# Hash password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Validation functions
def validate_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return re.match(pattern, email) is not None

def validate_phone(phone):
    return re.match(r"^[0-9]{10}$", phone) is not None

def validate_password(password):
    # At least 8 characters
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check for digit
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    # Check for special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"

def validate_website(url):
    if not url:  # Website is optional
        return True
    return validators.url(url)

# Get available events for registration
def get_available_events():
    conn = connect_db()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Get events that are live and not closed or complete
        query = """
        SELECT event_id, event_name 
        FROM Event 
        WHERE is_live = 1 AND is_closed = 0 AND is_complete = 0
        """
        cursor.execute(query)
        events = cursor.fetchall()
        return events
    except mysql.connector.Error as err:
        st.error(f"Error fetching available events: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

# Register driver
def register_driver(driver_data, profile_pic):
    conn = connect_db()
    if not conn:
        return False, "Failed to connect to database"
    
    cursor = conn.cursor()
    
    # Convert profile picture to binary data if provided
    dp_data = None
    if profile_pic is not None:
        try:
            img = Image.open(profile_pic)
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            dp_data = buf.getvalue()
        except Exception as e:
            return False, f"Error processing image: {e}"
    
    # Hash the password
    password_hash = hash_password(driver_data['password'])
    
    query = """
    INSERT INTO Driver 
    (driver_id, driver_name, user_name, country, dob, insta_id, website,
     password_salt, email, phone_number, dp, event_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    values = (
        driver_data['driver_id'],
        driver_data['driver_name'],
        driver_data['user_name'],
        driver_data['country'],
        driver_data['dob'],
        driver_data['insta_id'],
        driver_data['website'],
        password_hash,
        driver_data['email'],
        driver_data['phone_number'],
        dp_data,
        driver_data['event_id']
    )
    
    try:
        cursor.execute(query, values)
        conn.commit()
        
        # Verify the data was inserted by querying it back
        verify_query = "SELECT driver_name FROM Driver WHERE driver_id = %s"
        cursor.execute(verify_query, (driver_data['driver_id'],))
        result = cursor.fetchone()
        
        if result and result[0] == driver_data['driver_name']:
            return True, "Driver registered successfully! Data confirmed in database."
        else:
            return False, "Registration appeared to succeed but verification failed."
    except mysql.connector.Error as err:
        return False, f"Database error: {err}"
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
            return True, "Database connection successful!"
        else:
            return False, "Could not establish database connection."
    except mysql.connector.Error as err:
        return False, f"Database connection error: {err}"

# Login driver
def login_driver():
    st.subheader("Driver Login")
    
    login_col1, login_col2 = st.columns(2)
    
    with login_col1:
        login_username = st.text_input("Username", key="login_username")
    
    with login_col2:
        login_password = st.text_input("Password", type="password", key="login_password")
    
    login_button = st.button("Login")
    
    if login_button:
        if not login_username or not login_password:
            st.error("Please enter both username and password")
            return False, None
        
        conn = connect_db()
        if not conn:
            st.error("Failed to connect to database")
            return False, None
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Hash the password for comparison
            password_hash = hash_password(login_password)
            
            query = """
            SELECT d.*, e.event_name 
            FROM Driver d
            LEFT JOIN Event e ON d.event_id = e.event_id
            WHERE d.user_name = %s AND d.password_salt = %s
            """
            cursor.execute(query, (login_username, password_hash))
            driver = cursor.fetchone()
            
            if driver:
                st.success(f"Login successful! Welcome, {driver['driver_name']}")
                return True, driver
            else:
                st.error("Invalid username or password")
                return False, None
        except mysql.connector.Error as err:
            st.error(f"Database error: {err}")
            return False, None
        finally:
            cursor.close()
            conn.close()
    
    return False, None

# Main app
def main():
    st.set_page_config(page_title="Driver Registration Portal", page_icon="🏎️", layout="wide")
    
    # Test database connection
    db_success, db_message = test_db_connection()
    if not db_success:
        st.error(db_message)
        st.stop()
    
    # Create table if it doesn't exist
    if not create_driver_table_if_not_exists():
        st.error("Failed to create or verify database table. Please check your connection.")
        st.stop()
    
    st.title("Racing Driver Registration Portal")
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register as Driver"])
    
    with tab1:
        login_success, driver_data = login_driver()
        
        if login_success and driver_data:
            st.subheader(f"Driver Dashboard: {driver_data['driver_name']}")
            
            # Display driver information
            info_col1, info_col2 = st.columns(2)
            
            with info_col1:
                st.write(f"**Driver ID:** {driver_data['driver_id']}")
                st.write(f"**Driver Name:** {driver_data['driver_name']}")
                st.write(f"**Username:** {driver_data['user_name']}")
                st.write(f"**Country:** {driver_data['country']}")
                st.write(f"**Date of Birth:** {driver_data['dob']}")
            
            with info_col2:
                st.write(f"**Email:** {driver_data['email']}")
                st.write(f"**Phone:** {driver_data['phone_number']}")
                if driver_data['insta_id']:
                    st.write(f"**Instagram:** {driver_data['insta_id']}")
                if driver_data['website']:
                    st.write(f"**Website:** {driver_data['website']}")
                if driver_data['event_name']:
                    st.write(f"**Registered for Event:** {driver_data['event_name']}")
            
            # Display driver photo if available
            if driver_data['dp']:
                st.subheader("Profile Photo")
                image = Image.open(io.BytesIO(driver_data['dp']))
                st.image(image, caption=driver_data['driver_name'])
    
    with tab2:
        # Get available events
        available_events = get_available_events()
        
        if not available_events:
            st.warning("⚠️ There are no active events available for registration at this time. Please check back later.")
        else:
            st.subheader("Register as a Driver")
            st.write("Complete the form below to register as a racing driver.")
            
            with st.form("driver_registration_form"):
                # Event selection
                st.write("### Event Selection")
                event_options = {event['event_id']: f"{event['event_name']} (ID: {event['event_id']})" for event in available_events}
                selected_event_id = st.selectbox(
                    "Select Event to Register For", 
                    options=list(event_options.keys()),
                    format_func=lambda x: event_options[x]
                )
                
                # Driver Information
                st.write("### Driver Information")
                basic_col1, basic_col2 = st.columns(2)
                
                with basic_col1:
                    driver_id = st.number_input("Driver ID", min_value=1, step=1, help="Unique identifier for the driver")
                    driver_name = st.text_input("Driver Name", help="Your full name")
                    user_name = st.text_input("Username", help="Choose a unique username")
                    country = st.text_input("Country", help="Your country of origin")
                
                with basic_col2:
                    dob = st.date_input("Date of Birth", min_value=datetime(1900, 1, 1), max_value=datetime.today())
                    email = st.text_input("Email", help="Your email address")
                    phone_number = st.text_input("Phone Number", help="Your contact number (exactly 10 digits)")
                    password = st.text_input("Password", type="password", 
                                            help="Must contain uppercase, lowercase, number, and special character")
                
                # Additional Information
                st.write("### Additional Information")
                add_col1, add_col2 = st.columns(2)
                
                with add_col1:
                    insta_id = st.text_input("Instagram ID", help="Your Instagram handle (optional)")
                
                with add_col2:
                    website = st.text_input("Website", help="Your personal website (optional)")
                
                # Profile Photo
                st.write("### Profile Photo")
                profile_pic = st.file_uploader("Upload Profile Photo", type=["jpg", "jpeg", "png"])
                
                submit_button = st.form_submit_button("Register")
                
                if submit_button:
                    # Validate inputs
                    errors = []
                    
                    if not driver_id:
                        errors.append("Driver ID is required")
                    
                    if not driver_name:
                        errors.append("Driver Name is required")
                    
                    if not user_name:
                        errors.append("Username is required")
                    elif not is_username_unique(user_name):
                        errors.append("Username is already taken")
                    
                    if not email:
                        errors.append("Email is required")
                    elif not validate_email(email):
                        errors.append("Invalid email format")
                    
                    if not phone_number:
                        errors.append("Phone number is required")
                    elif not validate_phone(phone_number):
                        errors.append("Phone number must be exactly 10 digits")
                    
                    # Password validation
                    if not password:
                        errors.append("Password is required")
                    else:
                        is_valid_password, password_message = validate_password(password)
                        if not is_valid_password:
                            errors.append(password_message)
                    
                    # Website validation
                    if website and not validate_website(website):
                        errors.append("Invalid website URL format")
                    
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        # Prepare data for registration
                        driver_data = {
                            'driver_id': driver_id,
                            'driver_name': driver_name,
                            'user_name': user_name,
                            'country': country,
                            'dob': dob,
                            'insta_id': insta_id,
                            'website': website,
                            'password': password,
                            'email': email,
                            'phone_number': phone_number,
                            'event_id': selected_event_id
                        }
                        
                        with st.spinner("Registering driver..."):
                            success, message = register_driver(driver_data, profile_pic)
                        
                        if success:
                            st.success(message)
                            st.balloons()
                            
                            # Display confirmation of database entry
                            st.info("✅ Your information has been successfully registered in the database!")
                            
                            # Show a summary of the registered information
                            st.subheader("Registration Summary")
                            summary_col1, summary_col2 = st.columns(2)
                            
                            with summary_col1:
                                st.write(f"**Driver ID:** {driver_id}")
                                st.write(f"**Driver Name:** {driver_name}")
                                st.write(f"**Username:** {user_name}")
                                st.write(f"**Country:** {country}")
                                st.write(f"**Date of Birth:** {dob}")
                            
                            with summary_col2:
                                st.write(f"**Email:** {email}")
                                st.write(f"**Phone:** {phone_number}")
                                if insta_id:
                                    st.write(f"**Instagram:** {insta_id}")
                                if website:
                                    st.write(f"**Website:** {website}")
                                st.write(f"**Event:** {event_options[selected_event_id]}")
                        else:
                            st.error(message)

if __name__ == "__main__":
    main()