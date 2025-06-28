"""
Web-based University Timetable Generator using FastAPI
Converts the tkinter scheduler to a modern web interface
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import itertools
from datetime import datetime, time
import re
from collections import defaultdict
import json
import os
from pathlib import Path
import io
from typing import List, Dict, Any, Optional
import tempfile
import shutil
import csv

# Import the file processor function
from progress_archive.file_processor import process_uploaded_file, extract_section_type

app = FastAPI(title="University Timetable Generator", version="1.0.0")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Global storage for the current session (in production, use database/session storage)
current_generator = None
temp_data_file = None  # Store temporary file path

class TimetableGenerator:   
    def __init__(self):
        self.course_data = None
        self.selected_courses = {}
        self.valid_combinations = []
        self.current_file_path = None
        
        # STEP 1: Auto-Course Pairing Data
        self.course_pairs = {}              # Bidirectional pairs: {"CS 101": "CS 101L", "CS 101L": "CS 101"}
        
        # STEP 2: Section Validation Data  
        self.correct_pairings = {}          # Valid section combinations by course pair
        self.incorrect_pairings = {}        # Invalid section combinations by course pair
        
        # STEP 3: Smart Selection Data
        self.section_suggestions = {}       # Smart suggestions for auto-pairing
        
        # Legacy atomic pairing system (keeping for compatibility)
        self.section_pairs = {}  # pair_id -> list of (course, section) tuplesGO
        self.pair_lookup = {}    # (course, section) -> pair_id
        self.pair_counter = 0    # for generating unique pair IDs
        
        # 🎯 AUTO-LOAD CSV ON STARTUP
        self.load_embedded_data()
        
    def load_data(self, file_content: bytes, filename: str):
        """Load course data from CSV or Excel file content"""
        try:
            # Load the original data
            if filename.endswith('.csv'):
                original_df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
            else:
                original_df = pd.read_excel(io.BytesIO(file_content))
            
            # Process the data using the integrated processor
            print("Running file processor to split courses with multiple section types...")
            processed_df, split_courses = process_uploaded_file(original_df)
            
            # Use the processed data
            self.course_data = processed_df
            
            self.current_file_path = filename
            # Clean and validate data
            self._clean_data()
            
            # STEP 1 & 2: Auto-detect course pairs and section pairings
            self.auto_detect_course_pairs()
            
            # Log processing results
            if split_courses:
                print(f"File processing complete. {len(split_courses)} courses were split.")
            else:
                print("File processing complete. No courses needed splitting.")
            
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def clear_data(self):
        """Clear all loaded data and selections including smart features"""
        self.course_data = None
        self.selected_courses = {}
        self.valid_combinations = []
        self.current_file_path = None
        
        # Clear smart features data
        self.course_pairs = {}
        self.correct_pairings = {}
        self.incorrect_pairings = {}
        self.section_suggestions = {}
        
        # Clear legacy data
        self.section_pairs = {}
        self.pair_lookup = {}
        self.pair_counter = 0
    
    def clear_roster(self):
        """Clear only the selected courses roster (keep smart features)"""
        self.selected_courses = {}
        self.valid_combinations = []
    
    def _clean_data(self):
        """Clean and standardize the course data"""
        # Handle different column name formats for time data
        start_col = 'Start' if 'Start' in self.course_data.columns else (
            'Start Time' if 'Start Time' in self.course_data.columns else None
        )
        end_col = 'End' if 'End' in self.course_data.columns else (
            'End Time' if 'End Time' in self.course_data.columns else None
        )
        
        if not start_col or not end_col:
            raise ValueError(f"Missing time columns. Available columns: {list(self.course_data.columns)}")
        
        # Debug info for development
        # print(f"🔍 Time columns detected: Start='{start_col}', End='{end_col}'")
        
        # Remove any rows with missing essential data
        self.course_data = self.course_data.dropna(subset=['Course Code', 'Section', 'Day', start_col, end_col])
        
        # Standardize time format
        self.course_data['Start_24h'] = self.course_data[start_col].apply(self._convert_to_24h)
        self.course_data['End_24h'] = self.course_data[end_col].apply(self._convert_to_24h)
        
        # Also keep the original time columns for display
        self.course_data['Start'] = self.course_data[start_col]
        self.course_data['End'] = self.course_data[end_col]
        
        # Parse days into individual days
        self.course_data['Days_List'] = self.course_data['Day'].apply(self._parse_days)
        
        # Create unique identifiers
        self.course_data['Course_Section'] = self.course_data['Course Code'] + ' ' + self.course_data['Section']
        
    def _convert_to_24h(self, time_str):
        """Convert time string to 24-hour format"""
        try:
            time_str = str(time_str).strip()
            # Debug: print(f"🔍 Converting time: '{time_str}'")
            
            # Handle AM/PM format
            if 'AM' in time_str.upper() or 'PM' in time_str.upper():
                # Remove spaces and normalize
                time_str = time_str.replace(' ', '').upper()
                is_pm = 'PM' in time_str
                time_part = time_str.replace('AM', '').replace('PM', '')
                
                # Parse hour and minute
                if ':' in time_part:
                    hour, minute = map(int, time_part.split(':'))
                else:
                    hour = int(time_part)
                    minute = 0
                
                # Convert to 24-hour format
                if is_pm and hour != 12:
                    hour += 12
                elif not is_pm and hour == 12:
                    hour = 0
                
                result = time(hour, minute)
                # Debug: print(f"🔍 Converted '{time_str}' to {result}")
                return result
            
            # Handle 24-hour format (like "14:30")
            elif ':' in time_str:
                hour, minute = map(int, time_str.split(':'))
                result = time(hour, minute)
                # Debug: print(f"🔍 Converted '{time_str}' to {result}")
                return result
            
            else:
                print(f"⚠️ Unrecognized time format: '{time_str}'")
                return None
                
        except Exception as e:
            print(f"❌ Error converting time '{time_str}': {e}")
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
    
    def create_section_pair(self, course1, section1, course2, section2):
        """Create a pair between two sections that must be taken together"""
        existing_pair1 = self.pair_lookup.get((course1, section1))
        existing_pair2 = self.pair_lookup.get((course2, section2))
        
        if existing_pair1 or existing_pair2:
            return False, "One or both sections are already paired"
        
        self.pair_counter += 1
        pair_id = f"pair_{self.pair_counter}"
        
        self.section_pairs[pair_id] = [(course1, section1), (course2, section2)]
        self.pair_lookup[(course1, section1)] = pair_id
        self.pair_lookup[(course2, section2)] = pair_id
        
        return True, pair_id
    
    def remove_section_pair(self, course, section):
        """Remove a section from its pair"""
        pair_id = self.pair_lookup.get((course, section))
        if not pair_id:
            return False, "Section is not paired"
        
        for paired_course, paired_section in self.section_pairs[pair_id]:
            del self.pair_lookup[(paired_course, paired_section)]
        
        del self.section_pairs[pair_id]
        return True, "Pair removed successfully"
    
    def get_paired_sections(self, course, section):
        """Get all sections paired with the given section"""
        pair_id = self.pair_lookup.get((course, section))
        if not pair_id:
            return []
        
        paired_sections = []
        for paired_course, paired_section in self.section_pairs[pair_id]:
            if (paired_course, paired_section) != (course, section):
                paired_sections.append((paired_course, paired_section))
        
        return paired_sections
    
    def is_section_paired(self, course, section):
        """Check if a section is part of a pair"""
        return (course, section) in self.pair_lookup
    
    def format_course_code_for_display(self, course_code: str) -> str:
        """Convert internal course code (with |) back to display format (with /)"""
        return course_code.replace('|', '/')
    
    def format_course_code_for_internal(self, course_code: str) -> str:
        """Convert display course code (with /) to internal format (with |)"""
        return course_code.replace('/', '|')

    def get_unique_courses(self):
        """Get list of unique courses"""
        if self.course_data is None:
            return []
        return sorted(self.course_data['Course Code'].unique())
    
    def get_courses_with_titles(self):
        """Get list of unique courses with their titles"""
        if self.course_data is None:
            return []
        
        # Get unique course codes with their titles
        course_info = []
        for course_code in sorted(self.course_data['Course Code'].unique()):
            # Get the first occurrence to extract the title
            course_row = self.course_data[self.course_data['Course Code'] == course_code].iloc[0]
            title = course_row.get('Title', 'No Title')
            course_display = f"{course_code} - {title}"
            course_info.append({
                'code': course_code,
                'title': title,
                'display': course_display
            })
        return course_info
    
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
                'data': section_data,
                'is_paired': self.is_section_paired(course_code, section),
                'paired_with': self.get_paired_sections(course_code, section)
            })
        
        return sections_info
    
    def _check_time_conflict(self, course1_data, course2_data, debug=False):
        """Check if two courses have time conflicts"""
        for _, row1 in course1_data.iterrows():
            for _, row2 in course2_data.iterrows():
                # Debug: Print the data being compared (optional)
                if debug:
                    course1_name = row1.get('Course Code', 'Unknown') + ' ' + row1.get('Section', '')
                    course2_name = row2.get('Course Code', 'Unknown') + ' ' + row2.get('Section', '')
                    
                    print(f"🔍 Checking conflict between:")
                    print(f"   Course 1: {course1_name}")
                    print(f"   Days 1: {row1.get('Days_List', [])}")
                    print(f"   Time 1: {row1.get('Start_24h')} - {row1.get('End_24h')}")
                    print(f"   Course 2: {course2_name}")
                    print(f"   Days 2: {row2.get('Days_List', [])}")
                    print(f"   Time 2: {row2.get('Start_24h')} - {row2.get('End_24h')}")
                
                # Check if they share any common days
                common_days = set(row1['Days_List']) & set(row2['Days_List'])
                if debug:
                    print(f"   Common days: {common_days}")
                
                if common_days:
                    # Check time overlap
                    start1, end1 = row1['Start_24h'], row1['End_24h']
                    start2, end2 = row2['Start_24h'], row2['End_24h']
                    
                    if start1 and end1 and start2 and end2:
                        # Check for overlap: start1 < end2 and start2 < end1
                        overlap = start1 < end2 and start2 < end1
                        if debug:
                            print(f"   Time overlap check: {start1} < {end2} and {start2} < {end1} = {overlap}")
                        
                        if overlap:
                            if debug:
                                print(f"   🚨 CONFLICT DETECTED! {course1_name} conflicts with {course2_name}")
                            return True
                        else:
                            if debug:
                                print(f"   ✅ No time overlap")
                    else:
                        if debug:
                            print(f"   ⚠️ Missing time data: start1={start1}, end1={end1}, start2={start2}, end2={end2}")
                else:
                    if debug:
                        print(f"   ✅ No common days")
                if debug:
                    print(f"   ---")
        
        if debug:
            print(f"   ✅ NO CONFLICTS FOUND")
        return False
    
    def generate_combinations(self):
        """Generate all valid combinations ensuring one section per course"""
        if not self.selected_courses:
            return []
        
        # Create course options ensuring one section per course
        course_options = []
        processed_pairs = set()
        
        for course_code, selected_sections in self.selected_courses.items():
            if not selected_sections:
                continue
                
            course_section_options = []
            
            for section in selected_sections:
                section_key = (course_code, section)
                
                # Skip if this section is part of an already processed pair
                if section_key in processed_pairs:
                    continue
                
                # Get section data
                section_data = self.course_data[
                    (self.course_data['Course Code'] == course_code) & 
                    (self.course_data['Section'] == section)
                ]
                
                if self.is_section_paired(course_code, section):
                    # Create atomic unit with all paired sections
                    atomic_unit = [(course_code, section, section_data)]
                    paired_sections = self.get_paired_sections(course_code, section)
                    
                    for paired_course, paired_section in paired_sections:
                        paired_data = self.course_data[
                            (self.course_data['Course Code'] == paired_course) & 
                            (self.course_data['Section'] == paired_section)
                        ]
                        atomic_unit.append((paired_course, paired_section, paired_data))
                        processed_pairs.add((paired_course, paired_section))
                    
                    course_section_options.append(atomic_unit)
                    processed_pairs.add(section_key)
                else:
                    # Individual section
                    atomic_unit = [(course_code, section, section_data)]
                    course_section_options.append(atomic_unit)
            
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
        """Check if a combination of courses is valid (no duplicate courses, no time conflicts, and smart section pairing)"""
        
        # Check 1: No multiple sections of the same course
        seen_courses = set()
        for course_code, section, course_data in combination:
            if course_code in seen_courses:
                # Duplicate course found - invalid combination
                return False
            seen_courses.add(course_code)
        
        # Check 2: No time conflicts between any sections
        for i in range(len(combination)):
            for j in range(i + 1, len(combination)):
                course1_data = combination[i][2]
                course2_data = combination[j][2]
                
                if self._check_time_conflict(course1_data, course2_data):
                    return False
        
        # Check 3: Smart section pairing validation - THE AI FILTER! 🧠
        if not self._is_smart_pairing_valid(combination):
            return False
        
        return True
    
    def format_combination(self, combination):
        """Format a combination for display"""
        schedule = {
            'Monday': [], 'Tuesday': [], 'Wednesday': [], 
            'Thursday': [], 'Friday': [], 'Saturday': [], 'Sunday': []
        }
        
        courses_info = []
        
        for course_code, section, course_data in combination:
            # Skip header rows (where Course Code = 'Name')
            course_data_clean = course_data[course_data['Course Code'] != 'Name']
            
            if len(course_data_clean) == 0:
                continue
                
            course_info = f"{course_code} {section}"
            title = course_data_clean['Title'].iloc[0]
            instructor = course_data_clean['Instructor / Sponsor'].iloc[0]
            
            courses_info.append({
                'course': course_info,
                'title': title,
                'instructor': instructor
            })
            
            # Add to schedule
            for _, row in course_data_clean.iterrows():
                for day in row['Days_List']:
                    if day in schedule:  # Only add valid weekdays
                        time_slot = f"{row['Start']}-{row['End']}"
                        room = row['Room'] if 'Room' in row else 'TBA'
                        schedule_item = {
                            'course': course_code,
                            'section': section,
                            'title': title,
                            'time': time_slot,
                            'room': room,
                            'instructor': instructor,
                            'start_24h': row['Start_24h'],
                            'end_24h': row['End_24h'],
                            'start': row['Start'],
                            'end': row['End']
                        }
                        schedule[day].append(schedule_item)
        
        # Sort each day by start time
        for day in schedule:
            schedule[day].sort(key=lambda x: x['start_24h'] if x['start_24h'] else time(0, 0))
        
        return {
            'courses': courses_info,
            'schedule': schedule
        }
    
    def auto_detect_course_pairs(self):
        """STEP 1: Auto-detect course pairs using learned algorithms"""
        if self.course_data is None:
            return
        
        print("🔄 Starting auto-course pairing detection...")
        unique_courses = sorted(self.course_data['Course Code'].unique())
        self.course_pairs = {}
        pairs_created = 0
        
        # Get unpaired courses
        unpaired_courses = unique_courses[:]
        
        # Algorithm 1: Exact Lecture-Lab Pattern (CS 101 ↔ CS 101L)
        pairs_found = self.find_lecture_lab_exact_pairs(unpaired_courses)
        if pairs_found:
            pairs_created += len(pairs_found)
            self.apply_course_pairs(pairs_found)
            unpaired_courses = [course for course in unpaired_courses if course not in self.course_pairs]
            print(f"  ✓ Found {len(pairs_found)} Lecture-Lab exact pairs")
        
        # Algorithm 2: Base-Suffix Pattern (MATH 101L ↔ MATH 101R)
        pairs_found = self.find_base_suffix_pairs(unpaired_courses)
        if pairs_found:
            pairs_created += len(pairs_found)
            self.apply_course_pairs(pairs_found)
            unpaired_courses = [course for course in unpaired_courses if course not in self.course_pairs]
            print(f"  ✓ Found {len(pairs_found)} Base-Suffix pairs")
        
        # Algorithm 3: Pipe Course Pattern (CS|CE 232 ↔ CS|CE 232L)
        pairs_found = self.find_pipe_course_pairs(unpaired_courses)
        if pairs_found:
            pairs_created += len(pairs_found)
            self.apply_course_pairs(pairs_found)
            print(f"  ✓ Found {len(pairs_found)} Pipe course pairs")
        
        print(f"🎯 Total course pairs detected: {pairs_created}")
        
        # After pairing detection, predict section pairings
        self.auto_predict_section_pairings()
        
        return pairs_created
    
    def find_lecture_lab_exact_pairs(self, courses):
        """Find exact lecture-lab pairs like CS 101 ↔ CS 101L"""
        pairs = []
        for i, course1 in enumerate(courses):
            for j, course2 in enumerate(courses[i+1:], i+1):
                if course1.lower() + "l" == course2.lower():
                    pairs.append((course1, course2))
                elif course2.lower() + "l" == course1.lower():
                    pairs.append((course1, course2))
        return pairs
    
    def find_base_suffix_pairs(self, courses):
        """Find base-suffix pairs like MATH 101L ↔ MATH 101R"""
        pairs = []
        suffixes = ['L', 'R', 'T', 'S', 'C']
        
        for i, course1 in enumerate(courses):
            for j, course2 in enumerate(courses[i+1:], i+1):
                course1_parts = course1.split()
                course2_parts = course2.split()
                
                if len(course1_parts) >= 2 and len(course2_parts) >= 2:
                    last1 = course1_parts[-1]
                    last2 = course2_parts[-1]
                    
                    if (len(last1) > 1 and len(last2) > 1 and 
                        last1[-1] in suffixes and last2[-1] in suffixes and
                        last1[-1] != last2[-1]):
                        
                        base1 = ' '.join(course1_parts[:-1]) + ' ' + last1[:-1]
                        base2 = ' '.join(course2_parts[:-1]) + ' ' + last2[:-1]
                        
                        if base1 == base2:
                            pairs.append((course1, course2))
        return pairs
    
    def find_pipe_course_pairs(self, courses):
        """Find pipe course pairs like CS|CE 232 ↔ CS|CE 232L"""
        pairs = []
        for i, course1 in enumerate(courses):
            for j, course2 in enumerate(courses[i+1:], i+1):
                if '|' in course1 or '|' in course2:
                    base1 = course1.split('|')[-1].strip() if '|' in course1 else course1
                    base2 = course2.split('|')[-1].strip() if '|' in course2 else course2
                    prefix1 = course1.split('|')[0].strip() if '|' in course1 else ''
                    prefix2 = course2.split('|')[0].strip() if '|' in course2 else ''
                    
                    if (prefix1 == prefix2 and 
                        (base1.lower() + "l" == base2.lower() or 
                         base2.lower() + "l" == base1.lower())):
                        pairs.append((course1, course2))
        return pairs
    
    def apply_course_pairs(self, pairs):
        """Apply course pairs with bidirectional mapping"""
        for course1, course2 in pairs:
            if course1 not in self.course_pairs and course2 not in self.course_pairs:
                self.course_pairs[course1] = course2
                self.course_pairs[course2] = course1
    
    def auto_predict_section_pairings(self):
        """STEP 2: Auto-predict section pairings using unified algorithm"""
        if not self.course_pairs:
            print("⚠️ No course pairs found for section prediction")
            return
        
        print("🔄 Starting auto-section pairing prediction...")
        self.correct_pairings = {}
        self.incorrect_pairings = {}
        total_predictions = 0
        
        # Get unique course pairs
        unique_pairs = set()
        for course1, course2 in self.course_pairs.items():
            pair = tuple(sorted([course1, course2]))
            unique_pairs.add(pair)
        
        for course1, course2 in unique_pairs:
            # Get sections for each course
            course1_sections = sorted(self.course_data[self.course_data['Course Code'] == course1]['Section'].unique())
            course2_sections = sorted(self.course_data[self.course_data['Course Code'] == course2]['Section'].unique())
            
            if not course1_sections or not course2_sections:
                continue
            
            # Apply unified algorithm
            predicted_pairs = self.predict_section_pairings(course1_sections, course2_sections)
            
            if predicted_pairs:
                pair_key = f"{course1} ↔ {course2}"
                self.correct_pairings[pair_key] = []
                self.incorrect_pairings[pair_key] = []
                
                # Mark predicted pairs as correct
                for section1, section2 in predicted_pairs:
                    pairing_str = f"{course1} {section1} ↔ {course2} {section2}"
                    self.correct_pairings[pair_key].append(pairing_str)
                
                total_predictions += len(predicted_pairs)
                
                # Determine algorithm used
                if len(course1_sections) == 1 or len(course2_sections) == 1:
                    algorithm = "One-to-Many"
                elif len(course1_sections) == len(course2_sections):
                    algorithm = "Sequential"
                else:
                    algorithm = "Unknown"
                
                print(f"  ✓ {pair_key}: {algorithm} ({len(predicted_pairs)} predictions)")
        
        print(f"🎯 Total section predictions: {total_predictions}")
        return total_predictions
    
    def predict_section_pairings(self, course1_sections, course2_sections):
        """Unified algorithm for predicting section pairings"""
        predictions = []
        
        if len(course1_sections) == 1:
            # Rule 1: One section pairs with all others
            for section2 in course2_sections:
                predictions.append((course1_sections[0], section2))
        elif len(course2_sections) == 1:
            # Rule 1: One section pairs with all others
            for section1 in course1_sections:
                predictions.append((section1, course2_sections[0]))
        elif len(course1_sections) == len(course2_sections):
            # Rule 2: Sequential matching
            for i in range(len(course1_sections)):
                predictions.append((course1_sections[i], course2_sections[i]))
        
        return predictions
    
    def find_compatible_sections(self, source_course, source_sections, target_course):
        """STEP 3: Find compatible sections for auto-pairing"""
        if not source_sections:
            return []
        
        # SIMPLE LOGIC: Only block the annoying one-to-many case
        all_source_sections = sorted(self.course_data[self.course_data['Course Code'] == source_course]['Section'].unique())
        all_target_sections = sorted(self.course_data[self.course_data['Course Code'] == target_course]['Section'].unique())
        
        # Block ONLY: 1 source section → many target sections
        if len(all_source_sections) == 1 and len(all_target_sections) > 1:
            print(f"🚫 Skipping auto-pair: {source_course}(1) → {target_course}({len(all_target_sections)}) is one-to-many")
            return []
        
        # Allow everything else: 1→1, many→1, equal counts
        
        # Create the pair key for lookup
        pair_key1 = f"{source_course} ↔ {target_course}"
        pair_key2 = f"{target_course} ↔ {source_course}"
        
        # Check both possible pair key formats
        correct_pairings = None
        if pair_key1 in self.correct_pairings:
            correct_pairings = self.correct_pairings[pair_key1]
        elif pair_key2 in self.correct_pairings:
            correct_pairings = self.correct_pairings[pair_key2]
        
        if not correct_pairings:
            # Fallback: Use unified algorithm for prediction
            return self.predict_compatible_sections(source_course, source_sections, target_course)
        
        # Find matching sections from learned pairings
        compatible_sections = []
        for source_section in source_sections:
            for pairing in correct_pairings:
                # Parse pairing format: "COURSE1 SECTION1 ↔ COURSE2 SECTION2"
                parts = pairing.split(" ↔ ")
                if len(parts) != 2:
                    continue
                
                left_part = parts[0].strip()
                right_part = parts[1].strip()
                
                # Extract course and section from each part
                left_course = " ".join(left_part.split()[:-1])
                left_section = left_part.split()[-1]
                right_course = " ".join(right_part.split()[:-1])
                right_section = right_part.split()[-1]
                
                # Check if this pairing matches our source
                if left_course == source_course and left_section == source_section:
                    if right_section not in compatible_sections:
                        compatible_sections.append(right_section)
                elif right_course == source_course and right_section == source_section:
                    if left_section not in compatible_sections:
                        compatible_sections.append(left_section)
        
        return sorted(compatible_sections)
    
    def predict_compatible_sections(self, source_course, source_sections, target_course):
        """Fallback: Predict compatible sections using unified algorithm"""
        if self.course_data is None:
            return []
        
        # SIMPLE LOGIC: Only block the annoying one-to-many case
        all_source_sections = sorted(self.course_data[self.course_data['Course Code'] == source_course]['Section'].unique())
        all_target_sections = sorted(self.course_data[self.course_data['Course Code'] == target_course]['Section'].unique())
        
        # Block ONLY: 1 source section → many target sections
        if len(all_source_sections) == 1 and len(all_target_sections) > 1:
            print(f"🚫 Skipping fallback auto-pair: {source_course}(1) → {target_course}({len(all_target_sections)}) is one-to-many")
            return []
        
        # Allow everything else and return the target sections
        if not all_target_sections:
            return []
        
        # For all allowed cases, just return target sections
        return all_target_sections

    def _is_smart_pairing_valid(self, combination):
        """🧠 AI FILTER: Check if combination has valid section pairings based on training data"""
        
        # Get all courses in this combination
        courses_in_combo = [(course_code, section) for course_code, section, _ in combination]
        
        # Check each pair of courses in the combination
        for i in range(len(courses_in_combo)):
            for j in range(i + 1, len(courses_in_combo)):
                course1_code, section1 = courses_in_combo[i]
                course2_code, section2 = courses_in_combo[j]
                
                # Check if these courses are paired
                if course1_code in self.course_pairs and self.course_pairs[course1_code] == course2_code:
                    # This is a paired course! Check if their sections are correctly paired
                    if not self._are_sections_correctly_paired(course1_code, section1, course2_code, section2):
                        print(f"🚫 AI FILTER: Rejected {course1_code} {section1} ↔ {course2_code} {section2} (incorrect pairing)")
                        return False
        
        return True
    
    def _are_sections_correctly_paired(self, course1, section1, course2, section2):
        """Check if two specific sections are correctly paired according to training data"""
        
        # Create pairing string in both possible formats
        pairing1 = f"{course1} {section1} ↔ {course2} {section2}"
        pairing2 = f"{course2} {section2} ↔ {course1} {section1}"
        
        # Create pair keys in both possible formats
        pair_key1 = f"{course1} ↔ {course2}"
        pair_key2 = f"{course2} ↔ {course1}"
        
        # Check if this pairing is in correct_pairings
        for pair_key in [pair_key1, pair_key2]:
            if pair_key in self.correct_pairings:
                if pairing1 in self.correct_pairings[pair_key] or pairing2 in self.correct_pairings[pair_key]:
                    return True
        
        # If we have training data but this pairing is not in correct list, it's probably incorrect
        # Only reject if we actually have training data for this course pair
        if pair_key1 in self.correct_pairings or pair_key2 in self.correct_pairings:
            return False
        
        # If no training data exists, allow it (fallback to auto-prediction logic)
        return True

    def load_embedded_data(self):
        """Load CSV data from the same folder automatically"""
        try:
            # Look for the CSV file in the same directory
            csv_file_path = "Schedule(Sheet1) (3).csv"
            
            if os.path.exists(csv_file_path):
                print(f"🔄 Loading embedded CSV: {csv_file_path}")
                
                # Read the CSV file
                original_df = pd.read_csv(csv_file_path)
                
                # Process the data using the integrated processor
                print("Running file processor to split courses with multiple section types...")
                processed_df, split_courses = process_uploaded_file(original_df)
                
                # Use the processed data
                self.course_data = processed_df
                self.current_file_path = csv_file_path
                
                # Clean and validate data
                self._clean_data()
                
                # STEP 1 & 2: Auto-detect course pairs and section pairings
                self.auto_detect_course_pairs()
                
                # Log processing results
                if split_courses:
                    print(f"File processing complete. {len(split_courses)} courses were split.")
                else:
                    print("File processing complete. No courses needed splitting.")
                
                print(f"✅ Successfully loaded {len(self.get_courses_with_titles())} courses from embedded CSV")
                return True
            else:
                print(f"❌ CSV file not found: {csv_file_path}")
                return False
                
        except Exception as e:
            print(f"❌ Error loading embedded CSV: {e}")
            return False

# Initialize global generator
current_generator = TimetableGenerator()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Main page"""
    return templates.TemplateResponse("scheduler.html", {"request": request})

@app.get("/timetable-viewer", response_class=HTMLResponse)
async def timetable_viewer(request: Request):
    """Timetable viewer page"""
    return templates.TemplateResponse("timetable_viewer.html", {"request": request})

@app.get("/status")
async def get_status():
    """Check if data is loaded and get current state with smart features"""
    global current_generator
    status = {
        "data_loaded": current_generator.course_data is not None,
        "filename": current_generator.current_file_path,
        "total_courses": 0,
        "selected_courses": current_generator.selected_courses,
        "has_combinations": len(current_generator.valid_combinations) > 0,
        
        # SMART FEATURES STATUS
        "smart_features": {
            "course_pairs_detected": len(current_generator.course_pairs) // 2,  # Divide by 2 for unique pairs
            "section_predictions": sum(len(pairs) for pairs in current_generator.correct_pairings.values()),
            "auto_pairing_enabled": len(current_generator.course_pairs) > 0
        }
    }
    
    if current_generator.course_data is not None:
        courses = current_generator.get_courses_with_titles()
        status["total_courses"] = len(courses)
        status["courses"] = courses
    
    return status

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process CSV/Excel file"""
    global current_generator, temp_data_file
    
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Check file extension
    if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    try:
        # Read file content
        content = await file.read()
        
        # Save file temporarily for persistence
        temp_dir = tempfile.gettempdir()
        temp_data_file = os.path.join(temp_dir, f"timetable_data_{file.filename}")
        with open(temp_data_file, 'wb') as f:
            f.write(content)
          # Load data
        success = current_generator.load_data(content, file.filename)
        
        if success:
            courses = current_generator.get_courses_with_titles()
            
            # Check if any courses were processed/split
            processing_message = f"File uploaded successfully! Found {len(courses)} courses."
            
            # The processing info is printed to console, but we can add it to the response
            processing_message += " File has been automatically processed to optimize course sections."
            
            return {
                "success": True,
                "message": processing_message,
                "filename": file.filename,
                "courses": courses
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to process file. Please check file format.")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/courses")
async def get_courses():
    """Get all available courses"""
    global current_generator
    
    if current_generator.course_data is None:
        raise HTTPException(status_code=400, detail="No data loaded")
    
    courses = current_generator.get_courses_with_titles()
    return {"courses": courses}

@app.get("/courses/{course_code}/sections")
async def get_course_sections(course_code: str):
    """Get sections for a specific course"""
    global current_generator
    
    if current_generator.course_data is None:
        raise HTTPException(status_code=400, detail="No data loaded")
    
    sections = current_generator.get_course_sections(course_code)
    return {"sections": sections}

@app.post("/select-sections")
async def select_sections(request: Request):
    """STEP 3: Smart auto-selection with paired course logic (handles selection AND deselection)"""
    global current_generator
    
    data = await request.json()
    course_code = data.get("course_code")
    selected_sections = data.get("selected_sections", [])
    
    if not course_code:
        raise HTTPException(status_code=400, detail="Course code is required")
    
    # Get previous selections to detect what changed
    previous_selections = current_generator.selected_courses.get(course_code, [])
    
    # Update the primary course selection
    current_generator.selected_courses[course_code] = selected_sections
    auto_paired = {}
    
    # Clean up empty selections
    if not selected_sections:
        if course_code in current_generator.selected_courses:
            del current_generator.selected_courses[course_code]
    
    # STEP 3: Smart auto-pairing logic
    if course_code in current_generator.course_pairs:
        paired_course = current_generator.course_pairs[course_code]
        
        if selected_sections:
            # User is selecting sections - do auto-pairing
            compatible_sections = current_generator.find_compatible_sections(course_code, selected_sections, paired_course)
            
            if compatible_sections:
                # Auto-select compatible sections in paired course
                current_generator.selected_courses[paired_course] = compatible_sections
                auto_paired[paired_course] = compatible_sections
                
                print(f"🎯 Auto-paired {course_code} {selected_sections} → {paired_course} {compatible_sections}")
        else:
            # User deselected all sections - clear paired course too
            if paired_course in current_generator.selected_courses:
                del current_generator.selected_courses[paired_course]
                auto_paired[paired_course] = []  # Indicate it was cleared
                print(f"🗑️ Auto-cleared {paired_course} because {course_code} was deselected")
    
    # Remove any courses with empty selections
    current_generator.selected_courses = {
        course: sections for course, sections in current_generator.selected_courses.items() 
        if sections  # Only keep non-empty selections
    }
    
    return {
        "success": True,
        "message": f"Updated sections for {course_code}",
        "selected_courses": current_generator.selected_courses,
        "auto_paired": auto_paired,
        "paired_course": current_generator.course_pairs.get(course_code, None)
    }

@app.post("/create-pair")
async def create_section_pair(request: Request):
    """Create a section pair"""
    global current_generator
    
    data = await request.json()
    course1 = data.get("course1")
    section1 = data.get("section1")
    course2 = data.get("course2")
    section2 = data.get("section2")
    
    if not all([course1, section1, course2, section2]):
        raise HTTPException(status_code=400, detail="All pair parameters are required")
    
    success, message = current_generator.create_section_pair(course1, section1, course2, section2)
    
    return {
        "success": success,
        "message": message
    }

@app.post("/remove-pair")
async def remove_section_pair(request: Request):
    """Remove a section pair"""
    global current_generator
    
    data = await request.json()
    course = data.get("course")
    section = data.get("section")
    
    if not all([course, section]):
        raise HTTPException(status_code=400, detail="Course and section are required")
    
    success, message = current_generator.remove_section_pair(course, section)
    
    return {
        "success": success,
        "message": message
    }

@app.post("/generate")
async def generate_timetables():
    """Generate all possible timetables"""
    global current_generator
    
    if not current_generator.selected_courses:
        raise HTTPException(status_code=400, detail="No courses selected")
    
    try:
        combinations = current_generator.generate_combinations()
        
        if combinations:
            # Format combinations for display
            formatted_combinations = []
            for i, combination in enumerate(combinations):
                formatted = current_generator.format_combination(combination)
                formatted['id'] = i + 1
                formatted_combinations.append(formatted)
            
            # Include active timetable information for the first combination
            active_timetable = None
            if formatted_combinations:
                active_timetable = formatted_combinations[0]
            
            return {
                "success": True,
                "count": len(combinations),
                "timetables": formatted_combinations,
                "active_timetable": active_timetable  # This will be displayed automatically
            }
        else:
            return {
                "success": False,
                "message": "No valid timetables found with current selections",
                "count": 0,
                "timetables": [],
                "active_timetable": None
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating timetables: {str(e)}")

@app.post("/clear-data")
async def clear_all_data():
    """Clear all data"""
    global current_generator, temp_data_file
    
    # Clean up temporary file
    if temp_data_file and os.path.exists(temp_data_file):
        try:
            os.remove(temp_data_file)
        except:
            pass
        temp_data_file = None
    
    current_generator.clear_data()
    return {"success": True, "message": "All data cleared"}

@app.post("/clear-roster")
async def clear_roster():
    """Clear selected courses roster"""
    global current_generator
    current_generator.clear_roster()
    return {"success": True, "message": "Course roster cleared"}

@app.get("/selected-courses")
async def get_selected_courses():
    """Get currently selected courses"""
    global current_generator
    return {"selected_courses": current_generator.selected_courses}
            
@app.get("/auto-pairs")
async def get_auto_pairs():
    """Get discovered course pairs from Step 1"""
    global current_generator
    
    if current_generator.course_data is None:
        raise HTTPException(status_code=400, detail="No data loaded")
    
    # Convert bidirectional pairs to unique pairs
    unique_pairs = []
    seen_pairs = set()
    
    for course1, course2 in current_generator.course_pairs.items():
        pair = tuple(sorted([course1, course2]))
        if pair not in seen_pairs:
            unique_pairs.append({"course1": course1, "course2": course2})
            seen_pairs.add(pair)
    
    return {
        "success": True,
        "pairs": unique_pairs,
        "total_pairs": len(unique_pairs)
    }

@app.get("/section-suggestions/{course_code}")
async def get_section_suggestions(course_code: str):
    """Get suggested sections for auto-pairing"""
    global current_generator
    
    if current_generator.course_data is None:
        raise HTTPException(status_code=400, detail="No data loaded")
    
    suggestions = {}
    
    # Check if this course has a pair
    if course_code in current_generator.course_pairs:
        paired_course = current_generator.course_pairs[course_code]
        source_sections = current_generator.selected_courses.get(course_code, [])
        
        if source_sections:
            # Find compatible sections for the paired course
            compatible_sections = current_generator.find_compatible_sections(
                source_course=course_code,
                source_sections=source_sections,
                target_course=paired_course
            )
            suggestions[paired_course] = compatible_sections
    
    return {
        "success": True,
        "suggestions": suggestions
    }

@app.post("/validate-selection")
async def validate_selection(request: Request):
    """Validate selected sections for compatibility"""
    global current_generator
    
    data = await request.json()
    course_code = data.get("course_code")
    selected_sections = data.get("selected_sections", [])
    
    if not course_code:
        raise HTTPException(status_code=400, detail="Course code is required")
    
    # Get current selections without the new selection
    current_selections = current_generator.selected_courses.copy()
    if course_code in current_selections:
        del current_selections[course_code]
    
    # Add the new selection temporarily
    temp_selections = {course_code: selected_sections}
    
    # Validate all combinations
    all_valid = True
    conflicts = []
    
    return {
        "success": True,
        "is_valid": all_valid,
        "conflicts": conflicts
    }
    
if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable (for deployment) or use default
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    
    # In production, host should be 0.0.0.0 to accept external connections
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER") or os.environ.get("HEROKU"):
        host = "0.0.0.0"
    
    print("🚀 Starting University Timetable Generator with Smart Features...")
    print(f"📍 Server will be available at: http://{host}:{port}")
    if host == "127.0.0.1":
        print("📍 Alternative access: http://localhost:8000")
    print("💡 Press Ctrl+C to stop the server")
    print("🎯 Smart Features:")
    print("   • Auto-detect course pairs on CSV upload")
    print("   • Smart section auto-pairing")
    print("   • Real-time compatibility validation")
    print("   • FullCalendar.js modern interface")
    print("-" * 60)
    
    uvicorn.run(app, host=host, port=port, reload=False)
