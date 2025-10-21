
import streamlit as st
import os
from supabase import create_client, Client
from datetime import datetime, date, timedelta
import json
import pandas as pd
import io
import base64
import calendar
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuration
SUPABASE_URL = st.secrets.get("SUPABASEURL") or os.getenv("SUPABASEURL")
SUPABASE_KEY = st.secrets.get("SUPABASEKEY") or os.getenv("SUPABASEKEY")

# Initialize Supabase client
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# Authentication functions
class AuthManager:
    @staticmethod
    def sign_up(email, password, full_name):
        try:
            response = supabase.auth.sign_up({
                "email": email, 
                "password": password,
                "options": {
                    "data": {"full_name": full_name}
                }
            })
            return response
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def sign_in(email, password):
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email, 
                "password": password
            })
            return response
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def sign_out():
        try:
            supabase.auth.sign_out()
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def get_session():
        try:
            session = supabase.auth.get_session()
            return session
        except Exception as e:
            return None

# Data export functions
class DataExporter:
    @staticmethod
    def to_csv(data, filename):
        df = pd.DataFrame(data)
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        return f'<a href="data:file/csv;base64,{b64}" download="{filename}">ðŸ’¾ Preuzmi CSV</a>'

    @staticmethod
    def to_excel(data, filename):
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Eventi', index=False)
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode()
        return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">ðŸ“Š Preuzmi Excel</a>'

# Analytics functions
class AnalyticsEngine:
    @staticmethod
    def get_event_stats(user_id, date_from, date_to):
        try:
            # Osnovne statistike
            events = supabase.table("mu_event").select("*, mu_category(name, mu_area(name))").eq("user_id", user_id).gte("occurred_at", date_from.isoformat()).lte("occurred_at", date_to.isoformat()).execute()

            if not events.data:
                return {"total": 0, "by_area": {}, "by_category": {}, "by_day": {}}

            total = len(events.data)

            # Po podruÄjima
            by_area = {}
            for event in events.data:
                area = event['mu_category']['mu_area']['name'] if event['mu_category'] and event['mu_category']['mu_area'] else 'N/A'
                by_area[area] = by_area.get(area, 0) + 1

            # Po kategorijama
            by_category = {}
            for event in events.data:
                category = event['mu_category']['name'] if event['mu_category'] else 'N/A'
                by_category[category] = by_category.get(category, 0) + 1

            # Po danima
            by_day = {}
            for event in events.data:
                day = event['occurred_at'][:10]
                by_day[day] = by_day.get(day, 0) + 1

            return {
                "total": total,
                "by_area": by_area,
                "by_category": by_category,
                "by_day": by_day,
                "events": events.data
            }
        except Exception as e:
            st.error(f"GreÅ¡ka pri dohvaÄ‡anju statistika: {str(e)}")
            return {"total": 0, "by_area": {}, "by_category": {}, "by_day": {}}

# Bulk operations
class BulkOperations:
    @staticmethod
    def bulk_add_events(events_data, user_id):
        try:
            for event in events_data:
                event['user_id'] = user_id

            response = supabase.table("mu_event").insert(events_data).execute()
            return {"success": True, "count": len(events_data)}
        except Exception as e:
            return {"error": str(e)}

# Initialize session state for authentication
def init_auth_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'

    # Check if user has valid session
    session = AuthManager.get_session()
    if session and session.user:
        st.session_state.authenticated = True
        st.session_state.user = session.user
        st.session_state.user_id = session.user.id

def login_page():
    st.title("ðŸ” Multi-User Event Diary Login")

    tab1, tab2 = st.tabs(["Prijava", "Registracija"])

    with tab1:
        st.subheader("Prijavite se")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Lozinka", type="password")
            submitted = st.form_submit_button("Prijavi se")

            if submitted:
                with st.spinner("Prijavljivanje..."):
                    response = AuthManager.sign_in(email, password)
                    if hasattr(response, 'user') and response.user:
                        st.session_state.authenticated = True
                        st.session_state.user = response.user
                        st.session_state.user_id = response.user.id
                        st.success("UspjeÅ¡no ste se prijavili!")
                        st.rerun()
                    else:
                        st.error("Neispravni podaci za prijavu")

    with tab2:
        st.subheader("Registrirajte se")
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            full_name = st.text_input("Puno ime")
            password = st.text_input("Lozinka", type="password", key="signup_password")
            password_confirm = st.text_input("Potvrdi lozinku", type="password")
            submitted = st.form_submit_button("Registriraj se")

            if submitted:
                if password != password_confirm:
                    st.error("Lozinke se ne poklapaju")
                elif len(password) < 6:
                    st.error("Lozinka mora imati najmanje 6 znakova")
                else:
                    with st.spinner("Registracija..."):
                        response = AuthManager.sign_up(email, password, full_name)
                        if hasattr(response, 'user') and response.user:
                            st.success("UspjeÅ¡no ste se registrirali! Molimo prijavite se.")
                        else:
                            st.error(f"GreÅ¡ka pri registraciji: {response.get('error', 'Nepoznata greÅ¡ka')}")

def navigation_sidebar():
    st.sidebar.title("ðŸ§­ Navigacija")

    pages = {
        "dashboard": "ðŸ“… Dashboard",
        "add_event": "âž• Dodaj dogaÄ‘aj",
        "bulk_add": "ðŸ“ Bulk dodavanje",
        "analytics": "ðŸ“Š Analytics",
        "calendar": "ðŸ—“ï¸ Kalendar",
        "export": "ðŸ’¾ Export podataka"
    }

    current_page = st.sidebar.radio(
        "Odaberite stranicu:",
        options=list(pages.keys()),
        format_func=lambda x: pages[x],
        index=list(pages.keys()).index(st.session_state.current_page) if st.session_state.current_page in pages else 0
    )

    if current_page != st.session_state.current_page:
        st.session_state.current_page = current_page
        st.rerun()

    st.sidebar.divider()

    # User info
    st.sidebar.write(f"ðŸ‘¤ {st.session_state.user.email}")

    if st.sidebar.button("ðŸšª Odjavi se"):
        AuthManager.sign_out()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

def main_dashboard():
    st.title("ðŸ“… Event Diary Dashboard")

    # Initialize filters
    if 'selected_areas' not in st.session_state:
        st.session_state.selected_areas = []
    if 'selected_categories' not in st.session_state:
        st.session_state.selected_categories = []
    if 'date_from' not in st.session_state:
        st.session_state.date_from = date.today() - timedelta(days=30)
    if 'date_to' not in st.session_state:
        st.session_state.date_to = date.today()
    if 'search_text' not in st.session_state:
        st.session_state.search_text = ""

    # Load user areas and categories
    try:
        areas_response = supabase.table("mu_area").select("*").eq("user_id", st.session_state.user_id).execute()
        areas = areas_response.data if areas_response.data else []

        categories_response = supabase.table("mu_category").select("*, mu_area(name)").eq("user_id", st.session_state.user_id).execute()
        categories = categories_response.data if categories_response.data else []
    except Exception as e:
        st.error(f"GreÅ¡ka pri dohvaÄ‡anju podataka: {str(e)}")
        areas, categories = [], []

    # Advanced filters
    st.subheader("ðŸ” Napredni filteri")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        area_options = {area['id']: area['name'] for area in areas}
        selected_areas = st.multiselect(
            "PodruÄja:",
            options=list(area_options.keys()),
            format_func=lambda x: area_options.get(x, ""),
            default=st.session_state.selected_areas
        )
        st.session_state.selected_areas = selected_areas

    with col2:
        if selected_areas:
            filtered_categories = [cat for cat in categories if cat['area_id'] in selected_areas]
        else:
            filtered_categories = categories

        category_options = {cat['id']: cat['name'] for cat in filtered_categories}
        selected_categories = st.multiselect(
            "Kategorije:",
            options=list(category_options.keys()),
            format_func=lambda x: category_options.get(x, ""),
            default=[cat for cat in st.session_state.selected_categories if cat in category_options.keys()]
        )
        st.session_state.selected_categories = selected_categories

    with col3:
        date_from = st.date_input("Od:", value=st.session_state.date_from)
        st.session_state.date_from = date_from

    with col4:
        date_to = st.date_input("Do:", value=st.session_state.date_to)
        st.session_state.date_to = date_to

    # Text search
    search_text = st.text_input("ðŸ” PretraÅ¾i po komentaru:", value=st.session_state.search_text)
    st.session_state.search_text = search_text

    # Load events based on filters
    try:
        query = supabase.table("mu_event").select("*, mu_category(name, mu_area(name))").eq("user_id", st.session_state.user_id)

        if selected_categories:
            query = query.in_("category_id", selected_categories)

        query = query.gte("occurred_at", date_from.isoformat()).lte("occurred_at", date_to.isoformat())
        query = query.order("occurred_at", desc=True)

        events_response = query.execute()
        events = events_response.data if events_response.data else []

        # Filter by search text
        if search_text:
            events = [e for e in events if search_text.lower() in (e.get('comment', '') or '').lower()]

    except Exception as e:
        st.error(f"GreÅ¡ka pri dohvaÄ‡anju dogaÄ‘aja: {str(e)}")
        events = []

    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Ukupno dogaÄ‘aja", len(events))
    with col2:
        unique_days = len(set(e['occurred_at'][:10] for e in events))
        st.metric("Aktivnih dana", unique_days)
    with col3:
        if events:
            avg_per_day = round(len(events) / max(unique_days, 1), 1)
        else:
            avg_per_day = 0
        st.metric("Prosjek po danu", avg_per_day)
    with col4:
        if events:
            last_event = max(events, key=lambda x: x['occurred_at'])
            days_since = (date.today() - datetime.fromisoformat(last_event['occurred_at']).date()).days
        else:
            days_since = "N/A"
        st.metric("Zadnji dogaÄ‘aj prije", f"{days_since} dana" if isinstance(days_since, int) else days_since)

    # Display events with pagination
    st.subheader(f"ðŸ“‹ DogaÄ‘aji")

    # Pagination
    items_per_page = 10
    total_pages = (len(events) + items_per_page - 1) // items_per_page if events else 1

    if total_pages > 1:
        page = st.selectbox(f"Stranica (ukupno {total_pages}):", range(1, total_pages + 1))
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_events = events[start_idx:end_idx]
    else:
        page_events = events

    if page_events:
        for event in page_events:
            with st.expander(f"{event['occurred_at'][:16]} - {event['mu_category']['name'] if event['mu_category'] else 'N/A'}"):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**PodruÄje:** {event['mu_category']['mu_area']['name'] if event['mu_category'] and event['mu_category']['mu_area'] else 'N/A'}")
                    st.write(f"**Kategorija:** {event['mu_category']['name'] if event['mu_category'] else 'N/A'}")
                    st.write(f"**Komentar:** {event['comment'] or 'Nema komentara'}")
                    if event['data']:
                        st.write(f"**Dodatni podaci:** {event['data']}")

                with col2:
                    col_edit, col_delete = st.columns(2)
                    with col_edit:
                        if st.button(f"âœï¸", key=f"edit_{event['id']}", help="Uredi"):
                            st.session_state.edit_event_id = event['id']
                            st.session_state.current_page = 'edit_event'
                            st.rerun()
                    with col_delete:
                        if st.button(f"ðŸ—‘ï¸", key=f"delete_{event['id']}", help="ObriÅ¡i"):
                            if st.session_state.get(f"confirm_delete_{event['id']}", False):
                                # Delete confirmed
                                try:
                                    supabase.table("mu_event").delete().eq("id", event['id']).execute()
                                    st.success("DogaÄ‘aj je obrisan!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"GreÅ¡ka pri brisanju: {str(e)}")
                            else:
                                st.session_state[f"confirm_delete_{event['id']}"] = True
                                st.warning("Kliknite ponovno za potvrdu brisanja!")
    else:
        st.info("Nema dogaÄ‘aja prema odabranim filtrima.")

def add_event_page():
    st.title("âž• Dodaj novi dogaÄ‘aj")

    # Load areas and categories
    try:
        areas_response = supabase.table("mu_area").select("*").eq("user_id", st.session_state.user_id).execute()
        areas = areas_response.data if areas_response.data else []

        categories_response = supabase.table("mu_category").select("*").eq("user_id", st.session_state.user_id).execute()
        categories = categories_response.data if categories_response.data else []
    except Exception as e:
        st.error(f"GreÅ¡ka pri dohvaÄ‡anju podataka: {str(e)}")
        return

    # Default values based on current filters
    default_area_id = st.session_state.selected_areas[0] if st.session_state.selected_areas else (areas[0]['id'] if areas else None)
    default_category_id = st.session_state.selected_categories[0] if st.session_state.selected_categories else None

    with st.form("add_event_form"):
        col1, col2 = st.columns(2)

        with col1:
            # Area selection
            area_options = {area['id']: area['name'] for area in areas}
            if area_options:
                selected_area_id = st.selectbox(
                    "PodruÄje:",
                    options=list(area_options.keys()),
                    format_func=lambda x: area_options.get(x, ""),
                    index=list(area_options.keys()).index(default_area_id) if default_area_id and default_area_id in area_options else 0
                )
            else:
                st.error("Nema dostupnih podruÄja. Molimo dodajte podruÄje putem Supabase interface.")
                return

        with col2:
            # Category selection
            filtered_categories = [cat for cat in categories if cat['area_id'] == selected_area_id]
            if filtered_categories:
                category_options = {cat['id']: cat['name'] for cat in filtered_categories}
                selected_category_id = st.selectbox(
                    "Kategorija:",
                    options=list(category_options.keys()),
                    format_func=lambda x: category_options.get(x, ""),
                    index=list(category_options.keys()).index(default_category_id) if default_category_id and default_category_id in category_options else 0
                )
            else:
                st.warning("Nema kategorija za odabrano podruÄje")
                selected_category_id = None

        occurred_at = st.datetime_input("Datum i vrijeme:", value=datetime.now())
        comment = st.text_area("Komentar:")
        data = st.text_input("Dodatni podaci (JSON format, opcionalno):")

        submitted = st.form_submit_button("ðŸ’¾ Spremi dogaÄ‘aj", type="primary")

        if submitted and selected_category_id:
            try:
                # Validate JSON data
                json_data = None
                if data.strip():
                    json_data = json.loads(data)

                with st.spinner("Spremanje dogaÄ‘aja..."):
                    response = supabase.table("mu_event").insert({
                        "category_id": selected_category_id,
                        "occurred_at": occurred_at.isoformat(),
                        "comment": comment,
                        "data": json_data,
                        "user_id": st.session_state.user_id
                    }).execute()

                if response.data:
                    st.success("DogaÄ‘aj je uspjeÅ¡no dodan!")
                    # Clear form
                    st.rerun()
                else:
                    st.error("GreÅ¡ka pri dodavanju dogaÄ‘aja")
            except json.JSONDecodeError:
                st.error("Neispravni JSON format u dodatnim podacima")
            except Exception as e:
                st.error(f"GreÅ¡ka: {str(e)}")

def edit_event_page():
    if 'edit_event_id' not in st.session_state:
        st.error("Nema dogaÄ‘aja za ureÄ‘ivanje")
        return

    event_id = st.session_state.edit_event_id

    st.title("âœï¸ Uredi dogaÄ‘aj")

    # Load event data
    try:
        response = supabase.table("mu_event").select("*, mu_category(*, mu_area(*))").eq("id", event_id).eq("user_id", st.session_state.user_id).single().execute()
        event = response.data

        if not event:
            st.error("DogaÄ‘aj nije pronaÄ‘en")
            return
    except Exception as e:
        st.error(f"GreÅ¡ka pri dohvaÄ‡anju dogaÄ‘aja: {str(e)}")
        return

    # Load areas and categories
    try:
        areas_response = supabase.table("mu_area").select("*").eq("user_id", st.session_state.user_id).execute()
        areas = areas_response.data if areas_response.data else []

        categories_response = supabase.table("mu_category").select("*").eq("user_id", st.session_state.user_id).execute()
        categories = categories_response.data if categories_response.data else []
    except Exception as e:
        st.error(f"GreÅ¡ka pri dohvaÄ‡anju podataka: {str(e)}")
        return

    with st.form("edit_event_form"):
        col1, col2 = st.columns(2)

        current_area_id = event['mu_category']['area_id'] if event['mu_category'] else areas[0]['id']
        current_category_id = event['category_id']

        with col1:
            area_options = {area['id']: area['name'] for area in areas}
            selected_area_id = st.selectbox(
                "PodruÄje:",
                options=list(area_options.keys()),
                format_func=lambda x: area_options.get(x, ""),
                index=list(area_options.keys()).index(current_area_id) if current_area_id in area_options else 0
            )

        with col2:
            filtered_categories = [cat for cat in categories if cat['area_id'] == selected_area_id]
            category_options = {cat['id']: cat['name'] for cat in filtered_categories}
            selected_category_id = st.selectbox(
                "Kategorija:",
                options=list(category_options.keys()),
                format_func=lambda x: category_options.get(x, ""),
                index=list(category_options.keys()).index(current_category_id) if current_category_id in category_options else 0
            )

        occurred_at = st.datetime_input(
            "Datum i vrijeme:",
            value=datetime.fromisoformat(event['occurred_at'].replace('Z', '+00:00')).replace(tzinfo=None)
        )
        comment = st.text_area("Komentar:", value=event['comment'] or "")
        data = st.text_input(
            "Dodatni podaci (JSON format):",
            value=json.dumps(event['data']) if event['data'] else ""
        )

        col_save, col_cancel = st.columns(2)

        with col_save:
            submitted = st.form_submit_button("ðŸ’¾ Spremi promjene", type="primary")
        with col_cancel:
            cancelled = st.form_submit_button("âŒ Odustani")

        if cancelled:
            if 'edit_event_id' in st.session_state:
                del st.session_state['edit_event_id']
            st.session_state.current_page = 'dashboard'
            st.rerun()

        if submitted:
            try:
                json_data = None
                if data.strip():
                    json_data = json.loads(data)

                with st.spinner("Spremanje promjena..."):
                    response = supabase.table("mu_event").update({
                        "category_id": selected_category_id,
                        "occurred_at": occurred_at.isoformat(),
                        "comment": comment,
                        "data": json_data,
                        "updated_at": datetime.now().isoformat()
                    }).eq("id", event_id).eq("user_id", st.session_state.user_id).execute()

                if response.data:
                    st.success("DogaÄ‘aj je uspjeÅ¡no aÅ¾uriran!")
                    if 'edit_event_id' in st.session_state:
                        del st.session_state['edit_event_id']
                    st.session_state.current_page = 'dashboard'
                    st.rerun()
                else:
                    st.error("GreÅ¡ka pri aÅ¾uriranju dogaÄ‘aja")
            except json.JSONDecodeError:
                st.error("Neispravni JSON format u dodatnim podacima")
            except Exception as e:
                st.error(f"GreÅ¡ka: {str(e)}")

def bulk_add_page():
    st.title("ðŸ“ Bulk dodavanje dogaÄ‘aja")

    st.info("Dodajte viÅ¡e dogaÄ‘aja odjednom koristeÄ‡i CSV format ili manual unos.")

    tab1, tab2 = st.tabs(["ðŸ“Š CSV Upload", "âœï¸ Manual unos"])

    # Load areas and categories for reference
    try:
        areas_response = supabase.table("mu_area").select("*").eq("user_id", st.session_state.user_id).execute()
        areas = areas_response.data if areas_response.data else []

        categories_response = supabase.table("mu_category").select("*").eq("user_id", st.session_state.user_id).execute()
        categories = categories_response.data if categories_response.data else []
    except Exception as e:
        st.error(f"GreÅ¡ka pri dohvaÄ‡anju podataka: {str(e)}")
        return

    with tab1:
        st.subheader("CSV Upload")

        # Show example CSV format
        with st.expander("ðŸ“– Prikaz CSV formata"):
            example_df = pd.DataFrame({
                'category_id': [categories[0]['id'] if categories else 1, categories[1]['id'] if len(categories) > 1 else 1],
                'occurred_at': ['2024-10-14T10:00:00', '2024-10-14T14:30:00'],
                'comment': ['Prvi dogaÄ‘aj', 'Drugi dogaÄ‘aj'],
                'data': ['{}', '{"tip": "meeting"}']
            })
            st.dataframe(example_df)

            st.write("**Dostupne kategorije:**")
            for cat in categories[:5]:  # Show first 5
                st.write(f"- {cat['id']}: {cat['name']}")

        uploaded_file = st.file_uploader("Odaberite CSV datoteku:", type=['csv'])

        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.write(f"UÄitan CSV s {len(df)} redaka")
                st.dataframe(df.head())

                if st.button("ðŸ“¥ Dodaj sve dogaÄ‘aje iz CSV-a"):
                    events_to_add = []
                    for _, row in df.iterrows():
                        event = {
                            'category_id': int(row['category_id']),
                            'occurred_at': row['occurred_at'],
                            'comment': str(row['comment']),
                            'data': json.loads(row['data']) if pd.notna(row['data']) and row['data'].strip() else None,
                            'user_id': st.session_state.user_id
                        }
                        events_to_add.append(event)

                    with st.spinner("Dodavanje dogaÄ‘aja..."):
                        result = BulkOperations.bulk_add_events(events_to_add, st.session_state.user_id)

                    if result.get('success'):
                        st.success(f"UspjeÅ¡no dodano {result['count']} dogaÄ‘aja!")
                    else:
                        st.error(f"GreÅ¡ka: {result.get('error')}")

            except Exception as e:
                st.error(f"GreÅ¡ka pri obradi CSV-a: {str(e)}")

    with tab2:
        st.subheader("Manual unos viÅ¡e dogaÄ‘aja")

        # Number of events to add
        num_events = st.number_input("Broj dogaÄ‘aja za dodavanje:", min_value=1, max_value=20, value=3)

        events_data = []

        for i in range(num_events):
            st.write(f"### DogaÄ‘aj {i+1}")
            col1, col2, col3 = st.columns(3)

            with col1:
                area_options = {area['id']: area['name'] for area in areas}
                selected_area = st.selectbox(f"PodruÄje {i+1}:", list(area_options.keys()), format_func=lambda x: area_options[x], key=f"area_{i}")

            with col2:
                filtered_cats = [cat for cat in categories if cat['area_id'] == selected_area]
                cat_options = {cat['id']: cat['name'] for cat in filtered_cats}
                selected_cat = st.selectbox(f"Kategorija {i+1}:", list(cat_options.keys()), format_func=lambda x: cat_options[x], key=f"cat_{i}")

            with col3:
                occurred_at = st.datetime_input(f"Datum/vrijeme {i+1}:", key=f"datetime_{i}")

            comment = st.text_area(f"Komentar {i+1}:", key=f"comment_{i}")

            events_data.append({
                'category_id': selected_cat,
                'occurred_at': occurred_at.isoformat(),
                'comment': comment,
                'user_id': st.session_state.user_id
            })

        if st.button("ðŸ“ Dodaj sve dogaÄ‘aje"):
            with st.spinner("Dodavanje dogaÄ‘aja..."):
                result = BulkOperations.bulk_add_events(events_data, st.session_state.user_id)

            if result.get('success'):
                st.success(f"UspjeÅ¡no dodano {result['count']} dogaÄ‘aja!")
            else:
                st.error(f"GreÅ¡ka: {result.get('error')}")

def analytics_page():
    st.title("ðŸ“Š Analytics Dashboard")

    # Date range for analytics
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Od datuma:", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("Do datuma:", value=date.today())

    # Get analytics data
    stats = AnalyticsEngine.get_event_stats(st.session_state.user_id, start_date, end_date)

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Ukupno dogaÄ‘aja", stats['total'])
    with col2:
        unique_days = len(stats['by_day'])
        st.metric("Aktivnih dana", unique_days)
    with col3:
        avg_per_day = round(stats['total'] / max(unique_days, 1), 1) if stats['total'] > 0 else 0
        st.metric("Prosjek po danu", avg_per_day)
    with col4:
        most_active_area = max(stats['by_area'], key=stats['by_area'].get) if stats['by_area'] else "N/A"
        st.metric("Najaktivnije podruÄje", most_active_area)

    if stats['total'] > 0:
        # Charts
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("DogaÄ‘aji po podruÄjima")
            if stats['by_area']:
                fig = px.pie(
                    values=list(stats['by_area'].values()),
                    names=list(stats['by_area'].keys()),
                    title="Distribucija po podruÄjima"
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("DogaÄ‘aji po kategorijama")
            if stats['by_category']:
                fig = px.bar(
                    x=list(stats['by_category'].keys()),
                    y=list(stats['by_category'].values()),
                    title="Broj dogaÄ‘aja po kategorijama"
                )
                fig.update_xaxes(tickangle=45)
                st.plotly_chart(fig, use_container_width=True)

        # Timeline chart
        st.subheader("Vremenska linija aktivnosti")
        if stats['by_day']:
            dates = list(stats['by_day'].keys())
            counts = list(stats['by_day'].values())

            fig = px.line(
                x=dates,
                y=counts,
                title="Broj dogaÄ‘aja po danima",
                markers=True
            )
            fig.update_layout(xaxis_title="Datum", yaxis_title="Broj dogaÄ‘aja")
            st.plotly_chart(fig, use_container_width=True)

        # Weekly pattern analysis
        if stats['events']:
            st.subheader("Analiza po danima u tjednu")

            # Prepare data for weekly analysis
            weekly_data = {}
            for event in stats['events']:
                event_date = datetime.fromisoformat(event['occurred_at'])
                day_name = calendar.day_name[event_date.weekday()]
                weekly_data[day_name] = weekly_data.get(day_name, 0) + 1

            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekly_counts = [weekly_data.get(day, 0) for day in days_order]

            fig = px.bar(
                x=['Pon', 'Uto', 'Sri', 'ÄŒet', 'Pet', 'Sub', 'Ned'],
                y=weekly_counts,
                title="Aktivnost po danima u tjednu"
            )
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Nema podataka za odabrani period.")

def calendar_view_page():
    st.title("ðŸ—“ï¸ Kalendarski prikaz")

    # Month/year selector
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox("Godina:", range(2020, 2030), index=range(2020, 2030).index(date.today().year))
    with col2:
        selected_month = st.selectbox("Mjesec:", range(1, 13), index=date.today().month - 1, format_func=lambda x: calendar.month_name[x])

    # Get events for selected month
    start_date = date(selected_year, selected_month, 1)
    if selected_month == 12:
        end_date = date(selected_year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(selected_year, selected_month + 1, 1) - timedelta(days=1)

    try:
        query = supabase.table("mu_event").select("*, mu_category(name, mu_area(name))").eq("user_id", st.session_state.user_id)
        query = query.gte("occurred_at", start_date.isoformat()).lte("occurred_at", end_date.isoformat())
        events_response = query.execute()
        events = events_response.data if events_response.data else []
    except Exception as e:
        st.error(f"GreÅ¡ka pri dohvaÄ‡anju dogaÄ‘aja: {str(e)}")
        events = []

    # Group events by day
    events_by_day = {}
    for event in events:
        day = datetime.fromisoformat(event['occurred_at']).date()
        if day not in events_by_day:
            events_by_day[day] = []
        events_by_day[day].append(event)

    # Display calendar
    st.subheader(f"ðŸ“… {calendar.month_name[selected_month]} {selected_year}")

    # Generate calendar HTML
    cal = calendar.monthcalendar(selected_year, selected_month)

    # Calendar grid
    days_of_week = ['Pon', 'Uto', 'Sri', 'ÄŒet', 'Pet', 'Sub', 'Ned']

    # Header
    cols = st.columns(7)
    for i, day_name in enumerate(days_of_week):
        cols[i].write(f"**{day_name}**")

    # Calendar days
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                current_date = date(selected_year, selected_month, day)
                day_events = events_by_day.get(current_date, [])

                with cols[i]:
                    if day_events:
                        st.write(f"**{day}** ðŸ”´({len(day_events)})")
                        for event in day_events[:2]:  # Show max 2 events
                            time_str = datetime.fromisoformat(event['occurred_at']).strftime('%H:%M')
                            st.write(f"â€¢ {time_str}")
                        if len(day_events) > 2:
                            st.write(f"... +{len(day_events) - 2}")
                    else:
                        st.write(f"{day}")

    # Detailed events list
    if events:
        st.subheader(f"ðŸ“‹ Svi dogaÄ‘aji u {calendar.month_name[selected_month]}")
        for event in sorted(events, key=lambda x: x['occurred_at']):
            event_date = datetime.fromisoformat(event['occurred_at'])
            with st.expander(f"{event_date.strftime('%d.%m. %H:%M')} - {event['mu_category']['name'] if event['mu_category'] else 'N/A'}"):
                st.write(f"**PodruÄje:** {event['mu_category']['mu_area']['name'] if event['mu_category'] and event['mu_category']['mu_area'] else 'N/A'}")
                st.write(f"**Komentar:** {event['comment'] or 'Nema komentara'}")

def export_page():
    st.title("ðŸ’¾ Export podataka")

    # Export options
    col1, col2 = st.columns(2)

    with col1:
        export_format = st.selectbox("Format:", ["CSV", "Excel", "JSON"])
    with col2:
        date_range = st.selectbox("Raspon:", ["Zadnjih 30 dana", "Zadnjih 90 dana", "Ova godina", "Sve podatke", "PrilagoÄ‘eno"])

    # Date range selection
    if date_range == "PrilagoÄ‘eno":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Od:", value=date.today() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Do:", value=date.today())
    else:
        end_date = date.today()
        if date_range == "Zadnjih 30 dana":
            start_date = end_date - timedelta(days=30)
        elif date_range == "Zadnjih 90 dana":
            start_date = end_date - timedelta(days=90)
        elif date_range == "Ova godina":
            start_date = date(end_date.year, 1, 1)
        else:  # Sve podatke
            start_date = date(2020, 1, 1)

    # Get data to export
    try:
        query = supabase.table("mu_event").select("*, mu_category(name, mu_area(name))").eq("user_id", st.session_state.user_id)
        query = query.gte("occurred_at", start_date.isoformat()).lte("occurred_at", end_date.isoformat())
        query = query.order("occurred_at", desc=False)
        events_response = query.execute()
        events = events_response.data if events_response.data else []
    except Exception as e:
        st.error(f"GreÅ¡ka pri dohvaÄ‡anju podataka: {str(e)}")
        return

    if events:
        st.write(f"ðŸ“Š PronaÄ‘eno {len(events)} dogaÄ‘aja za export")

        # Prepare data for export
        export_data = []
        for event in events:
            export_data.append({
                'Datum': event['occurred_at'][:10],
                'Vrijeme': event['occurred_at'][11:16],
                'PodruÄje': event['mu_category']['mu_area']['name'] if event['mu_category'] and event['mu_category']['mu_area'] else 'N/A',
                'Kategorija': event['mu_category']['name'] if event['mu_category'] else 'N/A',
                'Komentar': event['comment'] or '',
                'Dodatni_podaci': json.dumps(event['data']) if event['data'] else '',
                'Kreiran': event['created_at'][:10]
            })

        # Preview
        st.subheader("ðŸ” Pregled podataka")
        df = pd.DataFrame(export_data)
        st.dataframe(df.head(10))

        # Export buttons
        st.subheader("â¬‡ï¸ Preuzimanje")

        col1, col2, col3 = st.columns(3)

        with col1:
            if export_format in ["CSV", "Excel"]:
                if st.button("ðŸ“¥ Preuzmi CSV"):
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="ðŸ’¾ Preuzmi CSV datoteku",
                        data=csv,
                        file_name=f"eventi_{start_date}_{end_date}.csv",
                        mime="text/csv"
                    )

        with col2:
            if export_format in ["Excel"]:
                if st.button("ðŸ“¥ Preuzmi Excel"):
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, sheet_name='Eventi', index=False)
                    excel_data = output.getvalue()

                    st.download_button(
                        label="ðŸ“Š Preuzmi Excel datoteku",
                        data=excel_data,
                        file_name=f"eventi_{start_date}_{end_date}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

        with col3:
            if export_format == "JSON":
                if st.button("ðŸ“¥ Preuzmi JSON"):
                    json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="ðŸ”— Preuzmi JSON datoteku",
                        data=json_data,
                        file_name=f"eventi_{start_date}_{end_date}.json",
                        mime="application/json"
                    )

    else:
        st.info("Nema podataka za export u odabranom rasponu.")

def main():
    st.set_page_config(
        page_title="Event Diary Pro", 
        page_icon="ðŸ“…", 
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize authentication state
    init_auth_state()

    # Navigation
    if not st.session_state.authenticated:
        login_page()
    else:
        navigation_sidebar()

        # Route to appropriate page
        if st.session_state.current_page == 'dashboard':
            main_dashboard()
        elif st.session_state.current_page == 'add_event':
            add_event_page()
        elif st.session_state.current_page == 'bulk_add':
            bulk_add_page()
        elif st.session_state.current_page == 'analytics':
            analytics_page()
        elif st.session_state.current_page == 'calendar':
            calendar_view_page()
        elif st.session_state.current_page == 'export':
            export_page()
        elif st.session_state.current_page == 'edit_event':
            edit_event_page()

if __name__ == "__main__":
    main()