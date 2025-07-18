"""
Web-based University Timetable Generator using FastAPI
Converts the tkinter scheduler to a modern web interface
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request, Response, Cookie
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, time
import itertools
import pandas as pd
import re
from collections import defaultdict
import json
import os
from pathlib import Path
import io
import time as time_module
from typing import List, Dict, Any, Optional
import tempfile
import shutil
import csv
import uuid
import asyncio
from fastapi.responses import StreamingResponse

app = FastAPI(title="University Timetable Generator", version="1.0.0")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Import OLSSS functionality
from olsss_main import register_olsss_routes

# Session-based TimetableGenerator management
session_store = {}  # In-memory dictionary for session data
SESSION_COOKIE = "session_id"

def get_session_id(session_id: str = None):
    if session_id is None:
        session_id = str(uuid.uuid4())
    return session_id

def get_generator(session_id):
    if session_id not in session_store:
        session_store[session_id] = TimetableGenerator()
    return session_store[session_id]

# Register OLSSS routes
register_olsss_routes(app, templates)

# Import the file processor function
from progress_archive.file_processor import process_uploaded_file, extract_section_type

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
        
        # Elective course categories
        self.elective_categories = {} # e.g., {"NS Elective": ["BIO 101", "PHY 101"]}
        self.course_assignments = {} # e.g., {"BIO 101": "NS Elective", "CS 101": "core"}
        
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
        
        # Clear elective categories
        self.elective_categories = {}
        self.course_assignments = {}
        
        # Clear legacy data
        self.section_pairs = {}
        self.pair_lookup = {}
        self.pair_counter = 0
    
    def clear_roster(self):
        """Clear only the selected courses roster (keep smart features)"""
        self.selected_courses = {}
        self.valid_combinations = []
        # Also clear elective categories since they reference courses
        self.elective_categories = {}
        self.course_assignments = {}
    
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
            
            # Skip if it's NaN, empty, or column headers
            if time_str.lower() in ['nan', '', 'start time', 'end time', 'start', 'end']:
                return None
            
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

    
        """Optimized combination generation with smart filtering"""
        if not self.selected_courses:
            return []
        
        # Pre-filter incompatible sections before generating combinations
        filtered_course_options = self._prefilter_course_options()
        
        if not filtered_course_options:
            return []
        
        valid_combinations = []
        total_combinations = 1
        for options in filtered_course_options:
            total_combinations *= len(options)
        
        print(f"🔍 Checking {total_combinations} combinations...")
        
        # Use itertools.product but with early validation
        combinations_checked = 0
        for combination in itertools.product(*filtered_course_options):
            combinations_checked += 1
            
            # Progress indicator for large searches
            if combinations_checked % 1000 == 0:
                print(f"   Checked {combinations_checked}/{total_combinations}...")
            
            # Flatten combination
            flattened_combination = []
            for unit in combination:
                flattened_combination.extend(unit)
            
            if self._is_valid_combination_optimized(flattened_combination):
                valid_combinations.append(flattened_combination)
                
                # Optional: Stop after finding N valid combinations
                if len(valid_combinations) >= 100:  # Limit to first 100 valid combinations
                    print(f"⚡ Found {len(valid_combinations)} combinations, stopping search...")
                    break
        
        print(f"✅ Found {len(valid_combinations)} valid combinations from {combinations_checked} checked")
        self.valid_combinations = valid_combinations
        return valid_combinations

    def _is_valid_combination_optimized(self, combination):
        """Optimized validation with early exits and caching"""
        
        # Check 1: No multiple sections of the same course (fastest check first)
        seen_courses = set()
        course_time_slots = []  # Cache time slots for conflict checking
        
        for course_code, section, course_data in combination:
            if course_code in seen_courses:
                return False  # Early exit on duplicate course
            seen_courses.add(course_code)
            
            # Pre-process time slots once
            for _, row in course_data.iterrows():
                if row['Start_24h'] and row['End_24h']:  # Skip invalid times
                    course_time_slots.append({
                        'course': f"{course_code} {section}",
                        'days': set(row['Days_List']),
                        'start': row['Start_24h'],
                        'end': row['End_24h']
                    })
        
        # Check 2: Optimized time conflict detection
        if self._has_time_conflicts_optimized(course_time_slots):
            return False
        
        # Check 3: Smart pairing validation (already optimized)
        return self._is_smart_pairing_valid(combination)

    def _has_time_conflicts_optimized(self, time_slots):
        """Optimized conflict detection with early exit"""
        n = len(time_slots)
        
        for i in range(n):
            for j in range(i + 1, n):
                slot1, slot2 = time_slots[i], time_slots[j]
                
                # Quick day overlap check
                if not slot1['days'] & slot2['days']:  # No common days
                    continue
                    
                # Time overlap check (only if days overlap)
                if slot1['start'] < slot2['end'] and slot2['start'] < slot1['end']:
                    return True  # Conflict found - early exit
        
        return False

    def generate_combinations_smart_limit(self, max_combinations=300, max_time_seconds=50):
        """Generate combinations with smart limits"""
        start_time = time_module.time()
        
        if not self.selected_courses:
            return []
        
        filtered_course_options = self._prefilter_course_options()
        if not filtered_course_options:
            return []
        
        valid_combinations = []
        combinations_checked = 0
        
        for combination in itertools.product(*filtered_course_options):
            # Time limit check
            if time_module.time() - start_time > max_time_seconds:
                print(f"⏰ Time limit reached ({max_time_seconds}s), stopping search...")
                break
            
            # Combination limit check
            if len(valid_combinations) >= max_combinations:
                print(f"🎯 Found {max_combinations} combinations, stopping search...")
                break
            
            combinations_checked += 1
            
            flattened_combination = []
            for unit in combination:
                flattened_combination.extend(unit)
            
            if self._is_valid_combination_optimized(flattened_combination):
                valid_combinations.append(flattened_combination)
        
        print(f"✅ Generated {len(valid_combinations)} combinations in {time_module.time() - start_time:.2f}s")
        self.valid_combinations = valid_combinations
        return valid_combinations

    def _prefilter_course_options(self):
        """
        Pre-filter course options for combination generation.
        Now uses course assignments instead of separate elective_categories.
        """
        course_options = []
        processed_pairs = set()

        # 1. Process core courses (assigned to "core" or not assigned)
        core_courses = {}
        for course_code, selected_sections in self.selected_courses.items():
            assignment = self.course_assignments.get(course_code, "core")
            if assignment == "core":
                core_courses[course_code] = selected_sections

        for course_code, selected_sections in core_courses.items():
            if not selected_sections:
                continue
                
            course_section_options = []
            
            for section in selected_sections:
                section_key = (course_code, section)
                
                if section_key in processed_pairs:
                    continue
                
                section_data = self.course_data[
                    (self.course_data['Course Code'] == course_code) & 
                    (self.course_data['Section'] == section)
                ]
                
                if self.is_section_paired(course_code, section):
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
                    atomic_unit = [(course_code, section, section_data)]
                    course_section_options.append(atomic_unit)
            
            if course_section_options:
                course_options.append(course_section_options)

        # 2. Process elective categories (courses assigned to category names)
        # Group courses by their assignments, treating paired courses as atomic units
        elective_groups = {}
        processed_elective_courses = set()
        
        for course_code, assignment in self.course_assignments.items():
            if assignment != "core" and course_code in self.selected_courses and course_code not in processed_elective_courses:
                if assignment not in elective_groups:
                    elective_groups[assignment] = []
                
                # Check if this course has a pair
                paired_courses = [course_code]
                if course_code in self.course_pairs:
                    paired_course = self.course_pairs[course_code]
                    if paired_course in self.selected_courses and self.course_assignments.get(paired_course) == assignment:
                        paired_courses.append(paired_course)
                        processed_elective_courses.add(paired_course)
                
                elective_groups[assignment].append(paired_courses)
                processed_elective_courses.add(course_code)

        for category_name, course_groups in elective_groups.items():
            if not course_groups:
                continue

            category_choices = []
            for course_group in course_groups:  # course_group is either [course] or [course, paired_course]
                group_sections = []
                
                # Get all section combinations for this course group
                group_section_options = []
                for course_code in course_group:
                    selected_sections = self.selected_courses.get(course_code, [])
                    course_section_list = []
                    
                    for section in selected_sections:
                        section_key = (course_code, section)
                        if section_key in processed_pairs:
                            continue
                            
                        section_data = self.course_data[
                            (self.course_data['Course Code'] == course_code) & 
                            (self.course_data['Section'] == section)
                        ]
                        
                        atomic_unit = [(course_code, section, section_data)]
                        if self.is_section_paired(course_code, section):
                            paired_sections = self.get_paired_sections(course_code, section)
                            for paired_course, paired_section in paired_sections:
                                paired_data = self.course_data[
                                    (self.course_data['Course Code'] == paired_course) & 
                                    (self.course_data['Section'] == paired_section)
                                ]
                                atomic_unit.append((paired_course, paired_section, paired_data))
                                processed_pairs.add((paired_course, paired_section))
                        
                        course_section_list.append(atomic_unit)
                        processed_pairs.add(section_key)
                    
                    if course_section_list:
                        group_section_options.append(course_section_list)
                
                # For course groups (like BIO 101 + BIO 101L), we need to create valid combinations
                if len(group_section_options) == 1:
                    # Single course in group
                    category_choices.extend(group_section_options[0])
                elif len(group_section_options) == 2:
                    # Paired courses - combine their sections appropriately
                    for sections1 in group_section_options[0]:
                        for sections2 in group_section_options[1]:
                            combined_sections = sections1 + sections2
                            category_choices.append(combined_sections)
            
            if category_choices:
                course_options.append(category_choices)
        
        return course_options

    def _build_conflict_matrix(self):
        """Build a conflict matrix for O(1) conflict lookups"""
        if hasattr(self, '_conflict_matrix'):
            return  # Already built
        
        self._conflict_matrix = {}
        all_sections = []
        
        # Collect all section identifiers
        for course_code, selected_sections in self.selected_courses.items():
            for section in selected_sections:
                section_id = f"{course_code}_{section}"
                all_sections.append(section_id)
                
                # Get time data for this section
                section_data = self.course_data[
                    (self.course_data['Course Code'] == course_code) & 
                    (self.course_data['Section'] == section)
                ]
                
                time_slots = []
                for _, row in section_data.iterrows():
                    if row.get('Start_24h') and row.get('End_24h'):
                        time_slots.append({
                            'days': set(row['Days_List']) if 'Days_List' in row else set(),
                            'start': row['Start_24h'],
                            'end': row['End_24h']
                        })
                
                self._conflict_matrix[section_id] = time_slots
        
        print(f"🔧 Built conflict matrix for {len(all_sections)} sections")
    
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
        
        # Early exit if no course pairs exist
        if not self.course_pairs:
            return True
        
        # Build a set of paired courses for O(1) lookup
        paired_courses = set(self.course_pairs.keys())
        
        # Extract course info once
        courses_in_combo = [(course_code, section) for course_code, section, _ in combination]
        
        # Convert to dict for faster lookup
        course_sections_dict = {course_code: section for course_code, section, _ in combination}
        
        # Only check courses that are actually paired
        for course1_code, section1 in courses_in_combo:
            if course1_code not in paired_courses:
                continue
                
            course2_code = self.course_pairs[course1_code]
            
            # Use dict lookup instead of loop (more efficient)
            course2_section = course_sections_dict.get(course2_code)
            
            # If paired course is in combination, validate the pairing
            if course2_section is not None:
                if not self._are_sections_correctly_paired(course1_code, section1, course2_code, course2_section):
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

    def format_combination(self, combination):
        """Format a combination for display in the web interface"""
        formatted_courses = []
        schedule = {
            'Monday': [],
            'Tuesday': [],
            'Wednesday': [],
            'Thursday': [],
            'Friday': [],
            'Saturday': [],
            'Sunday': []
        }
        
        for course_code, section, course_data in combination:
            # Get course title from the first row
            title = course_data['Title'].iloc[0] if not course_data.empty else "Unknown Title"
            instructor = course_data['Instructor / Sponsor'].iloc[0] if not course_data.empty else "Unknown Instructor"
            
            # Collect all time slots for this course section
            time_slots = []
            for _, row in course_data.iterrows():
                day = row['Day']
                start_time = row['Start']
                end_time = row['End']
                # Try multiple possible column names for location
                location = row.get('Room', row.get('Location', 'TBA'))
                
                time_slots.append({
                    'day': day,
                    'start_time': start_time,
                    'end_time': end_time,
                    'location': location
                })
                
                # Add to schedule organized by day
                # Parse days (handle TTh, MW, etc.)
                days_list = row.get('Days_List', [])
                if not days_list:
                    # Fallback to parsing the day string
                    days_list = self._parse_days(day)
                
                for parsed_day in days_list:
                    if parsed_day in schedule:
                        schedule[parsed_day].append({
                            'course': self.format_course_code_for_display(course_code),
                            'section': section,
                            'title': title,
                            'instructor': instructor,
                            'room': location,  # This will now use the correct location from above
                            'start': start_time,
                            'end': end_time,
                            'time': f"{start_time} - {end_time}"
                        })
            
            formatted_courses.append({
                'course_code': self.format_course_code_for_display(course_code),
                'section': section,
                'title': title,
                'instructor': instructor,
                'time_slots': time_slots
            })
        
        return {
            'courses': formatted_courses,
            'total_courses': len(formatted_courses),
            'schedule': schedule
        }

    def load_embedded_data(self):
        """Load CSV data from the same folder automatically"""
        try:
            # Look for the CSV file in the same directory
            csv_file_path = "Courses.csv"
            
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

    def create_elective_category(self, category_name: str):
        """Creates a new, empty elective category."""
        if category_name and category_name not in self.elective_categories:
            self.elective_categories[category_name] = []
            return True, f"Category '{category_name}' created successfully."
        return False, f"Category '{category_name}' already exists or is invalid."

    def add_course_to_elective_category(self, category_name: str, course_code: str):
        """Adds a course to an elective category and removes it from main selection."""
        if category_name not in self.elective_categories:
            return False, "Elective category not found."
        if course_code not in self.elective_categories[category_name]:
            self.elective_categories[category_name].append(course_code)
            # Remove from the main selected_courses dict to avoid duplication
            if course_code in self.selected_courses:
                del self.selected_courses[course_code]
            return True, f"Added '{course_code}' to category '{category_name}'."
        return False, f"'{course_code}' is already in category '{category_name}'."

    def remove_course_from_elective_category(self, category_name: str, course_code: str):
        """Removes a course from an elective category."""
        if category_name in self.elective_categories and course_code in self.elective_categories[category_name]:
            self.elective_categories[category_name].remove(course_code)
            # If the category is now empty, consider removing it or leaving it
            return True, f"Removed '{course_code}' from category '{category_name}'."
        return False, "Course or category not found."

    def delete_elective_category(self, category_name: str):
        """Deletes an entire elective category."""
        if category_name in self.elective_categories:
            # Optional: move courses back to main selection, for now just delete
            del self.elective_categories[category_name]
            return True, f"Category '{category_name}' deleted."
        return False, "Category not found."

    def assign_course_to_category(self, course_code: str, category_name: str):
        """Assign a course to a specific category (or 'core' for core courses)
        Also automatically assigns all paired courses to the same category."""
        if course_code not in self.selected_courses:
            return False, "Course not found in selected courses"
        
        # Assign the main course
        self.course_assignments[course_code] = category_name
        assigned_courses = [course_code]
        
        # Find and assign paired courses if they exist and are selected
        # Check if this course has a pair in course_pairs
        if course_code in self.course_pairs:
            paired_course_code = self.course_pairs[course_code]
            
            # Only assign if the paired course is also selected
            if paired_course_code in self.selected_courses:
                self.course_assignments[paired_course_code] = category_name
                assigned_courses.append(paired_course_code)
        
        if len(assigned_courses) > 1:
            courses_str = ", ".join(assigned_courses)
            return True, f"Assigned '{courses_str}' to '{category_name}' (paired courses)"
        else:
            return True, f"Assigned '{course_code}' to '{category_name}'"

    def get_available_categories(self):
        """Get list of available categories including 'core'"""
        categories = ["core"]
        categories.extend(list(self.elective_categories.keys()))
        return categories

    def get_course_assignments(self):
        """Get the current course assignments"""
        return self.course_assignments

# Initialize global generator
# current_generator = TimetableGenerator()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Main page"""
    return templates.TemplateResponse("scheduler.html", {"request": request})

@app.get("/timetable-viewer", response_class=HTMLResponse)
async def timetable_viewer(request: Request):
    """Timetable viewer page"""
    return templates.TemplateResponse("timetable_viewer.html", {"request": request})

@app.get("/status")
async def get_status(response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    status = {
        "data_loaded": generator.course_data is not None,
        "filename": generator.current_file_path,
        "total_courses": 0,
        "selected_courses": generator.selected_courses,
        "has_combinations": len(generator.valid_combinations) > 0,
        "smart_features": {
            "course_pairs_detected": len(generator.course_pairs) // 2,
            "section_predictions": sum(len(pairs) for pairs in generator.correct_pairings.values()),
            "auto_pairing_enabled": len(generator.course_pairs) > 0,
            "elective_categories": len(generator.elective_categories),
            "elective_courses": sum(len(courses) for courses in generator.elective_categories.values())
        }
    }
    if generator.course_data is not None:
        courses = generator.get_courses_with_titles()
        status["total_courses"] = len(courses)
        status["courses"] = courses
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
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

@app.post("/select_courses")
async def select_courses(request: Request, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    data = await request.json()
    generator.selected_courses = data.get("selected_courses", {})
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"message": "Courses selected"}

@app.get("/get_courses")
async def get_courses(response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"selected_courses": generator.selected_courses}

@app.post("/generate")
async def generate_timetable(request: Request, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    # Optionally update selected_courses here if needed
    generator.valid_combinations = generator.generate_combinations_smart_limit()
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": True, "count": len(generator.valid_combinations), "timetables": [generator.format_combination(c) for c in generator.valid_combinations]}

@app.post("/clear_data")
async def clear_data(response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    generator.clear_data()
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"message": "Data cleared"}

@app.post("/clear_roster")
async def clear_roster(response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    generator.clear_roster()
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"message": "Roster cleared"}

@app.get("/get_timetables")
async def get_timetables(response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"timetables": [generator.format_combination(c) for c in generator.valid_combinations]}

@app.post("/select-sections")
async def select_sections(request: Request, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    data = await request.json()
    course_code = data.get("course_code")
    selected_sections = data.get("selected_sections", [])
    if not course_code:
        raise HTTPException(status_code=400, detail="Course code is required")
    previous_selections = generator.selected_courses.get(course_code, [])
    generator.selected_courses[course_code] = selected_sections
    auto_paired = {}
    if not selected_sections:
        if course_code in generator.selected_courses:
            del generator.selected_courses[course_code]
    if course_code in generator.course_pairs:
        paired_course = generator.course_pairs[course_code]
        if selected_sections:
            compatible_sections = generator.find_compatible_sections(course_code, selected_sections, paired_course)
            if compatible_sections:
                generator.selected_courses[paired_course] = compatible_sections
                auto_paired[paired_course] = compatible_sections
                print(f"🎯 Auto-paired {course_code} {selected_sections} → {paired_course} {compatible_sections}")
        else:
            if paired_course in generator.selected_courses:
                del generator.selected_courses[paired_course]
                auto_paired[paired_course] = []
                print(f"🗑️ Auto-cleared {paired_course} because {course_code} was deselected")
    generator.selected_courses = {
        course: sections for course, sections in generator.selected_courses.items() if sections
    }
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {
        "success": True,
        "message": f"Updated sections for {course_code}",
        "selected_courses": generator.selected_courses,
        "auto_paired": auto_paired,
        "paired_course": generator.course_pairs.get(course_code, None)
    }

@app.post("/create-pair")
async def create_section_pair(request: Request, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    data = await request.json()
    course1 = data.get("course1")
    section1 = data.get("section1")
    course2 = data.get("course2")
    section2 = data.get("section2")
    if not all([course1, section1, course2, section2]):
        raise HTTPException(status_code=400, detail="All pair parameters are required")
    success, message = generator.create_section_pair(course1, section1, course2, section2)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": success, "message": message}

@app.post("/remove-pair")
async def remove_section_pair(request: Request, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    data = await request.json()
    course = data.get("course")
    section = data.get("section")
    if not all([course, section]):
        raise HTTPException(status_code=400, detail="Course and section are required")
    success, message = generator.remove_section_pair(course, section)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": success, "message": message}

@app.get("/selected-courses")
async def get_selected_courses(response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"selected_courses": generator.selected_courses}

@app.get("/auto-pairs")
async def get_auto_pairs(response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    if generator.course_data is None:
        return {"success": True, "pairs": [], "total_pairs": 0}
    unique_pairs = []
    seen_pairs = set()
    for course1, course2 in generator.course_pairs.items():
        pair = tuple(sorted([course1, course2]))
        if pair not in seen_pairs:
            unique_pairs.append(pair)
            seen_pairs.add(pair)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": True, "pairs": unique_pairs, "total_pairs": len(unique_pairs)}

@app.get("/section-suggestions/{course_code}")
async def get_section_suggestions(course_code: str, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    if generator.course_data is None:
        return {"success": True, "suggestions": {}}
    suggestions = {}
    if course_code in generator.course_pairs:
        paired_course = generator.course_pairs[course_code]
        selected_sections = generator.selected_courses.get(course_code, [])
        suggestions[paired_course] = generator.find_compatible_sections(course_code, selected_sections, paired_course)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": True, "suggestions": suggestions}

@app.post("/validate-selection")
async def validate_selection(request: Request, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    data = await request.json()
    course_code = data.get("course_code")
    selected_sections = data.get("selected_sections", [])
    if not course_code:
        raise HTTPException(status_code=400, detail="Course code is required")
    # Example validation logic (customize as needed):
    # Check if selected sections are compatible
    # For now, just return success
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": True, "message": "Selection validated"}
    
@app.get("/courses/{course_code}/sections")
async def get_course_sections(course_code: str, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    sections = generator.get_course_sections(course_code)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"sections": sections}
    
@app.get("/get-results")
async def get_results(response: Response, session_id: str = Cookie(None)):
    """Get existing timetable results without regenerating"""
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    
    if generator.valid_combinations:
        return {
            "success": True, 
            "count": len(generator.valid_combinations), 
            "timetables": [generator.format_combination(c) for c in generator.valid_combinations]
        }
    else:
        return {"success": False, "count": 0, "timetables": []}
    
@app.post("/electives/create-category")
async def create_elective_category_endpoint(request: Request, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    data = await request.json()
    category_name = data.get("category_name")
    success, message = generator.create_elective_category(category_name)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": success, "message": message, "categories": generator.elective_categories}

@app.post("/electives/add-course")
async def add_course_to_category_endpoint(request: Request, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    data = await request.json()
    category_name = data.get("category_name")
    course_code = data.get("course_code")
    success, message = generator.add_course_to_elective_category(category_name, course_code)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": success, "message": message, "categories": generator.elective_categories}

@app.post("/electives/remove-course")
async def remove_course_from_category_endpoint(request: Request, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    data = await request.json()
    category_name = data.get("category_name")
    course_code = data.get("course_code")
    success, message = generator.remove_course_from_elective_category(category_name, course_code)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": success, "message": message, "categories": generator.elective_categories}

@app.post("/electives/delete-category")
async def delete_elective_category_endpoint(request: Request, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    data = await request.json()
    category_name = data.get("category_name")
    success, message = generator.delete_elective_category(category_name)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": success, "message": message, "categories": generator.elective_categories}

@app.get("/electives/get-categories")
async def get_elective_categories_endpoint(response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": True, "categories": generator.elective_categories}

@app.post("/electives/assign-course")
async def assign_course_to_category_endpoint(request: Request, response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    data = await request.json()
    course_code = data.get("course_code")
    category_name = data.get("category_name")
    success, message = generator.assign_course_to_category(course_code, category_name)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {"success": success, "message": message, "assignments": generator.course_assignments}

@app.get("/electives/get-assignments")
async def get_course_assignments_endpoint(response: Response, session_id: str = Cookie(None)):
    session_id = get_session_id(session_id)
    generator = get_generator(session_id)
    response.set_cookie(key=SESSION_COOKIE, value=session_id, httponly=True)
    return {
        "success": True, 
        "assignments": generator.course_assignments,
        "available_categories": generator.get_available_categories()
    }

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable (for deployment) or use default
    # port = int(os.environ.get("PORT", 8000))
    # host = os.environ.get("HOST", "127.0.0.1")
    
    # Get port from environment variable (for deployment) or use default
    port = int(os.environ.get("PORT", 2002))
    host = os.environ.get("HOST", "0.0.0.0")
    # host = os.environ.get("HOST", "192.168.1.2") for sharing on the same network locally running
 
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
    print("   • Elective course categorization")
    print("🍽️ OLSSS (Online Lunch Sale & Tally System):")
    print(f"   • Available at: http://{host}:{port}/OLSSS")
    print("   • Real-time order management")
    print("   • Admin panel for payment tracking")
    print("   • Live updates via Server-Sent Events")
    print("-" * 60)
    
    uvicorn.run(app, host=host, port=port, reload=False)

