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

# Gemini AI Configuration (you'll get these from Google AI Studio)
GEMINI_API_KEY = "your-gemini-api-key"  # Get from: https://aistudio.google.com/
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

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
        c.execute('''
            CREATE TABLE IF NOT EXISTS events
            (event_id TEXT PRIMARY KEY,
             event_name TEXT NOT NULL,
             event_date TEXT,
             event_description TEXT,
             google_form_url TEXT,
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
        ''')
        conn.commit()
        conn.close()
    
    def generate_event_form_with_ai(self, event_name, event_date, event_description):
        """Use Gemini AI to generate a professional form description and questions"""
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
            """
            
            headers = {
                'Content-Type': 'application/json',
            }
            
            data = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            response = requests.post(GEMINI_URL, headers=headers, json=data)
            response_data = response.json()
            
            if 'candidates' in response_data:
                ai_content = response_data['candidates'][0]['content']['parts'][0]['text']
                # Extract JSON from AI response
                import re
                json_match = re.search(r'\{.*\}', ai_content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            
            # Fallback if AI fails
            return {
                "form_title": f"Event Registration: {event_name}",
                "form_description": f"Join us for {event_name} on {event_date}! Please register below.",
                "welcome_message": "Thank you for registering! See you at the event!"
            }
            
        except Exception as e:
            st.error(f"AI form generation failed: {e}")
            # Fallback template
            return {
                "form_title": f"Event Registration: {event_name}",
                "form_description": f"Join us for {event_name} on {event_date}! Please register below.",
                "welcome_message": "Thank you for registering! See you at the event!"
            }
    
    def create_google_form_automatically(self, event_name, event_date, event_description=""):
        """Create a Google Form automatically using their API"""
        try:
            # Generate form content with AI
            form_content = self.generate_event_form_with_ai(event_name, event_date, event_description)
            
            # For now, we'll create a template form structure
            # In production, you'd use Google Forms API
            
            form_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{form_content['form_title']}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: #f8f9fa; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                    .form-group {{ margin-bottom: 15px; }}
                    label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
                    input, select {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }}
                    button {{ background: #FF4B4B; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>{form_content['form_title']}</h1>
                    <p>{form_content['form_description']}</p>
                </div>
                
                <form action="#" method="post">
                    <div class="form-group">
                        <label for="name">Full Name *</label>
                        <input type="text" id="name" name="name" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="phone">Phone Number *</label>
                        <input type="tel" id="phone" name="phone" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="email">Email Address *</label>
                        <input type="email" id="email" name="email" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="package">Event Package *</label>
                        <select id="package" name="package" required>
                            <option value="">Select a package</option>
                            <option value="Karaoke Only">Karaoke Only</option>
                            <option value="Karaoke + Paint & Sip">Karaoke + Paint & Sip</option>
                        </select>
                    </div>
                    
                    <button type="submit">Register Now</button>
                </form>
                
                <div id="thankYou" style="display: none; margin-top: 20px; padding: 20px; background: #d4edda; border-radius: 5px;">
                    <h3>✅ {form_content['welcome_message']}</h3>
                    <p>You will receive a confirmation email shortly with your QR code ticket.</p>
                </div>
                
                <script>
                    document.querySelector('form').addEventListener('submit', function(e) {{
                        e.preventDefault();
                        document.querySelector('form').style.display = 'none';
                        document.getElementById('thankYou').style.display = 'block';
                        // In production, this would submit to your backend
                    }});
                </script>
            </body>
            </html>
            """
            
            # Save the form as HTML file
            event_id = f"EVENT-{self.sanitize_id(event_name)}-{int(time.time())}"
            form_filename = f"forms/{self.sanitize_id(self.admin_id)}/{event_id}.html"
            os.makedirs(f"forms/{self.sanitize_id(self.admin_id)}", exist_ok=True)
            
            with open(form_filename, 'w', encoding='utf-8') as f:
                f.write(form_template)
            
            # For now, we'll host it on the same Streamlit app
            form_url = f"https://event-manager-app-aicon.streamlit.app/?page=form&event={event_id}&admin={self.admin_id}"
            
            # Save event to database
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('INSERT INTO events (event_id, event_name, event_date, event_description, google_form_url) VALUES (?, ?, ?, ?, ?)',
                      (event_id, event_name, event_date, event_description, form_url))
            conn.commit()
            conn.close()
            
            return event_id, form_url
            
        except Exception as e:
            st.error(f"Form creation failed: {e}")
            # Fallback: Create a simple event record
            event_id = f"EVENT-{self.sanitize_id(event_name)}-{int(time.time())}"
            form_url = f"https://event-manager-app-aicon.streamlit.app/?page=form&event={event_id}&admin={self.admin_id}"
            
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('INSERT INTO events (event_id, event_name, event_date, event_description, google_form_url) VALUES (?, ?, ?, ?, ?)',
                      (event_id, event_name, event_date, event_description, form_url))
            conn.commit()
            conn.close()
            
            return event_id, form_url

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

def show_custom_form(event_id, admin_id):
    """Show a custom registration form within the app"""
    st.title("🎟️ Event Registration")
    
    # Get event details
    event_manager = EventManager(admin_id)
    conn = sqlite3.connect(event_manager.db_path)
    c = conn.cursor()
    c.execute('SELECT event_name, event_date, event_description FROM events WHERE event_id = ?', (event_id,))
    event_data = c.fetchone()
    conn.close()
    
    if not event_data:
        st.error("Event not found")
        return
    
    event_name, event_date, event_description = event_data
    
    st.success(f"Register for: **{event_name}**")
    st.write(f"**Date:** {event_date}")
    if event_description:
        st.write(f"**Description:** {event_description}")
    st.markdown("---")
    
    with st.form("registration_form"):
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
                # Generate ticket
                ticket_id = f"TKT-{phone}-{int(time.time())}"
                
                # Save registration (you'd save to database here)
                st.success("✅ Registration Complete!")
                st.balloons()
                
                # Generate QR code
                qr_filename = f"tickets/{ticket_id}.png"
                os.makedirs("tickets", exist_ok=True)
                generate_qr_code(ticket_id, qr_filename)
                
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.image(qr_filename, caption="Your Entry QR Code")
                with col2:
                    st.subheader("🎫 Your Ticket")
                    st.write(f"**Name:** {name}")
                    st.write(f"**Phone:** {phone}")
                    st.write(f"**Email:** {email}")
                    st.write(f"**Package:** {event_type}")
                    st.write(f"**Ticket ID:** `{ticket_id}`")
                    st.warning("**💡 Save this QR code for event entry!**")
            else:
                st.error("Please fill in all required fields")

def admin_login():
    st.title("🔐 Event Manager Pro - Admin Portal")
    st.markdown("---")
    
    with st.form("admin_login"):
        admin_id = st.text_input("Organization Name *")
        admin_password = st.text_input("Admin Password *", type="password")
        
        submitted = st.form_submit_button("Login to Admin Portal 🚀")
        
        if submitted:
            if admin_id and admin_password:
                if len(admin_password) >= 4:
                    st.session_state['admin_id'] = admin_id
                    st.session_state['authenticated'] = True
                    st.success(f"✅ Welcome back, {admin_id}!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

def admin_dashboard():
    admin_id = st.session_state['admin_id']
    event_manager = EventManager(admin_id)
    
    st.sidebar.title(f"👤 {admin_id}")
    if st.sidebar.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    menu = st.sidebar.radio("Navigation", ["📊 Dashboard", "🎪 Create Event"])
    
    if menu == "📊 Dashboard":
        show_dashboard(event_manager)
    elif menu == "🎪 Create Event":
        show_event_creation(event_manager)

def show_dashboard(event_manager):
    st.header("📊 Dashboard")
    
    events = event_manager.get_events()
    st.metric("Active Events", len(events))
    
    if events:
        st.subheader("Your Events")
        for event_id, event_name, event_date, event_description, google_form_url in events:
            with st.expander(f"🎪 {event_name} - {event_date}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Event:** {event_name}")
                    st.write(f"**Date:** {event_date}")
                    st.write(f"**Form URL:** [Open Registration]({google_form_url})")
                with col2:
                    qr_path = f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}/{event_id}_public.png"
                    if os.path.exists(qr_path):
                        st.image(qr_path, width=150)
    else:
        st.info("No events yet. Create your first event!")

def show_event_creation(event_manager):
    st.header("🎪 Create New Event")
    
    with st.form("create_event"):
        event_name = st.text_input("Event Name *", placeholder="Karaoke Night 2024")
        event_date = st.date_input("Event Date *")
        event_description = st.text_area("Event Description", placeholder="Describe your event...")
        
        submitted = st.form_submit_button("🎫 Generate Event & Registration Form")
    
    if submitted and event_name:
        with st.spinner("🤖 AI is creating your professional registration form..."):
            event_id, form_url = event_manager.create_google_form_automatically(
                event_name, str(event_date), event_description
            )
            
            # Generate QR code
            qr_filename = f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}/{event_id}_public.png"
            os.makedirs(f"public_qr/{event_manager.sanitize_id(event_manager.admin_id)}", exist_ok=True)
            generate_qr_code(form_url, qr_filename)
            
            st.success("🎉 Event & Registration Form Created!")
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(qr_filename, caption="Registration QR Code")
                with open(qr_filename, 'rb') as f:
                    st.download_button("📥 Download QR", f.read(), f"qr_{event_name}.png", "image/png")
            
            with col2:
                st.subheader("Event Ready!")
                st.write(f"**Event:** {event_name}")
                st.write(f"**Date:** {event_date}")
                st.write(f"**Registration Form:** [Open Form]({form_url})")
                st.info("""
                **Next Steps:**
                1. Share the QR code with guests
                2. Guests scan → Register instantly
                3. No login required for guests
                4. Manage check-ins from dashboard
                """)

def main():
    query_params = st.query_params
    page = query_params.get("page", [""])[0]
    
    if page == "form":
        # PUBLIC REGISTRATION FORM - NO AUTH REQUIRED
        event_id = query_params.get("event", [""])[0]
        admin_id = query_params.get("admin", [""])[0]
        if event_id and admin_id:
            show_custom_form(event_id, admin_id)
        else:
            st.error("Invalid registration link")
    else:
        # ADMIN INTERFACE
        if 'authenticated' not in st.session_state:
            st.session_state['authenticated'] = False
        
        if not st.session_state['authenticated']:
            admin_login()
        else:
            admin_dashboard()

if __name__ == "__main__":
    main()
