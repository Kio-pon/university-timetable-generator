"""
TIMETABLE GENERATOR CORE LOGIC
=============================

This file contains the main TimetableGenerator class with all the smart pairing logic,
course processing, and combination generation functionality.
"""

import pandas as pd
import itertools
from datetime import datetime, time
from collections import defaultdict
import re

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
        self.section_pairs = {}  # pair_id -> list of (course, section) tuples
        self.pair_lookup = {}    # (course, section) -> pair_id
        self.pair_counter = 0    # for generating unique pair IDs
        
    def load_data(self, file_content: bytes, filename: str):
        """Load course data from CSV or Excel file content"""
        try:
            if filename.endswith('.csv'):
                import io
                self.course_data = pd.read_csv(io.BytesIO(file_content))
            else:
                import io
                self.course_data = pd.read_excel(io.BytesIO(file_content))
            
            self.current_file_path = filename
            
            # Process the uploaded file
            from .file_processor import process_uploaded_file
            processed_df, courses_with_multiple_types = process_uploaded_file(self.course_data)
            self.course_data = processed_df
            
            # Clean and validate data
            self._clean_data()
            
            # Auto-detect course pairs
            pairs_detected = self.auto_detect_course_pairs()
            
            return True, f"File loaded successfully! Auto-detected {pairs_detected} course pairs."
        except Exception as e:
            return False, f"Error loading data: {str(e)}"
    
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
        # Remove any rows with missing essential data
        self.course_data = self.course_data.dropna(subset=['Course Code', 'Section', 'Day', 'Start', 'End'])
        
        # Standardize time format
        self.course_data['Start_24h'] = self.course_data['Start'].apply(self._convert_to_24h)
        self.course_data['End_24h'] = self.course_data['End'].apply(self._convert_to_24h)
        
        # Parse days into individual days
        self.course_data['Days_List'] = self.course_data['Day'].apply(self._parse_days)
        
        # Create unique identifiers
        self.course_data['Course_Section'] = self.course_data['Course Code'] + ' ' + self.course_data['Section']
        
    def _convert_to_24h(self, time_str):
        """Convert time string to 24-hour format"""
        try:
            time_str = str(time_str).strip()
            if 'p' in time_str.lower() and not time_str.lower().startswith('12'):
                # PM time (except 12 PM)
                time_part = time_str.lower().replace('p', '')
                hour, minute = map(int, time_part.split(':'))
                hour += 12
            elif 'a' in time_str.lower() and time_str.lower().startswith('12'):
                # 12 AM (midnight)
                time_part = time_str.lower().replace('a', '')
                hour, minute = map(int, time_part.split(':'))
                hour = 0
            else:
                # AM time or already in 24h format
                time_part = time_str.lower().replace('a', '').replace('p', '')
                hour, minute = map(int, time_part.split(':'))
            
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
    
    # =================================================================
    # SMART PAIRING SYSTEM - STEP 1: AUTO-COURSE PAIRING
    # =================================================================
    
    def auto_detect_course_pairs(self):
        """STEP 1: Auto-detect course pairs using learned algorithms"""
        if self.course_data is None:
            return 0
        
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
    
    # =================================================================
    # SMART PAIRING SYSTEM - STEP 2: SECTION PREDICTION
    # =================================================================
    
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
    
    # =================================================================
    # COURSE AND SECTION MANAGEMENT
    # =================================================================
    
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
    
    # =================================================================
    # LEGACY SECTION PAIRING SYSTEM
    # =================================================================
    
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
    
    # =================================================================
    # TIMETABLE GENERATION
    # =================================================================
    
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
                        # Check for overlap
                        if not (end1 <= start2 or end2 <= start1):
                            return True
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
        """Check if a combination of courses is valid (no duplicate courses and no time conflicts)"""
        
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
        
        return True
    
    def format_combination(self, combination):
        """Format a combination for display"""
        schedule = {
            'Monday': [], 'Tuesday': [], 'Wednesday': [], 
            'Thursday': [], 'Friday': [], 'Saturday': [], 'Sunday': []
        }
        
        courses_info = []
        
        for course_code, section, course_data in combination:
            course_info = f"{course_code} {section}"
            title = course_data['Title'].iloc[0]
            instructor = course_data['Instructor / Sponsor'].iloc[0]
            
            courses_info.append({
                'course': course_info,
                'title': title,
                'instructor': instructor
            })
            
            # Add to schedule
            for _, row in course_data.iterrows():
                for day in row['Days_List']:
                    time_slot = f"{row['Start']}-{row['End']}"
                    room = row.get('Room', 'TBA')
                    schedule[day].append({
                        'course': course_info,
                        'time': time_slot,
                        'room': room,
                        'instructor': instructor,
                        'start_24h': row['Start_24h']
                    })
        
        # Sort each day by start time
        for day in schedule:
            schedule[day].sort(key=lambda x: x['start_24h'] if x['start_24h'] else time(0, 0))
        
        return {
            'courses': courses_info,
            'schedule': schedule
        }
    
    # =================================================================
    # EXPORT FUNCTIONALITY
    # =================================================================
    
    def generate_combinations_csv(self):
        """Generate CSV content with all timetable combinations"""
        if not self.valid_combinations:
            return None, "No valid combinations generated yet"
        
        csv_data = []
        
        for i, combination in enumerate(self.valid_combinations, 1):
            # For each combination, create rows for each course section
            base_row = {
                'Combination_Number': i,
                'Total_Courses': len(combination),
                'Course_Code': '',
                'Section': '',
                'Title': '',
                'Day': '',
                'Start_Time': '',
                'End_Time': '',
                'Instructor': '',
                'Room': ''
            }
            
            # Add a row for each course in the combination
            for course_code, section, section_data in combination:
                # Use the section_data that's already available
                if len(section_data) > 0:
                    for _, row in section_data.iterrows():
                        combination_row = base_row.copy()
                        combination_row.update({
                            'Course_Code': course_code,
                            'Section': section,
                            'Title': row.get('Title', ''),
                            'Day': row.get('Day', ''),
                            'Start_Time': row.get('Start', ''),
                            'End_Time': row.get('End', ''),
                            'Instructor': row.get('Instructor / Sponsor', ''),
                            'Room': row.get('Room', 'TBA')
                        })
                        csv_data.append(combination_row)
            
            # Add a separator row between combinations
            if i < len(self.valid_combinations):
                separator_row = {key: '' for key in base_row.keys()}
                separator_row['Combination_Number'] = f'--- End of Combination {i} ---'
                csv_data.append(separator_row)
        
        # Convert to DataFrame and then to CSV
        df = pd.DataFrame(csv_data)
        
        # Generate CSV content
        csv_content = df.to_csv(index=False)
        
        # Generate summary
        summary = f"""
TIMETABLE COMBINATIONS EXPORT SUMMARY
=====================================
Total Combinations: {len(self.valid_combinations)}
Total Courses per Combination: {len(self.valid_combinations[0]) if self.valid_combinations else 0}
Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CSV Format:
- Each row represents one course section in a combination
- Combination_Number groups sections that belong together
- Multiple rows with same Combination_Number = one complete timetable
"""
        
        return csv_content, summary

    def get_combinations_stats(self):
        """Get statistics about generated combinations"""
        if not self.valid_combinations:
            return None
        
        stats = {
            'total_combinations': len(self.valid_combinations),
            'courses_per_combination': len(self.valid_combinations[0]) if self.valid_combinations else 0,
            'selected_courses': list(self.selected_courses.keys()),
            'sections_per_course': {course: len(sections) for course, sections in self.selected_courses.items()},
            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return stats
