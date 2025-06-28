import streamlit as st
import pandas as pd
import json
import os
from typing import Dict, List

class CoursePairingManagerGUI:
    def __init__(self):
        self.pairings_file = "course_pairings.json"
        
    def load_pairings(self):
        """Load existing course pairings from JSON file"""
        try:
            if os.path.exists(self.pairings_file):
                with open(self.pairings_file, 'r', encoding='utf-8') as file:
                    return json.load(file)
            else:
                return {}
        except Exception as e:
            st.error(f"Error loading pairings: {e}")
            return {}
    
    def save_pairings(self, pairings):
        """Save course pairings to JSON file"""
        try:
            with open(self.pairings_file, 'w', encoding='utf-8') as file:
                json.dump(pairings, file, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            st.error(f"Error saving pairings: {e}")
            return False
    
    def get_course_display_name(self, course_row):
        """Get a display name for a course"""
        return f"{course_row['Course Code']} ({course_row['Section']}) - {course_row['Title']}"
    
    def get_course_key(self, course_row):
        """Get a unique key for a course"""
        return f"{course_row['Course Code']}_{course_row['Section']}"

def main():
    st.set_page_config(
        page_title="Course Pairing Manager",
        page_icon="🎓",
        layout="wide"
    )
    
    manager = CoursePairingManagerGUI()
    
    # Title and header
    st.title("🎓 Course Pairing Manager")
    st.markdown("---")
    
    # Sidebar for file upload
    st.sidebar.header("📁 Upload CSV File")
    uploaded_file = st.sidebar.file_uploader(
        "Choose your courses CSV file",
        type=['csv'],
        help="Upload a CSV file with course data"
    )
    
    if uploaded_file is not None:
        try:
            # Load the CSV data
            df = pd.read_csv(uploaded_file)
            
            # Validate required columns
            required_columns = ['Course Code', 'Section', 'Title', 'Day', 'Start', 'End', 'Room', 'Instructor / Sponsor']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"Missing required columns: {missing_columns}")
                st.stop()
            
            st.sidebar.success(f"✅ Loaded {len(df)} courses")
            
            # Load existing pairings
            pairings = manager.load_pairings()
            
            # Main content tabs
            tab1, tab2, tab3, tab4 = st.tabs(["📚 View Courses", "🔗 Create Pairing", "👀 View Pairings", "🗑️ Manage Pairings"])
            
            # Tab 1: View Courses
            with tab1:
                st.header("📚 All Courses")
                
                # Search functionality
                search_term = st.text_input("🔍 Search courses:", placeholder="Enter course code, title, or instructor...")
                
                if search_term:
                    filtered_df = df[
                        df['Course Code'].str.contains(search_term, case=False, na=False) |
                        df['Title'].str.contains(search_term, case=False, na=False) |
                        df['Instructor / Sponsor'].str.contains(search_term, case=False, na=False)
                    ]
                else:
                    filtered_df = df
                
                # Display courses in a nice format
                for idx, course in filtered_df.iterrows():
                    with st.expander(f"{manager.get_course_display_name(course)}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**📅 Day:** {course['Day']}")
                            st.write(f"**🕒 Time:** {course['Start']} - {course['End']}")
                        with col2:
                            st.write(f"**🏫 Room:** {course['Room']}")
                            st.write(f"**👨‍🏫 Instructor:** {course['Instructor / Sponsor']}")
            
            # Tab 2: Create Pairing
            with tab2:
                st.header("🔗 Create New Course Pairing")
                
                if len(df) < 2:
                    st.warning("Need at least 2 courses to create pairings!")
                else:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("First Course")
                        course_options = [manager.get_course_display_name(course) for _, course in df.iterrows()]
                        selected_course1_idx = st.selectbox(
                            "Select first course:",
                            range(len(course_options)),
                            format_func=lambda x: course_options[x],
                            key="course1"
                        )
                        
                        if selected_course1_idx is not None:
                            course1 = df.iloc[selected_course1_idx]
                            st.info(f"**Selected:** {manager.get_course_display_name(course1)}")
                    
                    with col2:
                        st.subheader("Course to Pair With")
                        # Filter out the selected first course
                        available_courses = df[df.index != selected_course1_idx]
                        available_options = [manager.get_course_display_name(course) for _, course in available_courses.iterrows()]
                        
                        if len(available_options) > 0:
                            selected_course2_name = st.selectbox(
                                "Select course to pair with:",
                                available_options,
                                key="course2"
                            )
                            
                            # Find the actual course data
                            course2 = None
                            for _, course in available_courses.iterrows():
                                if manager.get_course_display_name(course) == selected_course2_name:
                                    course2 = course
                                    break
                            
                            if course2 is not None:
                                st.info(f"**Pairing with:** {manager.get_course_display_name(course2)}")
                    
                    # Create pairing button
                    if st.button("✅ Create Pairing", type="primary"):
                        if selected_course1_idx is not None and course2 is not None:
                            course1_key = manager.get_course_key(course1)
                            course2_key = manager.get_course_key(course2)
                            
                            # Check if pairing already exists
                            if course1_key in pairings:
                                st.warning(f"⚠️ {manager.get_course_display_name(course1)} is already paired!")
                                if st.button("Overwrite existing pairing?"):
                                    pairings[course1_key] = course2_key
                                    pairings[course2_key] = course1_key
                                    if manager.save_pairings(pairings):
                                        st.success("✅ Pairing updated successfully!")
                                        st.rerun()
                            else:
                                # Create new pairing
                                pairings[course1_key] = course2_key
                                pairings[course2_key] = course1_key
                                
                                if manager.save_pairings(pairings):
                                    st.success(f"✅ Successfully paired: {manager.get_course_display_name(course1)} ↔ {manager.get_course_display_name(course2)}")
                                    st.rerun()
            
            # Tab 3: View Pairings
            with tab3:
                st.header("👀 All Course Pairings")
                
                if not pairings:
                    st.info("📝 No course pairings found. Create some pairings in the 'Create Pairing' tab!")
                else:
                    # Group pairings to avoid duplicates
                    displayed_pairs = set()
                    
                    for course_key, paired_key in pairings.items():
                        pair_tuple = tuple(sorted([course_key, paired_key]))
                        
                        if pair_tuple not in displayed_pairs:
                            displayed_pairs.add(pair_tuple)
                            
                            # Find course details
                            course1_details = None
                            course2_details = None
                            
                            try:
                                code1, section1 = course_key.split('_')
                                code2, section2 = paired_key.split('_')
                                
                                course1_details = df[(df['Course Code'] == code1) & (df['Section'] == section1)]
                                course2_details = df[(df['Course Code'] == code2) & (df['Section'] == section2)]
                                
                                if not course1_details.empty and not course2_details.empty:
                                    course1 = course1_details.iloc[0]
                                    course2 = course2_details.iloc[0]
                                    
                                    with st.container():
                                        st.markdown("### 🔗 Pairing")
                                        col1, col2, col3 = st.columns([5, 1, 5])
                                        
                                        with col1:
                                            st.info(f"**{manager.get_course_display_name(course1)}**\n\n📅 {course1['Day']} | 🕒 {course1['Start']}-{course1['End']}\n\n🏫 {course1['Room']} | 👨‍🏫 {course1['Instructor / Sponsor']}")
                                        
                                        with col2:
                                            st.markdown("<div style='text-align: center; font-size: 2em; margin-top: 50px;'>↔</div>", unsafe_allow_html=True)
                                        
                                        with col3:
                                            st.success(f"**{manager.get_course_display_name(course2)}**\n\n📅 {course2['Day']} | 🕒 {course2['Start']}-{course2['End']}\n\n🏫 {course2['Room']} | 👨‍🏫 {course2['Instructor / Sponsor']}")
                                        
                                        st.markdown("---")
                            except:
                                continue
            
            # Tab 4: Manage Pairings
            with tab4:
                st.header("🗑️ Manage Course Pairings")
                
                if not pairings:
                    st.info("📝 No course pairings to manage.")
                else:
                    st.subheader("Delete Pairings")
                    
                    # Get unique pairings for deletion
                    unique_pairings = []
                    displayed_pairs = set()
                    
                    for course_key, paired_key in pairings.items():
                        pair_tuple = tuple(sorted([course_key, paired_key]))
                        
                        if pair_tuple not in displayed_pairs:
                            displayed_pairs.add(pair_tuple)
                            
                            try:
                                code1, section1 = course_key.split('_')
                                code2, section2 = paired_key.split('_')
                                
                                course1_details = df[(df['Course Code'] == code1) & (df['Section'] == section1)]
                                course2_details = df[(df['Course Code'] == code2) & (df['Section'] == section2)]
                                
                                if not course1_details.empty and not course2_details.empty:
                                    course1 = course1_details.iloc[0]
                                    course2 = course2_details.iloc[0]
                                    
                                    pairing_display = f"{manager.get_course_display_name(course1)} ↔ {manager.get_course_display_name(course2)}"
                                    unique_pairings.append((pairing_display, course_key, paired_key))
                            except:
                                continue
                    
                    if unique_pairings:
                        for display_name, key1, key2 in unique_pairings:
                            col1, col2 = st.columns([8, 2])
                            
                            with col1:
                                st.write(display_name)
                            
                            with col2:
                                if st.button(f"🗑️ Delete", key=f"delete_{key1}_{key2}"):
                                    # Remove both directions of the pairing
                                    if key1 in pairings:
                                        del pairings[key1]
                                    if key2 in pairings:
                                        del pairings[key2]
                                    
                                    if manager.save_pairings(pairings):
                                        st.success("✅ Pairing deleted successfully!")
                                        st.rerun()
                    
                    # Clear all pairings
                    st.markdown("---")
                    st.subheader("⚠️ Danger Zone")
                    if st.button("🗑️ Clear All Pairings", type="secondary"):
                        if st.button("⚠️ Confirm: Delete ALL pairings", type="secondary"):
                            pairings.clear()
                            if manager.save_pairings(pairings):
                                st.success("✅ All pairings cleared!")
                                st.rerun()
        
        except Exception as e:
            st.error(f"Error loading CSV file: {e}")
            st.info("Please make sure your CSV file has the correct format with these columns:")
            st.code("Course Code, Section, Title, Day, Start, End, Room, Instructor / Sponsor")
    
    else:
        st.info("👆 Please upload a CSV file to get started!")
        
        # Show sample CSV format
        st.subheader("📋 Expected CSV Format")
        sample_data = {
            'Course Code': ['CORE 200', 'EE|CE 354|361L', 'ANT 325'],
            'Section': ['L1', 'L2', 'S1'],
            'Title': ['Scientific Methods', 'Intro to Probability & Stats', 'Truth in Anthropology'],
            'Day': ['M', 'MW', 'TTh'],
            'Start': ['2:30 PM', '11:30 AM', '8:30 AM'],
            'End': ['3:45 PM', '12:45 PM', '9:45 AM'],
            'Room': ['W-234', 'GF-E121', 'FF-E220'],
            'Instructor / Sponsor': ['Aamir Hasan', 'Aamir Hasan', 'Aaron Mulvany']
        }
        sample_df = pd.DataFrame(sample_data)
        st.dataframe(sample_df, use_container_width=True)

if __name__ == "__main__":
    main()
