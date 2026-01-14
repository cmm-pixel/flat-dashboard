import streamlit as st
import pandas as pd
import os
import streamlit.components.v1 as components

# ================= LOGIN =================
def login_page():
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if (
            username == st.secrets["auth"]["username"]
            and password == st.secrets["auth"]["password"]
        ):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid username or password")

def logout_button():
    if st.button("Logout"):
        st.session_state["authenticated"] = False
        st.rerun()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    login_page()
    st.stop()

# ================= CONFIG =================
BASE_PATH = "FORM DETAILS"

ALLOTMENT_FILE = os.path.join(BASE_PATH, "salesforce.xlsx")
PAYMENT_FILE   = os.path.join(BASE_PATH, "salesforce payment.xlsx")

FLAT_COLUMN   = "Flat"
GKC_COLUMN    = "GKC"
STATUS_COLUMN = "Status"
STATUS_VALUE  = "Cleared"

AADHAR_COLUMN = "Aadhar"
PREFERRED_PAYMENT_SHEET = "OLD Booking Tracker"

BUILDINGS = [
    "AMAZON A", "AMAZON B",
    "DANUBE A", "DANUBE B", "DANUBE C", "DANUBE D",
    "TAPI A"
]

HIDE_PAYMENT_COLUMNS = ["Sr. No.", "GKC", "Wing", "Flat No."]

PAYMENT_COLUMN_ORDER = [
    "Name of Applicant",
    "Amount",
    "Mode",
    "Cheque Number",
    "Bank Name",
    "Payment Made Against",
    "Status",
    "Unit No"
]

# ================= PAGE =================
st.set_page_config(page_title="Flat Allotment & Payment Dashboard", layout="wide")

top_left, top_right = st.columns([6, 1])
with top_left:
    st.title("Flat Allotment & Payment Dashboard")
    st.caption("Search flat details and cleared payments instantly")
with top_right:
    logout_button()

# ================= FILE CHECK =================
for f in [ALLOTMENT_FILE, PAYMENT_FILE]:
    if not os.path.exists(f):
        st.error(f"Missing file: {f}")
        st.stop()

# ================= HELPERS =================
def clean_dates(df):
    for c in df.columns:
        if "date" in c.lower():
            df[c] = pd.to_datetime(df[c], errors="coerce").dt.strftime("%d/%m/%Y")
    return df

def clean_aadhar(s):
    return s.astype(str).str.replace(" ", "", regex=False).str.replace("-", "", regex=False)

def clean_email(s):
    return s.astype(str).str.strip()

def copy_button(value):
    safe = str(value).replace("`", "").replace("$", "")
    components.html(
        f"""
        <button onclick="navigator.clipboard.writeText(`{safe}`)"
        style="padding:3px 8px;border:1px solid #ccc;border-radius:5px;cursor:pointer;">
        Copy
        </button>
        """,
        height=32
    )

# ================= LOAD PAYMENT (SAFE) =================
@st.cache_data
def load_payment():
    xl = pd.ExcelFile(PAYMENT_FILE)

    sheet = (
        PREFERRED_PAYMENT_SHEET
        if PREFERRED_PAYMENT_SHEET in xl.sheet_names
        else xl.sheet_names[0]
    )

    df = xl.parse(sheet)

    # ---------- AUTO-DETECT GKC COLUMN ----------
    possible_gkc_cols = [
        "GKC",
        "GKC No",
        "GKC Number",
        "GKC_ID",
        "Booking No",
        "Booking Number"
    ]

    gkc_col = None
    for c in df.columns:
        if c.strip() in possible_gkc_cols:
            gkc_col = c
            break

    if gkc_col is None:
        st.error("Payment file does not contain a GKC / Booking column")
        st.stop()

    # normalize column name
    df[GKC_COLUMN] = df[gkc_col].astype(str).str.strip()

    # ---------- STATUS COLUMN CHECK ----------
    if STATUS_COLUMN not in df.columns:
        st.error("Payment file does not contain Status column")
        st.stop()

    df[STATUS_COLUMN] = df[STATUS_COLUMN].astype(str).str.strip()

    return clean_dates(df)


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

    allot_df = pd.read_excel(ALLOTMENT_FILE, sheet_name=building)
    allot_df[FLAT_COLUMN] = allot_df[FLAT_COLUMN].astype(str).str.strip()
    allot_df[GKC_COLUMN]  = allot_df[GKC_COLUMN].astype(str).str.strip()
    allot_df = clean_dates(allot_df)

    if AADHAR_COLUMN in allot_df.columns:
        allot_df[AADHAR_COLUMN] = clean_aadhar(allot_df[AADHAR_COLUMN])

    for e in ["Email1", "Email2", "Email 1", "Email 2"]:
        if e in allot_df.columns:
            allot_df[e] = clean_email(allot_df[e])

    result = allot_df[allot_df[FLAT_COLUMN].str.upper() == flat_no.upper()]

    if result.empty:
        st.error("Invalid flat number")
        st.stop()

    row = result.iloc[0]

    if pd.isna(row[GKC_COLUMN]) or str(row[GKC_COLUMN]).strip() == "":
        st.warning("No booking available for this flat")
        st.stop()

    st.success("Flat details found")

    # ================= ALLOTMENT DETAILS =================
    st.subheader("Allotment Details")

    for field, value in row.items():
        c1, c2, c3 = st.columns([2, 4, 1])
        c1.write(field)
        c2.write(str(value))
        with c3:
            copy_button(value)

    # ================= PAYMENT DETAILS =================
    st.subheader("Payment Details (Cleared)")

    payment_result = payment_df[
        (payment_df[GKC_COLUMN] == row[GKC_COLUMN]) &
        (payment_df[STATUS_COLUMN].str.contains(STATUS_VALUE, case=False, na=False))
    ]

    if payment_result.empty:
        st.info("No cleared payments found")
        st.stop()

    payment_display = payment_result.drop(
        columns=[c for c in HIDE_PAYMENT_COLUMNS if c in payment_result.columns],
        errors="ignore"
    )

    date_cols = [c for c in payment_display.columns if "date" in c.lower()]
    if date_cols:
        dc = date_cols[0]
        payment_display["_d"] = pd.to_datetime(payment_display[dc], errors="coerce")
        payment_display = payment_display.sort_values("_d").drop(columns="_d")

    ordered = [c for c in PAYMENT_COLUMN_ORDER if c in payment_display.columns]
    rest = [c for c in payment_display.columns if c not in ordered]
    payment_display = payment_display[ordered + rest].reset_index(drop=True)

    header_cols = st.columns(len(payment_display.columns) + 1)
    for i, col in enumerate(payment_display.columns):
        header_cols[i].markdown(f"**{col}**")
    header_cols[-1].markdown("**Copy**")

    for _, r in payment_display.iterrows():
        row_cols = st.columns(len(payment_display.columns) + 1)
        for i, col in enumerate(payment_display.columns):
            row_cols[i].write(str(r[col]))
            with row_cols[-1]:
                copy_button(r[col])

