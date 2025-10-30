import streamlit as st
import sqlite3
import qrcode
import pandas as pd
import os
from datetime import datetime, timedelta
import time
import urllib.parse

# Set up the page
st.set_page_config(
    page_title="Event Manager Platform",
    page_icon="🎪",
    layout="wide"
)

# SINGLE DATABASE FILE - Shared across all sessions
DATABASE_PATH = "event_manager.db"

class EventManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        os.makedirs("databases", exist_ok=True)
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Events table with admin_id to separate organizations
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
        
        # Registrations table
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
        """Create a new event in the database"""
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
        """Get all events for this admin"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT event_id, event_name, event_date, event_description 
            FROM events 
            WHERE admin_id = ?
            ORDER BY created_at DESC
        ''', (admin_id,))
        events = c.fetchall()
        conn.close()
        return events
    
    def get_event_details(self, event_id, admin_id):
        """Get specific event details"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT event_name, event_date, event_description, 
                   collect_name, collect_phone, collect_email, collect_company, collect_dietary
            FROM events 
            WHERE event_id = ? AND admin_id = ?
        ''', (event_id, admin_id))
        event_data = c.fetchone()
        conn.close()
        return event_data

def generate_qr_code(data, filename):
    """Generate QR code image"""
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

# ===== GUEST REGISTRATION INTERFACE =====
def show_guest_registration():
    """Public guest registration - NO AUTH REQUIRED"""
    query_params = st.query_params
    
    # FIX: Get ALL values for each parameter, not just first character
    event_id = query_params.get("event", [""])[0] if query_params.get("event") else ""
    admin_id = query_params.get("admin", [""])[0] if query_params.get("admin") else ""
    
    st.sidebar.title("🔍 Debug Info")
    st.sidebar.write(f"Full Event ID: {event_id}")
    st.sidebar.write(f"Full Admin ID: {admin_id}")
    st.sidebar.write(f"All query params: {dict(query_params)}")
    
    if not event_id or not admin_id:
        st.error("❌ Invalid registration link - missing parameters")
        st.info("Please scan the QR code provided by the event organizer")
        return
    
    # Initialize event manager and get event details
    event_manager = EventManager()
    event_data = event_manager.get_event_details(event_id, admin_id)
    
    st.sidebar.write(f"Event found in DB: {event_data is not None}")
    
    if not event_data:
        st.error("❌ Event not found in database")
        
        # Show what events ARE in the database for debugging
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute("SELECT event_id, admin_id, event_name FROM events")
        all_events = c.fetchall()
        conn.close()
        
        st.sidebar.write("Events in database:")
        for evt in all_events:
            st.sidebar.write(f"- {evt}")
        
        st.info("""
        Possible reasons:
        - The QR code was generated incorrectly
        - The event was deleted
        - Database connection issue
        
        Please contact the event organizer for assistance.
        """)
        return
    
    (event_name, event_date, event_description, 
     collect_name, collect_phone, collect_email, collect_company, collect_dietary) = event_data
    
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
        
        form_data = {}
        
        if collect_name:
            form_data['name'] = st.text_input("Full Name *", placeholder="John Doe")
        
        if collect_phone:
            form_data['phone'] = st.text_input("Phone Number *", placeholder="08012345678")
        
        if collect_email:
            form_data['email'] = st.text_input("Email Address *", placeholder="john@example.com")
        
        if collect_company:
            form_data['company'] = st.text_input("Company/Organization", placeholder="Your company name")
        
        if collect_dietary:
            form_data['dietary'] = st.text_input("Dietary Preferences", placeholder="Any dietary requirements")
        
        form_data['event_type'] = st.selectbox("Event Package *", 
                                             ["Select package", "Karaoke Only", "Karaoke + Paint & Sip"])
        
        submitted = st.form_submit_button("Register Now 🎫")
        
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
                try:
                    # Save registration to database
                    phone = form_data.get('phone', '')
                    ticket_id = f"TKT-{phone}-{int(time.time())}" if phone else f"TKT-{int(time.time())}"
                    
                    conn = sqlite3.connect(DATABASE_PATH)
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO registrations 
                        (event_id, admin_id, name, phone, email, company, dietary, event_type, ticket_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (event_id, admin_id,
                          form_data.get('name'), 
                          form_data.get('phone'),
                          form_data.get('email'),
                          form_data.get('company'),
                          form_data.get('dietary'),
                          form_data.get('event_type'),
                          ticket_id))
                    conn.commit()
                    conn.close()
                    
                    st.success("✅ Registration Complete!")
                    st.balloons()
                    
                    # Generate personal QR ticket
                    qr_filename = f"personal_qr/{ticket_id}.png"
                    os.makedirs("personal_qr", exist_ok=True)
                    generate_qr_code(ticket_id, qr_filename)
                    
                    # Show ticket
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.image(qr_filename, caption="Your Entry QR Code")
                        with open(qr_filename, 'rb') as f:
                            st.download_button(
                                "📥 Download Your Ticket",
                                f.read(),
                                f"ticket_{ticket_id}.png",
                                "image/png"
                            )
                    with col2:
                        st.subheader("🎫 Your Digital Ticket")
                        if form_data.get('name'):
                            st.write(f"**Name:** {form_data['name']}")
                        if form_data.get('phone'):
                            st.write(f"**Phone:** {form_data['phone']}")
                        if form_data.get('email'):
                            st.write(f"**Email:** {form_data['email']}")
                        st.write(f"**Event:** {event_name}")
                        st.write(f"**Date:** {event_date}")
                        st.write(f"**Ticket ID:** `{ticket_id}`")
                        st.warning("**💡 Save this QR code! You'll need it for entry.**")
                        
                except Exception as e:
                    st.error(f"❌ Registration failed: {str(e)}")
                    st.info("Please try again or contact the event organizer.")

# ===== ADMIN INTERFACE =====
def admin_auth():
    st.title("🎪 Event Manager Pro")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["🚀 Register New Organization", "🔐 Login Existing Organization"])
    
    with tab1:
        st.subheader("Create New Organization Account")
        with st.form("admin_register"):
            new_admin_id = st.text_input("Organization Name *", placeholder="SchoolEventTeam")
            new_password = st.text_input("Create Admin Password *", type="password")
            confirm_password = st.text_input("Confirm Password *", type="password")
            
            registered = st.form_submit_button("Create Organization Account 📝")
            
            if registered:
                if new_admin_id and new_password and confirm_password:
                    if new_password == confirm_password:
                        if len(new_password) >= 4:
                            st.session_state['admin_id'] = new_admin_id
                            st.session_state['authenticated'] = True
                            st.success(f"✅ Organization '{new_admin_id}' created!")
                            st.rerun()
                        else:
                            st.error("Password must be at least 4 characters")
                    else:
                        st.error("Passwords do not match")
                else:
                    st.error("Please fill in all required fields")
    
    with tab2:
        st.subheader("Login to Existing Account")
        with st.form("admin_login"):
            admin_id = st.text_input("Organization Name *")
            admin_password = st.text_input("Admin Password *", type="password")
            
            submitted = st.form_submit_button("Login to Admin Portal 🔐")
            
            if submitted:
                if admin_id and admin_password:
                    if len(admin_password) >= 4:
                        st.session_state['admin_id'] = admin_id
                        st.session_state['authenticated'] = True
                        st.success(f"✅ Welcome back, {admin_id}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")

def admin_dashboard():
    admin_id = st.session_state['admin_id']
    event_manager = EventManager()
    
    st.sidebar.title(f"👤 {admin_id}")
    st.sidebar.success("Admin Portal")
    
    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    menu = st.sidebar.radio("Navigation", [
        "📊 Dashboard", 
        "🎪 Create Event", 
        "👥 View Registrations", 
        "✅ Check-In"
    ])
    
    if menu == "📊 Dashboard":
        show_dashboard(event_manager, admin_id)
    elif menu == "🎪 Create Event":
        show_event_creation(event_manager, admin_id)
    elif menu == "👥 View Registrations":
        view_registrations(event_manager, admin_id)
    elif menu == "✅ Check-In":
        show_check_in(event_manager, admin_id)

def show_dashboard(event_manager, admin_id):
    st.header("📊 Dashboard")
    
    events = event_manager.get_events(admin_id)
    
    total_events = len(events)
    total_registrations = 0
    
    conn = sqlite3.connect(DATABASE_PATH)
    for event_id, _, _, _ in events:
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM registrations WHERE event_id = ? AND admin_id = ?', (event_id, admin_id))
        count = c.fetchone()[0]
        total_registrations += count
    conn.close()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Active Events", total_events)
    with col2:
        st.metric("Total Registrations", total_registrations)
    
    if events:
        st.subheader("Your Events")
        for event_id, event_name, event_date, event_description in events:
            with st.expander(f"🎪 {event_name} - {event_date}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Event:** {event_name}")
                    st.write(f"**Date:** {event_date}")
                    if event_description:
                        st.write(f"**Description:** {event_description}")
                    
                    # FIX: Use proper URL encoding for parameters
                    registration_url = f"https://event-manager-app-aicon.streamlit.app/?event={urllib.parse.quote(event_id)}&admin={urllib.parse.quote(admin_id)}"
                    st.write("**Registration URL:**")
                    st.code(registration_url)
                    
                with col2:
                    qr_path = f"public_qr/{admin_id}/{event_id}_public.png"
                    os.makedirs(f"public_qr/{admin_id}", exist_ok=True)
                    generate_qr_code(registration_url, qr_path)
                    st.image(qr_path, width=150)
                    st.info("**Share this QR code**")
                    
                    with open(qr_path, 'rb') as f:
                        st.download_button(
                            "📥 Download QR Code",
                            f.read(),
                            f"qr_{event_name.replace(' ', '_')}.png",
                            "image/png"
                        )
    else:
        st.info("No events created yet. Create your first event!")

def show_event_creation(event_manager, admin_id):
    st.header("🎪 Create New Event")
    
    with st.form("create_event"):
        st.subheader("Event Details")
        event_name = st.text_input("Event Name *", placeholder="Karaoke Night 2024")
        event_date = st.date_input("Event Date *")
        event_description = st.text_area("Event Description (Optional)")
        
        st.subheader("📝 Information to Collect from Guests")
        
        col1, col2 = st.columns(2)
        with col1:
            collect_name = st.checkbox("Full Name", value=True)
            collect_phone = st.checkbox("Phone Number", value=True)
            collect_email = st.checkbox("Email Address", value=True)
        with col2:
            collect_company = st.checkbox("Company/Organization")
            collect_dietary = st.checkbox("Dietary Preferences")
        
        submitted = st.form_submit_button("🎫 Create Event & Generate QR Code")
    
    if submitted and event_name:
        form_fields = {
            'name': collect_name,
            'phone': collect_phone,
            'email': collect_email,
            'company': collect_company,
            'dietary': collect_dietary
        }
        
        event_id = event_manager.create_event(
            admin_id, event_name, str(event_date), event_description, form_fields
        )
        
        # FIX: Use URL encoding for parameters
        registration_url = f"https://event-manager-app-aicon.streamlit.app/?event={urllib.parse.quote(event_id)}&admin={urllib.parse.quote(admin_id)}"
        qr_filename = f"public_qr/{admin_id}/{event_id}_public.png"
        os.makedirs(f"public_qr/{admin_id}", exist_ok=True)
        generate_qr_code(registration_url, qr_filename)
        
        st.success("🎉 Event Created Successfully!")
        
        # Debug info
        st.sidebar.success("✅ Event saved to database!")
        st.sidebar.write(f"Event ID: {event_id}")
        st.sidebar.write(f"Admin ID: {admin_id}")
        st.sidebar.write(f"Registration URL: {registration_url}")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(qr_filename, caption="Guest Registration QR Code")
            with open(qr_filename, 'rb') as f:
                st.download_button(
                    "📥 Download QR Code",
                    f.read(),
                    f"qr_{event_name.replace(' ', '_')}.png",
                    "image/png"
                )
        
        with col2:
            st.subheader("Event Ready!")
            st.write(f"**Event:** {event_name}")
            st.write(f"**Date:** {event_date}")
            st.write(f"**Registration URL:**")
            st.code(registration_url)
            
            st.info("""
            **Next Steps:**
            1. Share the QR code with guests
            2. Guests scan → Register instantly
            3. Manage registrations from dashboard
            4. Check-in guests at the event
            """)

def view_registrations(event_manager, admin_id):
    st.header("👥 Event Registrations")
    
    events = event_manager.get_events(admin_id)
    if not events:
        st.info("No events created yet.")
        return
    
    event_options = {f"{name} - {date}": id for id, name, date, _ in events}
    selected_event = st.selectbox("Select Event", list(event_options.keys()))
    event_id = event_options[selected_event]
    
    conn = sqlite3.connect(DATABASE_PATH)
    df = pd.read_sql_query('''
        SELECT name, phone, email, company, dietary, event_type, ticket_id, checked_in, registered_at 
        FROM registrations 
        WHERE event_id = ? AND admin_id = ?
        ORDER BY registered_at DESC
    ''', conn, params=(event_id, admin_id))
    conn.close()
    
    if not df.empty:
        st.metric("Total Registrations", len(df))
        st.metric("Checked In", len(df[df['checked_in'] == 1]))
        st.dataframe(df)
        
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Export as CSV",
            csv,
            f"registrations_{event_id}.csv",
            "text/csv"
        )
    else:
        st.info("No registrations for this event yet.")

def show_check_in(event_manager, admin_id):
    st.header("✅ Guest Check-In")
    
    events = event_manager.get_events(admin_id)
    if not events:
        st.info("No events created yet.")
        return
    
    event_options = {f"{name} - {date}": id for id, name, date, _ in events}
    selected_event = st.selectbox("Select Event", list(event_options.keys()))
    event_id = event_options[selected_event]
    
    st.subheader("Check In Guest")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Manual Check-In**")
        ticket_id = st.text_input("Enter Ticket ID:", key="manual_checkin")
        if st.button("Check In Guest", key="manual_btn"):
            if ticket_id:
                check_in_guest(event_manager, ticket_id, event_id, admin_id)
            else:
                st.error("Please enter a Ticket ID")
    
    with col2:
        st.write("**QR Code Check-In**")
        st.info("Scan guest's personal QR ticket")
        uploaded_file = st.file_uploader("Upload QR Code Image", type=['png', 'jpg', 'jpeg'])
        if uploaded_file:
            st.warning("QR scanning feature coming soon")

def check_in_guest(event_manager, ticket_id, event_id, admin_id):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('SELECT * FROM registrations WHERE ticket_id = ? AND event_id = ? AND admin_id = ?', 
              (ticket_id, event_id, admin_id))
    guest = c.fetchone()
    
    if guest:
        if guest[11] == 1:  # checked_in field
            st.warning(f"ℹ️ {guest[3] or 'Guest'} is already checked in!")
        else:
            c.execute('UPDATE registrations SET checked_in = 1 WHERE ticket_id = ?', (ticket_id,))
            conn.commit()
            guest_name = guest[3] or "Guest"  # name field
            st.success(f"✅ {guest_name} checked in successfully!")
    else:
        st.error("❌ Ticket not found for this event.")
    
    conn.close()

def main():
    query_params = st.query_params
    
    # FIX: Proper parameter handling
    event_id = query_params.get("event", [""])[0] if query_params.get("event") else ""
    admin_id = query_params.get("admin", [""])[0] if query_params.get("admin") else ""
    
    if event_id and admin_id:
        show_guest_registration()
    else:
        if 'authenticated' not in st.session_state:
            st.session_state['authenticated'] = False
        
        if not st.session_state['authenticated']:
            admin_auth()
        else:
            admin_dashboard()

if __name__ == "__main__":
    main()
