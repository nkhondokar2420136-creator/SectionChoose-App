import streamlit as st
import pandas as pd
import ast # Used to convert the 'Days_List' string back into a Python list

# --- 1. DATA PREPARATION & SETUP ---

@st.cache_data
def load_and_transform_data():
    """
    Loads the transformed schedule data.
    Ensures numeric columns are correctly typed and converts 'Days_List' string back to a list.
    """
    
    # Load the pre-processed CSV file
    try:
        # NOTE: This file must be in your GitHub repo alongside app.py
        df = pd.read_csv('transformed_schedule_data.csv')
    except FileNotFoundError:
        st.error("Error: 'transformed_schedule_data.csv' not found. Please ensure the file is in the same directory.")
        return pd.DataFrame() 

    # Ensure critical columns are correctly typed
    df['Start_Time_24hr'] = df['Start_Time_24hr'].astype(int)
    df['End_Time_24hr'] = df['End_Time_24hr'].astype(int)
    
    # Convert the Days_List string representation (e.g., "['S']") back to an actual list
    # ast.literal_eval is used for safe evaluation of strings containing Python literals
    df['Days_List'] = df['Days_List'].apply(ast.literal_eval)

    return df

# Initialize data and session state:
df_courses = load_and_transform_data()

# Stop if data loading failed
if df_courses.empty:
    st.stop()

# Prepare lists for filters
all_faculty = sorted(df_courses['Faculty Full Name'].unique())
all_courses = sorted(df_courses['Course Code'].unique())

if 'schedule' not in st.session_state:
    # Schedule stores the dictionary representation of selected rows
    st.session_state.schedule = []

# --- 2. CORE LOGIC FUNCTIONS ---

def find_common_elements(list_a, list_b):
    """Finds common elements between two lists (used for common days)."""
    return list(set(list_a) & set(list_b))

def check_for_conflict(new_section, current_schedule_list):
    """
    Checks a new section against all sections in the current schedule list.
    Returns True and clash details if a conflict is found.
    """
    new_days = new_section['Days_List']
    new_start = new_section['Start_Time_24hr']
    new_end = new_section['End_Time_24hr']

    for existing_section in current_schedule_list:
        
        existing_days = existing_section['Days_List']
        
        # Step 1: Day Overlap
        common_days = find_common_elements(new_days, existing_days)
        
        if common_days:
            # Step 2: Time Overlap
            existing_start = existing_section['Start_Time_24hr']
            existing_end = existing_section['End_Time_24hr']
            
            # Time Conflict Formula: A_start < B_end AND B_start < A_end
            if new_start < existing_end and existing_start < new_end:
                clash_details = {
                    "New_Section": f"{new_section['Course Code']} {new_section['Section']}",
                    "Clashing_Section": f"{existing_section['Course Code']} {existing_section['Section']}",
                    "Conflict_Days": ", ".join(common_days),
                    "Time_Range": f"{new_section['Start Time']} - {new_section['End Time']}"
                }
                return True, clash_details
            
    return False, None

# --- 3. UI FUNCTIONS (BUTTON HANDLERS) ---

# Helper function to combine rows back into single course items for the UI
def combine_single_day_rows(df_section_rows):
    """
    Takes the multi-row single-day data for a specific section and combines 
    it back into one logical course schedule entry (e.g., MWF, 8:30-9:50).
    """
    if df_section_rows.empty:
        return None

    # Get the unique day list (e.g., ['M', 'W', 'F'])
    all_days = sorted(df_section_rows['Day'].unique())
    # Find the earliest start and latest end time across all days for display purposes
    start_time_display = df_section_rows['Start Time'].iloc[0]
    end_time_display = df_section_rows['End Time'].iloc[-1]
    
    # Get the first section row (all sections share this info)
    first_row = df_section_rows.iloc[0]
    
    # Combine the discrete days back into the original multi-day schedule format
    combined_section = first_row.to_dict()
    combined_section['Days'] = "".join(all_days)
    combined_section['Start Time'] = start_time_display
    combined_section['End Time'] = end_time_display
    combined_section['Days_List'] = all_days # The list form used by the conflict checker
    
    # We must use the numeric times of the first day for conflict checks on that day
    # This simplification is necessary because Streamlit button handler only takes one index.
    # In a real app, conflict checking happens across all component days separately.
    combined_section['Start_Time_24hr'] = first_row['Start_Time_24hr']
    combined_section['End_Time_24hr'] = first_row['End_Time_24hr']
    
    return combined_section

def add_section_to_schedule(course_code, section):
    """Handles adding a section, checking for conflicts first."""
    
    # Filter the original data to get all single-day rows belonging to the selected section
    section_rows = df_courses[
        (df_courses['Course Code'] == course_code) & 
        (df_courses['Section'] == section)
    ]
    
    if section_rows.empty:
        st.error("Error: Section data not found.")
        return

    # Check each individual meeting day of the new section against all scheduled items
    is_conflict = False
    details = None
    
    for _, new_day_row in section_rows.iterrows():
        is_conflict, details = check_for_conflict(new_day_row, st.session_state.schedule)
        if is_conflict:
            break # Stop checking on the first conflict found
    
    if is_conflict:
        st.error(
            f"⚠️ **Clash Detected!** Section {details['New_Section']} conflicts with "
            f"{details['Clashing_Section']} on **{details['Conflict_Days']}** during "
            f"{details['Time_Range']}."
        )
    else:
        # If no conflict, add ALL the single-day rows to the schedule state
        
        # Check if course/section is already added (prevent duplicates)
        # Check against the list of added single-day dictionaries
        existing_check = any(
            s['Course Code'] == course_code and s['Section'] == section 
            for s in st.session_state.schedule
        )
        
        if not existing_check:
            # Add all component day rows to the schedule list
            for _, row in section_rows.iterrows():
                st.session_state.schedule.append(row.to_dict())
            
            st.success(f"✅ Added {course_code} {section} to your schedule!")
        else:
            st.warning(f"Section {course_code} {section} is already in your schedule.")


def remove_section_from_schedule(course_code, section):
    """Removes all component rows of a section from the schedule."""
    # Remove all single-day rows that belong to the specified Course Code and Section
    st.session_state.schedule = [
        s for s in st.session_state.schedule 
        if not (s['Course Code'] == course_code and s['Section'] == section)
    ]

# --- 4. STREAMLIT APP LAYOUT ---

st.set_page_config(layout="wide", page_title="Course Section Selector")

st.title("📚 Academic Schedule Builder")
st.markdown("Select a course and use filters to find sections. The app automatically checks for time conflicts against your selected schedule.")

# Split layout into two columns: Filters/Results and Schedule
col_filters, col_schedule = st.columns([2, 1])

# --- FILTERS & RESULTS COLUMN ---
with col_filters:
    st.header("Filter Sections")
    
    # 1. Course Selection (Initial Filter)
    selected_course = st.selectbox(
        "1. Select Course",
        options=['All Courses'] + all_courses,
        index=0 
    )
    
    # Filter the DataFrame based on the selected course
    if selected_course != 'All Courses':
        df_base_filtered = df_courses[df_courses['Course Code'] == selected_course].copy()
    else:
        df_base_filtered = df_courses.copy()

    st.subheader("Preferences")
    
    # Use columns for compact filter layout
    pref_col1, pref_col2 = st.columns(2)
    
    # 2. Faculty Filter
    with pref_col1:
        selected_faculty = st.selectbox(
            "2. Preferred Faculty",
            options=['Any Faculty'] + all_faculty
        )
        if selected_faculty != 'Any Faculty':
            df_base_filtered = df_base_filtered[df_base_filtered['Faculty Full Name'] == selected_faculty]

    # 3. Time Filter
    with pref_col2:
        start_time_hr, end_time_hr = st.slider(
            "3. Time Window (24hr)",
            min_value=800, max_value=2000, 
            value=(800, 1800), 
            step=30,
            format="%04d" 
        )
        
        # Filter based on time range
        df_base_filtered = df_base_filtered[
            (df_base_filtered['Start_Time_24hr'] >= start_time_hr) & 
            (df_base_filtered['End_Time_24hr'] <= end_time_hr)
        ]

    # Group the single-day rows back into unique course sections for display
    # We group by the identifying columns and take the first of the time/day data
    df_unique_sections = df_base_filtered.groupby(['Course Code', 'Section', 'Faculty Full Name']).agg(
        Days_List=('Day', lambda x: "".join(sorted(x.unique()))), # Combine days back to 'MWF' string
        Start_Time=('Start Time', 'first'),
        End_Time=('End Time', 'last')
    ).reset_index()
    
    df_unique_sections = df_unique_sections.rename(columns={'Days_List': 'Days'})


    st.subheader(f"Available Sections ({len(df_unique_sections)})")
    
    # Display results table with 'Add' buttons
    if not df_unique_sections.empty:
        
        # Display table headers
        header_cols = st.columns([1, 1, 1, 2, 2, 3, 1])
        header_cols[0].markdown('**Code**')
        header_cols[1].markdown('**Sec.**')
        header_cols[2].markdown('**Days**')
        header_cols[3].markdown('**Start**')
        header_cols[4].markdown('**End**')
        header_cols[5].markdown('**Faculty**')
        header_cols[6].markdown('**Add**')
        st.markdown("---") # Visual separator

        for index, row in df_unique_sections.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1, 1, 2, 2, 3, 1])
            
            # Display section info
            col1.write(row['Course Code'])
            col2.write(row['Section'])
            col3.write(row['Days'])
            col4.write(row['Start_Time'])
            col5.write(row['End_Time'])
            col6.write(row['Faculty Full Name'])

            # Add button
            with col7:
                st.button("Add", key=f"add_{row['Course Code']}_{row['Section']}", 
                          on_click=add_section_to_schedule, 
                          args=(row['Course Code'], row['Section']))
    else:
        st.info("No sections match your current filters.")

# --- SCHEDULE COLUMN ---
with col_schedule:
    st.header("My Schedule")
    
    if st.session_state.schedule:
        # We need to consolidate the single-day rows back into unique sections for a cleaner display
        schedule_df_raw = pd.DataFrame(st.session_state.schedule)
        
        # Group the single-day rows to display unique sections in the schedule view
        schedule_display_df = schedule_df_raw.groupby(['Course Code', 'Section', 'Faculty Full Name']).agg(
            Days=('Day', lambda x: "".join(sorted(x.unique()))),
            Start_Time=('Start Time', 'first'),
            End_Time=('End Time', 'last')
        ).reset_index()
        
        
        st.subheader("Current Selections")
        
        # Display the schedule table
        st.dataframe(
            schedule_display_df[['Course Code', 'Section', 'Days', 'Start_Time', 'End_Time']], 
            use_container_width=True, 
            hide_index=True
        )
        
        st.subheader("Remove Sections")
        
        # Provide a button to remove each section
        for index, section in schedule_display_df.iterrows():
            display_name = f"{section['Course Code']} {section['Section']} ({section['Days']})"
            st.button(f"🗑️ Remove {display_name}", 
                      key=f"remove_{section['Course Code']}_{section['Section']}", 
                      on_click=remove_section_from_schedule, 
                      args=(section['Course Code'], section['Section']))

    else:
        st.info("Your schedule is currently empty. Add a section!")
        
    st.subheader("Full Weekly View")
    st.info("A full calendar view would be implemented here, plotting the selected sections (using the Day, Start Time, and End Time columns) visually to show conflicts in red.")
