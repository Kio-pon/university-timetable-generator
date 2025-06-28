import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import json
import os
from collections import defaultdict

class CoursePairingStep1:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Step 1: Course Pairing Manager")
        self.root.geometry("1000x700")
        
        self.courses_df = None
        self.course_pairs = {}  # Will store course-to-course pairs (not sections)
        self.pairs_file = "course_pairs_step1.json"
        
        self.setup_ui()
        self.load_course_pairs()
    
    def setup_ui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Load CSV
        self.load_tab = ttk.Frame(notebook)
        notebook.add(self.load_tab, text="📁 Load CSV")
        self.setup_load_tab()
        
        # Tab 2: View Courses
        self.view_tab = ttk.Frame(notebook)
        notebook.add(self.view_tab, text="📚 View Courses")
        self.setup_view_tab()
        
        # Tab 3: Create Course Pairs
        self.pair_tab = ttk.Frame(notebook)
        notebook.add(self.pair_tab, text="🔗 Create Course Pairs")
        self.setup_pair_tab()
        
        # Tab 4: View Course Pairs
        self.pairs_view_tab = ttk.Frame(notebook)
        notebook.add(self.pairs_view_tab, text="👀 View Course Pairs")
        self.setup_pairs_view_tab()
    
    def setup_load_tab(self):
        frame = ttk.Frame(self.load_tab)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Load Course CSV File", font=('Arial', 16, 'bold')).pack(pady=10)
        
        load_frame = ttk.Frame(frame)
        load_frame.pack(pady=20)
        
        ttk.Button(load_frame, text="📁 Browse CSV File", command=self.load_csv).pack(side='left', padx=10)
        
        self.file_label = ttk.Label(load_frame, text="No file loaded", foreground='red')
        self.file_label.pack(side='left', padx=10)
        
        # Status frame
        self.status_frame = ttk.Frame(frame)
        self.status_frame.pack(pady=20, fill='x')
        
        # Sample format
        ttk.Label(frame, text="Expected CSV Format:", font=('Arial', 12, 'bold')).pack(anchor='w', pady=(20,5))
        
        sample_text = """Course Code,Section,Title,Day,Start,End,Room,Instructor / Sponsor
CORE 200,L1,Scientific Methods,M,2:30 PM,3:45 PM,W-234,Aamir Hasan
CS 101,L1,Introduction to CS,MW,11:30 AM,12:45 PM,GF-E121,John Doe
CS 101L,T1,CS Lab,F,11:30 AM,12:20 PM,FF-N219,John Doe"""
        
        text_widget = tk.Text(frame, height=4, wrap='none')
        text_widget.insert('1.0', sample_text)
        text_widget.config(state='disabled')
        text_widget.pack(fill='x', pady=5)
    
    def setup_view_tab(self):
        frame = ttk.Frame(self.view_tab)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Course Overview", font=('Arial', 16, 'bold')).pack(pady=10)
        
        # Unique courses display
        self.courses_text = tk.Text(frame, height=25, wrap='word')
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.courses_text.yview)
        self.courses_text.configure(yscrollcommand=scrollbar.set)
        
        self.courses_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def setup_pair_tab(self):
        frame = ttk.Frame(self.pair_tab)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Create Course Pairs", font=('Arial', 16, 'bold')).pack(pady=10)
        
        # Course selection frame
        selection_frame = ttk.LabelFrame(frame, text="Select Courses to Pair", padding=15)
        selection_frame.pack(fill='x', pady=10)
        
        # First course
        ttk.Label(selection_frame, text="First Course:").grid(row=0, column=0, sticky='w', pady=5)
        self.course1_var = tk.StringVar()
        self.course1_combo = ttk.Combobox(selection_frame, textvariable=self.course1_var, width=40, state='readonly')
        self.course1_combo.grid(row=0, column=1, padx=10, pady=5)
        self.course1_combo.bind('<<ComboboxSelected>>', self.on_first_course_selected)  # Add event handler
        
        # Second course
        ttk.Label(selection_frame, text="Second Course:").grid(row=1, column=0, sticky='w', pady=5)
        self.course2_var = tk.StringVar()
        self.course2_combo = ttk.Combobox(selection_frame, textvariable=self.course2_var, width=40, state='readonly')
        self.course2_combo.grid(row=1, column=1, padx=10, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(selection_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=15)
        
        ttk.Button(button_frame, text="🔗 Create Pair", command=self.create_course_pair).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🔄 Refresh Courses", command=self.refresh_course_combos).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🤖 Auto-Pair All", command=self.auto_pair_courses).pack(side='left', padx=5)
        
        # Current pairs display
        pairs_frame = ttk.LabelFrame(frame, text="Current Course Pairs", padding=15)
        pairs_frame.pack(fill='both', expand=True, pady=10)
        
        self.pairs_text = tk.Text(pairs_frame, height=15, wrap='word')
        pairs_scrollbar = ttk.Scrollbar(pairs_frame, orient='vertical', command=self.pairs_text.yview)
        self.pairs_text.configure(yscrollcommand=pairs_scrollbar.set)
        
        self.pairs_text.pack(side='left', fill='both', expand=True)
        pairs_scrollbar.pack(side='right', fill='y')
    
    def setup_pairs_view_tab(self):
        frame = ttk.Frame(self.pairs_view_tab)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="All Course Pairs", font=('Arial', 16, 'bold')).pack(pady=10)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="🔄 Refresh", command=self.refresh_pairs_view).pack(side='left', padx=5)
        ttk.Button(button_frame, text="🗑️ Clear All Pairs", command=self.clear_all_pairs).pack(side='left', padx=5)
        
        # Pairs display
        self.all_pairs_text = tk.Text(frame, height=20, wrap='word')
        all_pairs_scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.all_pairs_text.yview)
        self.all_pairs_text.configure(yscrollcommand=all_pairs_scrollbar.set)
        
        self.all_pairs_text.pack(side='left', fill='both', expand=True)
        all_pairs_scrollbar.pack(side='right', fill='y')
    
    def load_csv(self):
        file_path = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.courses_df = pd.read_csv(file_path)
                
                # Validate required columns
                required_columns = ['Course Code', 'Section', 'Title', 'Day', 'Start', 'End', 'Room', 'Instructor / Sponsor']
                missing_columns = [col for col in required_columns if col not in self.courses_df.columns]
                
                if missing_columns:
                    messagebox.showerror("Error", f"Missing columns: {', '.join(missing_columns)}")
                    return
                
                self.file_label.config(text=f"✅ Loaded: {os.path.basename(file_path)}", foreground='green')
                
                # Show status
                self.show_load_status()
                self.show_courses_overview()
                self.refresh_course_combos()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV: {str(e)}")
    
    def show_load_status(self):
        # Clear previous status
        for widget in self.status_frame.winfo_children():
            widget.destroy()
        
        if self.courses_df is not None:
            # Get unique courses (without sections)
            unique_courses = self.get_unique_courses()
            paired_courses = len(self.course_pairs)
            unpaired_courses = len(unique_courses) - paired_courses
            
            status_text = f"📊 Total Records: {len(self.courses_df)}\n"
            status_text += f"🎓 Total Unique Courses: {len(unique_courses)}\n"
            status_text += f"� Paired Courses: {paired_courses}\n"
            status_text += f"⭕ Unpaired Courses: {unpaired_courses}\n"
            status_text += f"📚 Course Pairs: {len(self.course_pairs)//2}"
            
            ttk.Label(self.status_frame, text=status_text, font=('Arial', 10)).pack(anchor='w')
    
    def get_unique_courses(self):
        """Extract unique course codes (without sections)"""
        if self.courses_df is None:
            return []
        
        unique_courses = self.courses_df['Course Code'].unique()
        return sorted(unique_courses)
    
    def show_courses_overview(self):
        """Show unique courses in the view tab"""
        if self.courses_df is None:
            return
        
        self.courses_text.delete('1.0', tk.END)
        
        unique_courses = self.get_unique_courses()
        
        self.courses_text.insert(tk.END, f"📚 UNIQUE COURSES ({len(unique_courses)})\n")
        self.courses_text.insert(tk.END, "=" * 50 + "\n\n")
        
        for course in unique_courses:
            # Get all sections for this course
            course_data = self.courses_df[self.courses_df['Course Code'] == course]
            sections = course_data['Section'].unique()
            titles = course_data['Title'].unique()
            
            self.courses_text.insert(tk.END, f"🎓 {course}\n")
            self.courses_text.insert(tk.END, f"   📝 Title(s): {', '.join(titles)}\n")
            self.courses_text.insert(tk.END, f"   📋 Sections: {', '.join(sorted(sections))}\n")
            self.courses_text.insert(tk.END, f"   📊 Total Sections: {len(sections)}\n")
            self.courses_text.insert(tk.END, "\n")
    
    def refresh_course_combos(self):
        """Refresh the course dropdown menus - exclude already paired courses"""
        if self.courses_df is None:
            return
        
        unique_courses = self.get_unique_courses()
        
        # Filter out already paired courses
        unpaired_courses = []
        for course in unique_courses:
            if course not in self.course_pairs:
                unpaired_courses.append(course)
        
        self.course1_combo['values'] = unpaired_courses
        self.course2_combo['values'] = unpaired_courses
        
        # Clear selections
        self.course1_var.set('')
        self.course2_var.set('')
        
        # Update the pairing section to show how many courses are left
        if hasattr(self, 'status_frame'):
            self.show_load_status()
    
    def create_course_pair(self):
        """Create a course pair"""
        course1 = self.course1_var.get().strip()
        course2 = self.course2_var.get().strip()
        
        if not course1 or not course2:
            messagebox.showwarning("Warning", "Please select both courses")
            return
        
        if course1 == course2:
            messagebox.showwarning("Warning", "Cannot pair a course with itself")
            return
        
        # Check if pair already exists
        if course1 in self.course_pairs and self.course_pairs[course1] == course2:
            messagebox.showinfo("Info", f"Pair already exists: {course1} ↔ {course2}")
            return
        
        # Create bidirectional pairing
        self.course_pairs[course1] = course2
        self.course_pairs[course2] = course1
        
        # Save to file
        self.save_course_pairs()
        
        # Refresh displays and course combos automatically
        self.refresh_current_pairs()
        self.refresh_pairs_view()
        self.refresh_course_combos()  # Auto-refresh after pairing
        self.show_load_status()
        
        messagebox.showinfo("Success", f"Created pair: {course1} ↔ {course2}")
        
        # Clear selections
        self.course1_var.set('')
        self.course2_var.set('')
    
    def refresh_current_pairs(self):
        """Refresh the current pairs display in the pairing tab"""
        self.pairs_text.delete('1.0', tk.END)
        
        if not self.course_pairs:
            self.pairs_text.insert(tk.END, "No course pairs created yet.")
            return
        
        # Show unique pairs (avoid showing both A->B and B->A)
        shown_pairs = set()
        
        for course1, course2 in self.course_pairs.items():
            pair = tuple(sorted([course1, course2]))
            if pair not in shown_pairs:
                self.pairs_text.insert(tk.END, f"🔗 {course1} ↔ {course2}\n")
                shown_pairs.add(pair)
    
    def refresh_pairs_view(self):
        """Refresh the pairs view tab"""
        self.all_pairs_text.delete('1.0', tk.END)
        
        if not self.course_pairs:
            self.all_pairs_text.insert(tk.END, "No course pairs found.")
            return
        
        # Show unique pairs with details
        shown_pairs = set()
        
        self.all_pairs_text.insert(tk.END, f"📚 COURSE PAIRS ({len(self.course_pairs)//2})\n")
        self.all_pairs_text.insert(tk.END, "=" * 50 + "\n\n")
        
        for course1, course2 in self.course_pairs.items():
            pair = tuple(sorted([course1, course2]))
            if pair not in shown_pairs:
                self.all_pairs_text.insert(tk.END, f"🔗 {course1} ↔ {course2}\n")
                
                # Show sections for each course
                if self.courses_df is not None:
                    course1_sections = self.courses_df[self.courses_df['Course Code'] == course1]['Section'].unique()
                    course2_sections = self.courses_df[self.courses_df['Course Code'] == course2]['Section'].unique()
                    
                    self.all_pairs_text.insert(tk.END, f"   📋 {course1} sections: {', '.join(sorted(course1_sections))}\n")
                    self.all_pairs_text.insert(tk.END, f"   📋 {course2} sections: {', '.join(sorted(course2_sections))}\n")
                
                self.all_pairs_text.insert(tk.END, "\n")
                shown_pairs.add(pair)
    
    def save_course_pairs(self):
        """Save course pairs to JSON file"""
        try:
            with open(self.pairs_file, 'w', encoding='utf-8') as f:
                json.dump(self.course_pairs, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save pairs: {str(e)}")
    
    def load_course_pairs(self):
        """Load course pairs from JSON file"""
        try:
            if os.path.exists(self.pairs_file):
                with open(self.pairs_file, 'r', encoding='utf-8') as f:
                    self.course_pairs = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load pairs: {str(e)}")
            self.course_pairs = {}
    
    def clear_all_pairs(self):
        """Clear all course pairs"""
        if not self.course_pairs:
            messagebox.showinfo("Info", "No pairs to clear")
            return
        
        result = messagebox.askyesno("Confirm", "Are you sure you want to clear all course pairs?")
        if result:
            self.course_pairs = {}
            self.save_course_pairs()
            self.refresh_current_pairs()
            self.refresh_pairs_view()
            self.refresh_course_combos()  # Refresh combos to show all courses again
            self.show_load_status()
            messagebox.showinfo("Success", "All course pairs cleared")
    
    def on_first_course_selected(self, event):
        """Handle first course selection and reorder second course dropdown"""
        selected_course = self.course1_var.get()
        if not selected_course or self.courses_df is None:
            return
        
        # Get all unpaired courses
        unique_courses = self.get_unique_courses()
        unpaired_courses = [course for course in unique_courses if course not in self.course_pairs]
        
        # Remove the selected course from the list
        if selected_course in unpaired_courses:
            unpaired_courses.remove(selected_course)
        
        # Smart reordering: put likely pairs near the middle/top
        reordered_courses = self.smart_reorder_courses(selected_course, unpaired_courses)
        
        # Update second course dropdown
        self.course2_combo['values'] = reordered_courses
        self.course2_var.set('')  # Clear second selection
    
    def smart_reorder_courses(self, selected_course, available_courses):
        """Smart reordering to put likely pairs at the top"""
        if not available_courses:
            return available_courses
        
        # Create priority lists
        high_priority = []
        medium_priority = []
        low_priority = []
        
        selected_lower = selected_course.lower()
        
        for course in available_courses:
            course_lower = course.lower()
            
            # High priority: Lecture-Lab patterns
            if self.is_likely_pair(selected_course, course):
                high_priority.append(course)
            # Medium priority: Same department/prefix
            elif self.same_department(selected_course, course):
                medium_priority.append(course)
            # Low priority: everything else
            else:
                low_priority.append(course)
        
        # Combine lists: high priority first, then medium, then low
        reordered = high_priority + medium_priority + low_priority
        return reordered
    
    def is_likely_pair(self, course1, course2):
        """Check if two courses are likely to be a pair"""
        course1_lower = course1.lower()
        course2_lower = course2.lower()
        
        # Pattern 1: Course and CourseL (e.g., "CS 101" and "CS 101L")
        if course1_lower + "l" == course2_lower or course2_lower + "l" == course1_lower:
            return True
        
        # Pattern 2: Course and Course L (e.g., "BIO 101" and "BIO L")
        course1_parts = course1.split()
        course2_parts = course2.split()
        
        if len(course1_parts) >= 2 and len(course2_parts) >= 2:
            # Check if one ends with L and has same prefix
            if (course1_parts[0] == course2_parts[0] and 
                (course2_parts[-1].upper() == 'L' or course1_parts[-1].upper() == 'L')):
                return True
        
        # Pattern 3: Similar base with L/R/T suffix (e.g., "EE 354L" and "EE 354R")
        base1 = course1.replace('L', '').replace('R', '').replace('T', '').strip()
        base2 = course2.replace('L', '').replace('R', '').replace('T', '').strip()
        
        if base1 == base2 and base1 != course1 and base2 != course2:
            return True
        
        # Pattern 4: Handle pipe-separated courses (e.g., "CS|CE 101" and "CS|CE 101L")
        if '|' in course1 or '|' in course2:
            base1_clean = course1.split('|')[-1] if '|' in course1 else course1
            base2_clean = course2.split('|')[-1] if '|' in course2 else course2
            
            if base1_clean.lower() + "l" == base2_clean.lower() or base2_clean.lower() + "l" == base1_clean.lower():
                return True
        
        return False
    
    def same_department(self, course1, course2):
        """Check if two courses are from the same department"""
        # Extract department prefix (first word before space or |)
        def get_department(course):
            if '|' in course:
                return course.split('|')[0].strip()
            else:
                return course.split()[0] if course.split() else course
        
        dept1 = get_department(course1).upper()
        dept2 = get_department(course2).upper()
        
        return dept1 == dept2



    def auto_pair_courses(self):
        """Automatically pair courses based on learned patterns"""
        if self.courses_df is None:
            messagebox.showerror("Error", "Please load a CSV file first!")
            return
        
        # Ask for confirmation
        result = messagebox.askyesno("Auto-Pairing", 
                                   "This will automatically create course pairs based on learned patterns.\n\n" +
                                   "Patterns include:\n" +
                                   "• Lecture-Lab pairs (CS 101 ↔ CS 101L)\n" +
                                   "• Base-Suffix pairs (MATH 101L ↔ MATH 101R)\n" +
                                   "• Course-Lab pairs (BIO 101 ↔ BIO L)\n" +
                                   "• Pipe course pairs (CS|CE 232 ↔ CS|CE 232L)\n\n" +
                                   "Continue?")
        if not result:
            return
        
        original_pairs = len(self.course_pairs) // 2
        new_pairs = 0
        
        # Get all unique courses
        unique_courses = self.get_unique_courses()
        unpaired_courses = [course for course in unique_courses if course not in self.course_pairs]
        
        # Apply different pairing algorithms
        algorithm_results = []
        
        # Algorithm 1: Exact Lecture-Lab Pattern
        pairs_found = self.find_lecture_lab_exact_pairs(unpaired_courses)
        if pairs_found:
            new_pairs += len(pairs_found)
            algorithm_results.append(f"• {len(pairs_found)} Lecture-Lab exact pairs")
            self.apply_pairs(pairs_found)
            unpaired_courses = [course for course in unpaired_courses if course not in self.course_pairs]
        
        # Algorithm 2: Base-Suffix Pattern (L/R/T/S)
        pairs_found = self.find_base_suffix_pairs(unpaired_courses)
        if pairs_found:
            new_pairs += len(pairs_found)
            algorithm_results.append(f"• {len(pairs_found)} Base-Suffix pairs")
            self.apply_pairs(pairs_found)
            unpaired_courses = [course for course in unpaired_courses if course not in self.course_pairs]
        
        # Algorithm 3: Pipe Course Pattern
        pairs_found = self.find_pipe_course_pairs(unpaired_courses)
        if pairs_found:
            new_pairs += len(pairs_found)
            algorithm_results.append(f"• {len(pairs_found)} Pipe course pairs")
            self.apply_pairs(pairs_found)
            unpaired_courses = [course for course in unpaired_courses if course not in self.course_pairs]
        
        # Algorithm 4: Course-Lab Separated Pattern
        pairs_found = self.find_course_lab_separated_pairs(unpaired_courses)
        if pairs_found:
            new_pairs += len(pairs_found)
            algorithm_results.append(f"• {len(pairs_found)} Course-Lab separated pairs")
            self.apply_pairs(pairs_found)
        
        # Show results
        if new_pairs > 0:
            result_text = f"Auto-pairing completed!\n\n"
            result_text += f"📊 Results:\n"
            result_text += f"• {new_pairs} new pairs created\n"
            result_text += f"• {len(self.course_pairs)//2} total pairs now\n\n"
            result_text += "📋 Breakdown:\n" + "\n".join(algorithm_results)
            
            messagebox.showinfo("Auto-Pairing Results", result_text)
            
            # Save and refresh
            self.save_course_pairs()
            self.refresh_current_pairs()
            self.refresh_pairs_view()
            self.refresh_course_combos()
            self.show_load_status()
        else:
            messagebox.showinfo("Auto-Pairing Results", 
                              "No new pairs found.\n\nAll courses may already be paired or " +
                              "don't match the learned patterns.")
    
    def find_lecture_lab_exact_pairs(self, courses):
        """Find exact lecture-lab pairs like CS 101 ↔ CS 101L"""
        pairs = []
        
        for i, course1 in enumerate(courses):
            for j, course2 in enumerate(courses[i+1:], i+1):
                # Pattern: Course ↔ CourseL
                if course1.lower() + "l" == course2.lower():
                    pairs.append((course1, course2))
                elif course2.lower() + "l" == course1.lower():
                    pairs.append((course1, course2))
        
        return pairs
    
    def find_base_suffix_pairs(self, courses):
        """Find base-suffix pairs like MATH 101L ↔ MATH 101R"""
        pairs = []
        suffixes = ['L', 'R', 'T', 'S' , 'C']
        
        for i, course1 in enumerate(courses):
            for j, course2 in enumerate(courses[i+1:], i+1):
                # Check if both courses have suffixes
                course1_parts = course1.split()
                course2_parts = course2.split()
                
                if len(course1_parts) >= 2 and len(course2_parts) >= 2:
                    # Get the last part (number + suffix)
                    last1 = course1_parts[-1]
                    last2 = course2_parts[-1]
                    
                    # Check if they have different suffixes but same base
                    if (len(last1) > 1 and len(last2) > 1 and 
                        last1[-1] in suffixes and last2[-1] in suffixes and
                        last1[-1] != last2[-1]):
                        
                        # Check if base parts are the same
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
                    # Extract the base parts
                    base1 = course1.split('|')[-1].strip() if '|' in course1 else course1
                    base2 = course2.split('|')[-1].strip() if '|' in course2 else course2
                    prefix1 = course1.split('|')[0].strip() if '|' in course1 else ''
                    prefix2 = course2.split('|')[0].strip() if '|' in course2 else ''
                    
                    # Check if one is base and other is base + L
                    if (prefix1 == prefix2 and 
                        (base1.lower() + "l" == base2.lower() or 
                         base2.lower() + "l" == base1.lower())):
                        pairs.append((course1, course2))
        
        return pairs
    
    def find_course_lab_separated_pairs(self, courses):
        """Find course-lab separated pairs like CORE 101S ↔ CORE 101L"""
        pairs = []
        
        for i, course1 in enumerate(courses):
            for j, course2 in enumerate(courses[i+1:], i+1):
                course1_parts = course1.split()
                course2_parts = course2.split()
                
                if len(course1_parts) >= 2 and len(course2_parts) >= 2:
                    # Check if same prefix but different suffix pattern
                    prefix1 = ' '.join(course1_parts[:-1])
                    prefix2 = ' '.join(course2_parts[:-1])
                    
                    if prefix1 == prefix2:
                        last1 = course1_parts[-1]
                        last2 = course2_parts[-1]
                        
                        # Common pairing patterns from your data
                        pairing_patterns = [
                            ('101S', '101L'), ('121S', '121L'), ('201S', '201L'),
                            ('204S', '204L'), ('206S', '206L'), ('212S', '212L'),
                            ('101S', '101L'), ('323S', '323L'), ('301S', '301L')
                        ]
                        
                        for pattern1, pattern2 in pairing_patterns:
                            if (last1.endswith(pattern1[-1]) and last2.endswith(pattern2[-1]) and
                                last1[:-1] == last2[:-1]):
                                pairs.append((course1, course2))
                                break
        
        return pairs
    
    def apply_pairs(self, pairs):
        """Apply the found pairs to the course_pairs dictionary"""
        for course1, course2 in pairs:
            if course1 not in self.course_pairs and course2 not in self.course_pairs:
                self.course_pairs[course1] = course2
                self.course_pairs[course2] = course1
                
                
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = CoursePairingStep1()
    app.run()