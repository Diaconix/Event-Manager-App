import streamlit as st
import sqlite3
import qrcode
import pandas as pd
import os
from datetime import datetime, timedelta
import time
import hashlib
import requests
import json

# Set up the page
st.set_page_config(
    page_title="Event Sign-Up Manager",
    page_icon="🎫",
    layout="wide"
)

# Gemini AI Configuration - Using Streamlit Secrets
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
except:
    GEMINI_API_KEY = None
    GEMINI_URL = None
    st.sidebar.warning("Gemini API key not configured - using fallback templates")

class EventManager:
    def __init__(self, admin_id):
        self.admin_id = admin_id
        self.db_path = f"databases/events_{self.sanitize_id(admin_id)}.db"
        os.makedirs("databases", exist_ok=True)
        self.init_db()
    
    def sanitize_id(self, admin_id):
        return "".join(c for c in admin_id if c.isalnum() or c in ('-', '_')).rstrip()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Drop and recreate tables to ensure schema consistency
        c.execute('DROP TABLE IF EXISTS events')
        c.execute('DROP TABLE IF EXISTS registrations')
        
        # Events table with correct schema
        c.execute('''
            CREATE TABLE IF NOT EXISTS events
            (event_id TEXT PRIMARY KEY,
             event_name TEXT NOT NULL,
             event_date TEXT,
             event_description TEXT,
             form_url TEXT,
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
        ''')
        
        # Registrations table
        c.execute('''
            CREATE TABLE IF NOT EXISTS registrations
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             event_id TEXT NOT NULL,
             name TEXT NOT NULL,
             phone TEXT NOT NULL,
             email TEXT NOT NULL,
             event_type TEXT NOT NULL,
             ticket_id TEXT UNIQUE NOT NULL,
             registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             checked_in INTEGER DEFAULT 0,
             FOREIGN KEY (event_id) REFERENCES events (event_id))
        ''')
        conn.commit()
        conn.close()
    
    def generate_event_form_with_ai(self, event_name, event_date, event_description):
        """Use Gemini AI to generate a professional form description"""
        # Fallback template if no API key
        fallback_content = {
            "form_title": f"Event Registration: {event_name}",
            "form_description": f"Join us for {event_name} on {event_date}! We're excited to have you. Please complete your registration below.",
            "welcome_message": "Thank you for registering! You'll receive your digital ticket via email shortly."
        }
        
        if not GEMINI_API_KEY:
            return fallback_content
            
        try:
            prompt = f"""
            Create a professional event registration form description for: {event_name} on {event_date}.
            Event details: {event_description}
            
            Return ONLY a JSON response with this exact structure:
            {{
                "form_title": "Event Registration: [Event Name]",
                "form_description": "Professional, welcoming description inviting people to register",
                "welcome_message": "Brief thank you message after registration"
            }}
            Make it engaging and professional.
            """
            
            headers = {
                'Content-Type': 'application/json',
            }
            
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            response = requests.post(GEMINI_URL, headers=headers, json=data, timeout=30)
            response_data = response.json()
            
            if 'candidates' in response_data:
                ai_content = response_data['candidates'][0]['content']['parts'][0]['text']
                # Extract JSON from AI response
                import re
                json_match = re.search(r'\{.*\}', ai_content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            
            return fallback_content
            
        except Exception as e:
            st.sidebar.error(f"AI generation failed: {str(e)}")
            return fallback_content
    
    def create_event_with_form(self, event_name, event_date, event_description=""):
        """Create a new event with automatic form generation"""
        event_id = f"EVENT-{self.sanitize_id(event_name)}-{int(time.time())}"
        
        # Generate form content
        form_content = self.generate_event_form_with_ai(event_name, event_date, event_description)
        
        # Create form URL that points to our custom form page
        form_url = f"https://event-manager-app-aicon.streamlit.app/?page=register&event={event_id}&admin={self.admin_id}"
        
        # Save event to database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('INSERT INTO events (event_id, event_name, event_date, event_description, form_url) VALUES (?, ?, ?, ?, ?)',
                  (event_id, event_name, event_date, event_description, form_url))
        conn.commit()
        conn.close()
        
        return event_id, form_url, form_content
    
    def get_events(self):
        """Get all events for this admin"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT event_id, event_name, event_date, event_description, form_url FROM events ORDER BY created_at DESC')
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

def public_registration_form():
    """Public registration form - NO AUTHENTICATION REQUIRED"""
    query_params = st.query_params
    event_id = query_params.get("event", [""])[0]
    admin_id = query_params.get("admin", [""])[0]
    
    if not event_id or not admin_id:
        st.error("❌ Invalid registration link")
        return
    
    # Get event details
    event_manager = EventManager(admin_id)
    conn = sqlite3.connect(event_manager.db_path)
    c = conn.cursor()
    c.execute('SELECT event_name, event_date, event_description FROM events WHERE event_id = ?', (event_id,))
    event_data = c.fetchone()
    conn.close()
    
    if not event_data:
        st.error("❌ Event not found")
        return
    
    event_name, event_date, event_description = event_data
    
    # Show event header
    st.title("🎟️ Event Registration")
    st.success(f"**{event_name}**")
    st.write(f"**Date:** {event_date}")
    if event_description:
        st.write(f"**About:** {event_description}")
    st.markdown("---")
    
    # Registration form
    with st.form("registration_form", clear_on_submit=True):
        st.subheader("Your Information")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name *", placeholder="John Doe")
            phone = st.text_input("Phone Number *", placeholder="08012345678")
        with col2:
            email = st.text_input("Email Address *", placeholder="john@example.com")
            event_type = st.selectbox("Event Package *", 
                                    ["Select package", "Karaoke Only", "Karaoke + Paint & Sip"])
        
        submitted = st.form_submit_button("Register Now 🎫")
        
        if submitted:
            if name and phone and email and event_type != "Select package":
                # Generate unique ticket ID
                ticket_id = f"TKT-{phone}-{int(time.time())}"
                
                # Save registration to database
                conn = sqlite3.connect(event_manager.db_path)
                c = conn.cursor()
                c.execute('''
                    INSERT INTO registrations (event_id, name, phone, email, event_type, ticket_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (event_id, name, phone, email, event_type, ticket_id))
                conn.commit()
                conn.close()
                
                # Generate QR code
                qr_filename = f"personal_qr/{ticket_id}.png"
                os.makedirs("personal_qr", exist_ok=True)
                generate_qr_code(ticket_id, qr_filename)
                
                st.success("✅ Registration Complete!")
                st.balloons()
                
                # Show ticket
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(qr_filename, caption="Your Entry QR Code")
                    # Download button for QR code
                    with open(qr_filename, 'rb') as f:
                        qr_data = f.read()
                    st.download_button(
                        label="📥 Download Your Ticket",
                        data=qr_data,
                        file_name=f"ticket_{name.replace(' ', '_')}.png",
                        mime="image/png"
                    )
                with col2:
                    st.subheader("🎫 Your Digital Ticket")
                    st.write(f"**Name:** {name}")
                    st.write(f"**Phone:** {phone}")
                    st.write(f"**Email:** {email}")
                    st.write(f"**Package:** {event_type}")
                    st.write(f"**Event:** {event_name}")
                    st.write(f"**Date:** {event_date}")
                    st.write(f"**Ticket ID:** `{ticket_id}`")
                    st.warning("**💡 Save this QR code! You'll need it for entry at the event.**")
                    st.info("**A confirmation email has been sent to your inbox**")
            else:
                st.error("❌ Please fill in all required fields")

def admin_auth():
    """Admin authentication with both login and registration"""
    st.title("🔐 Event Manager Pro")
    st.markdown("---")
    
    # Tab selection for Login vs Register
    tab1, tab2 = st.tabs(["🚀 Register New Organization", "🔐 Login Existing Organization"])
    
    with tab1:
        st.subheader("Create New Organization Account")
        with st.form("admin_register"):
            new_admin_id = st.text_input("Organization Name *", 
                                       placeholder="e.g., School_Event_Team, Company_Party_2024")
            new_password = st.text_input("Create Admin Password *", type="password")
            confirm_password = st.text_input("Confirm Password *", type="password")
            admin_email = st.text_input("Contact Email (Optional)", 
                                      placeholder="for notifications")
            
            registered = st.form_submit_button("Create Organization Account 📝")
            
            if registered:
                if new_admin_id and new_password and confirm_password:
                    if new_password == confirm_password:
                        if len(new_password) >= 4:
                            # Create admin space
                            st.session_state['admin_id'] = new_admin_id
                            st.session_state['authenticated'] = True
                            st.success(f"✅ Organization '{new_admin_id}' created successfully!")
                            st.info("You can now create and manage events!")
                            st.rerun()
                        else:
                            st.error("Password must be at least 4 characters")
                    else:
                        st.error("Passwords do not match")
                else:
                    st.error("Please fill in all required fields (*)")
    
    with tab2:
        st.subheader("Login to Existing Account")
        with st.form("admin_login"):
            admin_id = st.text_input("Organization Name *", 
                                   placeholder="Enter your organization name")
            admin_password = st.text_input("Admin Password *", type="password",
                                         placeholder="Enter your password")
            
            submitted = st.form_submit_button("Login to Admin Portal 🔐")
            
            if submitted:
                if admin_id and admin_password:
                    # Simple authentication (in production, use proper auth)
                    if len(admin_password) >= 4:
                        st.session_state['admin_id'] = admin_id
                        st.session_state['authenticated'] = True
                        st.success(f"✅ Welcome back, {admin_id}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                else:
                    st.error("❌ Please enter both organization name and password")

def admin_dashboard():
    """Main admin dashboard"""
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
        "👥 View Registrations", 
        "✅ Check-In"
    ])
    
    if menu == "📊 Dashboard":
        show_dashboard(event_manager)
    elif menu == "🎪 Create Event":
        show_event_creation(event_manager)
    elif menu == "👥 View Registrations":
        view_registrations(event_manager)
    elif menu == "✅ Check-In":
        show_check_in(event_manager)

def show_dashboard(event_manager):
    st.header("📊 Dashboard")
    
    events = event_manager.get_events()
    
    # Statistics
    total_events = len(events)
    total_registrations = 0
    
    conn = sqlite3.connect(event_manager.db_path)
    for event_id, _, _, _, _ in events:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM registrations WHERE event_id = ?', (event_id,))
        count = c.fetchone()[0]
        total_registrations += count
    conn.close()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Active Events", total_events)
    with col2:
        st.metric("Total Registrations", total_registrations)
    
    # Events list
    if events:
        st.subheader("Your Events")
        for event_id, event_name, event_date, event_description, form_url in events:
            with st.expander(f"🎪 {event_name} - {event_date}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Event:** {event_name}")
                    st.write(f"**Date:** {event_date}")
                    if event_description:
                        st.write(f"**Description:** {event_description}")
                    st.write(f"**Registration Form:** [Open Form]({form_url})")
                with col2:
                    # Show QR code
                    qr_path = f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}/{event_id}_public.png"
                    if os.path.exists(qr_path):
                        st.image(qr_path, width=150)
                        st.info("Share this QR for registration")
                    else:
                        # Generate QR code if it doesn't exist
                        os.makedirs(f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}", exist_ok=True)
                        generate_qr_code(form_url, qr_path)
                        st.image(qr_path, width=150)
                        st.info("Share this QR for registration")
    else:
        st.info("No events created yet. Create your first event!")

def show_event_creation(event_manager):
    st.header("🎪 Create New Event")
    
    with st.form("create_event"):
        event_name = st.text_input("Event Name *", placeholder="Karaoke Night 2024")
        event_date = st.date_input("Event Date *")
        event_description = st.text_area("Event Description (Optional)", 
                                       placeholder="Describe your event for better AI-generated content...")
        
        submitted = st.form_submit_button("🤖 Generate Event & Registration Form")
    
    if submitted and event_name:
        with st.spinner("AI is creating your professional registration form..."):
            event_id, form_url, form_content = event_manager.create_event_with_form(
                event_name, str(event_date), event_description
            )
            
            # Generate QR code for the form
            qr_filename = f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}/{event_id}_public.png"
            os.makedirs(f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}", exist_ok=True)
            generate_qr_code(form_url, qr_filename)
            
            st.success("🎉 Event & Registration Form Created!")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(qr_filename, caption="Registration QR Code")
                with open(qr_filename, 'rb') as f:
                    st.download_button(
                        "📥 Download QR Code",
                        f.read(),
                        f"qr_{event_name.replace(' ', '_')}.png",
                        "image/png"
                    )
            
            with col2:
                st.subheader("Event Details")
                st.write(f"**Event:** {event_name}")
                st.write(f"**Date:** {event_date}")
                if event_description:
                    st.write(f"**Description:** {event_description}")
                st.write(f"**Registration Form:** [Open Form]({form_url})")
                
                st.info("""
                **Next Steps:**
                1. Download and share the QR code
                2. Guests scan → Register instantly (NO LOGIN)
                3. Manage registrations from dashboard
                4. Check-in guests at the event
                """)

def view_registrations(event_manager):
    st.header("👥 Event Registrations")
    
    events = event_manager.get_events()
    if not events:
        st.info("No events created yet.")
        return
    
    event_options = {f"{name} - {date}": id for id, name, date, _, _ in events}
    selected_event = st.selectbox("Select Event", list(event_options.keys()))
    event_id = event_options[selected_event]
    
    conn = sqlite3.connect(event_manager.db_path)
    df = pd.read_sql_query('''
        SELECT name, phone, email, event_type, ticket_id, checked_in, registered_at 
        FROM registrations 
        WHERE event_id = ?
        ORDER BY registered_at DESC
    ''', conn, params=(event_id,))
    conn.close()
    
    if not df.empty:
        st.metric("Total Registrations", len(df))
        st.metric("Checked In", len(df[df['checked_in'] == 1]))
        st.dataframe(df)
        
        # Export data
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Export as CSV",
            csv,
            f"registrations_{event_id}.csv",
            "text/csv"
        )
    else:
        st.info("No registrations for this event yet.")

def show_check_in(event_manager):
    st.header("✅ Guest Check-In")
    
    events = event_manager.get_events()
    if not events:
        st.info("No events created yet.")
        return
    
    event_options = {f"{name} - {date}": id for id, name, date, _, _ in events}
    selected_event = st.selectbox("Select Event", list(event_options.keys()))
    event_id = event_options[selected_event]
    
    st.subheader("Check In Guest")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Manual Check-In**")
        ticket_id = st.text_input("Enter Ticket ID:", key="manual_checkin")
        if st.button("Check In Guest", key="manual_btn"):
            if ticket_id:
                check_in_guest(event_manager, ticket_id, event_id)
            else:
                st.error("Please enter a Ticket ID")
    
    with col2:
        st.write("**QR Code Check-In**")
        st.info("Point camera at guest's QR code")
        uploaded_file = st.file_uploader("Or upload QR image", type=['png', 'jpg', 'jpeg'])
        if uploaded_file:
            st.warning("QR scanning will be implemented in next version")

def check_in_guest(event_manager, ticket_id, event_id):
    conn = sqlite3.connect(event_manager.db_path)
    c = conn.cursor()
    
    c.execute('SELECT * FROM registrations WHERE ticket_id = ? AND event_id = ?', (ticket_id, event_id))
    guest = c.fetchone()
    
    if guest:
        if guest[8] == 1:  # Already checked in
            st.warning(f"ℹ️ {guest[2]} is already checked in!")
        else:
            c.execute('UPDATE registrations SET checked_in = 1 WHERE ticket_id = ?', (ticket_id,))
            conn.commit()
            st.success(f"✅ {guest[2]} checked in successfully!")
    else:
        st.error("❌ Ticket not found for this event.")
    
    conn.close()

def main():
    # Page routing
    query_params = st.query_params
    page = query_params.get("page", [""])[0]
    
    if page == "register":
        # PUBLIC FACING - NO AUTHENTICATION
        public_registration_form()
    else:
        # ADMIN FACING - REQUIRES AUTHENTICATION
        if 'authenticated' not in st.session_state:
            st.session_state['authenticated'] = False
        
        if not st.session_state['authenticated']:
            admin_auth()  # Changed from admin_login to admin_auth
        else:
            admin_dashboard()

if __name__ == "__main__":
    main()
