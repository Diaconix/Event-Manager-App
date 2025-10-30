import streamlit as st
import sqlite3
import qrcode
import pandas as pd
import os
from datetime import datetime, timedelta
import time

# Set up the page
st.set_page_config(
    page_title="Event Manager Platform",
    page_icon="🎪",
    layout="wide"
)

# SINGLE DATABASE FILE
DATABASE_PATH = "event_manager.db"

class EventManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                admin_id TEXT NOT NULL,
                event_name TEXT NOT NULL,
                event_date TEXT,
                event_description TEXT,
                collect_name INTEGER DEFAULT 1,
                collect_phone INTEGER DEFAULT 1,
                collect_email INTEGER DEFAULT 1,
                collect_company INTEGER DEFAULT 0,
                collect_dietary INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                admin_id TEXT NOT NULL,
                name TEXT,
                phone TEXT,
                email TEXT,
                company TEXT,
                dietary TEXT,
                event_type TEXT,
                ticket_id TEXT UNIQUE NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                checked_in INTEGER DEFAULT 0,
                FOREIGN KEY (event_id) REFERENCES events (event_id)
            )
        ''')
        conn.commit()
        conn.close()
    
    def create_event(self, admin_id, event_name, event_date, event_description, form_fields):
        event_id = f"EVENT-{event_name.replace(' ', '-')}-{int(time.time())}"
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        sql = '''
            INSERT INTO events 
            (event_id, admin_id, event_name, event_date, event_description, 
             collect_name, collect_phone, collect_email, collect_company, collect_dietary) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        '''
        
        params = (
            event_id, 
            admin_id,
            event_name, 
            event_date, 
            event_description or "",
            form_fields.get('name', 1), 
            form_fields.get('phone', 1), 
            form_fields.get('email', 1), 
            form_fields.get('company', 0),
            form_fields.get('dietary', 0)
        )
        
        c.execute(sql, params)
        conn.commit()
        conn.close()
        
        return event_id
    
    def get_events(self, admin_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT event_id, event_name, event_date, event_description FROM events WHERE admin_id = ? ORDER BY created_at DESC', (admin_id,))
        events = c.fetchall()
        conn.close()
        return events
    
    def get_event_details(self, event_id, admin_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT event_name, event_date, event_description, collect_name, collect_phone, collect_email, collect_company, collect_dietary FROM events WHERE event_id = ? AND admin_id = ?', (event_id, admin_id))
        event_data = c.fetchone()
        conn.close()
        return event_data

def generate_qr_code(data, filename):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
    return filename

# ===== TEST FORM FUNCTION =====
def test_registration_form():
    """TEST MODE: Show the registration form with test data"""
    st.title("🧪 TEST MODE - Registration Form Preview")
    st.warning("This is a TEST preview of how the registration form will look to guests")
    
    # Test event data
    test_event_data = {
        'event_name': 'Karaoke Night 2024',
        'event_date': '2024-12-25',
        'event_description': 'Join us for an amazing night of karaoke and fun!',
        'collect_name': True,
        'collect_phone': True, 
        'collect_email': True,
        'collect_company': True,
        'collect_dietary': True
    }
    
    (event_name, event_date, event_description, 
     collect_name, collect_phone, collect_email, collect_company, collect_dietary) = test_event_data.values()
    
    st.success(f"**{event_name}**")
    st.write(f"**Date:** {event_date}")
    if event_description:
        st.write(f"**About:** {event_description}")
    st.markdown("---")
    
    # Test registration form
    with st.form("test_registration_form"):
        st.subheader("Your Information")
        
        form_data = {}
        
        if collect_name:
            form_data['name'] = st.text_input("Full Name *", placeholder="John Doe", key="test_name")
        
        if collect_phone:
            form_data['phone'] = st.text_input("Phone Number *", placeholder="08012345678", key="test_phone")
        
        if collect_email:
            form_data['email'] = st.text_input("Email Address *", placeholder="john@example.com", key="test_email")
        
        if collect_company:
            form_data['company'] = st.text_input("Company/Organization", placeholder="Your company name", key="test_company")
        
        if collect_dietary:
            form_data['dietary'] = st.text_input("Dietary Preferences", placeholder="Any dietary requirements", key="test_dietary")
        
        form_data['event_type'] = st.selectbox("Event Package *", ["Select package", "Karaoke Only", "Karaoke + Paint & Sip"], key="test_package")
        
        submitted = st.form_submit_button("🧪 Test Registration")
        
        if submitted:
            # Validate required fields
            required_fields = []
            if collect_name and not form_data.get('name'):
                required_fields.append("Full Name")
            if collect_phone and not form_data.get('phone'):
                required_fields.append("Phone Number")
            if collect_email and not form_data.get('email'):
                required_fields.append("Email Address")
            if form_data.get('event_type') == "Select package":
                required_fields.append("Event Package")
            
            if required_fields:
                st.error(f"❌ Please fill in: {', '.join(required_fields)}")
            else:
                st.success("✅ TEST SUCCESSFUL! Form works correctly.")
                st.balloons()
                
                # Show what would happen
                st.info("""
                **In production, this would:**
                - Save registration to database
                - Generate a personal QR ticket
                - Send confirmation email
                - Allow check-in at event
                """)

# ===== SIMPLE GUEST REGISTRATION =====
def show_guest_registration():
    """Simple guest registration that actually works"""
    
    # METHOD 1: Try URL parameters (but don't rely on them)
    query_params = st.query_params
    event_id = query_params.get("event", [""])[0] if query_params.get("event") else ""
    admin_id = query_params.get("admin", [""])[0] if query_params.get("admin") else ""
    
    # METHOD 2: Manual entry fallback
    if not event_id or not admin_id:
        st.title("🎟️ Event Registration")
        st.info("Please enter the event details provided by the organizer")
        
        col1, col2 = st.columns(2)
        with col1:
            event_id = st.text_input("Event Code *", placeholder="EVENT-XXXXX")
        with col2:
            admin_id = st.text_input("Organizer Code *", placeholder="OrganizationName")
        
        if not event_id or not admin_id:
            st.stop()
    
    # Get event details
    event_manager = EventManager()
    event_data = event_manager.get_event_details(event_id, admin_id)
    
    if not event_data:
        st.error("❌ Event not found")
        st.info("""
        Please check:
        - Event code is correct
        - Organizer code is correct  
        - Contact the event organizer if issues persist
        """)
        return
    
    (event_name, event_date, event_description, 
     collect_name, collect_phone, collect_email, collect_company, collect_dietary) = event_data
    
    # Show registration form
    st.title("🎟️ Event Registration")
    st.success(f"**{event_name}**")
    st.write(f"**Date:** {event_date}")
    if event_description:
        st.write(f"**About:** {event_description}")
    st.markdown("---")
    
    with st.form("registration_form"):
        st.subheader("Your Information")
        
        name = st.text_input("Full Name *") if collect_name else None
        phone = st.text_input("Phone Number *") if collect_phone else None
        email = st.text_input("Email Address *") if collect_email else None
        company = st.text_input("Company/Organization") if collect_company else None
        dietary = st.text_input("Dietary Preferences") if collect_dietary else None
        event_type = st.selectbox("Event Package *", ["Select package", "Karaoke Only", "Karaoke + Paint & Sip"])
        
        submitted = st.form_submit_button("Register Now 🎫")
        
        if submitted:
            # Validate
            errors = []
            if collect_name and not name: errors.append("Full Name")
            if collect_phone and not phone: errors.append("Phone Number") 
            if collect_email and not email: errors.append("Email Address")
            if event_type == "Select package": errors.append("Event Package")
            
            if errors:
                st.error(f"Please fill in: {', '.join(errors)}")
            else:
                # Save registration
                ticket_id = f"TKT-{int(time.time())}"
                conn = sqlite3.connect(DATABASE_PATH)
                c = conn.cursor()
                c.execute('''
                    INSERT INTO registrations 
                    (event_id, admin_id, name, phone, email, company, dietary, event_type, ticket_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (event_id, admin_id, name, phone, email, company, dietary, event_type, ticket_id))
                conn.commit()
                conn.close()
                
                st.success("✅ Registration Complete!")
                
                # Generate ticket
                qr_filename = f"personal_qr/{ticket_id}.png"
                os.makedirs("personal_qr", exist_ok=True)
                generate_qr_code(ticket_id, qr_filename)
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(qr_filename, caption="Your Entry QR Code")
                with col2:
                    st.subheader("🎫 Your Ticket")
                    if name: st.write(f"**Name:** {name}")
                    if phone: st.write(f"**Phone:** {phone}")
                    st.write(f"**Event:** {event_name}")
                    st.write(f"**Ticket ID:** {ticket_id}")
                    st.warning("Save this QR code for event entry!")

# ===== SIMPLE ADMIN INTERFACE =====
def admin_auth():
    st.title("🎪 Event Manager")
    
    tab1, tab2 = st.tabs(["🚀 Register", "🔐 Login"])
    
    with tab1:
        admin_id = st.text_input("Organization Name")
        password = st.text_input("Password", type="password")
        if st.button("Create Account"):
            if admin_id:
                st.session_state.admin_id = admin_id
                st.session_state.authenticated = True
                st.success("Account created!")
                st.rerun()
    
    with tab2:
        admin_id = st.text_input("Organization Name", key="login")
        password = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login"):
            if admin_id:
                st.session_state.admin_id = admin_id
                st.session_state.authenticated = True
                st.success("Logged in!")
                st.rerun()

def admin_dashboard():
    admin_id = st.session_state.admin_id
    event_manager = EventManager()
    
    st.sidebar.title(f"👤 {admin_id}")
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    menu = st.sidebar.radio("Menu", ["📊 Dashboard", "🎪 Create Event", "👥 Registrations", "🧪 Test Form"])
    
    if menu == "📊 Dashboard":
        show_dashboard(event_manager, admin_id)
    elif menu == "🎪 Create Event":
        show_event_creation(event_manager, admin_id)
    elif menu == "👥 Registrations":
        view_registrations(event_manager, admin_id)
    elif menu == "🧪 Test Form":
        test_registration_form()

def show_dashboard(event_manager, admin_id):
    st.header("📊 Dashboard")
    
    events = event_manager.get_events(admin_id)
    
    # Create events if none exist
    if not events:
        st.info("No events yet. Create your first event!")
        return
    
    st.subheader("Your Events")
    for event_id, event_name, event_date, event_description in events:
        with st.expander(f"🎪 {event_name}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Date:** {event_date}")
                if event_description:
                    st.write(f"**Description:** {event_description}")
                
                # SIMPLE URL that actually works
                simple_url = f"https://event-manager-app-aicon.streamlit.app/?event={event_id}&admin={admin_id}"
                st.write("**Registration URL:**")
                st.code(simple_url)
                
            with col2:
                # Generate QR
                qr_path = f"qr_{event_id}.png"
                generate_qr_code(simple_url, qr_path)
                st.image(qr_path, width=150)
                st.info("Share QR or URL")

def show_event_creation(event_manager, admin_id):
    st.header("🎪 Create Event")
    
    with st.form("create_event"):
        event_name = st.text_input("Event Name *")
        event_date = st.date_input("Event Date *")
        event_description = st.text_area("Description")
        
        st.subheader("Collect from guests:")
        col1, col2 = st.columns(2)
        with col1:
            collect_name = st.checkbox("Full Name", True)
            collect_phone = st.checkbox("Phone", True)
            collect_email = st.checkbox("Email", True)
        with col2:
            collect_company = st.checkbox("Company")
            collect_dietary = st.checkbox("Dietary")
        
        if st.form_submit_button("Create Event"):
            if event_name:
                form_fields = {
                    'name': collect_name, 'phone': collect_phone, 'email': collect_email,
                    'company': collect_company, 'dietary': collect_dietary
                }
                
                event_id = event_manager.create_event(admin_id, event_name, str(event_date), event_description, form_fields)
                
                st.success("✅ Event Created!")
                
                # Show registration info
                url = f"https://event-manager-app-aicon.streamlit.app/?event={event_id}&admin={admin_id}"
                st.info(f"**Registration URL:** {url}")
                
                # Test link
                st.markdown(f'[🧪 Test Registration Form]({url})')

def view_registrations(event_manager, admin_id):
    st.header("👥 Registrations")
    
    events = event_manager.get_events(admin_id)
    if not events:
        st.info("No events")
        return
    
    event_options = {f"{name}": id for id, name, date, _ in events}
    selected_event = st.selectbox("Select Event", list(event_options.keys()))
    event_id = event_options[selected_event]
    
    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query('SELECT name, phone, email, event_type, ticket_id, checked_in FROM registrations WHERE event_id = ? AND admin_id = ?', conn, params=(event_id, admin_id))
    conn.close()
    
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("No registrations")

def main():
    # Check if we're in guest registration mode
    query_params = st.query_params
    has_event_params = query_params.get("event") and query_params.get("admin")
    
    if has_event_params:
        show_guest_registration()
    elif 'authenticated' in st.session_state and st.session_state.authenticated:
        admin_dashboard()
    else:
        admin_auth()

if __name__ == "__main__":
    main()
