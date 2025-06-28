"""
Comprehensive University Timetable Generator
A complete solution for generating all possible schedule combinations
from university course data with conflict detection and visualization.
"""

import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import itertools
from datetime import datetime, time
import re
from collections import defaultdict
import json
import os
from pathlib import Path

class TimetableGenerator:   
    def _init_(self):
        self.course_data = None
        self.selected_courses = {}
        self.valid_combinations = []
        self.current_file_path = None
        
        # Atomic pairing system
        self.section_pairs = {}  # pair_id -> list of (course, section) tuples
        self.pair_lookup = {}    # (course, section) -> pair_id
        self.pair_counter = 0    # for generating unique pair IDs
        
    def load_data(self, file_path):
        """Load course data from CSV or Excel file"""
        try:
            if file_path.endswith('.csv'):
                self.course_data = pd.read_csv(file_path)
            else:
                self.course_data = pd.read_excel(file_path)
            
            self.current_file_path = file_path
            # Clean and validate data
            self._clean_data()
            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
    
    def clear_data(self):
        """Clear all loaded data and selections"""
        self.course_data = None
        self.selected_courses = {}
        self.valid_combinations = []
        self.current_file_path = None
    
    def clear_roster(self):
        """Clear only the selected courses roster"""
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
                'data': section_data
            })
        
        return sections_info
    
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
                        if start1 < end2 and start2 < end1:
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
                    room = row['Room'] if 'Room' in row else 'TBA'
                    schedule[day].append({
                        'course': course_info,
                        'time': time_slot,
                        'room': room,
                        'instructor': instructor
                    })
        
        # Sort each day by start time
        for day in schedule:
            schedule[day].sort(key=lambda x: x['time'])
        
        return {
            'courses': courses_info,            'schedule': schedule
        }


class TimetableGUI:
    def _init_(self):
        self.generator = TimetableGenerator()
        self.root = tk.Tk()
        self.root.title("University Timetable Generator - Enhanced")
        self.root.geometry("1400x900")
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Data Loading and Course Selection
        self.setup_selection_tab()
        
        # Tab 2: Schedule Generation and Results
        self.setup_results_tab()
    
    def setup_selection_tab(self):
        """Setup course selection tab"""
        selection_frame = ttk.Frame(self.notebook)
        self.notebook.add(selection_frame, text="Course Selection")
        
        # File loading section with enhanced controls
        file_frame = ttk.LabelFrame(selection_frame, text="📁 Data Management")
        file_frame.pack(fill='x', padx=10, pady=5)
        
        # File operations
        file_ops_frame = ttk.Frame(file_frame)
        file_ops_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(file_ops_frame, text="📂 Load CSV/Excel File", 
                  command=self.load_file).pack(side='left', padx=5)
        
        ttk.Button(file_ops_frame, text="🗑 Clear All Data", 
                  command=self.clear_all_data).pack(side='left', padx=5)
        
        ttk.Button(file_ops_frame, text="📋 Clear Current Roster", 
                  command=self.clear_roster).pack(side='left', padx=5)
        
        self.file_label = ttk.Label(file_frame, text="No file loaded", foreground='gray')
        self.file_label.pack(padx=5, pady=2)
        
        # Course selection section
        course_frame = ttk.LabelFrame(selection_frame, text="📚 Select Courses")
        course_frame.pack(fill='both', expand=True, padx=10, pady=5)
          # Left side - Available courses
        left_frame = ttk.Frame(course_frame)
        left_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        ttk.Label(left_frame, text="Available Courses:").pack(anchor='w')
          # Search bar for courses
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill='x', pady=(5, 0))
        
        ttk.Label(search_frame, text="🔍 Search:").pack(side='left')
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=('Consolas', 10))
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(5, 0))
        
        # Add placeholder-like functionality
        self.search_placeholder = "Search by course code or name..."
        self.search_entry.insert(0, self.search_placeholder)
        self.search_entry.config(foreground='gray')
        
        # Bind events for placeholder behavior
        self.search_entry.bind('<FocusIn>', self.on_search_focus_in)
        self.search_entry.bind('<FocusOut>', self.on_search_focus_out)
        
        # Clear search button
        ttk.Button(search_frame, text="✖", width=3, 
                  command=self.clear_search).pack(side='right', padx=(5, 0))
        
        # Bind search functionality
        self.search_var.trace('w', self.on_search_change)
        
        self.courses_listbox = tk.Listbox(left_frame, height=15, font=('Consolas', 10))
        self.courses_listbox.pack(fill='both', expand=True, pady=5)
        self.courses_listbox.bind('<<ListboxSelect>>', self.on_course_select)
        
        # Middle - Course sections
        middle_frame = ttk.Frame(course_frame)
        middle_frame.pack(side='left', fill='both', expand=True, padx=5)
        
        ttk.Label(middle_frame, text="Available Sections:").pack(anchor='w')
        
        # Sections with checkboxes
        sections_canvas = tk.Canvas(middle_frame)
        sections_scrollbar = ttk.Scrollbar(middle_frame, orient="vertical", command=sections_canvas.yview)
        self.sections_frame = ttk.Frame(sections_canvas)
        
        self.sections_frame.bind(
            "<Configure>",
            lambda e: sections_canvas.configure(scrollregion=sections_canvas.bbox("all"))
        )
        
        sections_canvas.create_window((0, 0), window=self.sections_frame, anchor="nw")
        sections_canvas.configure(yscrollcommand=sections_scrollbar.set)
        
        sections_canvas.pack(side="left", fill="both", expand=True)
        sections_scrollbar.pack(side="right", fill="y")
        
        # Right side - Selected courses
        right_frame = ttk.Frame(course_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=5)
        
        ttk.Label(right_frame, text="Selected Courses:").pack(anchor='w')
        
        self.selected_text = scrolledtext.ScrolledText(right_frame, height=15, width=40, font=('Consolas', 9))
        self.selected_text.pack(fill='both', expand=True, pady=5)
        
        # Generate button
        generate_frame = ttk.Frame(course_frame)
        generate_frame.pack(pady=10)
        
        ttk.Button(generate_frame, text="🚀 Generate Timetables", 
                  command=self.generate_timetables).pack()
    
    def setup_results_tab(self):
        """Setup results display tab"""
        results_frame = ttk.Frame(self.notebook)
        self.notebook.add(results_frame, text="Generated Timetables")
        
        # Results summary
        summary_frame = ttk.LabelFrame(results_frame, text="📊 Summary")
        summary_frame.pack(fill='x', padx=10, pady=5)
        
        self.summary_label = ttk.Label(summary_frame, text="No timetables generated yet", font=('TkDefaultFont', 10, 'bold'))
        self.summary_label.pack(padx=5, pady=5)
        
        # Timetable selection
        selection_frame = ttk.Frame(results_frame)
        selection_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(selection_frame, text="Select Timetable:").pack(side='left', padx=5)
        
        self.timetable_var = tk.StringVar()
        self.timetable_combo = ttk.Combobox(selection_frame, textvariable=self.timetable_var,
                                           state='readonly', width=30)
        self.timetable_combo.pack(side='left', padx=5)
        self.timetable_combo.bind('<<ComboboxSelected>>', self.display_timetable)
        
        # Export buttons
        export_frame = ttk.Frame(selection_frame)
        export_frame.pack(side='right', padx=5)
        
        ttk.Button(export_frame, text="📤 Export All", 
                  command=self.export_all_timetables).pack(side='left', padx=2)
        ttk.Button(export_frame, text="📄 Export Selected", 
                  command=self.export_selected_timetable).pack(side='left', padx=2)
        
        # Timetable display
        display_frame = ttk.LabelFrame(results_frame, text="📅 Timetable View")
        display_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.timetable_text = scrolledtext.ScrolledText(display_frame, font=('Courier', 10))
        self.timetable_text.pack(fill='both', expand=True, padx=5, pady=5)
    
    def clear_all_data(self):
        """Clear all data including CSV and selections"""
        result = messagebox.askyesno("Clear All Data", 
                                   "Are you sure you want to clear all loaded data and selections?\n\nThis will:\n• Remove loaded CSV/Excel data\n• Clear all course selections\n• Clear generated timetables")
        if result:
            self.generator.clear_data()
            self.generator.clear_all_pairs()  # Clear section pairs
            self.courses_listbox.delete(0, tk.END)
            self.selected_text.delete(1.0, tk.END)
            self.selected_text.insert(1.0, "No data loaded.\n\n🔍 Please load a CSV or Excel file to get started.")
            
            # Clear sections display
            for widget in self.sections_frame.winfo_children():
                widget.destroy()
            
            # Clear section variables
            if hasattr(self.generator, 'section_vars'):
                delattr(self.generator, 'section_vars')
            
            # Clear results
            self.summary_label.config(text="No timetables generated yet")
            self.timetable_combo['values'] = []
            self.timetable_text.delete(1.0, tk.END)
            self.file_label.config(text="No file loaded", foreground='gray')
            messagebox.showinfo("✅ Success", "All data cleared successfully!")
    
    def clear_roster(self):
        """Clear only the current roster selections"""
        result = messagebox.askyesno("Clear Roster", 
                                   "Are you sure you want to clear all course selections?\n\nThis will:\n• Clear all selected courses\n• Clear generated timetables\n• Keep the loaded data file")
        if result:
            self.generator.clear_roster()
            self.generator.clear_all_pairs()  # Clear section pairs too
            
            # Reset all checkboxes
            if hasattr(self.generator, 'section_vars'):
                for course_vars in self.generator.section_vars.values():
                    for var in course_vars.values():
                        var.set(False)
            
            self.update_selected_courses()
              # Clear results
            self.summary_label.config(text="No timetables generated yet")
            self.timetable_combo['values'] = []
            self.timetable_text.delete(1.0, tk.END)
            
            messagebox.showinfo("✅ Success", "Course roster cleared successfully!")
    
    def load_file(self):
        """Load course data file"""
        file_path = filedialog.askopenfilename(
            title="Select Course Data File",
            filetypes=[("CSV files", ".csv"), ("Excel files", ".xlsx .xls"), ("All files", ".*")]
        )
        
        if file_path:
            if self.generator.load_data(file_path):
                filename = os.path.basename(file_path)
                self.file_label.config(text=f"✅ Loaded: {filename}", foreground='green')
                self.populate_courses()
                messagebox.showinfo("✅ Success", f"Course data loaded successfully!\n\nFile: {filename}\nCourses found: {len(self.generator.get_unique_courses())}")
            else:
                messagebox.showerror("❌ Error", "Failed to load course data file.\n\nPlease check that the file contains the required columns:\n• Course Code\n• Section\n• Day\n• Start\n• End")
    
    def populate_courses(self, search_term=""):
        """Populate the courses listbox with optional search filtering"""
        self.courses_listbox.delete(0, tk.END)
        
        # Get courses with titles for better display and search
        courses_info = self.generator.get_courses_with_titles()
        
        # Filter courses based on search term (search both code and title)
        if search_term:
            search_term = search_term.lower()
            filtered_courses = []
            for course_info in courses_info:
                # Search in course code, title, and display text
                if (search_term in course_info['code'].lower() or 
                    search_term in course_info['title'].lower() or
                    search_term in course_info['display'].lower()):
                    filtered_courses.append(course_info)
            courses_info = filtered_courses
        
        # Add courses to listbox with enhanced display
        for course_info in courses_info:
            self.courses_listbox.insert(tk.END, course_info['display'])
        
        # Store course mapping for selection handling
        self.course_mapping = {course_info['display']: course_info['code'] for course_info in courses_info}
          # Initialize the selected courses display
        self.update_selected_courses()
    
    def on_course_select(self, event):
        """Handle course selection"""
        selection = self.courses_listbox.curselection()
        if selection:
            course_display = self.courses_listbox.get(selection[0])
            # Extract the actual course code from the display text
            if hasattr(self, 'course_mapping') and course_display in self.course_mapping:
                course_code = self.course_mapping[course_display]
            else:                # Fallback: extract course code from display text (before the first dash)
                course_code = course_display.split(' - ')[0] if ' - ' in course_display else course_display
            self.show_course_sections(course_code)
    
    def on_search_change(self, *args):
        """Handle search text changes - filter courses dynamically"""
        search_term = self.search_var.get()
        # Don't search if it's the placeholder text
        if search_term == self.search_placeholder:
            search_term = ""
        self.populate_courses(search_term)
    
    def clear_search(self):
        """Clear the search bar and show all courses"""
        self.search_var.set("")
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, self.search_placeholder)
        self.search_entry.config(foreground='gray')
        self.populate_courses()
    
    def on_search_focus_in(self, event):
        """Handle search entry focus in - remove placeholder"""
        if self.search_entry.get() == self.search_placeholder:
            self.search_entry.delete(0, tk.END)
            self.search_entry.config(foreground='black')
    
    def on_search_focus_out(self, event):
        """Handle search entry focus out - add placeholder if empty"""
        if not self.search_entry.get():
            self.search_entry.insert(0, self.search_placeholder)
            self.search_entry.config(foreground='gray')
    
    def show_course_sections(self, course_code):
        """Show sections for selected course with L/R pairing logic"""
        # Clear previous sections
        for widget in self.sections_frame.winfo_children():
            widget.destroy()
        
        sections = self.generator.get_course_sections(course_code)
        
        if not hasattr(self.generator, 'section_vars'):
            self.generator.section_vars = {}
        
        if course_code not in self.generator.section_vars:
            self.generator.section_vars[course_code] = {}
        
        # Show all sections (L, R, and others) as independent checkboxes
        ttk.Label(self.sections_frame, text=f"📚 Sections for {course_code}:", 
                 font=('TkDefaultFont', 9, 'bold')).pack(anchor='w', pady=5)

        for section_info in sections:
            section = section_info['section']
            # Create or reuse checkbox variable
            if section not in self.generator.section_vars[course_code]:
                var = tk.BooleanVar()
                self.generator.section_vars[course_code][section] = var
            else:
                var = self.generator.section_vars[course_code][section]            # Create checkbox frame
            section_frame = ttk.Frame(self.sections_frame)
            section_frame.pack(fill='x', padx=5, pady=2)

            # Main section checkbox
            checkbox_frame = ttk.Frame(section_frame)
            checkbox_frame.pack(fill='x')
            
            cb = ttk.Checkbutton(checkbox_frame, text=f"Section {section}", 
                                variable=var, command=lambda: self.on_section_selection_change(course_code, section))
            cb.pack(side='left')
            
            # Pairing controls
            pairing_frame = ttk.Frame(checkbox_frame)
            pairing_frame.pack(side='right', padx=5)
            
            # Check if this section is already paired
            if self.generator.is_section_paired(course_code, section):
                paired_sections = self.generator.get_paired_sections(course_code, section)
                pair_text = " ⟷ ".join([f"{pc} {ps}" for pc, ps in paired_sections])
                ttk.Label(pairing_frame, text=f"Paired with: {pair_text}", 
                         foreground='green', font=('TkDefaultFont', 8)).pack(side='left')
                ttk.Button(pairing_frame, text="Unlink", width=6,
                          command=lambda: self.remove_section_pair(course_code, section)).pack(side='left', padx=2)
            else:
                # Pairing dropdown
                ttk.Label(pairing_frame, text="Link to:", font=('TkDefaultFont', 8)).pack(side='left')
                
                # Course selection dropdown
                course_var = tk.StringVar()
                course_combo = ttk.Combobox(pairing_frame, textvariable=course_var, width=10, state='readonly')
                course_combo['values'] = self.generator.get_unique_courses()
                course_combo.pack(side='left', padx=2)
                
                # Section selection dropdown  
                section_var = tk.StringVar()
                section_combo = ttk.Combobox(pairing_frame, textvariable=section_var, width=8, state='readonly')
                section_combo.pack(side='left', padx=2)
                  # Update section dropdown when course changes
                def update_sections(*args):
                    selected_course = course_var.get()
                    if selected_course:
                        try:
                            sections_info = self.generator.get_course_sections(selected_course)
                            sections_list = [s['section'] for s in sections_info]
                            section_combo['values'] = sections_list
                            section_combo['state'] = 'readonly'
                            section_var.set('')  # Clear previous selection
                        except Exception as e:
                            print(f"Error updating sections: {e}")
                            section_combo['values'] = []
                    else:
                        section_combo['values'] = []
                        section_combo['state'] = 'disabled'
                
                # Bind the trace after defining the function
                course_var.trace('w', update_sections)
                
                # Initially disable section dropdown
                section_combo['state'] = 'disabled'
                  # Link button
                def create_pair_wrapper():
                    target_course = course_var.get()
                    target_section = section_var.get()
                    if target_course and target_section:
                        self.create_section_pair(course_code, section, target_course, target_section)
                    else:
                        messagebox.showwarning("⚠ Warning", "Please select both course and section to create a pair.")
                
                ttk.Button(pairing_frame, text="Link", width=5,
                          command=create_pair_wrapper).pack(side='left', padx=2)            # Show section details
            details = f"  📖 Title: {section_info['title']}\n"
            details += f"  👨‍🏫 Instructor: {section_info['instructor']}\n"
            details += f"  🕐 Times: {', '.join(section_info['times'])}"
            
            details_label = ttk.Label(section_frame, text=details, 
                                     font=('TkDefaultFont', 8), foreground='darkblue')
            details_label.pack(anchor='w', padx=20, pady=2)
                  # Add separator
            ttk.Separator(self.sections_frame, orient='horizontal').pack(fill='x', padx=10, pady=5)
    
    def on_section_selection_change(self, course_code, section):
        """Handle section checkbox changes with automatic pair synchronization"""
        var = self.generator.section_vars[course_code][section]
        is_selected = var.get()
        
        # If this section is paired, sync the paired sections
        if self.generator.is_section_paired(course_code, section):
            paired_sections = self.generator.get_paired_sections(course_code, section)
            for paired_course, paired_section in paired_sections:
                if paired_course in self.generator.section_vars and paired_section in self.generator.section_vars[paired_course]:
                    self.generator.section_vars[paired_course][paired_section].set(is_selected)
        
        self.update_selected_courses()
    
    def create_section_pair(self, course1, section1, course2, section2):
        """Create a new section pair"""
        if not course2 or not section2:
            messagebox.showwarning("⚠ Warning", "Please select both course and section to create a pair.")
            return
        
        success, message = self.generator.create_section_pair(course1, section1, course2, section2)
        
        if success:
            messagebox.showinfo("✅ Success", f"Created pair: {course1} {section1} ⟷ {course2} {section2}")
            # Refresh the sections display to show the new pairing
            self.show_course_sections(course1)
        else:
            messagebox.showerror("❌ Error", f"Failed to create pair: {message}")
    
    def remove_section_pair(self, course, section):
        """Remove a section from its pair"""
        success, message = self.generator.remove_section_pair(course, section)
        
        if success:
            messagebox.showinfo("✅ Success", "Section pair removed successfully.")
            # Refresh the sections display
            self.show_course_sections(course)
        else:
            messagebox.showerror("❌ Error", f"Failed to remove pair: {message}")
    
    def handle_lr_pair_selection(self, pair_var, l_var, r_var, course_code, l_key, r_key):
        """Handle selection/deselection of L/R pairs"""
        is_selected = pair_var.get()
        
        # Set both L and R variables to the same state
        l_var.set(is_selected)
        r_var.set(is_selected)
        
        # Update the selected courses display
        self.update_selected_courses()
    
    def update_selected_courses(self):
        """Update the selected courses display"""
        if not hasattr(self.generator, 'section_vars'):
            self.selected_text.delete(1.0, tk.END)
            self.selected_text.insert(1.0, "No data loaded.\n\n🔍 Please load a CSV or Excel file first.")
            return
        
        self.generator.selected_courses = {}
        selected_text = "🎯 SELECTED COURSES\n" + "="*50 + "\n\n"
        
        total_sections = 0
        total_courses = 0
        
        for course_code, sections_vars in self.generator.section_vars.items():
            selected_sections = []
            for section, var in sections_vars.items():
                if var.get():
                    selected_sections.append(section)
                    total_sections += 1
            if selected_sections:
                total_courses += 1
                self.generator.selected_courses[course_code] = selected_sections
                selected_text += f"📚 {course_code}:\n"
                for section in selected_sections:
                    # Show L and R sections distinctly
                    if section.startswith('L'):
                        selected_text += f"    ✅ 📖 Lecture Section {section}\n"
                    elif section.startswith('R'):
                        selected_text += f"    ✅ 📚 Recitation Section {section}\n"
                    else:
                        selected_text += f"    ✅ Section {section}\n"
                selected_text += "\n"
        
        if total_sections == 0:
            selected_text += "❌ No courses selected yet.\n\n"
            selected_text += "📝 How to get started:\n"
            selected_text += "1️⃣ Select a course from the left panel\n"
            selected_text += "2️⃣ Choose sections in the middle panel\n"           
            selected_text += "3️⃣ Repeat for all desired courses\n"
            selected_text += "4️⃣ Click 'Generate Timetables'"
        else:
            selected_text += f"📊 SUMMARY:\n"
            selected_text += f"• {total_courses} courses selected\n"
            selected_text += f"• {total_sections} sections total\n\n"
            selected_text += "💡 TIP: Select multiple sections per course\n"
            selected_text += "   to generate different timetable options!\n"
            selected_text += "   (Each timetable will use only one section per course)\n\n"
            selected_text += "🚀 Ready to generate timetables!"
        
        self.selected_text.delete(1.0, tk.END)
        self.selected_text.insert(1.0, selected_text)
    
    def generate_timetables(self):
        """Generate all possible timetables"""
        if not self.generator.selected_courses:
            messagebox.showwarning("⚠ Warning", "Please select at least one course section before generating timetables.")
            return
        
        try:
            # Show progress
            self.summary_label.config(text="🔄 Generating timetables...")
            self.root.update()
            
            combinations = self.generator.generate_combinations()
            
            if combinations:
                # Update summary
                num_combinations = len(combinations)
                self.summary_label.config(text=f"✅ Generated {num_combinations} valid timetable(s)")
                
                # Populate combo box
                combo_values = [f"Timetable {i+1}" for i in range(num_combinations)]
                self.timetable_combo['values'] = combo_values
                if combo_values:
                    self.timetable_combo.set(combo_values[0])
                    self.display_timetable(None)
                
                # Switch to results tab
                self.notebook.select(1)
                
                messagebox.showinfo("🎉 Success", f"Generated {num_combinations} valid timetable(s)!\n\nYou can now view and export your schedules in the 'Generated Timetables' tab.")
            else:
                self.summary_label.config(text="❌ No valid timetables found")
                messagebox.showwarning("❌ No Valid Timetables", 
                                     "No valid timetables found with your current selections.\n\nPossible reasons:\n• Time conflicts between selected courses\n• No compatible sections\n\nTry selecting different sections or fewer courses.")
        except Exception as e:
            self.summary_label.config(text="❌ Error during generation")
            messagebox.showerror("❌ Error", f"Error generating timetables:\n\n{str(e)}")
    
    def display_timetable(self, event):
        """Display selected timetable"""
        if not self.timetable_var.get() or not self.generator.valid_combinations:
            return
        
        try:
            # Get selected combination index
            index = int(self.timetable_var.get().split()[-1]) - 1
            combination = self.generator.valid_combinations[index]
            
            # Format the combination
            formatted = self.generator.format_combination(combination)
            
            # Create display text
            display_text = "📅 UNIVERSITY TIMETABLE\n"
            display_text += "="*80 + "\n\n"
            
            # Course list
            display_text += "📚 ENROLLED COURSES:\n"
            display_text += "-"*50 + "\n"
            for course_info in formatted['courses']:
                display_text += f"🔹 {course_info['course']}: {course_info['title']}\n"
                display_text += f"   👨‍🏫 Instructor: {course_info['instructor']}\n\n"
            
            # Weekly schedule
            display_text += "\n📅 WEEKLY SCHEDULE:\n"
            display_text += "="*80 + "\n"
            
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_emojis = ['🌟', '🔥', '💪', '⚡', '🎉', '🌈', '😊']
            
            for i, day in enumerate(days):
                if formatted['schedule'][day]:
                    display_text += f"\n{day_emojis[i]} {day.upper()}:\n"
                    display_text += "-" * (len(day) + 2) + "\n"
                    
                    for slot in formatted['schedule'][day]:
                        display_text += f"  🕐 {slot['time']}: {slot['course']} ({slot['room']})\n"
                        display_text += f"      👨‍🏫 {slot['instructor']}\n"
            
            # Update display
            self.timetable_text.delete(1.0, tk.END)
            self.timetable_text.insert(1.0, display_text)
            
        except Exception as e:
            messagebox.showerror("❌ Error", f"Error displaying timetable:\n\n{str(e)}")
    
    def export_selected_timetable(self):
        """Export the currently selected timetable"""
        if not self.timetable_var.get():
            messagebox.showwarning("⚠ Warning", "Please select a timetable to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Timetable",
            defaultextension=".txt",
            filetypes=[("Text files", ".txt"), ("All files", ".*")]
        )
        
        if file_path:
            try:
                content = self.timetable_text.get(1.0, tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("✅ Success", f"Timetable exported successfully!\n\nFile saved to: {file_path}")
            except Exception as e:
                messagebox.showerror("❌ Error", f"Error exporting timetable:\n\n{str(e)}")
    
    def export_all_timetables(self):
        """Export all generated timetables"""
        if not self.generator.valid_combinations:
            messagebox.showwarning("⚠ Warning", "No timetables to export")
            return
        
        folder_path = filedialog.askdirectory(title="Select Export Folder")
        
        if folder_path:
            try:
                for i, combination in enumerate(self.generator.valid_combinations):
                    formatted = self.generator.format_combination(combination)
                    
                    # Create filename
                    filename = f"timetable_{i+1}.txt"
                    file_path = os.path.join(folder_path, filename)
                    
                    # Generate content (similar to display_timetable)
                    content = f"📅 UNIVERSITY TIMETABLE {i+1}\n"
                    content += "="*80 + "\n\n"
                    
                    # Course list
                    content += "📚 ENROLLED COURSES:\n"
                    content += "-"*50 + "\n"
                    for course_info in formatted['courses']:
                        content += f"🔹 {course_info['course']}: {course_info['title']}\n"
                        content += f"   👨‍🏫 Instructor: {course_info['instructor']}\n\n"
                    
                    # Weekly schedule
                    content += "\n📅 WEEKLY SCHEDULE:\n"
                    content += "="*80 + "\n"
                    
                    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    day_emojis = ['🌟', '🔥', '💪', '⚡', '🎉', '🌈', '😊']
                    
                    for j, day in enumerate(days):
                        if formatted['schedule'][day]:
                            content += f"\n{day_emojis[j]} {day.upper()}:\n"
                            content += "-" * (len(day) + 2) + "\n"
                            
                            for slot in formatted['schedule'][day]:
                                content += f"  🕐 {slot['time']}: {slot['course']} ({slot['room']})\n"
                                content += f"      👨‍🏫 {slot['instructor']}\n"
                    
                    # Write to file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                
                messagebox.showinfo("✅ Success", f"Exported {len(self.generator.valid_combinations)} timetables successfully!\n\nFiles saved to: {folder_path}")
            except Exception as e:                messagebox.showerror("❌ Error", f"Error exporting timetables:\n\n{str(e)}")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    """Main function to run the application"""
    try:
        app = TimetableGUI()
        app.run()
    except Exception as e:
        messagebox.showerror("❌ Fatal Error", f"Application failed to start:\n\n{str(e)}")


if __name__ == "__main__":
    main()