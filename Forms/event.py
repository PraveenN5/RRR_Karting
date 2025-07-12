import streamlit as st
import mysql.connector
import hashlib
import os
import re
from datetime import datetime, timedelta
from PIL import Image
import io
import validators

def connect_db():
    try:
        conn = mysql.connector.connect(
            host="mysql-1f1fce20-pgsbssnk-fae1.e.aivencloud.com",
            port=18570,
            user="avnadmin",
            password="",
            database="defaultdb"
        )
        return conn
    except mysql.connector.Error as err:
        st.error(f"Database connection error: {err}")
        return None

def create_event_table_if_not_exists():
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Event (
            event_id INT PRIMARY KEY,
            event_short_name VARCHAR(50) UNIQUE NOT NULL,
            event_cred VARCHAR(100),
            password VARCHAR(128) NOT NULL,
            is_complete TINYINT DEFAULT 0,
            is_closed TINYINT DEFAULT 0,
            is_live TINYINT DEFAULT 0,
            is_multi_day TINYINT DEFAULT 0,
            start_date DATE NOT NULL,
            end_date DATE,
            event_name VARCHAR(100) NOT NULL,
            organiser VARCHAR(100) NOT NULL,
            organiser_website VARCHAR(100),
            location VARCHAR(200),
            map_location VARCHAR(200),
            event_photo LONGBLOB
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

def is_event_short_name_unique(event_short_name):
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        query = "SELECT COUNT(*) FROM Event WHERE event_short_name = %s"
        cursor.execute(query, (event_short_name,))
        count = cursor.fetchone()[0]
        return count == 0
    except mysql.connector.Error as err:
        st.error(f"Error checking event short name: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

def hash_password(password):
    # Simple password hashing
    return hashlib.sha256(password.encode()).hexdigest()

def validate_website(url):
    if not url:  # Website is optional
        return True
    return validators.url(url)

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

def register_event(event_data, event_photo):
    conn = connect_db()
    if not conn:
        return False, "Failed to connect to database"
    
    cursor = conn.cursor()
    
    # Convert event photo to binary data if provided
    photo_data = None
    if event_photo is not None:
        try:
            img = Image.open(event_photo)
            buf = io.BytesIO()
            img.save(buf, format="JPEG")
            photo_data = buf.getvalue()
        except Exception as e:
            return False, f"Error processing image: {e}"
    
    # Hash the password
    password_hash = hash_password(event_data['password'])
    
    query = """
    INSERT INTO Event 
    (event_id, event_short_name, event_cred, password, is_complete, is_closed, 
     is_live, is_multi_day, start_date, end_date, event_name, organiser, 
     organiser_website, location, map_location, event_photo)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    values = (
        event_data['event_id'],
        event_data['event_short_name'],
        event_data['event_cred'],
        password_hash,
        event_data['is_complete'],
        event_data['is_closed'],
        event_data['is_live'],
        event_data['is_multi_day'],
        event_data['start_date'],
        event_data['end_date'],
        event_data['event_name'],
        event_data['organiser'],
        event_data['organiser_website'],
        event_data['location'],
        event_data['map_location'],
        photo_data
    )
    
    try:
        cursor.execute(query, values)
        conn.commit()
        
        # Verify the data was inserted by querying it back
        verify_query = "SELECT event_name FROM Event WHERE event_id = %s"
        cursor.execute(verify_query, (event_data['event_id'],))
        result = cursor.fetchone()
        
        if result and result[0] == event_data['event_name']:
            return True, "Event registered successfully! Data confirmed in database."
        else:
            return False, "Registration appeared to succeed but verification failed."
    except mysql.connector.Error as err:
        return False, f"Database error: {err}"
    finally:
        cursor.close()
        conn.close()

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

def login_event_organizer():
    st.subheader("Event Organizer Login")
    
    login_col1, login_col2 = st.columns(2)
    
    with login_col1:
        login_event_short_name = st.text_input("Event Short Name", key="login_event_short_name")
    
    with login_col2:
        login_password = st.text_input("Password", type="password", key="login_password")
    
    login_button = st.button("Login")
    
    if login_button:
        if not login_event_short_name or not login_password:
            st.error("Please enter both event short name and password")
            return False, None
        
        conn = connect_db()
        if not conn:
            st.error("Failed to connect to database")
            return False, None
        
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Hash the password for comparison
            password_hash = hash_password(login_password)
            
            query = "SELECT * FROM Event WHERE event_short_name = %s AND password = %s"
            cursor.execute(query, (login_event_short_name, password_hash))
            event = cursor.fetchone()
            
            if event:
                st.success(f"Login successful! Welcome to {event['event_name']}")
                return True, event
            else:
                st.error("Invalid event short name or password")
                return False, None
        except mysql.connector.Error as err:
            st.error(f"Database error: {err}")
            return False, None
        finally:
            cursor.close()
            conn.close()
    
    return False, None

def main():
    st.set_page_config(page_title="Event Organizer Portal", page_icon="🎪", layout="wide")
    
    # Test database connection
    db_success, db_message = test_db_connection()
    if not db_success:
        st.error(db_message)
        st.stop()
    
    # Create table if it doesn't exist
    if not create_event_table_if_not_exists():
        st.error("Failed to create or verify database table. Please check your connection.")
        st.stop()
    
    st.title("Event Organizer Portal")
    
    # Create tabs for login and registration
    tab1, tab2 = st.tabs(["Login", "Register New Event"])
    
    with tab1:
        login_success, event_data = login_event_organizer()
        
        if login_success and event_data:
            st.subheader(f"Event Dashboard: {event_data['event_name']}")
            
            # Display event information
            info_col1, info_col2 = st.columns(2)
            
            with info_col1:
                st.write(f"**Event ID:** {event_data['event_id']}")
                st.write(f"**Event Name:** {event_data['event_name']}")
                st.write(f"**Short Name:** {event_data['event_short_name']}")
                st.write(f"**Organizer:** {event_data['organiser']}")
                st.write(f"**Location:** {event_data['location']}")
            
            with info_col2:
                st.write(f"**Start Date:** {event_data['start_date']}")
                st.write(f"**End Date:** {event_data['end_date']}")
                st.write(f"**Status:** {'Live' if event_data['is_live'] else 'Not Live'}")
                st.write(f"**Complete:** {'Yes' if event_data['is_complete'] else 'No'}")
                st.write(f"**Closed:** {'Yes' if event_data['is_closed'] else 'No'}")
            
            # Display event photo if available
            if event_data['event_photo']:
                st.subheader("Event Photo")
                image = Image.open(io.BytesIO(event_data['event_photo']))
                st.image(image, caption=event_data['event_name'])
            
            # Add more dashboard functionality here
            st.subheader("Event Management")
            st.write("Here you can manage your event details, participants, and more.")
            
            # Placeholder for additional functionality
            if st.button("Toggle Event Live Status"):
                st.info("This would toggle the live status of your event (functionality not implemented)")
            
            if st.button("Close Event"):
                st.info("This would mark the event as closed (functionality not implemented)")
    
    with tab2:
        st.subheader("Register New Event")
        st.write("Complete the form below to register a new event.")
        
        with st.form("event_registration_form"):
            # Basic Event Information
            st.write("### Basic Event Information")
            basic_col1, basic_col2 = st.columns(2)
            
            with basic_col1:
                event_id = st.number_input("Event ID", min_value=1, step=1, help="Unique identifier for the event")
                event_short_name = st.text_input("Event Short Name", help="Unique short name for the event (no spaces)")
                event_name = st.text_input("Event Name", help="Full name of the event")
            
            with basic_col2:
                event_cred = st.text_input("Event Credentials", help="Additional credentials for the event (optional)")
                password = st.text_input("Password", type="password", 
                                        help="Must contain uppercase, lowercase, number, and special character")
                
            # Event Dates and Status
            st.write("### Event Dates and Status")
            date_col1, date_col2 = st.columns(2)
            
            with date_col1:
                start_date = st.date_input("Start Date", min_value=datetime.today())
                is_multi_day = st.checkbox("Multi-day Event")
                
                # Only show end date if multi-day is checked
                end_date = None
                if is_multi_day:
                    end_date = st.date_input("End Date", 
                                            min_value=start_date, 
                                            value=start_date + timedelta(days=1))
            
            with date_col2:
                is_live = st.checkbox("Event is Live")
                is_complete = st.checkbox("Event is Complete")
                is_closed = st.checkbox("Event is Closed")
            
            # Organizer Information
            st.write("### Organizer Information")
            org_col1, org_col2 = st.columns(2)
            
            with org_col1:
                organiser = st.text_input("Organizer Name", help="Name of the event organizer")
                organiser_website = st.text_input("Organizer Website", help="Website of the organizer (optional)")
            
            with org_col2:
                location = st.text_input("Event Location", help="Physical location of the event")
                map_location = st.text_input("Map Location", help="Google Maps URL or coordinates (optional)")
            
            # Event Photo
            st.write("### Event Photo")
            event_photo = st.file_uploader("Upload Event Photo", type=["jpg", "jpeg", "png"])
            
            submit_button = st.form_submit_button("Register Event")
            
            if submit_button:
                # Validate inputs
                errors = []
                
                if not event_id:
                    errors.append("Event ID is required")
                
                if not event_short_name:
                    errors.append("Event Short Name is required")
                elif not is_event_short_name_unique(event_short_name):
                    errors.append("Event Short Name is already taken")
                
                if not event_name:
                    errors.append("Event Name is required")
                
                if not organiser:
                    errors.append("Organizer Name is required")
                
                # Password validation
                if not password:
                    errors.append("Password is required")
                else:
                    is_valid_password, password_message = validate_password(password)
                    if not is_valid_password:
                        errors.append(password_message)
                
                # Website validation
                if organiser_website and not validate_website(organiser_website):
                    errors.append("Invalid organizer website URL format")
                
                # Date validation for multi-day events
                if is_multi_day and end_date and end_date < start_date:
                    errors.append("End date must be after start date")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    # Prepare data for registration
                    event_data = {
                        'event_id': event_id,
                        'event_short_name': event_short_name,
                        'event_cred': event_cred,
                        'password': password,
                        'is_complete': 1 if is_complete else 0,
                        'is_closed': 1 if is_closed else 0,
                        'is_live': 1 if is_live else 0,
                        'is_multi_day': 1 if is_multi_day else 0,
                        'start_date': start_date,
                        'end_date': end_date if is_multi_day else start_date,
                        'event_name': event_name,
                        'organiser': organiser,
                        'organiser_website': organiser_website,
                        'location': location,
                        'map_location': map_location
                    }
                    
                    with st.spinner("Registering event..."):
                        success, message = register_event(event_data, event_photo)
                    
                    if success:
                        st.success(message)
                        st.balloons()
                        
                        # Display confirmation of database entry
                        st.info("✅ Your event has been successfully registered in the database!")
                        
                        # Show a summary of the registered information
                        st.subheader("Registration Summary")
                        summary_col1, summary_col2 = st.columns(2)
                        
                        with summary_col1:
                            st.write(f"**Event ID:** {event_id}")
                            st.write(f"**Event Name:** {event_name}")
                            st.write(f"**Short Name:** {event_short_name}")
                            st.write(f"**Start Date:** {start_date}")
                            if is_multi_day:
                                st.write(f"**End Date:** {end_date}")
                            st.write(f"**Organizer:** {organiser}")
                        
                        with summary_col2:
                            st.write(f"**Location:** {location}")
                            if map_location:
                                st.write(f"**Map Location:** {map_location}")
                            if organiser_website:
                                st.write(f"**Website:** {organiser_website}")
                            st.write(f"**Status:** {'Live' if is_live else 'Not Live'}")
                            st.write(f"**Multi-day:** {'Yes' if is_multi_day else 'No'}")
                    else:
                        st.error(message)

if __name__ == "__main__":
    main()