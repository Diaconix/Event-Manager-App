import streamlit as st
import sqlite3
import qrcode
import pandas as pd
import os
from datetime import datetime, timedelta
import time
import hashlib

# Set up the page
st.set_page_config(
    page_title="Event Sign-Up Manager",
    page_icon="🎫",
    layout="wide"
)

class EventManager:
    def __init__(self, admin_id):
        self.admin_id = admin_id
        # Each admin gets their own database
        self.db_path = f"databases/events_{self.sanitize_id(admin_id)}.db"
        os.makedirs("databases", exist_ok=True)
        self.init_db()
    
    def sanitize_id(self, admin_id):
        """Sanitize admin ID for filename safety"""
        return "".join(c for c in admin_id if c.isalnum() or c in ('-', '_')).rstrip()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        # Events table
        c.execute('''
            CREATE TABLE IF NOT EXISTS events
            (event_id TEXT PRIMARY KEY,
             event_name TEXT NOT NULL,
             event_date TEXT,
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
        ''')
        # Registrations table
        c.execute('''
            CREATE TABLE IF NOT EXISTS registrations
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             name TEXT NOT NULL,
             phone TEXT NOT NULL,
             event_type TEXT NOT NULL,
             ticket_id TEXT UNIQUE NOT NULL,
             event_id TEXT NOT NULL,
             registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             checked_in INTEGER DEFAULT 0,
             FOREIGN KEY (event_id) REFERENCES events (event_id))
        ''')
        conn.commit()
        conn.close()
    
    def create_event(self, event_name, event_date):
        """Create a new event and generate public registration QR"""
        event_id = f"EVENT-{self.sanitize_id(event_name)}-{int(time.time())}"
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('INSERT INTO events (event_id, event_name, event_date) VALUES (?, ?, ?)',
                  (event_id, event_name, event_date))
        conn.commit()
        conn.close()
        
        # Generate public registration QR code
        registration_url = f"https://event-manager-app-aicon.streamlit.app/?page=register&event={event_id}&admin={self.admin_id}"
        public_qr_filename = f"public_qr/{self.sanitize_id(self.admin_id)}/{event_id}_public.png"
        os.makedirs(f"public_qr/{self.sanitize_id(self.admin_id)}", exist_ok=True)
        generate_qr_code(registration_url, public_qr_filename)
        
        return event_id, public_qr_filename
    
    def get_events(self):
        """Get all events for this admin"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT event_id, event_name, event_date FROM events ORDER BY created_at DESC')
        events = c.fetchall()
        conn.close()
        return events

def generate_qr_code(data, filename):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
    return filename

def admin_login():
    """Secure admin authentication"""
    st.title("🔐 Admin Portal - Event Manager Pro")
    st.markdown("---")
    
    st.subheader("Admin Authentication")
    
    with st.form("admin_login"):
        admin_id = st.text_input("Organization Name *", 
                               placeholder="e.g., School_Event_Team, Company_Party_2024")
        admin_password = st.text_input("Admin Password *", type="password",
                                     placeholder="Enter your admin password")
        
        submitted = st.form_submit_button("Login to Admin Portal 🚀")
        
        if submitted:
            if admin_id and admin_password:
                # Simple password check (in production, use proper auth)
                if len(admin_password) >= 4:  # Basic validation
                    st.session_state['admin_id'] = admin_id
                    st.session_state['authenticated'] = True
                    st.success(f"✅ Welcome back, {admin_id}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
            else:
                st.error("Please enter both organization name and password")
    
    # Admin registration for new users
    st.markdown("---")
    st.subheader("New Organization?")
    with st.form("admin_register"):
        new_admin_id = st.text_input("New Organization Name *")
        new_password = st.text_input("Create Admin Password *", type="password")
        confirm_password = st.text_input("Confirm Password *", type="password")
        admin_email = st.text_input("Contact Email (Optional)")
        
        registered = st.form_submit_button("Register New Organization 📝")
        
        if registered:
            if new_admin_id and new_password and confirm_password:
                if new_password == confirm_password:
                    if len(new_password) >= 4:
                        st.session_state['admin_id'] = new_admin_id
                        st.session_state['authenticated'] = True
                        st.success(f"✅ Organization {new_admin_id} created successfully!")
                        st.rerun()
                    else:
                        st.error("Password must be at least 4 characters")
                else:
                    st.error("Passwords do not match")
            else:
                st.error("Please fill in all required fields")

def admin_dashboard():
    """Main admin dashboard after login"""
    admin_id = st.session_state['admin_id']
    event_manager = EventManager(admin_id)
    
    st.sidebar.title(f"👤 {admin_id}")
    st.sidebar.success("Admin Portal")
    
    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Navigation
    menu = st.sidebar.radio("Navigation", [
        "📊 Dashboard", 
        "🎪 Create Event", 
        "📝 View Registrations", 
        "✅ Check-In", 
        "📤 Export Data"
    ])
    
    if menu == "📊 Dashboard":
        show_dashboard(event_manager)
    elif menu == "🎪 Create Event":
        show_event_creation(event_manager)
    elif menu == "📝 View Registrations":
        view_registrations(event_manager)
    elif menu == "✅ Check-In":
        show_check_in(event_manager)
    elif menu == "📤 Export Data":
        export_data(event_manager)

def show_dashboard(event_manager):
    st.header("📊 Dashboard")
    
    # Quick stats
    conn = sqlite3.connect(event_manager.db_path)
    
    # Get event count
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM events')
    event_count = c.fetchone()[0]
    
    # Get registration count
    c.execute('SELECT COUNT(*) FROM registrations')
    reg_count = c.fetchone()[0]
    
    # Get check-in count
    c.execute('SELECT COUNT(*) FROM registrations WHERE checked_in = 1')
    checkin_count = c.fetchone()[0]
    
    conn.close()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Events", event_count)
    with col2:
        st.metric("Total Registrations", reg_count)
    with col3:
        st.metric("Checked In", checkin_count)
    
    # Recent events
    events = event_manager.get_events()
    if events:
        st.subheader("Your Events")
        for event_id, event_name, event_date in events:
            with st.expander(f"🎪 {event_name} - {event_date}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Event ID:** `{event_id}`")
                    st.write(f"**Date:** {event_date}")
                with col2:
                    # Show registration QR code if exists
                    qr_path = f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}/{event_id}_public.png"
                    if os.path.exists(qr_path):
                        st.image(qr_path, width=150)
    else:
        st.info("No events created yet. Go to 'Create Event' to get started!")

def show_event_creation(event_manager):
    st.header("🎪 Create New Event")
    
    with st.form("create_event"):
        event_name = st.text_input("Event Name *", placeholder="Karaoke Night 2024")
        event_date = st.date_input("Event Date *")
        event_description = st.text_area("Event Description (Optional)")
        
        submitted = st.form_submit_button("Create Event & Generate QR Code 🎫")
    
    if submitted and event_name:
        event_id, qr_filename = event_manager.create_event(event_name, str(event_date))
        
        st.success("🎉 Event Created Successfully!")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(qr_filename, caption="Public Registration QR Code")
            st.info("**Share this QR code for guest registration**")
            
            # Download QR code
            with open(qr_filename, 'rb') as f:
                qr_data = f.read()
            st.download_button(
                label="📥 Download QR Code",
                data=qr_data,
                file_name=f"qr_{event_name.replace(' ', '_')}.png",
                mime="image/png"
            )
        
        with col2:
            st.subheader("Event Details")
            st.write(f"**Event:** {event_name}")
            st.write(f"**Date:** {event_date}")
            if event_description:
                st.write(f"**Description:** {event_description}")
            st.write(f"**Event ID:** `{event_id}`")
            
            st.info("""
            **Next Steps:**
            1. Download and share the QR code
            2. Guests scan to register (NO LOGIN REQUIRED)
            3. Use 'Check-In' during the event
            4. Export data after the event
            """)
            
            # Show the registration URL for testing
            st.subheader("Registration Link")
            registration_url = f"https://event-manager-app-aicon.streamlit.app/?page=register&event={event_id}&admin={event_manager.admin_id}"
            st.markdown(f'[**Click to test registration**]({registration_url})')
            st.code(registration_url)
            st.success("✅ Public registration - NO AUTHENTICATION REQUIRED")

# ... KEEP public_registration, show_check_in, view_registrations, export_data FUNCTIONS EXACTLY AS BEFORE ...

def main():
    # Page routing
    query_params = st.query_params
    page = query_params.get("page", [""])[0]
    
    if page == "register":
        # PUBLIC FACING - NO AUTHENTICATION
        public_registration()
    else:
        # ADMIN FACING - REQUIRES AUTHENTICATION
        if 'authenticated' not in st.session_state:
            st.session_state['authenticated'] = False
        
        if not st.session_state['authenticated']:
            admin_login()
        else:
            admin_dashboard()

if __name__ == "__main__":
    main()

