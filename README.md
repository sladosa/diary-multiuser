# Event Diary Application

## 🎯 Complete Refactored Version with All Features

### ✨ Features Implemented

- ✅ **English Interface** - All text in English, clean labels
- ✅ **Error Handling** - All operations wrapped in try-catch blocks
- ✅ **Dashboard Logic** - Shows ALL events initially, remembers filters
- ✅ **Pagination** - 10 events per page with page selector
- ✅ **Date/Time Picker** - Calendar and time selection for events
- ✅ **Add Event** - Full form with area/category dropdowns
- ✅ **Edit Event** - Pre-filled form for editing
- ✅ **Delete Event** - Double-click confirmation
- ✅ **Manage Areas/Categories** - Dedicated page for data management
- ✅ **Bulk Import** - CSV upload and manual multi-event entry
- ✅ **Analytics** - Charts for daily/monthly trends, area/category distribution
- ✅ **Export** - Download data as CSV or Excel
- ✅ **Session Persistence** - Remembers last used area/category and filters
- ✅ **Email Confirmation** - Checks email_confirmed before login
- ✅ **Row Level Security** - Each user sees only their data

## 📁 File Structure

```
event_diary/
├── main.py                 # Complete application (THIS FILE)
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── secrets.toml       # Supabase credentials
└── README.md              # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Supabase

Create `.streamlit/secrets.toml`:

```toml
SUPABASEURL = "https://your-project.supabase.co"
SUPABASEKEY = "your-anon-key-here"
```

### 3. Setup Database Tables

You need these tables in Supabase:

**User Tables (with RLS enabled):**
- `mu_area` (id, name, user_id, created_at, updated_at)
- `mu_category` (id, name, area_id, user_id, created_at, updated_at)
- `mu_event` (id, category_id, occurred_at, comment, data, user_id, created_at, updated_at, duration_minutes)
- `mu_profiles` (id, email, full_name, created_at, updated_at)

**Public Tables (optional, for standard templates):**
- `area` (id, name)
- `category` (id, name, area_id)

### 4. Enable Row Level Security (RLS)

For each `mu_*` table, run:

```sql
-- Enable RLS
ALTER TABLE mu_area ENABLE ROW LEVEL SECURITY;
ALTER TABLE mu_category ENABLE ROW LEVEL SECURITY;
ALTER TABLE mu_event ENABLE ROW LEVEL SECURITY;

-- Create policies (example for mu_area)
CREATE POLICY "Users can view own areas"
  ON mu_area FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own areas"
  ON mu_area FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own areas"
  ON mu_area FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own areas"
  ON mu_area FOR DELETE
  USING (auth.uid() = user_id);

-- Repeat similar policies for mu_category, mu_event, mu_profiles
```

### 5. Run Application

```bash
streamlit run main.py
```

## 📖 Usage Guide

### Dashboard
1. Shows all events on first load (no filters)
2. Use sidebar to apply filters (area, category, date range, search)
3. Filters persist in session state
4. Navigate pages with pagination controls
5. Edit or delete events directly

### Add Event
1. Select area (dropdowns show your areas)
2. Select category (filtered by selected area)
3. Choose date using calendar picker
4. Choose time using time picker
5. Add comment (optional)
6. Last used area/category are remembered for next event

### Manage Areas & Categories
1. **Areas Tab**: Add/delete areas
2. **Categories Tab**: Add/delete categories (linked to areas)
3. Cannot delete areas with categories
4. Cannot delete categories with events

### Bulk Import
- **CSV Upload**: Upload CSV with columns: category_id, occurred_at, comment, duration_minutes
- **Manual Entry**: Enter multiple events in form fields

### Analytics
- View daily/monthly event trends
- See distribution by area and category
- Analyze weekly patterns
- All charts handle empty data gracefully

### Export
- Choose date range
- Select format (CSV or Excel)
- Preview before download
- Download file

## 🔧 Troubleshooting

**Problem: "Cannot connect to database"**
- Check `.streamlit/secrets.toml` exists and has correct credentials
- Verify SUPABASEURL and SUPABASEKEY are correct
- Test connection in Supabase dashboard

**Problem: "Error loading events"**
- Check RLS policies are enabled and correct
- Verify user_id matches auth.uid()
- Check table names match exactly

**Problem: "Please confirm your email"**
- Check email inbox (and spam folder)
- Click confirmation link in email
- Wait a few minutes and try again

**Problem: Date picker not showing**
- Update Streamlit: `pip install --upgrade streamlit>=1.37`
- Clear browser cache
- Try different browser

**Problem: Cannot add events**
- Check INSERT policy on mu_event table
- Verify category_id exists
- Check user is authenticated
- Look for error message in UI

## 🎨 Customization

### Change Theme

Create `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

### Change Pagination

In main.py, find:

```python
events_per_page = 10  # Change this value
```

### Add Custom Fields

To add custom fields to events, modify the `add_event` and `update_event` methods in `DataManager` class.

## 📝 Database Schema

### mu_event Table

```sql
CREATE TABLE mu_event (
  id BIGSERIAL PRIMARY KEY,
  category_id BIGINT REFERENCES mu_category(id),
  occurred_at TIMESTAMPTZ NOT NULL,
  comment TEXT,
  data JSONB,
  user_id UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ,
  duration_minutes INTEGER
);
```

### mu_area Table

```sql
CREATE TABLE mu_area (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  user_id UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ
);
```

### mu_category Table

```sql
CREATE TABLE mu_category (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  area_id BIGINT REFERENCES mu_area(id),
  user_id UUID REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ
);
```

## 🤝 Support

For issues or questions:
1. Check this README for common solutions
2. Review Supabase documentation: https://supabase.com/docs
3. Review Streamlit documentation: https://docs.streamlit.io

## 📄 License

This project is provided as-is for your personal use.

## 🎉 Enjoy!

Your Event Diary is now ready to use. Start tracking your events!
