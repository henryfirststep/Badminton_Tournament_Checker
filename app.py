# Import necessary libraries
import streamlit as st  # Streamlit for building the web app
import pandas as pd     # Pandas for handling Excel data
from datetime import datetime  # For timestamps (e.g., grading list updates)

# -------------------------------
# APP TITLE AND INTRODUCTION
# -------------------------------
# Display the main title of the app

st.title("BEC WIP") # Soon, title will be "BAWA Tournament Software Checker"

# -------------------------------
# TOURNAMENT DETAILS SECTION
# -------------------------------
# This section collects basic information about the tournament and the checker
st.header("Tournament Details")

# Text input for the tournament name
tournament_name = st.text_input("Tournament Name")

# Text input for the name of the person performing the check
checker_name = st.text_input("Your Name")

# -------------------------------
# GRADING LIST SECTION
# -------------------------------
# This section handles the grading list upload and displays revision info
st.header("Grading List")

# Instruction for the user
st.write("Upload the latest grading list (Excel format).")

# File uploader for the grading list (accepts .xlsx files only)
grading_file = st.file_uploader("Upload Grading List", type=["xlsx"])

# Placeholder for grading list revision info
# Later, this will be dynamically updated using GitHub commit history
st.subheader("Current Grading List Info")
st.write("**Last Updated:** (placeholder)")  # Will show actual timestamp later
st.write("**Update Comment:** (placeholder)")  # Will show last commit message later

# Button to view revision history (future feature)
if st.button("View Revision History"):
    st.info("Revision history feature coming soon!")  # Placeholder message

# -------------------------------
# ENTRANT LIST SECTION
# -------------------------------
# This section handles the entrant list upload
st.header("Entrant List")

# Instruction for the user
st.write("Upload the entrant list exported from Tournament Software.")

# File uploader for the entrant list (accepts .xlsx files only)
entrant_file = st.file_uploader("Upload Entrant List", type=["xlsx"])

# -------------------------------
# ANALYSIS PLACEHOLDER
# -------------------------------
# This button will trigger the analysis once both files are uploaded
if st.button("Run Analysis"):
    # Check if both files are uploaded
    if grading_file and entrant_file:
        # Placeholder success message
        st.success("Analysis will run here (coming soon).")
    else:
        # Error message if files are missing
        st.error("Please upload both files before running analysis.")

# -------------------------------
# REPORT DOWNLOAD PLACEHOLDER
# -------------------------------
# This section will allow users to download the final report
st.header("Download Report")
st.write("Report generation feature coming soon.")

