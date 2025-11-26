import streamlit as st
import pandas as pd
from rapidfuzz import fuzz, process  # For fuzzy matching

# -------------------------------
# Helper Functions
# -------------------------------

def load_excel_with_header_detection(file, expected_columns):
    """Detects header row and loads Excel file."""
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
    """Creates normalized full name column for matching."""
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
    """Extracts and normalizes grade from event string."""
    tokens = event.split()
    grade = tokens[-1]
    # Handle multi-word grades
    if len(tokens) >= 2 and " ".join(tokens[-2:]) in ["A Reserve", "A Open"]:
        grade = " ".join(tokens[-2:])
    # Normalize to grading list format
    grade_map = {"A Reserve": "A RES", "A Open": "A"}
    return grade_map.get(grade, grade)

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
        grade_order = ["D", "C", "B", "A RES", "A"]

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
                best_match, temp_confidence, _ = process.extractOne(entrant_name, choices, scorer=fuzz.token_sort_ratio)

                if temp_confidence >= 85:
                    matched_row = grading_df[grading_df['full_name'] == best_match].iloc[0]
                    match_status = "Name Search"
                    confidence = temp_confidence
                else:
                    short_name = (entrant.get('Firstname', '').strip() + " " + entrant.get('Name', '').strip()).lower()
                    best_match, temp_confidence, _ = process.extractOne(short_name, choices, scorer=fuzz.token_sort_ratio)
                    if temp_confidence >= 85:
                        matched_row = grading_df[grading_df['full_name'] == best_match].iloc[0]
                        match_status = "Name Search"
                        confidence = temp_confidence
                    else:
                        confidence = 0

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

        # Convert results to DataFrame
        results_df = pd.DataFrame(results)

        # -------------------------------
        # Apply Tournament Rules
        # -------------------------------
        violations_list = []

        for idx, row in results_df.iterrows():
            events = row['Events']
            event_list = [e.strip() for e in str(events).split(",")]

            # Count all events for max event rule
            total_events = len([e for e in event_list if e])

            # Filter out age-based events for grading/span checks
            filtered_events = [e for e in event_list if not any(x in e for x in ["U11", "U13", "U15", "45+"])]
            event_grades = [parse_event_grade(e) for e in filtered_events]
            normalized_grades = [g for g in event_grades if g in grade_order]

            entrant_violations = []

            # Rule 1: Max events (applies to all)
            if total_events > 3:
                entrant_violations.append("More than 3 events")

            # Rule 2: Grade span (skip age-based events)
            if normalized_grades:
                min_grade = min(normalized_grades, key=lambda g: grade_order.index(g))
                max_grade = max(normalized_grades, key=lambda g: grade_order.index(g))
                span = grade_order.index(max_grade) - grade_order.index(min_grade)
                if span >= 2:
                    entrant_violations.append("Grade span exceeds 2 levels")

            # Rule 3: Grade eligibility (check per event type)
            if matched_row is not None:
                for e in filtered_events:
                    eg = parse_event_grade(e)
                    if eg in grade_order:
                        if e.startswith(("MS", "WS")) and row['Singles Grade'] in grade_order:
                            if grade_order.index(eg) < grade_order.index(row['Singles Grade']):
                                entrant_violations.append(f"Singles event below grade: {eg}")
                        elif e.startswith(("MD", "WD")) and row['Doubles Grade'] in grade_order:
                            if grade_order.index(eg) < grade_order.index(row['Doubles Grade']):
                                entrant_violations.append(f"Doubles event below grade: {eg}")
                        elif e.startswith("XD") and row['Mixed Grade'] in grade_order:
                            if grade_order.index(eg) < grade_order.index(row['Mixed Grade']):
                                entrant_violations.append(f"Mixed event below grade: {eg}")

            violations_list.append(", ".join(entrant_violations) if entrant_violations else "OK")

        results_df['Rule Violations'] = violations_list

        # Display main results with violations
        st.subheader("Matching Results with Rule Checks")
        st.dataframe(results_df)

        # Display entrants with violations
        violations_df = results_df[results_df['Rule Violations'] != "OK"]
        st.subheader("⚠️ Entrants with Rule Violations")
        st.dataframe(violations_df[['Entrant Name', 'Events', 'Rule Violations']])

        # -------------------------------
        # Generate "No Match" Flags Table
        # -------------------------------
        no_match_df = results_df[results_df['Match Status'] == "No Match"].copy()
        exclude_keywords = ["U11", "U13", "U15", "45+"]
        no_match_df = no_match_df[~no_match_df['Events'].str.contains('|'.join(exclude_keywords), case=False, na=False)]

        st.subheader("⚠️ No Match Flags (Filtered)")
        st.write("Entrants with no match (excluding U11, U13, U15, and 45+ events):")
        st.dataframe(no_match_df[['Entrant Name', 'Events']])

    except Exception as e:
        st.error(f"Error processing files: {e}")

else:
    st.info("Please upload both the grading list and entrant list to proceed.")
