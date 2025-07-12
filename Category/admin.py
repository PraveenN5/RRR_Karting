import streamlit as st
import mysql.connector
import hashlib
from datetime import datetime
import pandas as pd
from PIL import Image
import io

# Set page config
st.set_page_config(page_title="Event Admin Portal", page_icon="⚙️", layout="wide")

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

# Hash password for admin authentication
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Admin authentication
def admin_login(username, password):
    # In a real application, you would check against an admin table
    # For this example, we'll use a hardcoded admin (you should change this)
    admin_username = "admin"
    admin_password_hash = hash_password("Admin123!")
    
    if username == admin_username and hash_password(password) == admin_password_hash:
        return True
    return False

# Get all events from database
def get_all_events():
    conn = connect_db()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT 
                event_id, event_short_name, event_name, organiser, 
                start_date, end_date, is_live, is_complete, is_closed,
                location
            FROM Event
            ORDER BY start_date DESC
        """)
        events = cursor.fetchall()
        return events
    except mysql.connector.Error as err:
        st.error(f"Error fetching events: {err}")
        return None
    finally:
        cursor.close()
        conn.close()

# Get event details by ID
def get_event_by_id(event_id):
    conn = connect_db()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Event WHERE event_id = %s", (event_id,))
        event = cursor.fetchone()
        return event
    except mysql.connector.Error as err:
        st.error(f"Error fetching event: {err}")
        return None
    finally:
        cursor.close()
        conn.close()

# Get categories for an event
def get_event_categories(event_id):
    conn = connect_db()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM Category WHERE event_id = %s", (event_id,))
        categories = cursor.fetchall()
        return categories
    except mysql.connector.Error as err:
        st.error(f"Error fetching categories: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

# Update event status
def update_event_status(event_id, status_field, status_value):
    conn = connect_db()
    if not conn:
        return False, "Database connection failed"
    
    cursor = conn.cursor()
    try:
        # Use parameterized query with format for field name
        query = f"UPDATE Event SET {status_field} = %s WHERE event_id = %s"
        cursor.execute(query, (status_value, event_id))
        conn.commit()
        
        # Verify the update
        verify_query = f"SELECT {status_field} FROM Event WHERE event_id = %s"
        cursor.execute(verify_query, (event_id,))
        result = cursor.fetchone()
        
        if result and result[0] == status_value:
            return True, f"Event {status_field} updated successfully"
        else:
            return False, "Update verification failed"
    except mysql.connector.Error as err:
        return False, f"Database error: {err}"
    finally:
        cursor.close()
        conn.close()

# Add a new category to an event
def add_category(event_id, category_name):
    conn = connect_db()
    if not conn:
        return False, "Database connection failed"
    
    cursor = conn.cursor()
    try:
        # Insert new category
        query = "INSERT INTO Category (event_id, category_name) VALUES (%s, %s)"
        cursor.execute(query, (event_id, category_name))
        conn.commit()
        
        return True, f"Category '{category_name}' added successfully"
    except mysql.connector.Error as err:
        return False, f"Database error: {err}"
    finally:
        cursor.close()
        conn.close()

# Delete a category
def delete_category(event_id, category_id):
    conn = connect_db()
    if not conn:
        return False, "Database connection failed"
    
    cursor = conn.cursor()
    try:
        # Delete category
        query = "DELETE FROM Category WHERE event_id = %s AND category_id = %s"
        cursor.execute(query, (event_id, category_id))
        conn.commit()
        
        return True, "Category deleted successfully"
    except mysql.connector.Error as err:
        return False, f"Database error: {err}"
    finally:
        cursor.close()
        conn.close()

# Admin dashboard
def admin_dashboard():
    st.title("Event Administrator Dashboard")
    
    # Get all events
    events = get_all_events()
    if not events:
        st.warning("No events found in the database")
        return
    
    # Convert to DataFrame for better display
    df = pd.DataFrame(events)
    
    # Format boolean columns
    for col in ['is_live', 'is_complete', 'is_closed']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: "Yes" if x == 1 else "No")
    
    # Format date columns
    for col in ['start_date', 'end_date']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x.strftime('%Y-%m-%d') if x else "")
    
    # Display events table
    st.subheader("All Events")
    st.dataframe(df, use_container_width=True)
    
    # Event management section
    st.subheader("Event Management")
    
    # Select event to manage
    event_ids = [event['event_id'] for event in events]
    event_names = [f"{event['event_id']} - {event['event_name']}" for event in events]
    
    selected_event_index = st.selectbox(
        "Select Event to Manage", 
        range(len(event_ids)), 
        format_func=lambda i: event_names[i]
    )
    
    selected_event_id = event_ids[selected_event_index]
    event_details = get_event_by_id(selected_event_id)
    
    if event_details:
        # Display current status
        st.write("### Current Status")
        status_col1, status_col2, status_col3 = st.columns(3)
        
        with status_col1:
            st.metric("Registration Status", "Open" if event_details['is_closed'] == 0 else "Closed")
        
        with status_col2:
            st.metric("Event Status", "Live" if event_details['is_live'] == 1 else "Not Started")
        
        with status_col3:
            st.metric("Completion Status", "Complete" if event_details['is_complete'] == 1 else "Incomplete")
        
        # Action buttons
        st.write("### Actions")
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            # Toggle registration status (is_closed)
            if event_details['is_closed'] == 0:
                if st.button("🛑 Stop Accepting Registrations", key="close_reg"):
                    success, message = update_event_status(selected_event_id, "is_closed", 1)
                    if success:
                        st.success(f"Registrations closed for {event_details['event_name']}")
                        st.rerun()
                    else:
                        st.error(message)
            else:
                if st.button("✅ Reopen Registrations", key="open_reg"):
                    success, message = update_event_status(selected_event_id, "is_closed", 0)
                    if success:
                        st.success(f"Registrations reopened for {event_details['event_name']}")
                        st.rerun()
                    else:
                        st.error(message)
        
        with action_col2:
            # Toggle event live status (is_live)
            if event_details['is_live'] == 0:
                if st.button("🚀 Start Event", key="start_event"):
                    success, message = update_event_status(selected_event_id, "is_live", 1)
                    if success:
                        st.success(f"Event {event_details['event_name']} is now live!")
                        st.rerun()
                    else:
                        st.error(message)
            else:
                if st.button("⏸️ Pause Event", key="pause_event"):
                    success, message = update_event_status(selected_event_id, "is_live", 0)
                    if success:
                        st.success(f"Event {event_details['event_name']} is now paused")
                        st.rerun()
                    else:
                        st.error(message)
        
        with action_col3:
            # Toggle event completion status (is_complete)
            if event_details['is_complete'] == 0:
                if st.button("🏁 Close Event", key="complete_event"):
                    # Set both is_complete and is_closed to 1
                    success1, message1 = update_event_status(selected_event_id, "is_complete", 1)
                    success2, message2 = update_event_status(selected_event_id, "is_closed", 1)
                    
                    if success1 and success2:
                        st.success(f"Event {event_details['event_name']} is now closed and complete")
                        st.rerun()
                    else:
                        st.error(f"Error: {message1}, {message2}")
            else:
                if st.button("🔄 Reopen Event", key="reopen_event"):
                    success, message = update_event_status(selected_event_id, "is_complete", 0)
                    if success:
                        st.success(f"Event {event_details['event_name']} is now reopened")
                        st.rerun()
                    else:
                        st.error(message)
        
        # Category Management
        st.write("### Category Management")
        
        # Display existing categories
        categories = get_event_categories(selected_event_id)
        if categories:
            st.write("#### Existing Categories")
            cat_df = pd.DataFrame(categories)
            st.dataframe(cat_df, use_container_width=True)
            
            # Delete category
            delete_cat_id = st.selectbox(
                "Select Category to Delete",
                options=[cat['category_id'] for cat in categories],
                format_func=lambda x: next((cat['category_name'] for cat in categories if cat['category_id'] == x), "")
            )
            
            if st.button("Delete Selected Category"):
                success, message = delete_category(selected_event_id, delete_cat_id)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        else:
            st.info("No categories defined for this event yet.")
        
        # Add new category
        st.write("#### Add New Category")
        
        # Predefined category options
        category_options = ["1250cc", "1600cc", "Open Class", "SUV"]
        new_category = st.selectbox("Select Category", options=category_options)
        
        if st.button("Add Category"):
            success, message = add_category(selected_event_id, new_category)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
        
        # Display event details
        with st.expander("View Event Details"):
            detail_col1, detail_col2 = st.columns(2)
            
            with detail_col1:
                st.write(f"**Event ID:** {event_details['event_id']}")
                st.write(f"**Event Name:** {event_details['event_name']}")
                st.write(f"**Short Name:** {event_details['event_short_name']}")
                st.write(f"**Organizer:** {event_details['organiser']}")
                st.write(f"**Location:** {event_details['location']}")
                if event_details['map_location']:
                    st.write(f"**Map Location:** {event_details['map_location']}")
            
            with detail_col2:
                st.write(f"**Start Date:** {event_details['start_date']}")
                st.write(f"**End Date:** {event_details['end_date']}")
                st.write(f"**Multi-day Event:** {'Yes' if event_details['is_multi_day'] == 1 else 'No'}")
                if event_details['organiser_website']:
                    st.write(f"**Website:** {event_details['organiser_website']}")
            
            # Display event photo if available
            if event_details['event_photo']:
                st.subheader("Event Photo")
                try:
                    image = Image.open(io.BytesIO(event_details['event_photo']))
                    st.image(image, caption=event_details['event_name'])
                except Exception as e:
                    st.error(f"Error displaying image: {e}")

# Admin login form
def login_form():
    st.title("Event Administrator Login")
    
    with st.form("admin_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if not username or not password:
                st.error("Please enter both username and password")
            elif admin_login(username, password):
                st.session_state.admin_logged_in = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password")

# Create Category table if it doesn't exist
def create_category_table_if_not_exists():
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Category (
            event_id INT,
            category_id INT AUTO_INCREMENT,
            category_name VARCHAR(255) NOT NULL,
            PRIMARY KEY (event_id, category_id),
            FOREIGN KEY (event_id) REFERENCES Event(event_id)
        )
        ''')
        
        conn.commit()
        return True
    except mysql.connector.Error as err:
        st.error(f"Error creating Category table: {err}")
        return False
    finally:
        cursor.close()
        conn.close()

# Main function
def main():
    # Check database connection
    conn = connect_db()
    if not conn:
        st.error("Database connection failed. Please check your connection settings.")
        st.stop()
    conn.close()
    
    # Create Category table if it doesn't exist
    if not create_category_table_if_not_exists():
        st.error("Failed to create or verify Category table. Please check your connection.")
        st.stop()
    
    # Initialize session state
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    
    # Show login or dashboard based on login status
    if st.session_state.admin_logged_in:
        # Logout button in sidebar
        if st.sidebar.button("Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()
        
        admin_dashboard()
    else:
        login_form()

if __name__ == "__main__":
    main()