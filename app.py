
import streamlit as st
import pandas as pd
from rapidfuzz import fuzz, process  # For fuzzy matching
from datetime import datetime

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
# GRADING LIST SECTION
# -------------------------------
st.header("Grading List")
st.write("Upload the latest grading list (Excel format).")

grading_file = st.file_uploader("Upload Grading List", type=["xlsx"])
entrant_file = st.file_uploader("Upload Entrant List", type=["xlsx"])

# -------------------------------
# PROCESS FILES IF BOTH ARE UPLOADED
# -------------------------------
if grading_file and entrant_file:
    # Read grading list
    grading_df = pd.read_excel(grading_file)
    # Expected columns: Surname, Firstname, Member ID, Singles, Doubles, Mixed

    # Read entrant list
    entrant_df = pd.read_excel(entrant_file)
    # Expected columns: Name (Surname), Firstname, Middlename (optional), Member ID, Events

    # Normalize names for matching
    grading_df['full_name'] = (grading_df['Firstname'].str.strip() + " " + grading_df['Surname'].str.strip()).str.lower()
    entrant_df['full_name'] = (entrant_df['Firstname'].str.strip() + " " + entrant_df['Name'].str.strip()).str.lower()

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

else:
    st.info("Please upload both the grading list and entrant list to proceed.")
