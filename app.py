import streamlit as st
import pandas as pd
from rapidfuzz import fuzz, process  # For fuzzy matching

# -------------------------------
# Page Configuration
# -------------------------------
st.set_page_config(page_title="Badminton Entry Checker", layout="wide", initial_sidebar_state="expanded")

# -------------------------------
# Helper Functions
# -------------------------------
def load_excel_with_header_detection(file, expected_columns):
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

def parse_event_grade(event):
    tokens = event.split()
    grade = tokens[-1]
    if len(tokens) >= 2 and " ".join(tokens[-2:]) in ["A Reserve", "A Open"]:
        grade = " ".join(tokens[-2:])
    grade_map = {"A Reserve": "A RES", "A Open": "A"}
    return grade_map.get(grade, grade)

# -------------------------------
# APP TITLE AND INTRODUCTION
# -------------------------------
st.title("BAWA Grading Committee Tournament Checking Tool")

st.markdown("""
#### This tool is designed to assist the Grading Committee of Badminton Association Western Australia.  
All intellectual property remains solely with Henry Le.  
For inquiries or support, please contact: **inbox.henry.le@gmail.com**
Version 4.0
""")

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
        grading_df = load_excel_with_header_detection(grading_file, ["Surname", "Firstname", "Member ID"])
        grading_df = build_full_name(grading_df, surname_col="Surname", firstname_col="Firstname")

        entrant_df = load_excel_with_header_detection(entrant_file, ["Name", "Firstname", "Member ID"])
        middlename_col = "Middlename" if "Middlename" in entrant_df.columns else None
        entrant_df = build_full_name(entrant_df, surname_col="Name", firstname_col="Firstname", middlename_col=middlename_col)

        results = []
        grade_order = ["D", "C", "B", "A RES", "A"]

        for idx, entrant in entrant_df.iterrows():
            entrant_name = entrant['full_name']
            entrant_id_raw = entrant.get('Member ID', '')
            events = entrant.get('Events', '')
            email = entrant.get('Email', 'N/A')
            entrant_id = str(entrant_id_raw).strip() if pd.notna(entrant_id_raw) else ""

            match_status = "No Match"
            matched_row = None

            # Match by Member ID
            if entrant_id != "":
                grading_ids = grading_df['Member ID'].dropna().astype(str).values
                if entrant_id in grading_ids:
                    matched_row = grading_df[grading_df['Member ID'].astype(str) == entrant_id].iloc[0]
                    match_status = "Member ID Match"

            # Fuzzy match if no ID match
            if matched_row is None:
                choices = grading_df['full_name'].tolist()
                best_match, temp_confidence, _ = process.extractOne(entrant_name, choices, scorer=fuzz.token_sort_ratio)
                if temp_confidence >= 85:
                    matched_row = grading_df[grading_df['full_name'] == best_match].iloc[0]
                    match_status = "Name Search"
                else:
                    short_name = (entrant.get('Firstname', '').strip() + " " + entrant.get('Name', '').strip()).lower()
                    best_match, temp_confidence, _ = process.extractOne(short_name, choices, scorer=fuzz.token_sort_ratio)
                    if temp_confidence >= 85:
                        matched_row = grading_df[grading_df['full_name'] == best_match].iloc[0]
                        match_status = "Name Search"

            # Collect result
            if matched_row is not None:
                results.append({
                    "Entrant Name": entrant_name.title(),
                    "Email": email,
                    "Member ID": entrant_id if entrant_id != "" else "None",
                    "Events": events,
                    "Singles Grade": matched_row['Singles'],
                    "Doubles Grade": matched_row['Doubles'],
                    "Mixed Grade": matched_row['Mixed'],
                    "Match Status": match_status
                })
            else:
                results.append({
                    "Entrant Name": entrant_name.title(),
                    "Email": email,
                    "Member ID": entrant_id if entrant_id != "" else "None",
                    "Events": events,
                    "Singles Grade": "N/A",
                    "Doubles Grade": "N/A",
                    "Mixed Grade": "N/A",
                    "Match Status": match_status
                })

        results_df = pd.DataFrame(results)

        # -------------------------------
        # Apply Tournament Rules
        # -------------------------------
        violations_list = []

        for idx, row in results_df.iterrows():
            events = row['Events']
            event_list = [e.strip() for e in str(events).split(",")]
            total_events = len([e for e in event_list if e])
            filtered_events = [e for e in event_list if not any(x in e for x in ["U11", "U13", "U15", "45+"])]
            event_grades = [parse_event_grade(e) for e in filtered_events]
            normalized_grades = [g for g in event_grades if g in grade_order]

            entrant_violations = []

            # Max events rule
            if total_events > 3:
                entrant_violations.append("More than 3 events")

            # Grade span rule
            if normalized_grades:
                min_grade = min(normalized_grades, key=lambda g: grade_order.index(g))
                max_grade = max(normalized_grades, key=lambda g: grade_order.index(g))
                span = grade_order.index(max_grade) - grade_order.index(min_grade)
                if span >= 2:
                    entrant_violations.append("Grade span exceeds 2 levels")

            # Grade eligibility rule
            if row['Singles Grade'] in grade_order or row['Doubles Grade'] in grade_order or row['Mixed Grade'] in grade_order:
                for e in filtered_events:
                    eg = parse_event_grade(e)
                    if eg in grade_order:
                        if e.startswith(("MS", "WS")) and row['Singles Grade'] in grade_order:
                            if grade_order.index(eg) < grade_order.index(row['Singles Grade']):
                                entrant_violations.append(f"Singles graded too high: {row['Singles Grade']}")
                        elif e.startswith(("MD", "WD")) and row['Doubles Grade'] in grade_order:
                            if grade_order.index(eg) < grade_order.index(row['Doubles Grade']):
                                entrant_violations.append(f"Doubles graded too high: {row['Doubles Grade']}")
                        elif e.startswith("XD") and row['Mixed Grade'] in grade_order:
                            if grade_order.index(eg) < grade_order.index(row['Mixed Grade']):
                                entrant_violations.append(f"Mixed graded too high: {row['Mixed Grade']}")

            violations_list.append(", ".join(entrant_violations) if entrant_violations else "OK")

        results_df['Rule Violations'] = violations_list

        # -------------------------------
        # Display Tables
        # -------------------------------
        st.subheader("Full Report")
        st.dataframe(results_df[['Entrant Name', 'Email', 'Member ID', 'Events', 'Singles Grade', 'Doubles Grade', 'Mixed Grade', 'Match Status', 'Rule Violations']],
                     use_container_width=True)

        violations_df = results_df[results_df['Rule Violations'] != "OK"]
        st.subheader("⚠️ Entrants with Rule Violations")
        st.dataframe(violations_df[['Entrant Name', 'Email', 'Events', 'Rule Violations']], use_container_width=True)

        no_match_df = results_df[results_df['Match Status'] == "No Match"].copy()
        exclude_keywords = ["U11", "U13", "U15", "45+"]
        no_match_df = no_match_df[~no_match_df['Events'].str.contains('|'.join(exclude_keywords), case=False, na=False)]

        st.subheader("⚠️ No Match Flags (Filtered) - No Juniors or +45")
        st.dataframe(no_match_df[['Entrant Name', 'Email', 'Events']], use_container_width=True)

        # Age-based No Match Flags
        age_no_match_df = results_df[(results_df['Match Status'] == "No Match") &
                                     (results_df['Events'].str.contains('|'.join(exclude_keywords), case=False, na=False))]
        st.subheader("List of Juniors and +45 Entrants Not Found")
        st.dataframe(age_no_match_df[['Entrant Name', 'Email', 'Events']], use_container_width=True)

    except Exception as e:
        st.error(f"Error processing files: {e}")

else:
    st.info("Please upload both the grading list and entrant list to proceed.")
