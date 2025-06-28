"""
FILE PROCESSING AND AI UTILITIES
================================

This file contains file processing functions, AI preference scoring,
and utility functions for the timetable generator.
"""

import pandas as pd
import re
from collections import defaultdict
from datetime import datetime, time

# =================================================================
# FILE PROCESSING FUNCTIONS
# =================================================================

def extract_section_type(section):
    """
    Extract the section type (letter part) from a section code.
    E.g., 'L1' -> 'L', 'R2' -> 'R', 'T1' -> 'T', 'S18' -> 'S'
    """
    match = re.match(r'^([A-Za-z]+)', str(section).strip())
    return match.group(1) if match else None

def process_uploaded_file(df):
    """
    Process the uploaded DataFrame to split courses with multiple section types
    and ensure correct headers are present.
    """
    print(f"Processing uploaded file with {len(df)} rows")
    print(f"Original columns: {list(df.columns)}")
    
    # Required headers in the correct order
    required_headers = ['Course Code', 'Section', 'Title', 'Day', 'Start', 'End', 'Room', 'Instructor / Sponsor']
    
    # Check if the current column headers match the required headers
    current_headers = list(df.columns)
    
    if current_headers != required_headers:
        print("Headers don't match required format. Adding proper headers and pushing data down...")
        
        # Create a new DataFrame with proper headers
        # First, convert the current DataFrame to a list of rows (including current headers as first row)
        all_rows = []
        
        # Add current column headers as the first data row
        all_rows.append(current_headers)
        
        # Add all existing data rows
        for _, row in df.iterrows():
            all_rows.append(row.tolist())
        
        # Create new DataFrame with required headers and all data pushed down
        new_df = pd.DataFrame(all_rows, columns=required_headers[:len(current_headers)])
        
        # If we have fewer columns than required, add empty columns
        for i, header in enumerate(required_headers):
            if i >= len(current_headers):
                new_df[header] = ''
        
        # Reorder columns to match required order
        df = new_df[required_headers]
        
        print(f"Added proper headers: {required_headers}")
        print(f"Data rows increased from {len(df)-len(all_rows)} to {len(df)} (headers became data)")
    else:
        print("Headers are already in the correct format.")
    
    # Group courses by course code to find section types
    course_sections = defaultdict(set)
    for index, row in df.iterrows():
        course_code = str(row['Course Code']).strip()
        # Skip empty or invalid course codes
        if not course_code or course_code.lower() in ['nan', 'course code']:
            continue
            
        # Replace forward slashes with pipe symbol for URL compatibility
        course_code = course_code.replace('/', '|')
        section = str(row['Section']).strip()
        section_type = extract_section_type(section)
        
        if section_type:
            course_sections[course_code].add(section_type)
    
    # Find courses with multiple section types
    courses_with_multiple_types = {
        course: types for course, types in course_sections.items() 
        if len(types) > 1
    }
    
    print(f"Found {len(courses_with_multiple_types)} courses with multiple section types:")
    for course, types in courses_with_multiple_types.items():
        print(f"  {course}: {sorted(types)}")
    
    # Create a new DataFrame with split course codes
    new_rows = []
    for index, row in df.iterrows():
        course_code = str(row['Course Code']).strip()
        
        # Skip empty or invalid course codes (like header rows that became data)
        if not course_code or course_code.lower() in ['nan', 'course code']:
            continue
            
        # Replace forward slashes with pipe symbol for URL compatibility
        course_code = course_code.replace('/', '|')
        section = str(row['Section']).strip()
        section_type = extract_section_type(section)
        
        # Create new row with modified course code
        new_row = row.copy()
        new_row['Course Code'] = course_code  # Update with cleaned course code
        
        if course_code in courses_with_multiple_types and section_type:
            # Split the course code by adding the section type
            new_course_code = f"{course_code}{section_type}"
            new_row['Course Code'] = new_course_code
            print(f"Modified: {course_code} (section {section}) -> {new_course_code}")
        
        new_rows.append(new_row)
    
    # Create new DataFrame with processed data
    processed_df = pd.DataFrame(new_rows)
    
    print(f"Processing complete:")
    print(f"Final columns: {list(processed_df.columns)}")
    print(f"Valid data rows: {len(processed_df)}")
    print(f"Original courses: {len(course_sections)}")
    print(f"Courses with multiple section types: {len(courses_with_multiple_types)}")
    
    return processed_df, courses_with_multiple_types

# =================================================================
# AI PREFERENCE SCORING FUNCTIONS
# =================================================================

def score_combinations_by_preferences(combinations, preferences):
    """Score combinations based on user preferences (AI implementation)"""
    scored_combinations = []
    
    for combination in combinations:
        score = 0
        
        # AI-based scoring based on preferences
        
        # Time preferences scoring
        if preferences.get('avoid_early_morning', False):
            early_classes = check_early_morning_classes(combination)
            score += (10 - early_classes * 2)  # Penalize early morning classes
            
        if preferences.get('avoid_late_evening', False):
            late_classes = check_late_evening_classes(combination)
            score += (10 - late_classes * 2)  # Penalize late evening classes
            
        # Gap preferences scoring
        if preferences.get('avoid_long_gaps', False):
            long_gaps = count_long_gaps(combination)
            score += (10 - long_gaps * 3)  # Heavily penalize long gaps
            
        # Day distribution scoring
        if preferences.get('minimize_commute', False):
            unique_days = count_unique_days(combination)
            score += (15 - unique_days * 2)  # Favor fewer days on campus
            
        # Lunch break scoring
        if preferences.get('lunch_break', False):
            has_lunch_conflict = check_lunch_conflicts(combination)
            score += 0 if has_lunch_conflict else 5  # Bonus for preserving lunch
            
        scored_combinations.append({
            'combination': combination,
            'score': max(score, 0),  # Ensure non-negative scores
            'details': get_combination_details(combination)
        })
    
    # Sort by score (highest first)
    return sorted(scored_combinations, key=lambda x: x['score'], reverse=True)

def check_early_morning_classes(combination):
    """Count classes before 9 AM"""
    count = 0
    for course_code, section, section_data in combination:
        for _, row in section_data.iterrows():
            start_time = row.get('Start_24h')
            if start_time and start_time.hour < 9:
                count += 1
    return count

def check_late_evening_classes(combination):
    """Count classes after 6 PM"""
    count = 0
    for course_code, section, section_data in combination:
        for _, row in section_data.iterrows():
            start_time = row.get('Start_24h')
            if start_time and start_time.hour >= 18:
                count += 1
    return count

def count_long_gaps(combination):
    """Count gaps longer than 2 hours"""
    # AI algorithm for detecting long gaps
    daily_schedules = {}
    
    for course_code, section, section_data in combination:
        for _, row in section_data.iterrows():
            if 'Days_List' in row and row['Days_List']:
                for day in row['Days_List']:
                    if day not in daily_schedules:
                        daily_schedules[day] = []
                    
                    start_time = row.get('Start_24h')
                    end_time = row.get('End_24h')
                    if start_time and end_time:
                        daily_schedules[day].append((start_time, end_time))
    
    long_gaps = 0
    for day, times in daily_schedules.items():
        times.sort(key=lambda x: x[0])
        for i in range(len(times) - 1):
            gap_hours = (times[i+1][0].hour - times[i][1].hour)
            if gap_hours > 2:
                long_gaps += 1
    
    return long_gaps

def count_unique_days(combination):
    """Count unique days in the combination"""
    days = set()
    for course_code, section, section_data in combination:
        for _, row in section_data.iterrows():
            if 'Days_List' in row and row['Days_List']:
                days.update(row['Days_List'])
    return len(days)

def check_lunch_conflicts(combination):
    """Check if any classes conflict with lunch time (12-1 PM)"""
    for course_code, section, section_data in combination:
        for _, row in section_data.iterrows():
            start_time = row.get('Start_24h')
            end_time = row.get('End_24h')
            if start_time and end_time:
                # Check if class overlaps with 12-1 PM
                if (start_time.hour < 13 and end_time.hour > 12):
                    return True
    return False

def get_combination_details(combination):
    """Get readable details for a combination"""
    details = {
        'courses': [],
        'total_hours': 0,
        'days_used': set()
    }
    
    for course_code, section, section_data in combination:
        course_info = {
            'code': course_code,
            'section': section,
            'schedule': []
        }
        
        for _, row in section_data.iterrows():
            if 'Days_List' in row and row['Days_List']:
                details['days_used'].update(row['Days_List'])
                course_info['schedule'].append({
                    'days': row['Days_List'],
                    'time': f"{row.get('Start', '')} - {row.get('End', '')}",
                    'location': row.get('Room', 'TBA')
                })
        
        details['courses'].append(course_info)
    
    details['days_used'] = list(details['days_used'])
    return details

# =================================================================
# CSV GENERATION UTILITIES
# =================================================================

def generate_selected_sections_csv(course_data, selected_courses):
    """Generate CSV content for selected sections only"""
    if course_data is None or not selected_courses:
        return ""
    
    import io
    import csv
    
    # Get original column headers from the uploaded data, excluding internal processing columns
    all_headers = list(course_data.columns)
    excluded_columns = ['Start_24h', 'End_24h', 'Days_List', 'Course_Section']
    headers = [header for header in all_headers if header not in excluded_columns]
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    
    # Write only selected sections
    for _, row in course_data.iterrows():
        course_code = row.get('Course Code', '')
        section = row.get('Section', '')
        
        # Check if this section is selected
        if course_code in selected_courses:
            if section in selected_courses[course_code]:
                # Create a filtered row dictionary without the excluded columns
                filtered_row = {key: value for key, value in row.to_dict().items() if key in headers}
                writer.writerow(filtered_row)
    
    return output.getvalue()
