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
            st.error("Invalid credentials")

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

@st.cache_data
def load_allotment(building):
    df = pd.read_excel(ALLOTMENT_FILE, sheet_name=building)
    df[FLAT_COLUMN] = df[FLAT_COLUMN].astype(str).str.strip()
    df[GKC_COLUMN] = df[GKC_COLUMN].astype(str).str.strip()
    return clean_dates(df)

@st.cache_data
def load_payment(all_gkc):
    xl = pd.ExcelFile(PAYMENT_FILE)
    sheet = xl.sheet_names[0]
    df = clean_dates(xl.parse(sheet))

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

# ================= SEARCH =================
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    building = st.selectbox("Building", BUILDINGS)
with c2:
    flat_no = st.text_input("Flat No")
with c3:
    search = st.button("Search", use_container_width=True)

if search:
    if not flat_no.strip():
        st.error("Enter flat number")
        st.stop()

    allot_df = load_allotment(building)

    if flat_no not in allot_df[FLAT_COLUMN].values:
        st.error("Invalid flat number")
        st.stop()

    row = allot_df[allot_df[FLAT_COLUMN] == flat_no].iloc[0]

    if not row[GKC_COLUMN]:
        st.warning("No booking available for this flat")
        st.stop()

    st.success("Flat details found")

    # ================= ALLOTMENT =================
    st.subheader("Allotment Details")
    st.dataframe(
        pd.DataFrame(row, columns=["Value"]),
        use_container_width=True
    )

    # ================= PAYMENT =================
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

    # ---------- TABLE ----------
    st.dataframe(pay, use_container_width=True)

    # ---------- COPY PER FIELD ----------
    st.subheader("Copy Payment Details")

    for i, r in pay.iterrows():
        with st.expander(f"Payment {i+1}"):
            for col in pay.columns:
                a, b, c = st.columns([2, 4, 1])
                a.write(col)
                b.write(str(r[col]))
                if c.button("Copy", key=f"{i}_{col}"):
                    st.session_state["clipboard"] = str(r[col])
                    st.success(f"{col} copied")
