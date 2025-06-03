import streamlit as st
import pandas as pd
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ─── 0. Password protection ────────────────────────────────────────────────────
pwd = st.text_input("Enter password", type="password")
if "PASSWORD" not in st.secrets:
    st.error("App not configured. Please set PASSWORD in Streamlit secrets.")
    st.stop()
if pwd != st.secrets["PASSWORD"]:
    st.warning("🔒 Unauthorized. Please enter the correct password.")
    st.stop()

# ─── 1. Initialize DataFrame ───────────────────────────────────────────────────
if 'budget' not in st.session_state:
    st.session_state.budget = pd.DataFrame(
        columns=['Timestamp', 'Date', 'Category', 'Subsegment', 'Amount', 'Notes']
    )

# ─── 2. Timezone setup ──────────────────────────────────────────────────────────
try:
    from zoneinfo import ZoneInfo
    pacific = ZoneInfo("America/Los_Angeles")
except ImportError:
    import pytz
    pacific = pytz.timezone("America/Los_Angeles")

# ─── 3. Default widget values ────────────────────────────────────────────────────
placeholder = "-- Select Category --"
if 'entry_date' not in st.session_state:
    st.session_state.entry_date = datetime.now(pacific).date()
if 'category' not in st.session_state:
    st.session_state.category = placeholder

st.title("Budget Entry Form")

# ─── 4. Date and Category Selection ────────────────────────────────────────────
entry_date = st.date_input("Select Date", key='entry_date')

categories = [placeholder,
              "Food and Drink", "Groceries", "San Diego Padres", "Entertainment",
              "Shopping / Self-Care", "Short Travel (Car, Transit within SD)",
              "Travel (non-driving, lodging, outside SD)", "Gifts", "Memberships", "Home"]

category = st.radio("Select Budget Category", options=categories,
                    index=categories.index(st.session_state.category), key='category')

# ─── 5. Subsegment and Inputs ──────────────────────────────────────────────────
if category != placeholder:
    subsegments_map = {
        "Food and Drink": [
            "Small meal / Coffee / Beer (<$20)",
            "Eating Out / Happy Hour ($20 -> $120)",
            "Big Dinner / Treating Others (>$120)"
        ],
        "Groceries": [],
        "San Diego Padres": [
            "Stadium Concessions",
            "Extra Tickets",
            "Merch",
            "Playoff Tickets",
            "Season Tickets"
        ],
        "Entertainment": [
            "YouTube Subscription",
            "ChatGPT Subscription",
            "Non-Food Entertainment",
            "Non-Padres Tickets",
            "RealDebrid",
            "Video Games",
            "Cash on Hand",
            "Domain Cost",
            "Google Storage"
        ],
        "Shopping / Self-Care": [
            "Amazon",
            "Self-Care (Grooming, Massage, etc)",
            "Clothes",
            'Other "Stuff" Misc.'
        ],
        "Short Travel (Car, Transit within SD)": [
            "Public Transit",
            "Lyft",
            "Gas",
            "Parking",
            "Car Maintenance"
        ],
        "Travel (non-driving, lodging, outside SD)": [
            "Flights",
            "Hotel / AirBnb / Lodging",
            "Long Train",
            "Food / Drinks / Groceries / Essentials",
            "Transit",
            "Experience / Event",
            "Travel Gear",
            "Gift"
        ],
        "Gifts": [
            "For Me",
            "For Others"
        ],
        "Memberships": [
            "Internet Membership (Calyx)",
            "Credit Card Membership",
            "Prime Membership"
        ],
        "Home": [
            "Mortgage",
            "HOA",
            "SDGE (Gas & Electric)",
            "Insurance",
            "Property Tax",
            "Income Tax",
            "Miscellaneous Purchase"
        ]
    }
    opts = subsegments_map.get(category, []).copy()
    if opts:
        opts.append("Other")
        subcat = st.radio("Select Subsegment", options=opts, key='subcat', format_func=lambda x: x.replace("$", r"\$"))
        if subcat == "Other":
            subcat = st.text_input("Please specify subsegment", key='other_subcat').strip()
    else:
        subcat = ""

    amount_input = st.text_input("Transaction Total", placeholder="e.g. 42.50", key='amount_input').strip()
    notes = st.text_area("Additional Notes", key='notes').strip()

    def append_to_gsheet(data):
        scope = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(st.secrets["SHEET_URL"])
        worksheet = sheet.sheet1
        worksheet.append_row(data, value_input_option='USER_ENTERED')

    def submit_and_reset():
        try:
            amt = float(st.session_state.amount_input)
        except ValueError:
            st.error("⚠️ Invalid amount. Please enter a number.")
            return

        now = datetime.now(pacific)
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        date_str = st.session_state.entry_date.strftime("%Y-%m-%d")
        new_entry = [ts, date_str, st.session_state.category, subcat, amt, st.session_state.notes]

        st.session_state.budget.loc[len(st.session_state.budget)] = new_entry
        append_to_gsheet(new_entry)

        st.session_state.entry_date = datetime.now(pacific).date()
        st.session_state.category = placeholder
        st.session_state.amount_input = ""
        st.session_state.notes = ""
        st.session_state.subcat = None
        st.session_state.other_subcat = ""

        st.success("Entry added to budget dataset and Google Sheet!")

    st.button("Submit Entry", on_click=submit_and_reset)
else:
    st.info("⚠️ Please select a category to submit an entry.")

# ─── 6. Display current entries ───────────────────────────────────────────────
st.subheader("New Budget Entries")
st.dataframe(st.session_state.budget)