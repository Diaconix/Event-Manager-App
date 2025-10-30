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
    page_title="Event Manager Pro - Admin",
    page_icon="🎪",
    layout="wide"
)

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
        
        # Events table
        c.execute('''
            CREATE TABLE IF NOT EXISTS events
            (event_id TEXT PRIMARY KEY,
             event_name TEXT NOT NULL,
             event_date TEXT,
             event_description TEXT,
             guest_app_url TEXT,
             collect_name INTEGER DEFAULT 1,
             collect_phone INTEGER DEFAULT 1,
             collect_email INTEGER DEFAULT 1,
             collect_company INTEGER DEFAULT 0,
             collect_dietary INTEGER DEFAULT 0,
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
        ''')
        
        # Registrations table
        c.execute('''
            CREATE TABLE IF NOT EXISTS registrations
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             event_id TEXT NOT NULL,
             name TEXT,
             phone TEXT,
             email TEXT,
             company TEXT,
             dietary TEXT,
             event_type TEXT,
             ticket_id TEXT UNIQUE NOT NULL,
             registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
             checked_in INTEGER DEFAULT 0,
             FOREIGN KEY (event_id) REFERENCES events (event_id))
        ''')
        conn.commit()
        conn.close()
    
    def create_event(self, event_name, event_date, event_description, form_fields):
        """Create a new event with custom form fields"""
        event_id = f"EVENT-{self.sanitize_id(event_name)}-{int(time.time())}"
        
        # Create guest app URL with all parameters
        guest_app_url = f"https://aicon-event-registration.streamlit.app/?event={event_id}&admin={self.admin_id}"
        
        # Add form fields to URL
        for field, value in form_fields.items():
            if value:  # Only include if field is selected
                guest_app_url += f"&{field}=1"
        
        # Save event to database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO events (event_id, event_name, event_date, event_description, guest_app_url, 
                              collect_name, collect_phone, collect_email, collect_company, collect_dietary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (event_id, event_name, event_date, event_description, guest_app_url,
              form_fields.get('name', 1), form_fields.get('phone', 1), 
              form_fields.get('email', 1), form_fields.get('company', 0),
              form_fields.get('dietary', 0)))
        conn.commit()
        conn.close()
        
        return event_id, guest_app_url
    
    def get_events(self):
        """Get all events for this admin"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT event_id, event_name, event_date, event_description, guest_app_url,
                   collect_name, collect_phone, collect_email, collect_company, collect_dietary
            FROM events ORDER BY created_at DESC
        ''')
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

def admin_auth():
    """Admin authentication with both login and registration"""
    st.title("🎪 Event Manager Pro - Admin Portal")
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
            admin_email = st.text_input("Contact Email (Optional)")
            
            registered = st.form_submit_button("Create Organization Account 📝")
            
            if registered:
                if new_admin_id and new_password and confirm_password:
                    if new_password == confirm_password:
                        if len(new_password) >= 4:
                            st.session_state['admin_id'] = new_admin_id
                            st.session_state['authenticated'] = True
                            st.success(f"✅ Organization '{new_admin_id}' created successfully!")
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
    for event_id, _, _, _, _, _, _, _, _, _ in events:
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
        for event in events:
            event_id, event_name, event_date, event_description, guest_app_url = event[:5]
            with st.expander(f"🎪 {event_name} - {event_date}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Event:** {event_name}")
                    st.write(f"**Date:** {event_date}")
                    if event_description:
                        st.write(f"**Description:** {event_description}")
                    st.write(f"**Registration URL:** [Guest App]({guest_app_url})")
                with col2:
                    # Generate and show QR code
                    qr_path = f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}/{event_id}_public.png"
                    os.makedirs(f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}", exist_ok=True)
                    generate_qr_code(guest_app_url, qr_path)
                    st.image(qr_path, width=150)
                    st.info("**Share this QR code with guests**")
    else:
        st.info("No events created yet. Create your first event!")

def show_event_creation(event_manager):
    st.header("🎪 Create New Event")
    
    with st.form("create_event"):
        st.subheader("Event Details")
        event_name = st.text_input("Event Name *", placeholder="Karaoke Night 2024")
        event_date = st.date_input("Event Date *")
        event_description = st.text_area("Event Description (Optional)")
        
        st.subheader("📝 Information to Collect from Guests")
        st.info("Select which information you want to collect from guests during registration")
        
        col1, col2 = st.columns(2)
        with col1:
            collect_name = st.checkbox("Full Name", value=True)
            collect_phone = st.checkbox("Phone Number", value=True)
            collect_email = st.checkbox("Email Address", value=True)
        with col2:
            collect_company = st.checkbox("Company/Organization")
            collect_dietary = st.checkbox("Dietary Preferences")
        
        # Event package selection
        event_type_required = st.checkbox("Require guests to select event package", value=True)
        
        submitted = st.form_submit_button("🎫 Create Event & Generate QR Code")
    
    if submitted and event_name:
        # Prepare form fields
        form_fields = {
            'name': collect_name,
            'phone': collect_phone,
            'email': collect_email,
            'company': collect_company,
            'dietary': collect_dietary,
            'package': event_type_required
        }
        
        event_id, guest_app_url = event_manager.create_event(
            event_name, str(event_date), event_description, form_fields
        )
        
        # Generate QR code
        qr_filename = f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}/{event_id}_public.png"
        os.makedirs(f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}", exist_ok=True)
        generate_qr_code(guest_app_url, qr_filename)
        
        st.success("🎉 Event Created Successfully!")
        
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
            st.write(f"**Guest Registration URL:**")
            st.code(guest_app_url)
            
            st.info("""
            **Next Steps:**
            1. Share the QR code with guests
            2. Guests scan → Go to registration form
            3. Guests register → Get personal QR ticket
            4. Scan guest tickets at event for check-in
            """)

def view_registrations(event_manager):
    st.header("👥 Event Registrations")
    
    events = event_manager.get_events()
    if not events:
        st.info("No events created yet.")
        return
    
    event_options = {f"{name} - {date}": id for id, name, date, _, _, _, _, _, _, _ in events}
    selected_event = st.selectbox("Select Event", list(event_options.keys()))
    event_id = event_options[selected_event]
    
    conn = sqlite3.connect(event_manager.db_path)
    df = pd.read_sql_query('''
        SELECT name, phone, email, company, dietary, event_type, ticket_id, checked_in, registered_at 
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
    
    event_options = {f"{name} - {date}": id for id, name, date, _, _, _, _, _, _, _ in events}
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
        st.info("Scan guest's personal QR ticket")
        uploaded_file = st.file_uploader("Upload QR Code Image", type=['png', 'jpg', 'jpeg'])
        if uploaded_file:
            st.warning("QR scanning feature coming soon")
            st.image(uploaded_file, caption="Uploaded QR Code", width=200)

def check_in_guest(event_manager, ticket_id, event_id):
    conn = sqlite3.connect(event_manager.db_path)
    c = conn.cursor()
    
    c.execute('SELECT * FROM registrations WHERE ticket_id = ? AND event_id = ?', (ticket_id, event_id))
    guest = c.fetchone()
    
    if guest:
        if guest[9] == 1:  # Already checked in
            st.warning(f"ℹ️ {guest[1] or 'Guest'} is already checked in!")
        else:
            c.execute('UPDATE registrations SET checked_in = 1 WHERE ticket_id = ?', (ticket_id,))
            conn.commit()
            guest_name = guest[1] or "Guest"
            st.success(f"✅ {guest_name} checked in successfully!")
    else:
        st.error("❌ Ticket not found for this event.")
    
    conn.close()

def main():
    # ADMIN APP ONLY - No public registration here
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    
    if not st.session_state['authenticated']:
        admin_auth()
    else:
        admin_dashboard()

if __name__ == "__main__":
    main()
