import streamlit as st
import pandas as pd
import os
import streamlit.components.v1 as components

# ================= CONFIG =================
BASE_PATH = "FORM DETAILS"

ALLOTMENT_FILE = os.path.join(BASE_PATH, "salesforce.xlsx")
PAYMENT_FILE   = os.path.join(BASE_PATH, "salesforce payment.xlsx")

FLAT_COLUMN   = "Flat"
GKC_COLUMN    = "GKC"
STATUS_COLUMN = "Status"
STATUS_VALUE  = "Cleared"

AADHAR_COLUMN = "Aadhar"

PAYMENT_SHEET = "OLD Booking Tracker"

BUILDINGS = [
    "AMAZON A", "AMAZON B",
    "DANUBE A", "DANUBE B", "DANUBE C", "DANUBE D",
    "TAPI A"
]

HIDE_PAYMENT_COLUMNS = [
    "Sr. No.",
    "GKC",
    "Wing",
    "Flat No."
]

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
# ==========================================

st.set_page_config(page_title="Flat Allotment & Payment Dashboard", layout="wide")
st.title("Flat Allotment & Payment Dashboard")
st.caption("Search flat details and cleared payments instantly")

# ---------- FILE CHECK ----------
for f in [ALLOTMENT_FILE, PAYMENT_FILE]:
    if not os.path.exists(f):
        st.error(f"Missing file: {f}")
        st.stop()

# ---------- HELPERS ----------
def clean_dates(df):
    for col in df.columns:
        if "date" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%d/%m/%Y")
    return df

def clean_aadhar(series):
    return series.astype(str).str.replace(" ", "", regex=False).str.replace("-", "", regex=False)

def clean_email(series):
    return series.astype(str).str.strip()

def copy_button(text):
    safe_text = text.replace("`", "").replace("$", "")
    components.html(
        f"""
        <button onclick="navigator.clipboard.writeText(`{safe_text}`)"
        style="
            padding:6px 12px;
            border-radius:6px;
            border:1px solid #ccc;
            cursor:pointer;
            background-color:#f5f5f5;
            margin-top:4px;">
            Copy
        </button>
        """,
        height=40
    )

# ---------- LOAD PAYMENT DATA ----------
@st.cache_data
def load_payment():
    df = pd.read_excel(PAYMENT_FILE, sheet_name=PAYMENT_SHEET)
    df[GKC_COLUMN] = df[GKC_COLUMN].astype(str).str.strip()
    df[STATUS_COLUMN] = df[STATUS_COLUMN].astype(str).str.strip()
    df = clean_dates(df)
    return df

payment_df = load_payment()

# ---------- UI ----------
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    building = st.selectbox("Building", BUILDINGS)
with c2:
    flat_no = st.text_input("Flat No")
with c3:
    search = st.button("Search", use_container_width=True)

# ---------- SEARCH ----------
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

    for ec in ["Email1", "Email2", "Email 1", "Email 2"]:
        if ec in allot_df.columns:
            allot_df[ec] = clean_email(allot_df[ec])

    result = allot_df[allot_df[FLAT_COLUMN].str.upper() == flat_no.upper()]
    if result.empty:
        st.error("No flat data found")
        st.stop()

    st.success("Flat details found")

    # ---------- ALLOTMENT ----------
    st.subheader("Allotment Details")
    row = result.iloc[0]
    allotment_view = pd.DataFrame({"Value": row.astype(str)})
    st.dataframe(allotment_view, use_container_width=True)

    # ---------- PAYMENT ----------
    st.subheader("Payment Details (Cleared)")
    gkc = row[GKC_COLUMN]

    payment_result = payment_df[
        (payment_df[GKC_COLUMN] == gkc) &
        (payment_df[STATUS_COLUMN].str.contains(STATUS_VALUE, case=False, na=False))
    ]

    payment_display = payment_result.drop(
        columns=[c for c in HIDE_PAYMENT_COLUMNS if c in payment_result.columns],
        errors="ignore"
    )

    # Sort by any date column
    date_cols = [c for c in payment_display.columns if "date" in c.lower()]
    if date_cols:
        dc = date_cols[0]
        payment_display["_sort_date"] = pd.to_datetime(
            payment_display[dc], format="%d/%m/%Y", errors="coerce"
        )
        payment_display = payment_display.sort_values("_sort_date").drop(columns="_sort_date")

    ordered = [c for c in PAYMENT_COLUMN_ORDER if c in payment_display.columns]
    rest = [c for c in payment_display.columns if c not in ordered]
    payment_display = payment_display[ordered + rest].reset_index(drop=True)

    # ---------- ROW VIEW WITH COPY BUTTON ----------
    for _, r in payment_display.iterrows():
        cols = st.columns(len(payment_display.columns) + 1)

        row_text = []
        for idx, col in enumerate(payment_display.columns):
            cols[idx].write(str(r[col]))
            row_text.append(f"{col}: {r[col]}")

        with cols[-1]:
            copy_button("\n".join(row_text))
