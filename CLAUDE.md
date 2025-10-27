# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-user event diary application built with Streamlit and Supabase. Users can track events across custom areas and categories, with features for analytics, bulk imports, and data export. The application uses Row Level Security (RLS) to ensure each user only sees their own data.

## Core Architecture

### Single-File Application Structure
The entire application is contained in `main.py` (~1500 lines) with a modular class-based design:

- **AuthManager** (line 73): Handles user authentication (sign up, sign in, sign out, session management)
- **DataManager** (line 129): Manages all database operations for areas, categories, and events
- **Page Functions** (lines 422-1512): Individual UI pages rendered based on `st.session_state.current_page`

### Database Schema (Supabase)
All user tables are prefixed with `mu_` (multi-user) and protected by Row Level Security:

- **mu_area**: User-defined areas (e.g., "Work", "Personal")
- **mu_category**: Categories linked to areas (e.g., "Meetings" in "Work")
- **mu_event**: Individual events with timestamp, category, comment, and duration_minutes field
- **mu_profiles**: User profile information

Key relationships:
- `mu_category.area_id` → `mu_area.id`
- `mu_event.category_id` → `mu_category.id`
- All tables have `user_id` (UUID) referencing `auth.users(id)`

**IMPORTANT**: The `duration_minutes` field is stored as a separate INTEGER column on `mu_event`, NOT inside the `data` JSONB field.

### Configuration
The app loads credentials in this order (main.py:31-49):
1. Environment variables via `python-dotenv` (.env file)
2. Streamlit secrets (.streamlit/secrets.toml)

Required secrets:
- `SUPABASEURL`: Supabase project URL
- `SUPABASEKEY`: Supabase anon/public key

### Session State Management
Session state (initialized at line 361) tracks:
- Authentication state (`authenticated`, `user_id`, `user_email`)
- Navigation (`current_page`, `event_to_edit`)
- UI persistence (`last_area_id`, `last_category_id`, filter states)
- Pagination (`current_page_num` for dashboard)

## Common Development Commands

### Running the Application
```bash
streamlit run main.py
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

### Database Setup
Run the SQL script in Supabase SQL Editor:
```bash
# The setup script is at: perplexity_temp/OLD/setup-database.sql
```

### Testing Database Connection
Check lines 56-66 in main.py for the `init_supabase()` function. If connection fails, verify:
1. `.env` or `.streamlit/secrets.toml` exists with correct credentials
2. Supabase project is active
3. Database tables and RLS policies are configured

## Key Implementation Details

### Row Level Security (RLS)
All queries automatically filter by `user_id` via Supabase RLS policies. The DataManager methods DO include `user_id` in queries for additional safety (e.g., line 140, 210).

### Event Filtering Logic
The dashboard (line 536) supports:
- Area filtering (client-side via category mapping)
- Category filtering (server-side via Supabase query)
- Date range filtering (server-side)
- Text search in comments (client-side after fetch)

Filters persist in session state and are applied in `DataManager.get_events()` (line 207).

### Pagination
Dashboard uses offset-based pagination (line 237-239):
- 10 events per page (configurable)
- `get_event_count()` provides total for page calculation
- Current page tracked in `st.session_state.current_page_num`

### Duration Handling
**Critical**: Duration is stored as `duration_minutes` INTEGER field, NOT in JSONB:
- Adding events: line 286-287 (`event_data["duration_minutes"] = duration_minutes`)
- Updating events: line 310-313 (explicitly set to None if not provided)
- Displaying: Access via `event.get('duration_minutes')`, not `event['data']['duration_minutes']`

### Analytics
The analytics page (line 1283) uses Plotly for visualizations:
- Daily/monthly event trends
- Area and category distribution
- Weekly patterns
- All charts handle empty data gracefully

### Bulk Import
Two methods (line 1130):
1. CSV upload: Expects columns `category_id`, `occurred_at`, `comment`, `duration_minutes`
2. Manual entry: Form with repeating fields

## Common Patterns

### Adding a New Page
1. Create page function: `def my_page(data_manager: DataManager):`
2. Add navigation option in `navigation_sidebar()` (line 492)
3. Add route in `main()` (line 1497-1514)
4. Initialize any required session state in `init_session_state()` (line 361)

### Database Operations
Always use DataManager methods:
- Wrap in try-except (all methods do this)
- Pass `user_id` explicitly (even though RLS enforces it)
- Use `.isoformat()` for datetime fields
- Check for None/empty results before accessing `.data`

### Error Handling
All database operations show errors via `st.error()` and return None/empty list/False on failure. Check return values before proceeding.

### Date/Time Handling
- Streamlit date_input returns `date` objects
- Streamlit time_input returns `time` objects
- Combine: `datetime.combine(date_val, time_val)`
- Store in DB: `.isoformat()`
- Parse from DB: `datetime.fromisoformat(str.replace('Z', '+00:00'))`

## File Structure Notes

- `main.py`: Complete production application
- `main-fix2.py`: Recent fix (untracked in git)
- `perplexity_temp/`: Historical development files and old versions
- `prod-ca-2021.crt`: SSL certificate for database connection
- `.env`: Local environment variables (not committed)

## Database Migration Note

The database uses cascading deletes:
- Deleting an area deletes its categories and events
- Deleting a category deletes its events
- The UI prevents these operations and shows warnings

## Testing Approach

No automated tests exist. Manual testing checklist:
1. Sign up new user → verify email confirmation required
2. Add area → verify appears in dropdowns
3. Add category → verify linked to area
4. Add event → verify appears in dashboard
5. Filter events → verify filters persist
6. Edit/delete event → verify RLS prevents access to other users' data
7. Export data → verify CSV/Excel format
8. Analytics → verify charts render with data

## Known Issues and Patterns

1. **Session State Reset**: Streamlit reruns on every interaction. Use session state for persistence.
2. **RLS Testing**: Test with multiple users to ensure data isolation.
3. **Timezone Handling**: All timestamps stored as UTC (TIMESTAMPTZ). Display converts to local.
4. **Email Confirmation**: Users must confirm email before login (checked at line 119-123).

## Deployment

The app is designed for Streamlit Cloud deployment:
1. Set secrets in Streamlit Cloud dashboard (SUPABASEURL, SUPABASEKEY)
2. Ensure Supabase project is on a paid plan for RLS and auth features
3. Configure email templates in Supabase for auth flows
