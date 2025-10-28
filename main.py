"""
Event Diary Application - Complete Refactored Version
English Interface | All Features Implemented | Production Ready
Author: AI Assistant for Event Diary Project
Date: October 2025
"""

import streamlit as st
import os
from supabase import create_client, Client
from datetime import datetime, date, timedelta
import json
import pandas as pd
import io
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv

# ============================================
# CONFIGURATION
# ============================================

st.set_page_config(
    page_title="Event Diary 1",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Učitaj .env prvo (ako postoji)
load_dotenv()

# Pokušaj dobiti iz environment variables (radi i za .env i za Streamlit Cloud!)
SUPABASE_URL = os.getenv("SUPABASEURL")
SUPABASE_KEY = os.getenv("SUPABASEKEY")

# Ako nisu u environment, pokušaj iz st.secrets (fallback)
if not SUPABASE_URL:
    try:
        SUPABASE_URL = st.secrets["SUPABASEURL"]
    except:
        pass

if not SUPABASE_KEY:
    try:
        SUPABASE_KEY = st.secrets["SUPABASEKEY"]
    except:
        pass

# ============================================
# SUPABASE CLIENT INITIALIZATION
# ============================================

@st.cache_resource
def init_supabase():
    """Initialize and cache Supabase client"""
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            st.error("⚠️ Supabase credentials not found. Please configure secrets.toml")
            return None
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"❌ Failed to connect to database: {str(e)}")
        return None

supabase = init_supabase()

# ============================================
# AUTHENTICATION MODULE
# ============================================

class AuthManager:
    """Handles all authentication operations"""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    def sign_up(self, email: str, password: str, full_name: str):
        """Register a new user"""
        try:
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {"full_name": full_name}
                }
            })
            return response
        except Exception as e:
            return {"error": str(e)}

    def sign_in(self, email: str, password: str):
        """Sign in existing user"""
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return response
        except Exception as e:
            return {"error": str(e)}

    def sign_out(self):
        """Sign out current user"""
        try:
            self.supabase.auth.sign_out()
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    def get_session(self):
        """Get current session"""
        try:
            return self.supabase.auth.get_session()
        except:
            return None

    def is_email_confirmed(self, user):
        """Check if user email is confirmed"""
        if user and hasattr(user, 'email_confirmed_at'):
            return user.email_confirmed_at is not None
        return False

# ============================================
# DATA MANAGEMENT MODULE
# ============================================

class DataManager:
    """Handles all database operations for events, areas, and categories"""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    # ===== AREA OPERATIONS =====

    def get_user_areas(self, user_id: str):
        """Get all areas for a user"""
        try:
            response = self.supabase.table("mu_area").select("*").eq("user_id", user_id).order("name").execute()
            return response.data if response.data else []
        except Exception as e:
            st.error(f"❌ Error loading areas: {str(e)}")
            return []

    def add_area(self, user_id: str, area_name: str):
        """Add a new area for user"""
        try:
            response = self.supabase.table("mu_area").insert({
                "name": area_name,
                "user_id": user_id,
                "created_at": datetime.now().isoformat()
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            st.error(f"❌ Error adding area: {str(e)}")
            return None

    def delete_area(self, area_id: int, user_id: str):
        """Delete an area"""
        try:
            self.supabase.table("mu_area").delete().eq("id", area_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            st.error(f"❌ Error deleting area: {str(e)}")
            return False

    # ===== CATEGORY OPERATIONS =====

    def get_user_categories(self, user_id: str, area_id: int = None):
        """Get categories for a user, optionally filtered by area"""
        try:
            query = self.supabase.table("mu_category").select("*, mu_area(name)").eq("user_id", user_id)
            if area_id:
                query = query.eq("area_id", area_id)
            response = query.order("name").execute()
            return response.data if response.data else []
        except Exception as e:
            st.error(f"❌ Error loading categories: {str(e)}")
            return []

    def add_category(self, user_id: str, category_name: str, area_id: int):
        """Add a new category for user"""
        try:
            response = self.supabase.table("mu_category").insert({
                "name": category_name,
                "area_id": area_id,
                "user_id": user_id,
                "created_at": datetime.now().isoformat()
            }).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            st.error(f"❌ Error adding category: {str(e)}")
            return None

    def delete_category(self, category_id: int, user_id: str):
        """Delete a category"""
        try:
            self.supabase.table("mu_category").delete().eq("id", category_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            st.error(f"❌ Error deleting category: {str(e)}")
            return False

    # ===== EVENT OPERATIONS =====

    def get_events(self, user_id: str, filters: dict = None, limit: int = None, offset: int = None):
        """Get events for user with optional filters"""
        try:
            query = self.supabase.table("mu_event").select("*, mu_category(name, area_id, mu_area(name))").eq("user_id", user_id)

            # Apply filters
            if filters:
                if filters.get('category_ids'):
                    query = query.in_("category_id", filters['category_ids'])

                if filters.get('area_ids'):
                    # Need to filter via category
                    categories = self.get_user_categories(user_id)
                    cat_ids = [c['id'] for c in categories if c.get('area_id') in filters['area_ids']]
                    if cat_ids:
                        query = query.in_("category_id", cat_ids)

                if filters.get('date_from'):
                    query = query.gte("occurred_at", filters['date_from'].isoformat())

                if filters.get('date_to'):
                    # Add one day to include the entire end date
                    end_date = filters['date_to'] + timedelta(days=1)
                    query = query.lt("occurred_at", end_date.isoformat())

            # Order by date descending
            query = query.order("occurred_at", desc=True)

            # Apply pagination
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.range(offset, offset + limit - 1 if limit else offset + 9)

            response = query.execute()
            events = response.data if response.data else []

            # Apply text search filter (client-side)
            if filters and filters.get('search_text'):
                search_text = filters['search_text'].lower()
                events = [e for e in events if search_text in (e.get('comment', '') or '').lower()]

            return events
        except Exception as e:
            st.error(f"❌ Error loading events: {str(e)}")
            return []

    def get_event_count(self, user_id: str, filters: dict = None):
        """Get total count of events for pagination"""
        try:
            query = self.supabase.table("mu_event").select("id", count="exact").eq("user_id", user_id)

            if filters:
                if filters.get('category_ids'):
                    query = query.in_("category_id", filters['category_ids'])
                if filters.get('date_from'):
                    query = query.gte("occurred_at", filters['date_from'].isoformat())
                if filters.get('date_to'):
                    end_date = filters['date_to'] + timedelta(days=1)
                    query = query.lt("occurred_at", end_date.isoformat())

            response = query.execute()
            return response.count if hasattr(response, 'count') else len(response.data)
        except Exception as e:
            st.error(f"❌ Error counting events: {str(e)}")
            return 0

    def add_event(self, user_id: str, category_id: int, occurred_at: datetime, comment: str = "", duration_minutes: int = None, data: dict = None):
        """Add a new event"""
        try:
            event_data = {
                "category_id": category_id,
                "occurred_at": occurred_at.isoformat(),
                "comment": comment,
                "user_id": user_id,
                "created_at": datetime.now().isoformat()
            }

            # Add duration_minutes as separate field (not in data JSON)
            if duration_minutes is not None and duration_minutes > 0:
                event_data["duration_minutes"] = duration_minutes

            # Add additional data if provided
            if data:
                event_data["data"] = data

            response = self.supabase.table("mu_event").insert(event_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            st.error(f"❌ Error adding event: {str(e)}")
            return None

    def update_event(self, event_id: int, user_id: str, category_id: int, occurred_at: datetime, comment: str = "", duration_minutes: int = None, data: dict = None):
        """Update an existing event"""
        try:
            event_data = {
                "category_id": category_id,
                "occurred_at": occurred_at.isoformat(),
                "comment": comment,
                "updated_at": datetime.now().isoformat()
            }

            # Add duration_minutes as separate field (not in data JSON)
            if duration_minutes is not None and duration_minutes > 0:
                event_data["duration_minutes"] = duration_minutes
            else:
                event_data["duration_minutes"] = None

            # Add additional data if provided
            if data:
                event_data["data"] = data

            response = self.supabase.table("mu_event").update(event_data).eq("id", event_id).eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            st.error(f"❌ Error updating event: {str(e)}")
            return None

    def delete_event(self, event_id: int, user_id: str):
        """Delete an event"""
        try:
            self.supabase.table("mu_event").delete().eq("id", event_id).eq("user_id", user_id).execute()
            return True
        except Exception as e:
            st.error(f"❌ Error deleting event: {str(e)}")
            return False

    def get_event_by_id(self, event_id: int, user_id: str):
        """Get a single event by ID"""
        try:
            response = self.supabase.table("mu_event").select("*, mu_category(*, mu_area(*))").eq("id", event_id).eq("user_id", user_id).single().execute()
            return response.data
        except Exception as e:
            st.error(f"❌ Error loading event: {str(e)}")
            return None

    def bulk_add_events(self, events_data: list, user_id: str):
        """Bulk add multiple events"""
        try:
            for event in events_data:
                event['user_id'] = user_id
                event['created_at'] = datetime.now().isoformat()
                if isinstance(event.get('occurred_at'), datetime):
                    event['occurred_at'] = event['occurred_at'].isoformat()

            response = self.supabase.table("mu_event").insert(events_data).execute()
            return {"success": True, "count": len(events_data)}
        except Exception as e:
            return {"error": str(e)}

# ============================================
# SESSION STATE INITIALIZATION
# ============================================

def init_session_state():
    """Initialize all session state variables"""

    # Authentication state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None

    # Navigation
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'

    # Dashboard filters - None means show ALL (no filter initially)
    if 'filter_areas' not in st.session_state:
        st.session_state.filter_areas = []
    if 'filter_categories' not in st.session_state:
        st.session_state.filter_categories = []
    if 'filter_date_from' not in st.session_state:
        st.session_state.filter_date_from = None
    if 'filter_date_to' not in st.session_state:
        st.session_state.filter_date_to = None
    if 'filter_search' not in st.session_state:
        st.session_state.filter_search = ""

    # Pagination
    if 'current_page_num' not in st.session_state:
        st.session_state.current_page_num = 1

    # Remember last used values for quick entry
    if 'last_area_id' not in st.session_state:
        st.session_state.last_area_id = None
    if 'last_category_id' not in st.session_state:
        st.session_state.last_category_id = None

    # Edit mode
    if 'editing_event_id' not in st.session_state:
        st.session_state.editing_event_id = None

    # Delete confirmation
    if 'delete_confirm_id' not in st.session_state:
        st.session_state.delete_confirm_id = None

    # Check for existing session
    if supabase and not st.session_state.authenticated:
        auth_manager = AuthManager(supabase)
        session = auth_manager.get_session()
        if session and hasattr(session, 'user') and session.user:
            if auth_manager.is_email_confirmed(session.user):
                st.session_state.authenticated = True
                st.session_state.user = session.user
                st.session_state.user_id = session.user.id



# ============================================
# LOGIN PAGE
# ============================================

def login_page(auth_manager: AuthManager):
    """Render login and registration page"""

    st.title("🔐 Event Diary - Login")

    # Show email confirmation warning if needed
    if st.session_state.get('email_not_confirmed', False):
        st.warning("⚠️ Please confirm your email address before logging in. Check your inbox for the confirmation link.")

    tab1, tab2 = st.tabs(["Sign In", "Register"])

    with tab1:
        st.subheader("Sign In")
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if not email or not password:
                    st.error("❌ Please enter both email and password")
                else:
                    with st.spinner("Signing in..."):
                        response = auth_manager.sign_in(email, password)

                        if hasattr(response, 'user') and response.user:
                            if auth_manager.is_email_confirmed(response.user):
                                st.session_state.authenticated = True
                                st.session_state.user = response.user
                                st.session_state.user_id = response.user.id
                                st.success("✅ Successfully signed in!")
                                st.rerun()
                            else:
                                st.error("❌ Please confirm your email address before logging in.")
                                st.session_state.email_not_confirmed = True
                        else:
                            error_msg = response.get('error', 'Invalid login credentials')
                            st.error(f"❌ Sign in failed: {error_msg}")

    with tab2:
        st.subheader("Create New Account")
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email", placeholder="your@email.com")
            full_name = st.text_input("Full Name", placeholder="John Doe")
            password = st.text_input("Password", type="password", key="signup_password", placeholder="Minimum 6 characters")
            password_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
            submitted = st.form_submit_button("Register", use_container_width=True)

            if submitted:
                if not email or not full_name or not password:
                    st.error("❌ Please fill in all fields")
                elif password != password_confirm:
                    st.error("❌ Passwords do not match")
                elif len(password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                else:
                    with st.spinner("Creating account..."):
                        response = auth_manager.sign_up(email, password, full_name)

                        if hasattr(response, 'user') and response.user:
                            st.success("✅ Registration successful! Please check your email to confirm your account.")
                            st.info("📧 Check your inbox (and spam folder) for the confirmation email.")
                        else:
                            error_msg = response.get('error', 'Unknown error occurred')
                            st.error(f"❌ Registration failed: {error_msg}")

# ============================================
# NAVIGATION SIDEBAR
# ============================================

def navigation_sidebar(auth_manager: AuthManager):
    """Render navigation sidebar"""

    st.sidebar.title("🧭 Navigation")

    pages = {
        "dashboard": "📅 Dashboard",
        "add_event": "➕ Add Event",
        "manage_data": "🏷️ Manage Areas & Categories",
        "bulk_import": "📄 Bulk Import",
        "analytics": "📊 Analytics",
        "export": "💾 Export Data"
    }

    # Radio button for page selection
    selected_page = st.sidebar.radio(
        "Select Page:",
        options=list(pages.keys()),
        format_func=lambda x: pages[x],
        index=list(pages.keys()).index(st.session_state.current_page) if st.session_state.current_page in pages else 0
    )

    if selected_page != st.session_state.current_page:
        st.session_state.current_page = selected_page
        st.rerun()

    st.sidebar.divider()

    # User info
    user_email = st.session_state.user.email if st.session_state.user else "Unknown"
    st.sidebar.write(f"👤 **User:** {user_email}")

    # Sign out button
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        auth_manager.sign_out()
        # Clear all session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ============================================
# DASHBOARD PAGE
# ============================================

def dashboard_page(data_manager: DataManager):
    """Main dashboard with event list, filters, and pagination"""

    st.title("📅 Event Dashboard")

    user_id = st.session_state.user_id

    # Get areas and categories for filters
    areas = data_manager.get_user_areas(user_id)
    categories = data_manager.get_user_categories(user_id)

    # Sidebar filters
    with st.sidebar:
        st.subheader("🔍 Filters")

        # Area filter
        if areas:
            area_options = {a['id']: a['name'] for a in areas}
            selected_areas = st.multiselect(
                "Filter by Area:",
                options=list(area_options.keys()),
                format_func=lambda x: area_options[x],
                default=st.session_state.filter_areas,
                key="area_filter"
            )
            st.session_state.filter_areas = selected_areas

        # Category filter
        if categories:
            cat_options = {c['id']: f"{c['name']} ({c['mu_area']['name'] if c.get('mu_area') else 'No area'})" for c in categories}
            selected_categories = st.multiselect(
                "Filter by Category:",
                options=list(cat_options.keys()),
                format_func=lambda x: cat_options[x],
                default=st.session_state.filter_categories,
                key="cat_filter"
            )
            st.session_state.filter_categories = selected_categories

        # Date range filter
        col1, col2 = st.columns(2)
        with col1:
            date_from = st.date_input(
                "From:",
                value=st.session_state.filter_date_from,
                key="date_from_filter"
            )
            st.session_state.filter_date_from = date_from

        with col2:
            date_to = st.date_input(
                "To:",
                value=st.session_state.filter_date_to,
                key="date_to_filter"
            )
            st.session_state.filter_date_to = date_to

        # Text search
        search_text = st.text_input(
            "🔎 Search in comments:",
            value=st.session_state.filter_search,
            placeholder="Type to search...",
            key="search_filter"
        )
        st.session_state.filter_search = search_text

        # Clear filters button
        if st.button("🗑️ Clear All Filters", use_container_width=True):
            st.session_state.filter_areas = []
            st.session_state.filter_categories = []
            st.session_state.filter_date_from = None
            st.session_state.filter_date_to = None
            st.session_state.filter_search = ""
            st.session_state.current_page_num = 1
            st.rerun()

    # Build filters dict
    filters = {}
    if st.session_state.filter_areas:
        filters['area_ids'] = st.session_state.filter_areas
    if st.session_state.filter_categories:
        filters['category_ids'] = st.session_state.filter_categories
    if st.session_state.filter_date_from:
        filters['date_from'] = st.session_state.filter_date_from
    if st.session_state.filter_date_to:
        filters['date_to'] = st.session_state.filter_date_to
    if st.session_state.filter_search:
        filters['search_text'] = st.session_state.filter_search

    # Get total count for pagination
    total_events = data_manager.get_event_count(user_id, filters if filters else None)

    # Pagination settings
    events_per_page = 10
    total_pages = max(1, (total_events + events_per_page - 1) // events_per_page)

    # Display stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Events", total_events)
    with col2:
        st.metric("Current Page", f"{st.session_state.current_page_num}/{total_pages}")
    with col3:
        active_filters = len([f for f in filters.values() if f])
        st.metric("Active Filters", active_filters)
    with col4:
        st.metric("Events/Page", events_per_page)

    st.divider()

    # Pagination controls
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col1:
            if st.button("⬅️ Previous", disabled=(st.session_state.current_page_num <= 1)):
                st.session_state.current_page_num -= 1
                st.rerun()
        with col2:
            page_num = st.selectbox(
                "Go to page:",
                options=range(1, total_pages + 1),
                index=st.session_state.current_page_num - 1,
                key="page_selector"
            )
            if page_num != st.session_state.current_page_num:
                st.session_state.current_page_num = page_num
                st.rerun()
        with col3:
            if st.button("Next ➡️", disabled=(st.session_state.current_page_num >= total_pages)):
                st.session_state.current_page_num += 1
                st.rerun()

    # Get events for current page
    offset = (st.session_state.current_page_num - 1) * events_per_page
    events = data_manager.get_events(user_id, filters if filters else None, limit=events_per_page, offset=offset)

    # Display events
    if not events:
        st.info("📭 No events found. Try adjusting your filters or add a new event!")
    else:
        for event in events:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

                with col1:
                    occurred_dt = datetime.fromisoformat(event['occurred_at'].replace('Z', '+00:00'))
                    st.write(f"**{occurred_dt.strftime('%Y-%m-%d %H:%M')}**")
                    if event.get('comment'):
                        st.write(event['comment'])
                    # Show duration if available
                    if event.get('duration_minutes') and event['duration_minutes'] > 0:
                        st.write(f"⏱️ Duration: {event['duration_minutes']} min")

                with col2:
                    if event.get('mu_category'):
                        area_name = event['mu_category'].get('mu_area', {}).get('name', 'No area') if event['mu_category'].get('mu_area') else 'No area'
                        st.write(f"📁 {area_name}")
                        st.write(f"🏷️ {event['mu_category']['name']}")

                with col3:
                    if st.button("✏️ Edit", key=f"edit_{event['id']}"):
                        st.session_state.editing_event_id = event['id']
                        st.session_state.current_page = 'edit_event'
                        st.rerun()

                with col4:
                    # Delete with confirmation
                    if st.session_state.delete_confirm_id == event['id']:
                        if st.button("⚠️ Confirm?", key=f"confirm_del_{event['id']}"):
                            if data_manager.delete_event(event['id'], user_id):
                                st.success("✅ Event deleted!")
                                st.session_state.delete_confirm_id = None
                                st.rerun()
                    else:
                        if st.button("🗑️ Delete", key=f"del_{event['id']}"):
                            st.session_state.delete_confirm_id = event['id']
                            st.rerun()

                st.divider()



# ============================================
# ADD EVENT PAGE
# ============================================

def add_event_page(data_manager: DataManager):
    """Page for adding new events with date/time picker"""

    st.title("➕ Add New Event")

    user_id = st.session_state.user_id

    # Get areas and categories
    areas = data_manager.get_user_areas(user_id)

    if not areas:
        st.warning("⚠️ No areas found. Please create an area first in 'Manage Areas & Categories'.")
        if st.button("Go to Manage Areas"):
            st.session_state.current_page = 'manage_data'
            st.rerun()
        return

    with st.form("add_event_form"):
        st.subheader("Event Details")

        # Area selection with "Add New" option
        col1, col2 = st.columns([3, 1])
        with col1:
            area_options = {a['id']: a['name'] for a in areas}
            default_area_idx = 0
            if st.session_state.last_area_id and st.session_state.last_area_id in area_options:
                default_area_idx = list(area_options.keys()).index(st.session_state.last_area_id)

            selected_area_id = st.selectbox(
                "Area *",
                options=list(area_options.keys()),
                format_func=lambda x: area_options[x],
                index=default_area_idx,
                help="Select the area for this event"
            )

        with col2:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.form_submit_button("+ New Area"):
                st.info("💡 Use 'Manage Areas & Categories' page to add new areas")

        # Category selection based on area
        categories = data_manager.get_user_categories(user_id, selected_area_id)

        if not categories:
            st.warning(f"⚠️ No categories found for this area. Please create a category first.")
            selected_category_id = None
        else:
            col1, col2 = st.columns([3, 1])
            with col1:
                cat_options = {c['id']: c['name'] for c in categories}
                default_cat_idx = 0
                if st.session_state.last_category_id and st.session_state.last_category_id in cat_options:
                    default_cat_idx = list(cat_options.keys()).index(st.session_state.last_category_id)

                selected_category_id = st.selectbox(
                    "Category *",
                    options=list(cat_options.keys()),
                    format_func=lambda x: cat_options[x],
                    index=default_cat_idx,
                    help="Select the category for this event"
                )

            with col2:
                st.write("")  # Spacing
                st.write("")  # Spacing
                st.write("💡 Use 'Manage Areas & Categories' to add new categories")

        st.divider()

        # Date and time selection
        col1, col2 = st.columns(2)
        with col1:
            event_date = st.date_input(
                "Event Date *",
                value=date.today(),
                help="Select the date when the event occurred"
            )

        with col2:
            event_time = st.time_input(
                "Event Time *",
                value=datetime.now().time(),
                help="Select the time when the event occurred"
            )

        # Combine date and time
        occurred_at = datetime.combine(event_date, event_time)

        st.write(f"📅 Event will be recorded as: **{occurred_at.strftime('%Y-%m-%d %H:%M')}**")

        st.divider()

        # Comment
        comment = st.text_area(
            "Comment (optional)",
            placeholder="Add any notes or details about this event...",
            height=100
        )

        # Duration (optional)
        duration = st.number_input(
            "Duration (minutes, optional)",
            min_value=0,
            value=0,
            help="How long did this event last?"
        )

        # Submit button
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submitted = st.form_submit_button("✅ Add Event", use_container_width=True)
        with col2:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state.current_page = 'dashboard'
                st.rerun()

        if submitted:
            if not selected_category_id:
                st.error("❌ Please select a category or create one first")
            else:
                # Add event with duration as separate field
                result = data_manager.add_event(
                    user_id=user_id,
                    category_id=selected_category_id,
                    occurred_at=occurred_at,
                    comment=comment,
                    duration_minutes=duration if duration > 0 else None
                )

                if result:
                    st.success("✅ Event added successfully!")
                    # Remember last used area and category
                    st.session_state.last_area_id = selected_area_id
                    st.session_state.last_category_id = selected_category_id
                    st.info("💡 Your last selections are remembered for the next event!")
                    st.session_state.show_redirect = True

    # Show redirect button outside of form
    if st.session_state.get('show_redirect', False):
        if st.button("Go to Dashboard"):
            st.session_state.current_page = 'dashboard'
            st.session_state.show_redirect = False
            st.rerun()

# ============================================
# EDIT EVENT PAGE
# ============================================

def edit_event_page(data_manager: DataManager):
    """Page for editing an existing event"""

    st.title("✏️ Edit Event")

    user_id = st.session_state.user_id
    event_id = st.session_state.editing_event_id

    if not event_id:
        st.error("❌ No event selected for editing")
        if st.button("Back to Dashboard"):
            st.session_state.current_page = 'dashboard'
            st.rerun()
        return

    # Load event
    event = data_manager.get_event_by_id(event_id, user_id)

    if not event:
        st.error("❌ Event not found or you don't have permission to edit it")
        if st.button("Back to Dashboard"):
            st.session_state.current_page = 'dashboard'
            st.rerun()
        return

    # Get areas and categories
    areas = data_manager.get_user_areas(user_id)

    with st.form("edit_event_form"):
        st.subheader("Edit Event Details")

        # Area selection
        area_options = {a['id']: a['name'] for a in areas}
        current_area_id = event['mu_category']['area_id']
        current_area_idx = list(area_options.keys()).index(current_area_id) if current_area_id in area_options else 0

        selected_area_id = st.selectbox(
            "Area *",
            options=list(area_options.keys()),
            format_func=lambda x: area_options[x],
            index=current_area_idx
        )

        # Category selection
        categories = data_manager.get_user_categories(user_id, selected_area_id)
        cat_options = {c['id']: c['name'] for c in categories}
        current_cat_idx = list(cat_options.keys()).index(event['category_id']) if event['category_id'] in cat_options else 0

        selected_category_id = st.selectbox(
            "Category *",
            options=list(cat_options.keys()),
            format_func=lambda x: cat_options[x],
            index=current_cat_idx
        )

        st.divider()

        # Parse current datetime
        occurred_dt = datetime.fromisoformat(event['occurred_at'].replace('Z', '+00:00'))

        # Date and time selection
        col1, col2 = st.columns(2)
        with col1:
            event_date = st.date_input(
                "Event Date *",
                value=occurred_dt.date()
            )

        with col2:
            event_time = st.time_input(
                "Event Time *",
                value=occurred_dt.time()
            )

        # Combine date and time
        occurred_at = datetime.combine(event_date, event_time)

        st.write(f"📅 Event will be recorded as: **{occurred_at.strftime('%Y-%m-%d %H:%M')}**")

        st.divider()

        # Comment
        comment = st.text_area(
            "Comment (optional)",
            value=event.get('comment', ''),
            height=100
        )

        # Duration - get from duration_minutes field
        current_duration = event.get('duration_minutes', 0) or 0
        duration = st.number_input(
            "Duration (minutes, optional)",
            min_value=0,
            value=current_duration
        )

        # Submit buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)
        with col2:
            if st.form_submit_button("❌ Cancel", use_container_width=True):
                st.session_state.editing_event_id = None
                st.session_state.current_page = 'dashboard'
                st.rerun()

        if submitted:
            # Prepare data
            event_data = {
                "duration_minutes": duration if duration > 0 else None
            }

            # Update event
            result = data_manager.update_event(
                event_id=event_id,
                user_id=user_id,
                category_id=selected_category_id,
                occurred_at=occurred_at,
                comment=comment,
                data=event_data if event_data["duration_minutes"] else None
            )

            if result:
                st.success("✅ Event updated successfully!")
                st.session_state.editing_event_id = None
                if st.button("Back to Dashboard"):
                    st.session_state.current_page = 'dashboard'
                    st.rerun()

# ============================================
# MANAGE AREAS & CATEGORIES PAGE
# ============================================

def manage_data_page(data_manager: DataManager):
    """Page for managing areas and categories"""

    st.title("🏷️ Manage Areas & Categories")

    user_id = st.session_state.user_id

    tab1, tab2 = st.tabs(["📁 Areas", "🏷️ Categories"])

    # === AREAS TAB ===
    with tab1:
        st.subheader("Your Areas")

        # Add new area form
        with st.form("add_area_form"):
            col1, col2 = st.columns([3, 1])
            with col1:
                new_area_name = st.text_input("New Area Name", placeholder="e.g., Work, Health, Personal")
            with col2:
                st.write("")
                st.write("")
                add_area_btn = st.form_submit_button("➕ Add Area", use_container_width=True)

            if add_area_btn:
                if not new_area_name or not new_area_name.strip():
                    st.error("❌ Area name cannot be empty")
                else:
                    result = data_manager.add_area(user_id, new_area_name.strip())
                    if result:
                        st.success(f"✅ Area '{new_area_name}' added successfully!")
                        st.rerun()

        st.divider()

        # List existing areas
        areas = data_manager.get_user_areas(user_id)

        if not areas:
            st.info("📭 No areas yet. Create your first area above!")
        else:
            st.write(f"**Total Areas:** {len(areas)}")

            for area in areas:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"📁 **{area['name']}**")
                with col2:
                    if st.button("🗑️", key=f"del_area_{area['id']}", help="Delete this area"):
                        # Check if area has categories
                        cats = data_manager.get_user_categories(user_id, area['id'])
                        if cats:
                            st.error(f"❌ Cannot delete area with {len(cats)} categories. Delete categories first.")
                        else:
                            if data_manager.delete_area(area['id'], user_id):
                                st.success("✅ Area deleted!")
                                st.rerun()
                st.divider()

    # === CATEGORIES TAB ===
    with tab2:
        st.subheader("Your Categories")

        areas = data_manager.get_user_areas(user_id)

        if not areas:
            st.warning("⚠️ Please create an area first before adding categories.")
        else:
            # Add new category form
            with st.form("add_category_form"):
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    area_options = {a['id']: a['name'] for a in areas}
                    selected_area_id = st.selectbox(
                        "Area",
                        options=list(area_options.keys()),
                        format_func=lambda x: area_options[x]
                    )

                with col2:
                    new_category_name = st.text_input("Category Name", placeholder="e.g., Meeting, Exercise")

                with col3:
                    st.write("")
                    st.write("")
                    add_cat_btn = st.form_submit_button("➕ Add", use_container_width=True)

                if add_cat_btn:
                    if not new_category_name or not new_category_name.strip():
                        st.error("❌ Category name cannot be empty")
                    else:
                        result = data_manager.add_category(user_id, new_category_name.strip(), selected_area_id)
                        if result:
                            st.success(f"✅ Category '{new_category_name}' added to area!")
                            st.rerun()

            st.divider()

            # List existing categories grouped by area
            for area in areas:
                st.write(f"### 📁 {area['name']}")

                cats = data_manager.get_user_categories(user_id, area['id'])

                if not cats:
                    st.write("  _No categories in this area_")
                else:
                    for cat in cats:
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.write(f"  🏷️ {cat['name']}")
                        with col2:
                            if st.button("🗑️", key=f"del_cat_{cat['id']}", help="Delete this category"):
                                if data_manager.delete_category(cat['id'], user_id):
                                    st.success("✅ Category deleted!")
                                    st.rerun()

                st.divider()



# ============================================
# BULK IMPORT PAGE
# ============================================

def bulk_import_page(data_manager: DataManager):
    """Page for bulk importing events"""

    st.title("📄 Bulk Import Events")

    user_id = st.session_state.user_id

    st.info("💡 Import multiple events at once using CSV upload or manual entry.")

    tab1, tab2 = st.tabs(["📤 CSV Upload", "✍️ Manual Entry"])

    # === CSV UPLOAD TAB ===
    with tab1:
        st.subheader("Upload CSV File")

        st.write("**CSV Format Requirements:**")
        st.code("""
category_id,occurred_at,comment,duration_minutes
1,2025-10-22 10:30:00,Morning meeting,60
2,2025-10-22 14:00:00,Gym workout,45
        """)

        st.write("**Instructions:**")
        st.write("- `category_id`: Must be one of your existing category IDs")
        st.write("- `occurred_at`: Format YYYY-MM-DD HH:MM:SS")
        st.write("- `comment`: Optional text description")
        st.write("- `duration_minutes`: Optional number")

        uploaded_file = st.file_uploader("Choose CSV file", type=['csv'])

        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)

                st.write("**Preview:**")
                st.dataframe(df.head(10))

                st.write(f"**Total rows:** {len(df)}")

                # Validate required columns
                required_cols = ['category_id', 'occurred_at']
                missing_cols = [col for col in required_cols if col not in df.columns]

                if missing_cols:
                    st.error(f"❌ Missing required columns: {', '.join(missing_cols)}")
                else:
                    if st.button("✅ Import All Events", use_container_width=True):
                        with st.spinner("Importing events..."):
                            events_data = []

                            for idx, row in df.iterrows():
                                try:
                                    event_dict = {
                                        "category_id": int(row['category_id']),
                                        "occurred_at": row['occurred_at'],
                                        "comment": str(row.get('comment', '')),
                                    }

                                    if 'duration_minutes' in row and pd.notna(row['duration_minutes']):
                                        event_dict['data'] = {"duration_minutes": int(row['duration_minutes'])}

                                    events_data.append(event_dict)
                                except Exception as e:
                                    st.warning(f"⚠️ Skipping row {idx + 1}: {str(e)}")

                            if events_data:
                                result = data_manager.bulk_add_events(events_data, user_id)

                                if result.get('success'):
                                    st.success(f"✅ Successfully imported {result['count']} events!")
                                    if st.button("Go to Dashboard"):
                                        st.session_state.current_page = 'dashboard'
                                        st.rerun()
                                else:
                                    st.error(f"❌ Import failed: {result.get('error')}")
                            else:
                                st.error("❌ No valid events to import")

            except Exception as e:
                st.error(f"❌ Error reading CSV file: {str(e)}")

    # === MANUAL ENTRY TAB ===
    with tab2:
        st.subheader("Manual Multi-Event Entry")

        # Get categories for selection
        categories = data_manager.get_user_categories(user_id)

        if not categories:
            st.warning("⚠️ No categories found. Please create categories first.")
            return

        cat_options = {c['id']: f"{c['name']} ({c.get('mu_area', {}).get('name', 'No area')})" for c in categories}

        num_events = st.number_input("How many events to add?", min_value=1, max_value=20, value=3)

        with st.form("bulk_manual_form"):
            events_to_add = []

            for i in range(num_events):
                st.write(f"**Event {i+1}**")
                col1, col2, col3, col4 = st.columns([2, 2, 2, 2])

                with col1:
                    cat_id = st.selectbox(
                        "Category",
                        options=list(cat_options.keys()),
                        format_func=lambda x: cat_options[x],
                        key=f"cat_{i}"
                    )

                with col2:
                    evt_date = st.date_input("Date", value=date.today(), key=f"date_{i}")

                with col3:
                    evt_time = st.time_input("Time", value=datetime.now().time(), key=f"time_{i}")

                with col4:
                    duration = st.number_input("Duration (min)", min_value=0, value=0, key=f"dur_{i}")

                comment = st.text_input("Comment (optional)", key=f"comment_{i}")

                occurred_at = datetime.combine(evt_date, evt_time)

                event_data = {
                    "category_id": cat_id,
                    "occurred_at": occurred_at,
                    "comment": comment,
                }
                # Add duration_minutes as separate field
                if duration > 0:
                    event_data["duration_minutes"] = duration
                events_to_add.append(event_data)

                st.divider()

            submitted = st.form_submit_button("✅ Add All Events", use_container_width=True)

            if submitted:
                result = data_manager.bulk_add_events(events_to_add, user_id)

                if result.get('success'):
                    st.success(f"✅ Successfully added {result['count']} events!")
                    if st.button("Go to Dashboard"):
                        st.session_state.current_page = 'dashboard'
                        st.rerun()
                else:
                    st.error(f"❌ Failed to add events: {result.get('error')}")

# ============================================
# ANALYTICS PAGE
# ============================================

def analytics_page(data_manager: DataManager):
    """Page for viewing analytics and charts"""

    st.title("📊 Analytics & Insights")

    user_id = st.session_state.user_id

    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From:", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To:", value=date.today())

    # Get events in date range
    filters = {
        'date_from': start_date,
        'date_to': end_date
    }

    events = data_manager.get_events(user_id, filters)

    if not events:
        st.info("📭 No events found in selected date range.")
        return

    # Convert to DataFrame for analysis
    df_events = []
    for e in events:
        occurred_dt = datetime.fromisoformat(e['occurred_at'].replace('Z', '+00:00'))
        df_events.append({
            'date': occurred_dt.date(),
            'datetime': occurred_dt,
            'area': e.get('mu_category', {}).get('mu_area', {}).get('name', 'Unknown'),
            'category': e.get('mu_category', {}).get('name', 'Unknown'),
            'comment': e.get('comment', ''),
            'duration': e.get('duration_minutes', 0) or 0
        })

    df = pd.DataFrame(df_events)

    # Summary metrics
    st.subheader("📈 Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Events", len(df))
    with col2:
        unique_days = df['date'].nunique()
        st.metric("Active Days", unique_days)
    with col3:
        avg_per_day = len(df) / max(unique_days, 1)
        st.metric("Avg Events/Day", f"{avg_per_day:.1f}")
    with col4:
        total_duration = df['duration'].sum()
        st.metric("Total Duration (hrs)", f"{total_duration / 60:.1f}")

    st.divider()

    # Charts
    tab1, tab2, tab3 = st.tabs(["📅 Timeline", "📁 By Area", "🏷️ By Category"])

    with tab1:
        st.subheader("Events Over Time")

        # Daily count
        daily_counts = df.groupby('date').size().reset_index(name='count')
        daily_counts['date'] = pd.to_datetime(daily_counts['date'])

        fig = px.line(daily_counts, x='date', y='count', 
                     title='Daily Event Count',
                     labels={'date': 'Date', 'count': 'Number of Events'})
        fig.update_traces(mode='lines+markers')
        st.plotly_chart(fig, use_container_width=True)

        # Weekly pattern
        df['weekday'] = df['datetime'].dt.day_name()
        weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekday_counts = df.groupby('weekday').size().reindex(weekday_order).fillna(0)

        fig2 = px.bar(x=weekday_counts.index, y=weekday_counts.values,
                     title='Events by Day of Week',
                     labels={'x': 'Day', 'y': 'Count'})
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader("Distribution by Area")

        area_counts = df.groupby('area').size().reset_index(name='count')

        fig = px.pie(area_counts, names='area', values='count',
                    title='Events by Area')
        st.plotly_chart(fig, use_container_width=True)

        # Table view
        st.write("**Breakdown:**")
        st.dataframe(area_counts.sort_values('count', ascending=False))

    with tab3:
        st.subheader("Distribution by Category")

        cat_counts = df.groupby(['area', 'category']).size().reset_index(name='count')

        fig = px.bar(cat_counts, x='category', y='count', color='area',
                    title='Events by Category',
                    labels={'category': 'Category', 'count': 'Count'})
        st.plotly_chart(fig, use_container_width=True)

        # Table view
        st.write("**Breakdown:**")
        st.dataframe(cat_counts.sort_values('count', ascending=False))

# ============================================
# EXPORT PAGE
# ============================================

def export_page(data_manager: DataManager):
    """Page for exporting data"""

    st.title("💾 Export Data")

    user_id = st.session_state.user_id

    st.write("Export your events data to CSV or Excel format.")

    # Date range
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From:", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To:", value=date.today())

    # Export format
    export_format = st.radio("Export Format:", ["CSV", "Excel"])

    if st.button("🔄 Load Preview", use_container_width=True):
        filters = {
            'date_from': start_date,
            'date_to': end_date
        }

        events = data_manager.get_events(user_id, filters)

        if not events:
            st.info("📭 No events found in selected date range.")
        else:
            # Convert to DataFrame
            export_data = []
            for e in events:
                occurred_dt = datetime.fromisoformat(e['occurred_at'].replace('Z', '+00:00'))
                export_data.append({
                    'Date': occurred_dt.strftime('%Y-%m-%d'),
                    'Time': occurred_dt.strftime('%H:%M:%S'),
                    'Area': e.get('mu_category', {}).get('mu_area', {}).get('name', ''),
                    'Category': e.get('mu_category', {}).get('name', ''),
                    'Comment': e.get('comment', ''),
                    'Duration (min)': e.get('data', {}).get('duration_minutes', 0) if e.get('data') else 0
                })

            df = pd.DataFrame(export_data)

            st.write(f"**Preview (Total: {len(df)} events):**")
            st.dataframe(df.head(20))

            # Download button
            if export_format == "CSV":
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"events_{start_date}_{end_date}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:  # Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Events')
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 Download Excel",
                    data=excel_data,
                    file_name=f"events_{start_date}_{end_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# ============================================
# MAIN APPLICATION ENTRY POINT
# ============================================

def main():
    """Main application entry point"""

    # Initialize session state
    init_session_state()

    # Check if Supabase is connected
    if not supabase:
        st.error("❌ Cannot connect to database. Please check your configuration.")
        st.stop()

    # Initialize managers
    auth_manager = AuthManager(supabase)
    data_manager = DataManager(supabase)

    # Check authentication
    if not st.session_state.authenticated:
        login_page(auth_manager)
    else:
        # Show navigation sidebar
        navigation_sidebar(auth_manager)

        # Route to appropriate page
        current_page = st.session_state.current_page

        if current_page == 'dashboard':
            dashboard_page(data_manager)
        elif current_page == 'add_event':
            add_event_page(data_manager)
        elif current_page == 'edit_event':
            edit_event_page(data_manager)
        elif current_page == 'manage_data':
            manage_data_page(data_manager)
        elif current_page == 'bulk_import':
            bulk_import_page(data_manager)
        elif current_page == 'analytics':
            analytics_page(data_manager)
        elif current_page == 'export':
            export_page(data_manager)
        else:
            st.error(f"❌ Unknown page: {current_page}")

# ============================================
# RUN APPLICATION 2025-10-27, 13:46
# ============================================

if __name__ == "__main__":
    main()
