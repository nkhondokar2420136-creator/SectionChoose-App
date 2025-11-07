import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. DATA PREPARATION & SETUP ---

# Sample data mimicking the transformed spreadsheet structure
@st.cache_data
def load_and_transform_data():
    """Loads and transforms the sample data into a usable format."""
    data = {
        'Course Code': ['CS 101', 'CS 101', 'MATH 203', 'PHYS 102', 'CS 102', 'MATH 203', 'CS 101'],
        'Section': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
        'Days': ['MWF', 'TR', 'W', 'TR', 'MW', 'R', 'MWF'],
        'Start Time': ['8:30 AM', '11:11 AM', '1:51 PM', '9:51 AM', '1:51 PM', '8:30 AM', '11:11 AM'],
        'End Time': ['9:50 AM', '12:30 PM', '3:10 PM', '11:10 AM', '3:10 PM', '11:00 AM', '12:30 PM'],
        'Faculty Name': ['Dr. Smith', 'Prof. Jones', 'Dr. Smith', 'Prof. Chen', 'Prof. Jones', 'Prof. Chen', 'Dr. Smith']
    }
    df = pd.DataFrame(data)

    # Convert time to 24-hour integer
    def convert_time_to_24hr_int(time_str):
        if pd.isna(time_str): return None
        try:
            return int(datetime.strptime(time_str, '%I:%M %p').strftime('%H%M'))
        except:
            return None

    # Normalize days to a list of characters
    def normalize_days_to_list(days_str):
        return list(days_str) if pd.notna(days_str) else []

    df['Start_Time_24hr'] = df['Start Time'].apply(convert_time_to_24hr_int)
    df['End_Time_24hr'] = df['End Time'].apply(convert_time_to_24hr_int)
    df['Days_List'] = df['Days'].apply(normalize_days_to_list)

    return df

df_courses = load_and_transform_data()
all_faculty = sorted(df_courses['Faculty Name'].unique())
all_courses = sorted(df_courses['Course Code'].unique())

# Initialize session state for the schedule
if 'schedule' not in st.session_state:
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

def add_section_to_schedule(section_index):
    """Handles adding a section, checking for conflicts first."""
    new_section = df_filtered.loc[section_index]
    
    # Check against the current schedule
    is_conflict, details = check_for_conflict(new_section, st.session_state.schedule)
    
    if is_conflict:
        st.error(
            f"⚠️ **Clash Detected!** Section {details['New_Section']} conflicts with "
            f"{details['Clashing_Section']} on **{details['Conflict_Days']}** during "
            f"{details['Time_Range']}."
        )
    else:
        # Check if already added (prevent duplicates)
        if new_section['Section'] not in [s['Section'] for s in st.session_state.schedule if s['Course Code'] == new_section['Course Code']]:
            st.session_state.schedule.append(new_section.to_dict())
            st.success(f"✅ Added {new_section['Course Code']} {new_section['Section']} to your schedule!")
        else:
            st.warning(f"Section {new_section['Course Code']} {new_section['Section']} is already in your schedule.")


def remove_section_from_schedule(section_info):
    """Removes a section from the schedule."""
    # Remove the section that matches both course code and section name
    st.session_state.schedule = [
        s for s in st.session_state.schedule 
        if not (s['Course Code'] == section_info['Course Code'] and s['Section'] == section_info['Section'])
    ]

# --- 4. STREAMLIT APP LAYOUT ---

st.set_page_config(layout="wide", page_title="Course Section Selector")

st.title("📚 Course Section Selector")
st.markdown("Use the filters to narrow down sections and build your conflict-free schedule!")

# Split layout into two columns: Filters/Results and Schedule
col_filters, col_schedule = st.columns([2, 1])

# --- FILTERS & RESULTS COLUMN ---
with col_filters:
    st.header("Filter Sections")
    
    # 1. Course Selection (Initial Filter)
    selected_course = st.selectbox(
        "1. Select Course",
        options=['All Courses'] + all_courses,
        index=0 # Start with 'All Courses'
    )
    
    # Filter the DataFrame based on the selected course
    if selected_course != 'All Courses':
        df_filtered = df_courses[df_courses['Course Code'] == selected_course].copy()
    else:
        df_filtered = df_courses.copy()

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
            df_filtered = df_filtered[df_filtered['Faculty Name'] == selected_faculty]

    # 3. Time Filter
    with pref_col2:
        start_time_hr, end_time_hr = st.slider(
            "3. Time Window (24hr)",
            min_value=800, max_value=2000, 
            value=(800, 1800), # Default 8:00 AM to 6:00 PM
            step=30,
            format="%04d" # Display as 0800, 1800
        )
        
        # Filter based on time range
        df_filtered = df_filtered[
            (df_filtered['Start_Time_24hr'] >= start_time_hr) & 
            (df_filtered['End_Time_24hr'] <= end_time_hr)
        ]

    st.subheader(f"Available Sections ({len(df_filtered)})")
    
    # Display results table with 'Add' buttons
    if not df_filtered.empty:
        df_display = df_filtered[['Course Code', 'Section', 'Days', 'Start Time', 'End Time', 'Faculty Name']].reset_index()
        
        for index, row in df_display.iterrows():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1, 1, 2, 2, 3, 1])
            
            with col1: st.write(row['Course Code'])
            with col2: st.write(row['Section'])
            with col3: st.write(row['Days'])
            with col4: st.write(row['Start Time'])
            with col5: st.write(row['End Time'])
            with col6: st.write(row['Faculty Name'])

            # Add button with unique key
            with col7:
                st.button("Add", key=f"add_{row['index']}", on_click=add_section_to_schedule, args=(row['index'],))
    else:
        st.info("No sections match your current filters.")

# --- SCHEDULE COLUMN ---
with col_schedule:
    st.header("My Schedule")
    
    if st.session_state.schedule:
        # Create a DataFrame for display
        schedule_df = pd.DataFrame(st.session_state.schedule)[['Course Code', 'Section', 'Days', 'Start Time', 'Faculty Name']]
        
        # Highlight any rows that clash with other schedule items
        
        schedule_list = st.session_state.schedule
        
        # Display the schedule table
        st.dataframe(schedule_df, use_container_width=True, hide_index=True)
        
        st.subheader("Remove Sections")
        
        # Provide a button to remove each section
        for section in schedule_list:
            display_name = f"{section['Course Code']} {section['Section']} ({section['Days']})"
            st.button(f"🗑️ Remove {display_name}", key=f"remove_{section['Course Code']}_{section['Section']}", 
                      on_click=remove_section_from_schedule, args=(section,))

    else:
        st.info("Your schedule is currently empty. Add a section!")