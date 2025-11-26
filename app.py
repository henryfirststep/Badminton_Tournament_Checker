
import streamlit as st
import pandas as pd
from rapidfuzz import fuzz, process  # For fuzzy matching
from datetime import datetime

# -------------------------------
# Helper Functions
# -------------------------------

def load_excel_with_header_detection(file, expected_columns):
    """
    Reads an Excel file and automatically detects the header row
    by searching for expected column names.
    :param file: Uploaded file object
    :param expected_columns: List of column names to look for
    :return: DataFrame with correct header
    """
    # Read the entire sheet without headers
    temp_df = pd.read_excel(file, header=None)

    # Detect header row by checking if expected columns exist in a row
    header_row = None
    for i, row in temp_df.iterrows():
        if all(col in row.values for col in expected_columns):
            header_row = i
            break

    if header_row is None:
        raise ValueError("Could not find header row with expected columns.")

    # Re-read the file using the detected header row
    df = pd.read_excel(file, header=header_row)
    return df

def build_full_name(df, surname_col, firstname_col, middlename_col=None):
    """
    Creates a normalized full name column for matching.
    Handles optional middle names.
    """
    if middlename_col and middlename_col in df.columns:
        df['full_name'] = (
            df[firstname_col].fillna('').str.strip() + " " +
            df[middlename_col].fillna('').str.strip() + " " +
            df[surname_col].fillna('').str.strip()
        ).str.lower()
    else:
        df['full_name'] = (
            df[firstname_col].fillna('').str.strip() + " " +
            df[surname_col].fillna('').str.strip()
        ).str.lower()
    return df

# -------------------------------
# APP TITLE AND INTRODUCTION
# -------------------------------
st.title("🏸 Badminton Tournament Entry Checker")

# -------------------------------
# TOURNAMENT DETAILS SECTION
# -------------------------------
st.header("Tournament Details")
tournament_name = st.text_input("Tournament Name")
checker_name = st.text_input("Your Name")

# -------------------------------
# FILE UPLOAD SECTION
# -------------------------------
st.header("Upload Files")
grading_file = st.file_uploader("Upload Grading List (Excel)", type=["xlsx"])
entrant_file = st.file_uploader("Upload Entrant List (Excel)", type=["xlsx"])

# -------------------------------
# PROCESS FILES IF BOTH ARE UPLOADED
# -------------------------------
if grading_file and entrant_file:
    try:
        # Load grading list with header detection
        grading_df = load_excel_with_header_detection(grading_file, ["Surname", "Firstname", "Member ID"])
        # Build full name for grading list
        grading_df = build_full_name(grading_df, surname_col="Surname", firstname_col="Firstname")

        # Load entrant list with header detection
        entrant_df = load_excel_with_header_detection(entrant_file, ["Name", "Firstname", "Member ID"])
        # Build full name for entrant list (handle optional Middlename)
        middlename_col = "Middlename" if "Middlename" in entrant_df.columns else None
        entrant_df = build_full_name(entrant_df, surname_col="Name", firstname_col="Firstname", middlename_col=middlename_col)

        # Prepare results list
        results = []

        # Loop through each entrant
        for idx, entrant in entrant_df.iterrows():
            entrant_name = entrant['full_name']
            entrant_id = str(entrant.get('Member ID', '')).strip()
            events = entrant.get('Events', '')

            match_status = "No Match"
            confidence = 0
            matched_row = None

            # First try exact Member ID match
            if entrant_id and entrant_id in grading_df['Member ID'].astype(str).values:
                matched_row = grading_df[grading_df['Member ID'].astype(str) == entrant_id].iloc[0]
                match_status = "Exact ID Match"
                confidence = 100
            else:
                # Fallback: Fuzzy name matching
                choices = grading_df['full_name'].tolist()
                best_match, confidence, _ = process.extractOne(entrant_name, choices, scorer=fuzz.token_sort_ratio)
                if confidence >= 85:  # Threshold for acceptable match
                    matched_row = grading_df[grading_df['full_name'] == best_match].iloc[0]
                    match_status = "Fuzzy Name Match"

            # Collect result
            if matched_row is not None:
                results.append({
                    "Entrant Name": entrant_name.title(),
                    "Member ID": entrant_id,
                    "Events": events,
                    "Matched Name": matched_row['full_name'].title(),
                    "Singles Grade": matched_row['Singles'],
                    "Doubles Grade": matched_row['Doubles'],
                    "Mixed Grade": matched_row['Mixed'],
                    "Match Status": match_status,
                    "Confidence": confidence
                })
            else:
                results.append({
                    "Entrant Name": entrant_name.title(),
                    "Member ID": entrant_id,
                    "Events": events,
                    "Matched Name": "None",
                    "Singles Grade": "N/A",
                    "Doubles Grade": "N/A",
                    "Mixed Grade": "N/A",
                    "Match Status": match_status,
                    "Confidence": confidence
                })

        # Convert results to DataFrame
        results_df = pd.DataFrame(results)

        # Display results in Streamlit
        st.subheader("Matching Results")
        st.dataframe(results_df)

    except Exception as e:
        st.error(f"Error processing files: {e}")

else:
    st.info("Please upload both the grading list and entrant list to proceed.")
