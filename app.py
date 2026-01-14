import streamlit as st
import pandas as pd
import os

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

BUILDINGS = [
    "AMAZON A", "AMAZON B",
    "DANUBE A", "DANUBE B", "DANUBE C", "DANUBE D",
    "TAPI A"
]

# ================= PAGE =================
st.set_page_config(page_title="Flat Dashboard", layout="wide")

l, r = st.columns([6, 1])
with l:
    st.title("Flat Allotment & Payment Dashboard")
    st.caption("Search flat details and cleared payments instantly")
with r:
    logout()

# ================= HELPERS =================
def clean_dates(df):
    for col in df.columns:
        if "date" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%d/%m/%Y")
    return df

@st.cache_data
def load_allotment(building):
    df = pd.read_excel(ALLOTMENT_FILE, sheet_name=building)
    df[FLAT_COLUMN] = df[FLAT_COLUMN].astype(str).str.strip()
    df[GKC_COLUMN] = df[GKC_COLUMN].astype(str).str.strip()
    return clean_dates(df)

@st.cache_data
def load_payment(all_gkc):
    xl = pd.ExcelFile(PAYMENT_FILE)
    df = clean_dates(xl.parse(xl.sheet_names[0]))

    # Auto-detect booking / GKC column
    booking_col = None
    for c in df.columns:
        if df[c].astype(str).isin(all_gkc).any():
            booking_col = c
            break

    if booking_col is None:
        st.error("Booking / GKC column not found in payment file")
        st.stop()

    df[GKC_COLUMN] = df[booking_col].astype(str)
    df[STATUS_COLUMN] = df[STATUS_COLUMN].astype(str)
    return df

# ================= SEARCH UI =================
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    building = st.selectbox("Building", BUILDINGS)
with c2:
    flat_no = st.text_input("Flat No")
with c3:
    search = st.button("Search", use_container_width=True)

# ================= SEARCH LOGIC =================
if search:
    if not flat_no.strip():
        st.error("Please enter Flat Number")
        st.stop()

    allot_df = load_allotment(building)

    if flat_no not in allot_df[FLAT_COLUMN].values:
        st.error("Invalid flat number")
        st.stop()

    row = allot_df[allot_df[FLAT_COLUMN] == flat_no].iloc[0]

    if not row[GKC_COLUMN] or str(row[GKC_COLUMN]).lower() == "nan":
        st.warning("No booking available for this flat")
        st.stop()

    st.success("Flat details found")

    # ================= ALLOTMENT DETAILS =================
    st.subheader("Allotment Details")

    allot_table = row.to_frame(name="Value")

    st.data_editor(
        allot_table,
        disabled=True,
        use_container_width=True
    )

    if st.button("Copy All Allotment Details"):
        text = "\n".join([f"{k}: {v}" for k, v in allot_table["Value"].items()])
        st.code(text, language="text")
        st.caption("Select text above and press Ctrl + C")

    # ================= PAYMENT DETAILS =================
    st.subheader("Payment Details (Cleared)")

    payment_df = load_payment(allot_df[GKC_COLUMN].unique())

    pay = payment_df[
        (payment_df[GKC_COLUMN] == row[GKC_COLUMN]) &
        (payment_df[STATUS_COLUMN].str.contains(STATUS_VALUE, case=False))
    ]

    if pay.empty:
        st.info("No cleared payments found")
        st.stop()

    # Sort by date
    date_cols = [c for c in pay.columns if "date" in c.lower()]
    if date_cols:
        pay["_d"] = pd.to_datetime(pay[date_cols[0]], errors="coerce")
        pay = pay.sort_values("_d").drop(columns="_d")

    pay = pay.reset_index(drop=True)

    st.data_editor(
        pay,
        disabled=True,
        use_container_width=True
    )

    if st.button("Copy All Payment Details"):
        text = ""
        for i, r in pay.iterrows():
            text += f"\n--- Payment {i + 1} ---\n"
            for col in pay.columns:
                text += f"{col}: {r[col]}\n"
        st.code(text, language="text")
        st.caption("Select text above and press Ctrl + C")
