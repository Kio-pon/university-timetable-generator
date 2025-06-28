import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import json
import os
from typing import Dict, List

class CoursePairingManagerTkinter:
    def __init__(self, root):
        self.root = root
        self.root.title("🎓 Course Pairing Manager")
        self.root.geometry("1200x800")
        self.root.configure(bg='#f0f0f0')
        
        # Data storage
        self.df = None
        self.pairings_file = "course_pairings.json"
        self.pairings = {}
        
        # Load existing pairings
        self.load_pairings()
        
        # Create the GUI
        self.create_widgets()
        
    def load_pairings(self):
        """Load existing course pairings from JSON file"""
        try:
            if os.path.exists(self.pairings_file):
                with open(self.pairings_file, 'r', encoding='utf-8') as file:
                    self.pairings = json.load(file)
            else:
                self.pairings = {}
        except Exception as e:
            messagebox.showerror("Error", f"Error loading pairings: {e}")
            self.pairings = {}
    
    def save_pairings(self):
        """Save course pairings to JSON file"""
        try:
            with open(self.pairings_file, 'w', encoding='utf-8') as file:
                json.dump(self.pairings, file, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Error saving pairings: {e}")
            return False
    
    def create_widgets(self):
        """Create the main GUI widgets"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_file_tab()
        self.create_courses_tab()
        self.create_pairing_tab()
        self.create_view_pairings_tab()
        self.create_manage_tab()
        
    def create_file_tab(self):
        """Create file upload and management tab"""
        file_frame = ttk.Frame(self.notebook)
        self.notebook.add(file_frame, text="📁 Load CSV")
        
        # Title
        title_label = tk.Label(file_frame, text="Course Pairing Manager", 
                              font=("Arial", 24, "bold"), bg='#f0f0f0', fg='#2c3e50')
        title_label.pack(pady=20)
        
        # File selection frame
        file_select_frame = ttk.LabelFrame(file_frame, text="Select CSV File", padding=20)
        file_select_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.file_path_var = tk.StringVar()
        self.file_path_entry = ttk.Entry(file_select_frame, textvariable=self.file_path_var, width=60)
        self.file_path_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        browse_btn = ttk.Button(file_select_frame, text="Browse", command=self.browse_file)
        browse_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        load_btn = ttk.Button(file_select_frame, text="Load CSV", command=self.load_csv)
        load_btn.pack(side=tk.LEFT)
        
        # Status frame
        status_frame = ttk.LabelFrame(file_frame, text="Status", padding=20)
        status_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.status_label = tk.Label(status_frame, text="No file loaded", 
                                   font=("Arial", 12), bg='#f0f0f0')
        self.status_label.pack()
        
        # Sample format frame
        sample_frame = ttk.LabelFrame(file_frame, text="Expected CSV Format", padding=20)
        sample_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        sample_text = """Required columns:
Course Code, Section, Title, Day, Start, End, Room, Instructor / Sponsor

Example:
CORE 200,L1,Scientific Methods,M,2:30 PM,3:45 PM,W-234,Aamir Hasan
EE|CE 354|361L,L2,Intro to Probability & Stats,MW,11:30 AM,12:45 PM,GF-E121,Aamir Hasan
ANT 325,S1,Truth in Anthropology,TTh,8:30 AM,9:45 AM,FF-E220,Aaron Mulvany"""
        
        sample_label = tk.Label(sample_frame, text=sample_text, 
                               font=("Courier", 10), justify=tk.LEFT, bg='#f0f0f0')
        sample_label.pack(anchor=tk.W)
        
    def create_courses_tab(self):
        """Create courses viewing tab"""
        courses_frame = ttk.Frame(self.notebook)
        self.notebook.add(courses_frame, text="📚 View Courses")
        
        # Search frame
        search_frame = ttk.LabelFrame(courses_frame, text="Search Courses", padding=10)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=(5, 10))
        
        clear_btn = ttk.Button(search_frame, text="Clear", command=self.clear_search)
        clear_btn.pack(side=tk.LEFT)
        
        # Courses list frame
        list_frame = ttk.LabelFrame(courses_frame, text="Courses", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create treeview for courses
        columns = ("Code", "Section", "Title", "Day", "Time", "Room", "Instructor")
        self.courses_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)
        
        # Configure columns
        self.courses_tree.heading("Code", text="Course Code")
        self.courses_tree.heading("Section", text="Section")
        self.courses_tree.heading("Title", text="Title")
        self.courses_tree.heading("Day", text="Day")
        self.courses_tree.heading("Time", text="Time")
        self.courses_tree.heading("Room", text="Room")
        self.courses_tree.heading("Instructor", text="Instructor")
        
        # Configure column widths
        self.courses_tree.column("Code", width=120)
        self.courses_tree.column("Section", width=80)
        self.courses_tree.column("Title", width=200)
        self.courses_tree.column("Day", width=80)
        self.courses_tree.column("Time", width=150)
        self.courses_tree.column("Room", width=100)
        self.courses_tree.column("Instructor", width=150)
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.courses_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.courses_tree.xview)
        self.courses_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.courses_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def create_pairing_tab(self):
        """Create course pairing tab"""
        pairing_frame = ttk.Frame(self.notebook)
        self.notebook.add(pairing_frame, text="🔗 Create Pairing")
        
        # Title
        title_label = tk.Label(pairing_frame, text="Create New Course Pairing", 
                              font=("Arial", 16, "bold"), bg='#f0f0f0')
        title_label.pack(pady=10)
        
        # Main pairing frame
        main_frame = ttk.Frame(pairing_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left side - First course
        left_frame = ttk.LabelFrame(main_frame, text="First Course", padding=15)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(left_frame, text="Select first course:").pack(anchor=tk.W)
        self.course1_var = tk.StringVar()
        self.course1_combo = ttk.Combobox(left_frame, textvariable=self.course1_var, 
                                         width=50, state="readonly")
        self.course1_combo.pack(fill=tk.X, pady=5)
        self.course1_combo.bind('<<ComboboxSelected>>', self.on_course1_selected)
        
        self.course1_info = scrolledtext.ScrolledText(left_frame, height=8, width=40)
        self.course1_info.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Right side - Second course
        right_frame = ttk.LabelFrame(main_frame, text="Course to Pair With", padding=15)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        tk.Label(right_frame, text="Select course to pair with:").pack(anchor=tk.W)
        self.course2_var = tk.StringVar()
        self.course2_combo = ttk.Combobox(right_frame, textvariable=self.course2_var, 
                                         width=50, state="readonly")
        self.course2_combo.pack(fill=tk.X, pady=5)
        self.course2_combo.bind('<<ComboboxSelected>>', self.on_course2_selected)
        
        self.course2_info = scrolledtext.ScrolledText(right_frame, height=8, width=40)
        self.course2_info.pack(fill=tk.BOTH, expand=True, pady=5)
          # Bottom frame - Create button and auto-pairing
        bottom_frame = ttk.Frame(pairing_frame)
        bottom_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Manual pairing button
        create_btn = ttk.Button(bottom_frame, text="✅ Create Pairing", 
                               command=self.create_pairing, style="Accent.TButton")
        create_btn.pack(pady=5)
        
        # Separator
        separator = ttk.Separator(bottom_frame, orient='horizontal')
        separator.pack(fill=tk.X, pady=15)
        
        # Auto-pairing section
        auto_label = tk.Label(bottom_frame, text="🤖 Automatic Pairing", 
                             font=("Arial", 14, "bold"), bg='#f0f0f0')
        auto_label.pack(pady=5)
        
        auto_info = tk.Label(bottom_frame, 
                            text="Let the algorithm automatically pair related courses based on patterns",
                            font=("Arial", 10), bg='#f0f0f0', fg='#666')
        auto_info.pack(pady=2)
        
        auto_btn = ttk.Button(bottom_frame, text="🤖 Auto-Pair All Courses", 
                             command=self.auto_pair_courses)
        auto_btn.pack(pady=10)
        
    def create_view_pairings_tab(self):
        """Create view pairings tab"""
        view_frame = ttk.Frame(self.notebook)
        self.notebook.add(view_frame, text="👀 View Pairings")
        
        # Title
        title_label = tk.Label(view_frame, text="All Course Pairings", 
                              font=("Arial", 16, "bold"), bg='#f0f0f0')
        title_label.pack(pady=10)
        
        # Refresh button
        refresh_btn = ttk.Button(view_frame, text="🔄 Refresh", command=self.refresh_pairings_view)
        refresh_btn.pack(pady=5)
        
        # Pairings display frame
        pairings_frame = ttk.LabelFrame(view_frame, text="Current Pairings", padding=10)
        pairings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.pairings_text = scrolledtext.ScrolledText(pairings_frame, height=25, width=100)
        self.pairings_text.pack(fill=tk.BOTH, expand=True)
        
    def create_manage_tab(self):
        """Create manage pairings tab"""
        manage_frame = ttk.Frame(self.notebook)
        self.notebook.add(manage_frame, text="🗑️ Manage Pairings")
        
        # Title
        title_label = tk.Label(manage_frame, text="Manage Course Pairings", 
                              font=("Arial", 16, "bold"), bg='#f0f0f0')
        title_label.pack(pady=10)
        
        # Delete specific pairing frame
        delete_frame = ttk.LabelFrame(manage_frame, text="Delete Specific Pairing", padding=15)
        delete_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(delete_frame, text="Select pairing to delete:").pack(anchor=tk.W)
        self.delete_pairing_var = tk.StringVar()
        self.delete_pairing_combo = ttk.Combobox(delete_frame, textvariable=self.delete_pairing_var, 
                                                width=80, state="readonly")
        self.delete_pairing_combo.pack(fill=tk.X, pady=5)
        
        delete_btn = ttk.Button(delete_frame, text="🗑️ Delete Selected Pairing", 
                               command=self.delete_specific_pairing)
        delete_btn.pack(pady=5)
        
        # Danger zone frame
        danger_frame = ttk.LabelFrame(manage_frame, text="⚠️ Danger Zone", padding=15)
        danger_frame.pack(fill=tk.X, padx=20, pady=10)
        
        warning_label = tk.Label(danger_frame, 
                                text="WARNING: This will delete ALL course pairings permanently!",
                                fg='red', font=("Arial", 10, "bold"))
        warning_label.pack(pady=5)
        
        clear_all_btn = ttk.Button(danger_frame, text="🗑️ Clear All Pairings", 
                                  command=self.clear_all_pairings)
        clear_all_btn.pack(pady=5)
        
    def browse_file(self):
        """Browse for CSV file"""
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            
    def load_csv(self):
        """Load CSV file"""
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showerror("Error", "Please select a CSV file first!")
            return
            
        try:
            self.df = pd.read_csv(file_path)
            
            # Validate required columns
            required_columns = ['Course Code', 'Section', 'Title', 'Day', 'Start', 'End', 'Room', 'Instructor / Sponsor']
            missing_columns = [col for col in required_columns if col not in self.df.columns]
            
            if missing_columns:
                messagebox.showerror("Error", f"Missing required columns: {missing_columns}")
                return
                
            self.status_label.config(text=f"✅ Loaded {len(self.df)} courses successfully!", fg='green')
            self.populate_courses_tree()
            self.populate_course_combos()
            self.refresh_pairings_view()
            self.populate_delete_combo()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading CSV file: {e}")
            
    def populate_courses_tree(self):
        """Populate the courses treeview"""
        if self.df is None:
            return
            
        # Clear existing items
        for item in self.courses_tree.get_children():
            self.courses_tree.delete(item)
            
        # Add courses to tree
        for _, course in self.df.iterrows():
            time_str = f"{course['Start']} - {course['End']}"
            self.courses_tree.insert("", tk.END, values=(
                course['Course Code'],
                course['Section'],
                course['Title'],
                course['Day'],
                time_str,
                course['Room'],
                course['Instructor / Sponsor']
            ))
            
    def populate_course_combos(self):
        """Populate course selection comboboxes"""
        if self.df is None:
            return
            
        course_options = []
        for _, course in self.df.iterrows():
            display_name = f"{course['Course Code']} ({course['Section']}) - {course['Title']}"
            course_options.append(display_name)
            
        self.course1_combo['values'] = course_options
        self.course2_combo['values'] = course_options
        
    def on_course1_selected(self, event):
        """Handle first course selection"""
        selected = self.course1_var.get()
        if not selected or self.df is None:
            return
            
        # Find the course details
        course = self.find_course_by_display_name(selected)
        if course is not None:
            info_text = f"Course: {course['Course Code']} ({course['Section']})\n"
            info_text += f"Title: {course['Title']}\n"
            info_text += f"Day: {course['Day']}\n"
            info_text += f"Time: {course['Start']} - {course['End']}\n"
            info_text += f"Room: {course['Room']}\n"
            info_text += f"Instructor: {course['Instructor / Sponsor']}"
            
            self.course1_info.delete(1.0, tk.END)
            self.course1_info.insert(1.0, info_text)
            
            # Update course2 combo to exclude selected course
            self.update_course2_combo()
            
    def on_course2_selected(self, event):
        """Handle second course selection"""
        selected = self.course2_var.get()
        if not selected or self.df is None:
            return
            
        course = self.find_course_by_display_name(selected)
        if course is not None:
            info_text = f"Course: {course['Course Code']} ({course['Section']})\n"
            info_text += f"Title: {course['Title']}\n"
            info_text += f"Day: {course['Day']}\n"
            info_text += f"Time: {course['Start']} - {course['End']}\n"
            info_text += f"Room: {course['Room']}\n"
            info_text += f"Instructor: {course['Instructor / Sponsor']}"
            
            self.course2_info.delete(1.0, tk.END)
            self.course2_info.insert(1.0, info_text)
            
    def update_course2_combo(self):
        """Update course2 combo to exclude selected course1"""
        if self.df is None:
            return
            
        selected_course1 = self.course1_var.get()
        course_options = []
        
        for _, course in self.df.iterrows():
            display_name = f"{course['Course Code']} ({course['Section']}) - {course['Title']}"
            if display_name != selected_course1:
                course_options.append(display_name)
                
        self.course2_combo['values'] = course_options
        self.course2_var.set("")  # Clear selection
        self.course2_info.delete(1.0, tk.END)
        
    def find_course_by_display_name(self, display_name):
        """Find course by display name"""
        if self.df is None:
            return None
            
        for _, course in self.df.iterrows():
            course_display = f"{course['Course Code']} ({course['Section']}) - {course['Title']}"
            if course_display == display_name:
                return course
        return None
        
    def get_course_key(self, course):
        """Get unique key for course"""
        return f"{course['Course Code']}_{course['Section']}"
        
    def create_pairing(self):
        """Create new course pairing"""
        course1_name = self.course1_var.get()
        course2_name = self.course2_var.get()
        
        if not course1_name or not course2_name:
            messagebox.showerror("Error", "Please select both courses!")
            return
            
        course1 = self.find_course_by_display_name(course1_name)
        course2 = self.find_course_by_display_name(course2_name)
        
        if course1 is None or course2 is None:
            messagebox.showerror("Error", "Could not find course details!")
            return
            
        course1_key = self.get_course_key(course1)
        course2_key = self.get_course_key(course2)
        
        # Check if pairing already exists
        if course1_key in self.pairings:
            result = messagebox.askyesno("Warning", 
                                       f"{course1_name} is already paired! Overwrite existing pairing?")
            if not result:
                return
                
        # Create pairing
        self.pairings[course1_key] = course2_key
        self.pairings[course2_key] = course1_key
        
        if self.save_pairings():
            messagebox.showinfo("Success", f"Successfully paired:\n{course1_name} ↔ {course2_name}")
            self.refresh_pairings_view()
            self.populate_delete_combo()
            
            # Clear selections
            self.course1_var.set("")
            self.course2_var.set("")
            self.course1_info.delete(1.0, tk.END)
            self.course2_info.delete(1.0, tk.END)
            self.populate_course_combos()
            
    def refresh_pairings_view(self):
        """Refresh the pairings view"""
        self.pairings_text.delete(1.0, tk.END)
        
        if not self.pairings:
            self.pairings_text.insert(tk.END, "📝 No course pairings found.\n\nCreate some pairings in the 'Create Pairing' tab!")
            return
            
        self.pairings_text.insert(tk.END, "🔗 Course Pairings:\n")
        self.pairings_text.insert(tk.END, "=" * 80 + "\n\n")
        
        # Group pairings to avoid duplicates
        displayed_pairs = set()
        
        for course_key, paired_key in self.pairings.items():
            pair_tuple = tuple(sorted([course_key, paired_key]))
            
            if pair_tuple not in displayed_pairs:
                displayed_pairs.add(pair_tuple)
                
                try:
                    course1_details = self.find_course_by_key(course_key)
                    course2_details = self.find_course_by_key(paired_key)
                    
                    if course1_details is not None and course2_details is not None:
                        course1_display = f"{course1_details['Course Code']} ({course1_details['Section']}) - {course1_details['Title']}"
                        course2_display = f"{course2_details['Course Code']} ({course2_details['Section']}) - {course2_details['Title']}"
                        
                        self.pairings_text.insert(tk.END, f"• {course1_display}\n")
                        self.pairings_text.insert(tk.END, f"  ↔ {course2_display}\n\n")
                        
                        # Add details
                        self.pairings_text.insert(tk.END, f"    Course 1: {course1_details['Day']} | {course1_details['Start']}-{course1_details['End']} | {course1_details['Room']}\n")
                        self.pairings_text.insert(tk.END, f"    Course 2: {course2_details['Day']} | {course2_details['Start']}-{course2_details['End']} | {course2_details['Room']}\n\n")
                        self.pairings_text.insert(tk.END, "-" * 80 + "\n\n")
                except:
                    continue
                    
    def find_course_by_key(self, course_key):
        """Find course by key"""
        if self.df is None:
            return None
            
        try:
            code, section = course_key.split('_')
            course_match = self.df[(self.df['Course Code'] == code) & (self.df['Section'] == section)]
            if not course_match.empty:
                return course_match.iloc[0]
        except:
            pass
        return None
        
    def populate_delete_combo(self):
        """Populate delete pairing combo"""
        if not self.pairings:
            self.delete_pairing_combo['values'] = []
            return
            
        pairing_options = []
        displayed_pairs = set()
        
        for course_key, paired_key in self.pairings.items():
            pair_tuple = tuple(sorted([course_key, paired_key]))
            
            if pair_tuple not in displayed_pairs:
                displayed_pairs.add(pair_tuple)
                
                try:
                    course1_details = self.find_course_by_key(course_key)
                    course2_details = self.find_course_by_key(paired_key)
                    
                    if course1_details is not None and course2_details is not None:
                        course1_display = f"{course1_details['Course Code']} ({course1_details['Section']}) - {course1_details['Title']}"
                        course2_display = f"{course2_details['Course Code']} ({course2_details['Section']}) - {course2_details['Title']}"
                        
                        pairing_display = f"{course1_display} ↔ {course2_display}"
                        pairing_options.append((pairing_display, course_key, paired_key))
                except:
                    continue
                    
        self.delete_pairing_combo['values'] = [option[0] for option in pairing_options]
        self.delete_pairing_options = pairing_options
        
    def delete_specific_pairing(self):
        """Delete specific pairing"""
        selected = self.delete_pairing_var.get()
        if not selected:
            messagebox.showerror("Error", "Please select a pairing to delete!")
            return
            
        result = messagebox.askyesno("Confirm", f"Are you sure you want to delete this pairing?\n\n{selected}")
        if not result:
            return
            
        # Find the keys for this pairing
        for display, key1, key2 in self.delete_pairing_options:
            if display == selected:
                if key1 in self.pairings:
                    del self.pairings[key1]
                if key2 in self.pairings:
                    del self.pairings[key2]
                break
                
        if self.save_pairings():
            messagebox.showinfo("Success", "Pairing deleted successfully!")
            self.refresh_pairings_view()
            self.populate_delete_combo()
            self.delete_pairing_var.set("")
            
    def clear_all_pairings(self):
        """Clear all pairings"""
        if not self.pairings:
            messagebox.showinfo("Info", "No pairings to clear!")
            return
            
        result = messagebox.askyesno("Confirm", 
                                   "WARNING: This will delete ALL course pairings permanently!\n\nAre you sure?")
        if not result:
            return
            
        result2 = messagebox.askyesno("Final Confirmation", 
                                    "This action cannot be undone!\n\nDelete ALL pairings?")
        if not result2:
            return
            
        self.pairings.clear()
        if self.save_pairings():
            messagebox.showinfo("Success", "All pairings cleared successfully!")
            self.refresh_pairings_view()
            self.populate_delete_combo()
            
    def on_search_change(self, *args):
        """Handle search text change"""
        if self.df is None:
            return
            
        search_term = self.search_var.get().lower()
        
        # Clear existing items
        for item in self.courses_tree.get_children():
            self.courses_tree.delete(item)
            
        # Filter and add courses
        for _, course in self.df.iterrows():
            if (search_term in course['Course Code'].lower() or 
                search_term in course['Title'].lower() or 
                search_term in course['Instructor / Sponsor'].lower()):
                
                time_str = f"{course['Start']} - {course['End']}"
                self.courses_tree.insert("", tk.END, values=(
                    course['Course Code'],
                    course['Section'],
                    course['Title'],
                    course['Day'],
                    time_str,
                    course['Room'],
                    course['Instructor / Sponsor']
                ))
                
    def clear_search(self):
        """Clear search"""
        self.search_var.set("")
        self.populate_courses_tree()
        
    def auto_pair_courses(self):
        """Automatically pair courses based on intelligent algorithms"""
        if self.df is None:
            messagebox.showerror("Error", "Please load a CSV file first!")
            return
        
        if len(self.df) < 2:
            messagebox.showwarning("Warning", "Need at least 2 courses to create pairings!")
            return
        
        # Ask user for confirmation
        result = messagebox.askyesno("Auto-Pairing", 
                                   "This will automatically create course pairings based on:\n\n" +
                                   "• Course codes (e.g., Math 101 ↔ Math 101L)\n" +
                                   "• Lecture/Lab patterns (e.g., Bio 200 ↔ Bio L)\n" +
                                   "• Same instructor courses\n" +
                                   "• Similar time slots\n\n" +
                                   "Continue with auto-pairing?")
        if not result:
            return
        
        # Store original pairings count
        original_count = len(self.pairings) // 2
        
        # Run different pairing algorithms
        new_pairings = {}
        pairing_results = []
        
        # Algorithm 1: Course Code + Lab/Lecture Pattern Matching
        lecture_lab_pairs = self.find_lecture_lab_pairs()
        new_pairings.update(lecture_lab_pairs)
        if lecture_lab_pairs:
            pairing_results.append(f"• {len(lecture_lab_pairs)//2} Lecture-Lab pairs found")
        
        # Algorithm 2: Same Course Code Different Sections
        section_pairs = self.find_section_pairs()
        new_pairings.update(section_pairs)
        if section_pairs:
            pairing_results.append(f"• {len(section_pairs)//2} Same-course section pairs found")
        
        # Algorithm 3: Same Instructor Time-Adjacent Courses
        instructor_pairs = self.find_instructor_time_pairs()
        new_pairings.update(instructor_pairs)
        if instructor_pairs:
            pairing_results.append(f"• {len(instructor_pairs)//2} Instructor time-adjacent pairs found")
        
        # Algorithm 4: Related Course Title Matching
        title_pairs = self.find_related_title_pairs()
        new_pairings.update(title_pairs)
        if title_pairs:
            pairing_results.append(f"• {len(title_pairs)//2} Related title pairs found")
        
        # Merge with existing pairings (avoid conflicts)
        conflicts = 0
        for key, value in new_pairings.items():
            if key not in self.pairings:
                self.pairings[key] = value
            else:
                conflicts += 1
        
        new_count = len(self.pairings) // 2
        total_new = new_count - original_count
        
        # Show results
        if total_new > 0:
            result_text = f"Auto-pairing completed!\n\n"
            result_text += f"📊 Results:\n"
            result_text += f"• {total_new} new pairings created\n"
            result_text += f"• {conflicts//2} conflicts skipped (already paired)\n\n"
            result_text += "📋 Breakdown:\n" + "\n".join(pairing_results)
            
            messagebox.showinfo("Auto-Pairing Results", result_text)
            
            # Save and refresh
            if self.save_pairings():
                self.refresh_pairings_view()
                self.populate_delete_combo()
        else:
            messagebox.showinfo("Auto-Pairing Results", 
                              "No new pairings found.\n\nAll potential pairs may already exist or " +
                              "courses may not match the pairing patterns.")
    
    def find_lecture_lab_pairs(self):
        """Find lecture-lab pairs based on course codes and patterns"""
        pairs = {}
        
        for i, course1 in self.df.iterrows():
            course1_code = course1['Course Code'].strip()
            course1_key = self.get_course_key(course1)
            
            # Skip if already paired
            if course1_key in self.pairings:
                continue
            
            for j, course2 in self.df.iterrows():
                if i >= j:  # Avoid duplicate checks
                    continue
                    
                course2_code = course2['Course Code'].strip()
                course2_key = self.get_course_key(course2)
                
                # Skip if already paired
                if course2_key in self.pairings:
                    continue
                
                # Pattern 1: Course + CourseL (e.g., "Bio 101" and "Bio 101L")
                if (course1_code + "L" == course2_code or 
                    course2_code + "L" == course1_code):
                    pairs[course1_key] = course2_key
                    pairs[course2_key] = course1_key
                    continue
                
                # Pattern 2: Course + Course L (e.g., "Bio 101" and "Bio L")
                if self.is_lecture_lab_pattern(course1_code, course2_code):
                    pairs[course1_key] = course2_key
                    pairs[course2_key] = course1_key
                    continue
                
                # Pattern 3: Similar codes with L/R/T suffixes
                if self.is_suffix_pattern(course1_code, course2_code):
                    pairs[course1_key] = course2_key
                    pairs[course2_key] = course1_key
        
        return pairs
    
    def find_section_pairs(self):
        """Find courses with same code but different sections"""
        pairs = {}
        
        for i, course1 in self.df.iterrows():
            course1_key = self.get_course_key(course1)
            if course1_key in self.pairings:
                continue
                
            for j, course2 in self.df.iterrows():
                if i >= j:
                    continue
                    
                course2_key = self.get_course_key(course2)
                if course2_key in self.pairings:
                    continue
                
                # Same course code, different sections
                if (course1['Course Code'] == course2['Course Code'] and 
                    course1['Section'] != course2['Section']):
                    pairs[course1_key] = course2_key
                    pairs[course2_key] = course1_key
                    break  # Only pair with first match
        
        return pairs
    
    def find_instructor_time_pairs(self):
        """Find courses by same instructor with adjacent time slots"""
        pairs = {}
        
        for i, course1 in self.df.iterrows():
            course1_key = self.get_course_key(course1)
            if course1_key in self.pairings:
                continue
                
            for j, course2 in self.df.iterrows():
                if i >= j:
                    continue
                    
                course2_key = self.get_course_key(course2)
                if course2_key in self.pairings:
                    continue
                
                # Same instructor
                if course1['Instructor / Sponsor'] == course2['Instructor / Sponsor']:
                    # Check if time slots are adjacent or overlapping
                    if self.are_times_related(course1, course2):
                        pairs[course1_key] = course2_key
                        pairs[course2_key] = course1_key
                        break
        
        return pairs
    
    def find_related_title_pairs(self):
        """Find courses with related titles"""
        pairs = {}
        
        for i, course1 in self.df.iterrows():
            course1_key = self.get_course_key(course1)
            if course1_key in self.pairings:
                continue
                
            for j, course2 in self.df.iterrows():
                if i >= j:
                    continue
                    
                course2_key = self.get_course_key(course2)
                if course2_key in self.pairings:
                    continue
                
                # Check for related titles
                if self.are_titles_related(course1['Title'], course2['Title']):
                    pairs[course1_key] = course2_key
                    pairs[course2_key] = course1_key
                    break
        
        return pairs
    
    def is_lecture_lab_pattern(self, code1, code2):
        """Check if two course codes represent lecture-lab pattern"""
        # Remove common suffixes and check base
        base1 = code1.replace('L', '').replace('R', '').replace('T', '').strip()
        base2 = code2.replace('L', '').replace('R', '').replace('T', '').strip()
        
        # Check if one is base and other has lab indicator
        if base1 == base2 and base1 != code1 and base2 != code2:
            return True
        
        # Check patterns like "Bio 101" and "Bio L"
        if ('L' in code2 and base1 in code2) or ('L' in code1 and base2 in code1):
            return True
            
        return False
    
    def is_suffix_pattern(self, code1, code2):
        """Check if courses have similar codes with different suffixes"""
        # Handle patterns like "EE|CE 354|361L" and "EE|CE 354|361R"
        base1 = code1.split('|')[-1] if '|' in code1 else code1
        base2 = code2.split('|')[-1] if '|' in code2 else code2
        
        # Remove last character if it's L, R, or T
        if base1 and base1[-1] in 'LRT':
            base1 = base1[:-1]
        if base2 and base2[-1] in 'LRT':
            base2 = base2[:-1]
            
        return base1 == base2 and base1 != "" and code1 != code2
    
    def are_times_related(self, course1, course2):
        """Check if two courses have related time slots"""
        try:
            # Parse times (basic implementation)
            start1 = course1['Start']
            end1 = course1['End']
            start2 = course2['Start']
            end2 = course2['End']
            
            # Same day or overlapping days
            days1 = set(course1['Day'])
            days2 = set(course2['Day'])
            
            if days1 & days2:  # Overlapping days
                # Simple time adjacency check (this could be improved)
                if end1 == start2 or end2 == start1:
                    return True
                # Back-to-back classes (within 30 minutes)
                # This is a simplified check - could be enhanced with proper time parsing
                return abs(hash(start1) - hash(end2)) < 1000 or abs(hash(start2) - hash(end1)) < 1000
                
        except:
            pass
        return False
    
    def are_titles_related(self, title1, title2):
        """Check if two course titles are related"""
        title1_lower = title1.lower()
        title2_lower = title2.lower()
        
        # Check for common keywords that indicate related courses
        related_keywords = [
            ('intro', 'advanced'), ('basic', 'intermediate'), ('part i', 'part ii'),
            ('theory', 'practice'), ('lecture', 'lab'), ('fundamentals', 'applications'),
            ('i', 'ii'), ('1', '2'), ('a', 'b')
        ]
        
        for keyword_pair in related_keywords:
            if (keyword_pair[0] in title1_lower and keyword_pair[1] in title2_lower) or \
               (keyword_pair[1] in title1_lower and keyword_pair[0] in title2_lower):
                return True
        
        # Check for common base words (at least 2 words in common)
        words1 = set(title1_lower.split())
        words2 = set(title2_lower.split())
        common_words = words1 & words2
        
        # Remove common stop words
        stop_words = {'to', 'in', 'of', 'and', 'the', 'for', 'with', 'an', 'a'}
        common_words -= stop_words
        
        return len(common_words) >= 2

def main():
    root = tk.Tk()
    app = CoursePairingManagerTkinter(root)
    root.mainloop()

if __name__ == "__main__":
    main()
