"""
ORIGINAL BASIC SCHEDULER (BEFORE SMART FEATURES)
===============================================

This was the original timetable generator before any smart pairing features.
It only had basic functionality:
- Manual course selection
- Simple timetable generation
- No auto-pairing
- No smart suggestions

This shows how far we've come!
"""

import pandas as pd
import itertools
from datetime import datetime, time
from collections import defaultdict

class BasicTimetableGenerator:
    def __init__(self):
        self.course_data = None
        self.selected_courses = {}
        self.valid_combinations = []
        
    def load_data(self, file_content, filename):
        """Load course data from CSV or Excel file content"""
        try:
            if filename.endswith('.csv'):
                self.course_data = pd.read_csv(file_content)
            else:
                self.course_data = pd.read_excel(file_content)
            
            self._clean_data()
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def _clean_data(self):
        """Clean and standardize the course data"""
        # Remove any rows with missing essential data
        self.course_data = self.course_data.dropna(subset=['Course Code', 'Section', 'Day', 'Start', 'End'])
        
        # Standardize time format
        self.course_data['Start_24h'] = self.course_data['Start'].apply(self._convert_to_24h)
        self.course_data['End_24h'] = self.course_data['End'].apply(self._convert_to_24h)
        
        # Parse days into individual days
        self.course_data['Days_List'] = self.course_data['Day'].apply(self._parse_days)
        
    def _convert_to_24h(self, time_str):
        """Convert time string to 24-hour format"""
        try:
            time_str = str(time_str).strip()
            if 'p' in time_str.lower() and not time_str.lower().startswith('12'):
                hour = int(time_str.split(':')[0]) + 12
                minute = int(time_str.split(':')[1].split('p')[0])
            elif 'a' in time_str.lower() and time_str.lower().startswith('12'):
                hour = 0
                minute = int(time_str.split(':')[1].split('a')[0])
            else:
                hour = int(time_str.split(':')[0])
                minute = int(time_str.split(':')[1][:2])
            
            return time(hour, minute)
        except:
            return None
    
    def _parse_days(self, day_str):
        """Parse day string into list of individual days"""
        day_mapping = {
            'M': 'Monday',
            'T': 'Tuesday', 
            'W': 'Wednesday',
            'Th': 'Thursday',
            'F': 'Friday',
            'S': 'Saturday',
            'Su': 'Sunday'
        }
        
        days = []
        day_str = str(day_str).strip()
        
        # Handle common patterns
        if 'TTh' in day_str:
            days.extend(['Tuesday', 'Thursday'])
            day_str = day_str.replace('TTh', '')
        if 'MW' in day_str:
            days.extend(['Monday', 'Wednesday'])
            day_str = day_str.replace('MW', '')
        if 'WF' in day_str:
            days.extend(['Wednesday', 'Friday'])
            day_str = day_str.replace('WF', '')
        if 'Th' in day_str:
            days.append('Thursday')
            day_str = day_str.replace('Th', '')
            
        # Handle remaining single characters
        for char in day_str:
            if char in day_mapping:
                days.append(day_mapping[char])
        
        return list(set(days))  # Remove duplicates
    
    def get_unique_courses(self):
        """Get list of unique courses"""
        if self.course_data is None:
            return []
        return sorted(self.course_data['Course Code'].unique())
    
    def get_course_sections(self, course_code):
        """Get all sections for a specific course"""
        if self.course_data is None:
            return []
        
        course_sections = self.course_data[self.course_data['Course Code'] == course_code]
        sections_info = []
        
        for section in course_sections['Section'].unique():
            section_data = course_sections[course_sections['Section'] == section]
            
            # Group by section to handle multiple time slots
            times = []
            for _, row in section_data.iterrows():
                time_info = f"{row['Day']} {row['Start']}-{row['End']}"
                times.append(time_info)
            
            instructor = section_data['Instructor / Sponsor'].iloc[0]
            title = section_data['Title'].iloc[0]
            
            sections_info.append({
                'section': section,
                'title': title,
                'instructor': instructor,
                'times': times,
                'data': section_data
            })
        
        return sections_info
    
    def select_course_sections(self, course_code, selected_sections):
        """Select specific sections for a course"""
        self.selected_courses[course_code] = selected_sections
    
    def generate_combinations(self):
        """Generate all valid combinations"""
        if not self.selected_courses:
            return []
        
        # Create course options
        course_options = []
        
        for course_code, selected_sections in self.selected_courses.items():
            if not selected_sections:
                continue
                
            course_section_options = []
            
            for section in selected_sections:
                section_data = self.course_data[
                    (self.course_data['Course Code'] == course_code) & 
                    (self.course_data['Section'] == section)
                ]
                course_section_options.append([(course_code, section, section_data)])
            
            if course_section_options:
                course_options.append(course_section_options)
        
        # Generate all combinations
        valid_combinations = []
        if course_options:
            for combination in itertools.product(*course_options):
                # Flatten combination
                flattened_combination = []
                for unit in combination:
                    flattened_combination.extend(unit)
                
                if self._is_valid_combination(flattened_combination):
                    valid_combinations.append(flattened_combination)
        
        self.valid_combinations = valid_combinations
        return valid_combinations
    
    def _is_valid_combination(self, combination):
        """Check if a combination is valid (no time conflicts)"""
        # Check for time conflicts between any sections
        for i in range(len(combination)):
            for j in range(i + 1, len(combination)):
                course1_data = combination[i][2]
                course2_data = combination[j][2]
                
                if self._check_time_conflict(course1_data, course2_data):
                    return False
        
        return True
    
    def _check_time_conflict(self, course1_data, course2_data):
        """Check if two courses have time conflicts"""
        for _, row1 in course1_data.iterrows():
            for _, row2 in course2_data.iterrows():
                # Check if they share any common days
                common_days = set(row1['Days_List']) & set(row2['Days_List'])
                
                if common_days:
                    # Check time overlap
                    start1, end1 = row1['Start_24h'], row1['End_24h']
                    start2, end2 = row2['Start_24h'], row2['End_24h']
                    
                    if start1 and end1 and start2 and end2:
                        if not (end1 <= start2 or end2 <= start1):
                            return True
        return False

if __name__ == "__main__":
    print("ORIGINAL BASIC SCHEDULER")
    print("This was before any smart features were added!")
    print("No auto-pairing, no smart suggestions - just basic functionality")
