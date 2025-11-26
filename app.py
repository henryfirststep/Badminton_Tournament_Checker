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
    temp_df = pd.read_excel(file, header=None)
    header_row = None
    for i, row in temp_df.iterrows():
        if all(col in row.values for col in expected_columns):
            header_row = i
            break
    if header_row is None:
        raise ValueError("Could not find header row with expected columns.")
    return pd.read_excel(file, header=header_row)

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
        # Load grading list
        grading_df = load_excel_with_header_detection(grading_file, ["Surname", "Firstname", "Member ID"])
        grading_df = build_full_name(grading_df, surname_col="Surname", firstname_col="Firstname")

        # Load entrant list
        entrant_df = load_excel_with_header_detection(entrant_file, ["Name", "Firstname", "Member ID"])
        middlename_col = "Middlename" if "Middlename" in entrant_df.columns else None
        entrant_df = build_full_name(entrant_df, surname_col="Name", firstname_col="Firstname", middlename_col=middlename_col)

        # Prepare results
        results = []

        for idx, entrant in entrant_df.iterrows():
            entrant_name = entrant['full_name']
            entrant_id_raw = entrant.get('Member ID', '')
            events = entrant.get('Events', '')

            # Handle NaN and convert to string safely
            entrant_id = str(entrant_id_raw).strip() if pd.notna(entrant_id_raw) else ""

            match_status = "No Match"
            confidence = 0
            matched_row = None

            # Check Member ID match only if entrant_id is not empty
            if entrant_id != "":
                grading_ids = grading_df['Member ID'].dropna().astype(str).values
                if entrant_id in grading_ids:
                    matched_row = grading_df[grading_df['Member ID'].astype(str) == entrant_id].iloc[0]
                    match_status = "Member ID Match"
                    confidence = 100

            # If no ID match, try fuzzy name matching
            if matched_row is None:
                choices = grading_df['full_name'].tolist()

                # Attempt 1: Full name (FN MN SN)
                best_match, temp_confidence, _ = process.extractOne(entrant_name, choices, scorer=fuzz.token_sort_ratio)

                if temp_confidence >= 85:  # Acceptable threshold for full name
                    matched_row = grading_df[grading_df['full_name'] == best_match].iloc[0]
                    match_status = "Name Search"
                    confidence = temp_confidence
                else:
                    # Attempt 2: Short name (FN SN only)
                    short_name = (entrant.get('Firstname', '').strip() + " " + entrant.get('Name', '').strip()).lower()
                    best_match, temp_confidence, _ = process.extractOne(short_name, choices, scorer=fuzz.token_sort_ratio)

                    if temp_confidence >= 85:  # Acceptable threshold for short name
                        matched_row = grading_df[grading_df['full_name'] == best_match].iloc[0]
                        match_status = "Name Search"
                        confidence = temp_confidence
                    else:
                        confidence = 0  # Reset confidence for rejected matches

            # Collect result
            if matched_row is not None:
                results.append({
                    "Entrant Name": entrant_name.title(),
                    "Member ID": entrant_id if entrant_id != "" else "None",
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
                    "Member ID": entrant_id if entrant_id != "" else "None",
                    "Events": events,
                    "Matched Name": "None",
                    "Singles Grade": "N/A",
                    "Doubles Grade": "N/A",
                    "Mixed Grade": "N/A",
                    "Match Status": match_status,
                    "Confidence": confidence
                })

        # Display main results table
        results_df = pd.DataFrame(results)
        st.subheader("Matching Results")
        st.dataframe(results_df)

        # -------------------------------
        # Generate "No Match" Flags Table
        # -------------------------------
        no_match_df = results_df[results_df['Match Status'] == "No Match"].copy()

        # Exclude entrants with U11, U15, or 45+ events
        exclude_keywords = ["U11", "U15", "45+"]
        no_match_df = no_match_df[~no_match_df['Events'].str.contains('|'.join(exclude_keywords), case=False, na=False)]

        # Prepare closest matches for these entrants
        closest_matches = []
        choices = grading_df['full_name'].tolist()

        for idx, entrant in no_match_df.iterrows():
            entrant_name = entrant['Entrant Name'].lower()
            best_match, temp_confidence, _ = process.extractOne(entrant_name, choices, scorer=fuzz.token_sort_ratio)

            matched_row = grading_df[grading_df['full_name'] == best_match].iloc[0]

            closest_matches.append({
                "Entrant Name": entrant['Entrant Name'],
                "Closest Match": best_match.title(),
                "Singles Grade": matched_row['Singles'],
                "Doubles Grade": matched_row['Doubles'],
                "Mixed Grade": matched_row['Mixed'],
                "Confidence": temp_confidence
            })

        closest_match_df = pd.DataFrame(closest_matches)

        # Display the "No Match" flags table
        st.subheader("⚠️ No Match Flags (Filtered)")
        st.write("Entrants with no match (excluding U11, U15, and 45+ events) and their closest grading list match:")
        st.dataframe(closest_match_df)

    except Exception as e:
        st.error(f"Error processing files: {e}")

else:
    st.info("Please upload both the grading list and entrant list to proceed.")
