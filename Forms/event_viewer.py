import streamlit as st
import mysql.connector
from PIL import Image
import io
from datetime import datetime
import pandas as pd
import base64
from io import BytesIO

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

def get_all_events():
    conn = connect_db()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Only get events that are live and not closed
        query = """
        SELECT * FROM Event 
        WHERE is_live = 1 AND is_closed = 0
        ORDER BY start_date ASC
        """
        cursor.execute(query)
        events = cursor.fetchall()
        return events
    except mysql.connector.Error as err:
        st.error(f"Error fetching events: {err}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_event_by_id(event_id):
    conn = connect_db()
    if not conn:
        return None
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = "SELECT * FROM Event WHERE event_id = %s"
        cursor.execute(query, (event_id,))
        event = cursor.fetchone()
        return event
    except mysql.connector.Error as err:
        st.error(f"Error fetching event: {err}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_image_base64(img_bytes):
    if img_bytes:
        return base64.b64encode(img_bytes).decode()
    return None

def format_date(date_obj):
    if date_obj:
        return date_obj.strftime("%B %d, %Y")
    return "N/A"

def create_event_card(event):
    # Create a card-like display for each event
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if event['event_photo']:
            try:
                image = Image.open(io.BytesIO(event['event_photo']))
                st.image(image, width=200)
            except Exception:
                st.image("https://via.placeholder.com/200x150?text=No+Image", width=200)
        else:
            st.image("https://via.placeholder.com/200x150?text=No+Image", width=200)
    
    with col2:
        st.subheader(event['event_name'])
        
        # Event dates
        if event['is_multi_day'] == 1:
            st.write(f"📅 **{format_date(event['start_date'])} - {format_date(event['end_date'])}**")
        else:
            st.write(f"📅 **{format_date(event['start_date'])}**")
        
        # Location
        if event['location']:
            st.write(f"📍 {event['location']}")
        
        # Organizer
        st.write(f"🏢 Organized by: **{event['organiser']}**")
        
        # Status badges
        status_html = ""
        if event['is_live'] == 1:
            status_html += '<span style="background-color:#28a745; color:white; padding:2px 6px; border-radius:3px; margin-right:5px;">LIVE</span>'
        if event['is_multi_day'] == 1:
            status_html += '<span style="background-color:#17a2b8; color:white; padding:2px 6px; border-radius:3px; margin-right:5px;">MULTI-DAY</span>'
        if event['is_complete'] == 1:
            status_html += '<span style="background-color:#dc3545; color:white; padding:2px 6px; border-radius:3px; margin-right:5px;">COMPLETED</span>'
        
        if status_html:
            st.markdown(status_html, unsafe_allow_html=True)
        
        # View details button
        if st.button(f"View Details 👉", key=f"view_{event['event_id']}"):
            st.session_state.selected_event = event['event_id']
            st.experimental_rerun()

def display_event_details(event):
    # Back button
    if st.button("← Back to Events"):
        st.session_state.selected_event = None
        st.experimental_rerun()
    
    # Event header with image as background
    if event['event_photo']:
        try:
            img_base64 = get_image_base64(event['event_photo'])
            header_html = f"""
            <div style="
                background-image: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), url(data:image/jpeg;base64,{img_base64});
                background-size: cover;
                background-position: center;
                color: white;
                padding: 40px 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                text-align: center;
            ">
                <h1 style="font-size: 2.5rem;">{event['event_name']}</h1>
                <p style="font-size: 1.2rem;">
                    {format_date(event['start_date'])}
                    {f" - {format_date(event['end_date'])}" if event['is_multi_day'] == 1 else ""}
                </p>
            </div>
            """
            st.markdown(header_html, unsafe_allow_html=True)
        except Exception:
            st.title(event['event_name'])
    else:
        st.title(event['event_name'])
    
    # Event details in tabs
    tab1, tab2, tab3 = st.tabs(["Event Details", "Location", "Organizer"])
    
    with tab1:
        st.subheader("Event Information")
        
        # Status indicators
        status_col1, status_col2, status_col3, status_col4 = st.columns(4)
        
        with status_col1:
            st.metric("Status", "Live" if event['is_live'] == 1 else "Not Live")
        
        with status_col2:
            st.metric("Type", "Multi-day" if event['is_multi_day'] == 1 else "Single-day")
        
        with status_col3:
            st.metric("Completed", "Yes" if event['is_complete'] == 1 else "No")
        
        with status_col4:
            st.metric("Closed", "Yes" if event['is_closed'] == 1 else "No")
        
        # Dates
        st.subheader("Event Dates")
        date_col1, date_col2 = st.columns(2)
        
        with date_col1:
            st.info(f"**Start Date:** {format_date(event['start_date'])}")
        
        with date_col2:
            if event['is_multi_day'] == 1:
                st.info(f"**End Date:** {format_date(event['end_date'])}")
        
        # Additional information
        st.subheader("Additional Information")
        st.write(f"**Event ID:** {event['event_id']}")
        st.write(f"**Event Short Name:** {event['event_short_name']}")
    
    with tab2:
        st.subheader("Event Location")
        
        if event['location']:
            st.write(f"**Address:** {event['location']}")
        else:
            st.write("No location information available.")
        
        if event['map_location']:
            st.subheader("Map")
            # If map_location is a Google Maps URL, embed it
            if "google.com/maps" in event['map_location']:
                st.markdown(f"""
                <iframe width="100%" height="450" style="border:0" loading="lazy" allowfullscreen
                src="{event['map_location']}"></iframe>
                """, unsafe_allow_html=True)
            else:
                # Otherwise just display the text
                st.write(event['map_location'])
    
    with tab3:
        st.subheader("Organizer Information")
        
        st.write(f"**Organizer:** {event['organiser']}")
        
        if event['organiser_website']:
            st.write(f"**Website:** [{event['organiser_website']}]({event['organiser_website']})")
        
        # Placeholder for organizer contact
        st.write("For more information, please visit the organizer's website.")
    
    # Registration section
    st.subheader("Driver Registration")
    st.write("Interested in participating in this event? Register now!")
    
    reg_col1, reg_col2 = st.columns(2)
    
    with reg_col1:
        driver_name = st.text_input("Your Name")
        driver_email = st.text_input("Your Email")
    
    with reg_col2:
        driver_phone = st.text_input("Your Phone Number")
        driver_category = st.selectbox("Racing Category", ["Amateur", "Professional", "Semi-Professional"])
    
    if st.button("Register for this Event", type="primary"):
        if driver_name and driver_email and driver_phone:
            # Here you would add code to save the registration to the database
            st.success(f"Thank you {driver_name}! Your registration for {event['event_name']} has been received.")
            st.balloons()
        else:
            st.error("Please fill in all required fields.")

def main():
    st.set_page_config(
        page_title="Racing Events Viewer",
        page_icon="🏎️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton button {
        width: 100%;
    }
    .event-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state for selected event
    if 'selected_event' not in st.session_state:
        st.session_state.selected_event = None
    
    # Sidebar for filtering
    with st.sidebar:
        st.title("Racing Events")
        st.write("Browse upcoming racing events and register to participate.")
        
        st.subheader("Filter Events")
        
        # Date filter
        st.date_input("From Date", datetime.today())
        
        # Location filter
        st.text_input("Location", placeholder="Enter city or venue")
        
        # Event type filter
        st.multiselect("Event Type", ["Single-day", "Multi-day"])
        
        # Apply filters button
        st.button("Apply Filters")
        
        st.divider()
        
        # Information for drivers
        st.info("👨‍💼 Are you an event organizer? [Login here](https://your-organizer-login-url)")
    
    # Main content
    if st.session_state.selected_event is not None:
        # Display detailed view of selected event
        event = get_event_by_id(st.session_state.selected_event)
        if event:
            display_event_details(event)
        else:
            st.error("Event not found.")
            st.session_state.selected_event = None
    else:
        # Display list of events
        st.title("Upcoming Racing Events")
        st.write("Browse and register for upcoming racing events.")
        
        events = get_all_events()
        
        if not events:
            st.info("No upcoming events found. Please check back later.")
        else:
            # Display events in a grid
            for event in events:
                with st.container():
                    st.markdown('<div class="event-card">', unsafe_allow_html=True)
                    create_event_card(event)
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()