import streamlit as st
import pandas as pd
import os
import streamlit.components.v1 as components

# ================= LOGIN =================
def login_page():
    st.title("Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        if u == st.secrets["auth"]["username"] and p == st.secrets["auth"]["password"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid username or password")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    login_page()
    st.stop()

def logout():
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

# ================= CONFIG =================
BASE_PATH = "FORM DETAILS"
ALLOTMENT_FILE = os.path.join(BASE_PATH, "salesforce.xlsx")
PAYMENT_FILE = os.path.join(BASE_PATH, "salesforce payment.xlsx")

FLAT_COLUMN = "Flat"
GKC_COLUMN = "GKC"
STATUS_COLUMN = "Status"
STATUS_VALUE = "Cleared"
AADHAR_COLUMN = "Aadhar"
PREFERRED_PAYMENT_SHEET = "OLD Booking Tracker"

BUILDINGS = [
    "AMAZON A", "AMAZON B",
    "DANUBE A", "DANUBE B", "DANUBE C", "DANUBE D",
    "TAPI A"
]

HIDE_PAYMENT_COLUMNS = ["Sr. No.", "Wing", "Flat No."]

# ================= PAGE =================
st.set_page_config(layout="wide", page_title="Flat Dashboard")

l, r = st.columns([6, 1])
with l:
    st.title("Flat Allotment & Payment Dashboard")
    st.caption("Search flat details and cleared payments instantly")
with r:
    logout()

# ================= HELPERS =================
def clean_dates(df):
    for c in df.columns:
        if "date" in c.lower():
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%d/%m/%Y")
    return df

def clean_aadhar(s):
    return s.astype(str).str.replace(" ", "", regex=False)

def copy_button(val):
    safe = str(val).replace("`", "")
    components.html(
        f"""
        <button onclick="navigator.clipboard.writeText(`{safe}`)"
        style="padding:3px 8px;border:1px solid #ccc;border-radius:5px;">
        Copy
        </button>
        """,
        height=30
    )

# ================= LOAD ALLOTMENT =================
@st.cache_data
def load_allotment(building):
    df = pd.read_excel(ALLOTMENT_FILE, sheet_name=building)
    df[FLAT_COLUMN] = df[FLAT_COLUMN].astype(str).str.strip()
    df[GKC_COLUMN] = df[GKC_COLUMN].astype(str).str.strip()
    return clean_dates(df)

# ================= LOAD PAYMENT (SMART) =================
@st.cache_data
def load_payment(gkc_values):
    xl = pd.ExcelFile(PAYMENT_FILE)
    sheet = PREFERRED_PAYMENT_SHEET if PREFERRED_PAYMENT_SHEET in xl.sheet_names else xl.sheet_names[0]
    df = xl.parse(sheet)
    df = clean_dates(df)

    # detect booking column by matching GKC values
    booking_col = None
    for col in df.columns:
        sample = df[col].astype(str).str.strip()
        if sample.isin(gkc_values).any():
            booking_col = col
            break

    if booking_col is None:
        raise ValueError("No column in payment file matches GKC values")

    df[GKC_COLUMN] = df[booking_col].astype(str).str.strip()

    if STATUS_COLUMN not in df.columns:
        raise ValueError("Status column missing in payment file")

    df[STATUS_COLUMN] = df[STATUS_COLUMN].astype(str).str.strip()
    return df

# ================= UI =================
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    building = st.selectbox("Building", BUILDINGS)
with c2:
    flat_no = st.text_input("Flat No")
with c3:
    search = st.button("Search", use_container_width=True)

# ================= LOGIC =================
if search:
    if not flat_no.strip():
        st.error("Please enter Flat Number")
        st.stop()

    allot_df = load_allotment(building)

    if flat_no not in allot_df[FLAT_COLUMN].values:
        st.error("Invalid flat number")
        st.stop()

    row = allot_df[allot_df[FLAT_COLUMN] == flat_no].iloc[0]

    if not row[GKC_COLUMN] or row[GKC_COLUMN].lower() == "nan":
        st.warning("No booking available for this flat")
        st.stop()

    st.success("Flat details found")

    # ---------- Allotment ----------
    st.subheader("Allotment Details")
    for k, v in row.items():
        a, b, c = st.columns([2, 4, 1])
        a.write(k)
        b.write(str(v))
        with c:
            copy_button(v)

    # ---------- Payment ----------
    try:
        payment_df = load_payment(allot_df[GKC_COLUMN].unique())
    except Exception as e:
        st.error(str(e))
        st.stop()

    st.subheader("Payment Details (Cleared)")

    pay = payment_df[
        (payment_df[GKC_COLUMN] == row[GKC_COLUMN]) &
        (payment_df[STATUS_COLUMN].str.contains(STATUS_VALUE, case=False, na=False))
    ]

    if pay.empty:
        st.info("No cleared payments found")
        st.stop()

    pay = pay.drop(columns=[c for c in HIDE_PAYMENT_COLUMNS if c in pay.columns], errors="ignore")

    headers = st.columns(len(pay.columns) + 1)
    for i, col in enumerate(pay.columns):
        headers[i].markdown(f"**{col}**")
    headers[-1].markdown("**Copy**")

    for _, r in pay.iterrows():
        cols = st.columns(len(pay.columns) + 1)
        for i, col in enumerate(pay.columns):
            cols[i].write(str(r[col]))
            with cols[-1]:
                copy_button(r[col])
