import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import json
import re
from collections import defaultdict

class CourseSchedulerMockup:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Course Scheduler Mockup - Auto Pipeline Test")
        self.root.geometry("1200x800")
        
        # Data storage
        self.courses_df = None
        self.course_pairs = {}
        self.correct_pairings = {}
        self.incorrect_pairings = {}
        self.selected_courses = {}
        
        self.setup_ui()
    
    def setup_ui(self):
        """Create the main UI"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Upload & Auto-Process
        self.upload_tab = ttk.Frame(notebook)
        notebook.add(self.upload_tab, text="📁 Upload & Auto-Process")
        self.setup_upload_tab()
        
        # Tab 2: Smart Course Selection
        self.selection_tab = ttk.Frame(notebook)
        notebook.add(self.selection_tab, text="🎯 Smart Course Selection")
        self.setup_selection_tab()
        
        # Tab 3: Results & Export
        self.results_tab = ttk.Frame(notebook)
        notebook.add(self.results_tab, text="📊 Results & Export")
        self.setup_results_tab()
    
    def setup_upload_tab(self):
        """Setup the upload and auto-process tab"""
        frame = ttk.Frame(self.upload_tab)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Course Scheduler - Auto Pipeline Test", 
                 font=('Arial', 18, 'bold')).pack(pady=10)
        
        # Upload section
        upload_frame = ttk.LabelFrame(frame, text="Step 1: Upload CSV File", padding=15)
        upload_frame.pack(fill='x', pady=10)
        
        upload_btn_frame = ttk.Frame(upload_frame)
        upload_btn_frame.pack(fill='x')
        
        ttk.Button(upload_btn_frame, text="📁 Browse CSV File", 
                  command=self.upload_csv).pack(side='left', padx=10)
        
        self.file_label = ttk.Label(upload_btn_frame, text="No file loaded", 
                                   foreground='red')
        self.file_label.pack(side='left', padx=10)
        
        # Auto-process section
        process_frame = ttk.LabelFrame(frame, text="Step 2: Auto-Process Pipeline", padding=15)
        process_frame.pack(fill='x', pady=10)
        
        ttk.Button(process_frame, text="🚀 Run Complete Auto-Pipeline", 
                  command=self.run_auto_pipeline).pack(pady=10)
        
        # Status display
        self.status_frame = ttk.LabelFrame(frame, text="Pipeline Status", padding=15)
        self.status_frame.pack(fill='both', expand=True, pady=10)
        
        self.status_text = tk.Text(self.status_frame, height=15, wrap='word')
        status_scrollbar = ttk.Scrollbar(self.status_frame, orient='vertical', command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        
        self.status_text.pack(side='left', fill='both', expand=True)
        status_scrollbar.pack(side='right', fill='y')
    
    def setup_selection_tab(self):
        """Setup the smart course selection tab"""
        frame = ttk.Frame(self.selection_tab)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Smart Course Selection", 
                 font=('Arial', 16, 'bold')).pack(pady=10)
        
        # Course selection area
        selection_frame = ttk.Frame(frame)
        selection_frame.pack(fill='both', expand=True)
        
        # Left side - Available courses
        left_frame = ttk.LabelFrame(selection_frame, text="Available Courses", padding=10)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        self.courses_listbox = tk.Listbox(left_frame, height=20)
        courses_scrollbar = ttk.Scrollbar(left_frame, orient='vertical', command=self.courses_listbox.yview)
        self.courses_listbox.configure(yscrollcommand=courses_scrollbar.set)
        self.courses_listbox.bind('<<ListboxSelect>>', self.on_course_selected)
        
        self.courses_listbox.pack(side='left', fill='both', expand=True)
        courses_scrollbar.pack(side='right', fill='y')
        
        # Right side - Selected courses & auto-paired
        right_frame = ttk.LabelFrame(selection_frame, text="Selected Courses & Auto-Paired", padding=10)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        self.selected_listbox = tk.Listbox(right_frame, height=20, bg='#e8f5e8')
        selected_scrollbar = ttk.Scrollbar(right_frame, orient='vertical', command=self.selected_listbox.yview)
        self.selected_listbox.configure(yscrollcommand=selected_scrollbar.set)
        
        self.selected_listbox.pack(side='left', fill='both', expand=True)
        selected_scrollbar.pack(side='right', fill='y')
        
        # Bottom info
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill='x', pady=(10, 0))
        
        self.info_label = ttk.Label(info_frame, text="💡 Click a course to automatically select its pair!", 
                                   font=('Arial', 10), foreground='blue')
        self.info_label.pack()
        
        # Action buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Button(button_frame, text="🗑️ Clear Selection", 
                  command=self.clear_selection).pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="📊 Generate Schedule", 
                  command=self.generate_schedule).pack(side='left', padx=5)
    
    def setup_results_tab(self):
        """Setup the results and export tab"""
        frame = ttk.Frame(self.results_tab)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Pipeline Results & Export", 
                 font=('Arial', 16, 'bold')).pack(pady=10)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="📤 Export Course Pairs", 
                  command=self.export_pairs).pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="📤 Export Predictions", 
                  command=self.export_predictions).pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="📄 View Summary", 
                  command=self.view_summary).pack(side='left', padx=5)
        
        # Results display
        self.results_text = tk.Text(frame, height=20, wrap='word')
        results_scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scrollbar.set)
        
        self.results_text.pack(side='left', fill='both', expand=True)
        results_scrollbar.pack(side='right', fill='y')
    
    def upload_csv(self):
        """Upload and validate CSV file"""
        file_path = filedialog.askopenfilename(
            title="Select Course CSV file",
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
                
                self.file_label.config(text=f"✅ Loaded: {file_path.split('/')[-1]}", 
                                     foreground='green')
                
                self.log_status(f"📁 CSV file loaded successfully!")
                self.log_status(f"📊 Total records: {len(self.courses_df)}")
                self.log_status(f"🎓 Unique courses: {len(self.courses_df['Course Code'].unique())}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV: {str(e)}")
    
    def run_auto_pipeline(self):
        """Run the complete auto-processing pipeline"""
        if self.courses_df is None:
            messagebox.showerror("Error", "Please upload a CSV file first!")
            return
        
        self.log_status("\n🚀 STARTING AUTO-PIPELINE...\n" + "="*50)
        
        # Step 1: Auto-pair courses
        self.log_status("🔄 Step 1: Auto-pairing courses...")
        step1_pairs = self.auto_pair_courses()
        
        # Step 2: Auto-predict section pairings
        self.log_status("🔄 Step 2: Auto-predicting section pairings...")
        step2_predictions = self.auto_predict_sections()
        
        # Step 3: Prepare smart selection
        self.log_status("🔄 Step 3: Preparing smart selection interface...")
        self.prepare_smart_selection()
        
        self.log_status(f"\n✅ AUTO-PIPELINE COMPLETED!")
        self.log_status(f"📋 Course pairs created: {len(self.course_pairs)//2}")
        self.log_status(f"🎯 Section predictions made: {sum(len(pairs) for pairs in self.correct_pairings.values())}")
        self.log_status(f"🎨 Smart selection ready!")
        
        messagebox.showinfo("Success", "Auto-pipeline completed! Check the Smart Course Selection tab.")
    
    def auto_pair_courses(self):
        """Step 1: Auto-pair courses using the algorithm from Step 1"""
        unique_courses = sorted(self.courses_df['Course Code'].unique())
        self.course_pairs = {}
        pairs_created = 0
        
        # Apply the Step 1 algorithms
        unpaired_courses = unique_courses[:]
        
        # Algorithm 1: Exact Lecture-Lab Pattern
        pairs_found = self.find_lecture_lab_exact_pairs(unpaired_courses)
        if pairs_found:
            pairs_created += len(pairs_found)
            self.apply_course_pairs(pairs_found)
            unpaired_courses = [course for course in unpaired_courses if course not in self.course_pairs]
            self.log_status(f"  ✓ Found {len(pairs_found)} Lecture-Lab exact pairs")
        
        # Algorithm 2: Base-Suffix Pattern
        pairs_found = self.find_base_suffix_pairs(unpaired_courses)
        if pairs_found:
            pairs_created += len(pairs_found)
            self.apply_course_pairs(pairs_found)
            unpaired_courses = [course for course in unpaired_courses if course not in self.course_pairs]
            self.log_status(f"  ✓ Found {len(pairs_found)} Base-Suffix pairs")
        
        # Algorithm 3: Pipe Course Pattern
        pairs_found = self.find_pipe_course_pairs(unpaired_courses)
        if pairs_found:
            pairs_created += len(pairs_found)
            self.apply_course_pairs(pairs_found)
            self.log_status(f"  ✓ Found {len(pairs_found)} Pipe course pairs")
        
        self.log_status(f"  📊 Total course pairs created: {pairs_created}")
        return pairs_created
    
    def auto_predict_sections(self):
        """Step 2: Auto-predict section pairings using the unified algorithm"""
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
            course1_sections = sorted(self.courses_df[self.courses_df['Course Code'] == course1]['Section'].unique())
            course2_sections = sorted(self.courses_df[self.courses_df['Course Code'] == course2]['Section'].unique())
            
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
                
                self.log_status(f"  ✓ {pair_key}: {algorithm} ({len(predicted_pairs)} predictions)")
        
        self.log_status(f"  📊 Total section predictions: {total_predictions}")
        return total_predictions
    
    def prepare_smart_selection(self):
        """Step 3: Prepare the smart selection interface"""
        if not self.course_pairs:
            self.log_status("  ⚠️ No course pairs available for smart selection")
            return
        
        # Populate available courses listbox
        self.courses_listbox.delete(0, tk.END)
        
        # Add individual courses that are part of pairs
        paired_courses = set(self.course_pairs.keys())
        for course in sorted(paired_courses):
            self.courses_listbox.insert(tk.END, course)
        
        self.log_status(f"  ✓ Loaded {len(paired_courses)} courses for smart selection")
    
    def on_course_selected(self, event):
        """Handle course selection - automatically add its pair"""
        selection = self.courses_listbox.curselection()
        if not selection:
            return
        
        selected_course = self.courses_listbox.get(selection[0])
        
        if selected_course in self.course_pairs:
            paired_course = self.course_pairs[selected_course]
            
            # Add both courses to selection if not already there
            current_selection = [self.selected_listbox.get(i) for i in range(self.selected_listbox.size())]
            
            if selected_course not in current_selection:
                self.selected_listbox.insert(tk.END, f"📚 {selected_course}")
                self.selected_courses[selected_course] = True
            
            if paired_course not in [item.replace("📚 ", "") for item in current_selection]:
                self.selected_listbox.insert(tk.END, f"🔗 {paired_course} (auto-paired)")
                self.selected_courses[paired_course] = True
            
            self.info_label.config(text=f"✅ Added {selected_course} and its pair {paired_course}")
    
    def clear_selection(self):
        """Clear the course selection"""
        self.selected_listbox.delete(0, tk.END)
        self.selected_courses = {}
        self.info_label.config(text="💡 Click a course to automatically select its pair!")
    
    def generate_schedule(self):
        """Generate schedule with selected courses"""
        if not self.selected_courses:
            messagebox.showwarning("Warning", "No courses selected!")
            return
        
        # Simple schedule generation - just show the selected courses
        schedule_text = "📅 GENERATED SCHEDULE\n" + "="*30 + "\n\n"
        
        for course in sorted(self.selected_courses.keys()):
            course_data = self.courses_df[self.courses_df['Course Code'] == course]
            schedule_text += f"🎓 {course}\n"
            
            for _, row in course_data.iterrows():
                schedule_text += f"   📋 {row['Section']}: {row['Day']} {row['Start']}-{row['End']}\n"
                schedule_text += f"   📍 {row['Room']} | {row['Instructor / Sponsor']}\n"
            
            schedule_text += "\n"
        
        # Show in results tab
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, schedule_text)
        
        messagebox.showinfo("Success", f"Schedule generated with {len(self.selected_courses)} courses!")
    
    def export_pairs(self):
        """Export course pairs to JSON"""
        if not self.course_pairs:
            messagebox.showwarning("Warning", "No course pairs to export!")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Course Pairs",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.course_pairs, f, indent=2)
                messagebox.showinfo("Success", f"Course pairs exported to: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def export_predictions(self):
        """Export section predictions to JSON"""
        if not self.correct_pairings:
            messagebox.showwarning("Warning", "No predictions to export!")
            return
        
        export_data = {
            "correct_pairings": self.correct_pairings,
            "incorrect_pairings": self.incorrect_pairings
        }
        
        file_path = filedialog.asksaveasfilename(
            title="Save Section Predictions",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)
                messagebox.showinfo("Success", f"Predictions exported to: {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def view_summary(self):
        """View complete pipeline summary"""
        summary = "📊 PIPELINE SUMMARY REPORT\n" + "="*60 + "\n\n"
        
        if self.courses_df is not None:
            summary += f"📁 Data Source: {len(self.courses_df)} course records loaded\n"
            summary += f"🎓 Unique Courses: {len(self.courses_df['Course Code'].unique())}\n\n"
        
        if self.course_pairs:
            summary += f"🔗 Course Pairs Created: {len(self.course_pairs)//2}\n"
            summary += "   Paired Courses:\n"
            shown_pairs = set()
            for course1, course2 in self.course_pairs.items():
                pair = tuple(sorted([course1, course2]))
                if pair not in shown_pairs:
                    summary += f"   • {course1} ↔ {course2}\n"
                    shown_pairs.add(pair)
            summary += "\n"
        
        if self.correct_pairings:
            total_predictions = sum(len(pairs) for pairs in self.correct_pairings.values())
            summary += f"🎯 Section Predictions: {total_predictions}\n"
            summary += f"📋 Predicted Pairs: {len(self.correct_pairings)}\n\n"
        
        if self.selected_courses:
            summary += f"✅ Selected Courses: {len(self.selected_courses)}\n"
            for course in sorted(self.selected_courses.keys()):
                summary += f"   • {course}\n"
        
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, summary)
    
    def log_status(self, message):
        """Log a message to the status display"""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.root.update()
    
    # Algorithm methods from Step 1
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
        """Apply course pairs to the dictionary"""
        for course1, course2 in pairs:
            if course1 not in self.course_pairs and course2 not in self.course_pairs:
                self.course_pairs[course1] = course2
                self.course_pairs[course2] = course1
    
    # Algorithm methods from Step 2
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
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = CourseSchedulerMockup()
    app.run()
