import streamlit as st
import pandas as pd
import os

# --- Configuration ---
# The name the Streamlit application is looking for
EXPECTED_FILENAME = 'transformed_schedule_data.csv' 
# The name of the file you originally uploaded to the environment
FALLBACK_FILENAME = 'course_data.csv'

def load_data():
    """
    Tries to load the data using the expected name, and falls back to 
    the original uploaded name if the first attempt fails.
    """
    # 1. Try the file name the application expects
    if os.path.exists(EXPECTED_FILENAME):
        st.info(f"Loading data from **{EXPECTED_FILENAME}**...")
        return pd.read_csv(EXPECTED_FILENAME)
    
    # 2. If that fails, try the original file name
    elif os.path.exists(FALLBACK_FILENAME):
        st.warning(f"Could not find **{EXPECTED_FILENAME}**. Falling back to **{FALLBACK_FILENAME}**...")
        return pd.read_csv(FALLBACK_FILENAME)

    # 3. If both fail, raise the error 
    else:
        st.error(f"Error: Neither **{EXPECTED_FILENAME}** nor **{FALLBACK_FILENAME}** were found.")
        st.stop()


# --- Streamlit Application ---

st.set_page_config(layout="wide", page_title="Course Schedule Viewer")

st.title("📚 University Course Schedule")
st.markdown("Use the filters below to browse the Fall 2025 offerings.")

try:
    df = load_data()

    # --- Data Cleaning and Preparation (As needed for the application) ---
    # Ensure column names are stripped of whitespace
    df.columns = df.columns.str.strip()
    
    # Clean up the Day columns
    day_mapping = {'U': 'Sun', 'Sat': 'Sat', 'Sun': 'Sun', 'Tue': 'Tue', 'Wed': 'Wed'}
    df['Day1'] = df['Day1'].astype(str).str.strip().map(day_mapping).fillna(df['Day1'])
    df['Day2'] = df['Day2'].astype(str).str.strip().map(day_mapping).fillna(df['Day2'])
    
    # Remove unnecessary columns for display
    df_display = df.drop(columns=['Room2', 'Time2'], errors='ignore')
    
    # --- Filters ---
    st.sidebar.header("Filter Options")
    
    all_programs = df['Program'].unique().tolist()
    selected_programs = st.sidebar.multiselect("Select Program", all_programs, default=all_programs)
    
    all_days = ['Sat', 'Sun', 'Tue', 'Wed']
    selected_days = st.sidebar.multiselect("Select Meeting Day", all_days, default=all_days)

    # --- Filtering Logic ---
    filtered_df = df[df['Program'].isin(selected_programs)]
    
    if selected_days:
        day_filter = filtered_df['Day1'].isin(selected_days) | filtered_df['Day2'].isin(selected_days)
        filtered_df = filtered_df[day_filter]

    st.subheader(f"Total Courses Found: {len(filtered_df)}")
    
    # --- Display Table ---
    st.dataframe(
        filtered_df, 
        use_container_width=True,
        hide_index=True,
        column_order=('Formal Code', 'Title', 'Section', 'Day1', 'Day2', 'Time1', 'Faculty Full Name', 'Cr.'),
        column_config={
            "Formal Code": "Code",
            "Title": "Course Title",
            "Day1": "Day 1",
            "Day2": "Day 2",
            "Time1": "Time",
            "Faculty Full Name": "Faculty",
            "Cr.": "Credits"
        }
    )

except Exception as e:
    # This catches other errors that might occur after the file is loaded (e.g., column errors)
    st.error(f"An error occurred during data processing: {e}")
