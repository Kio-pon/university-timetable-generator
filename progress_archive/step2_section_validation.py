import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import json
import os
from itertools import product

class SectionPairingStep2:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Step 2: Section Pairing Validator")
        self.root.geometry("1400x900")
        
        # Data storage
        self.courses_df = None
        self.course_pairs = {}
        self.section_combinations = {}
        self.correct_pairings = {}
        self.incorrect_pairings = {}
        
        # File paths
        self.course_pairs_file = "course_pairs_step1.json"
        self.correct_pairings_file = "correct_section_pairings.json"
        self.incorrect_pairings_file = "incorrect_section_pairings.json"
        
        # Current selection
        self.current_course_pair = None
        self.current_combinations = []
        
        self.setup_ui()
        self.load_data()
        
        # Bind global keyboard shortcut for next course
        self.root.bind('<Control-n>', lambda e: self.go_to_next_course())
        self.root.bind('<Control-N>', lambda e: self.go_to_next_course())
    
    def setup_ui(self):
        """Create the main UI"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Load Data
        self.load_tab = ttk.Frame(notebook)
        notebook.add(self.load_tab, text="📁 Load Data")
        self.setup_load_tab()
        
        # Tab 2: Validate Sections
        self.validate_tab = ttk.Frame(notebook)
        notebook.add(self.validate_tab, text="✅ Validate Sections")
        self.setup_validate_tab()
        
        # Tab 3: View Results
        self.results_tab = ttk.Frame(notebook)
        notebook.add(self.results_tab, text="📊 View Results")
        self.setup_results_tab()
    
    def setup_load_tab(self):
        """Setup the data loading tab"""
        frame = ttk.Frame(self.load_tab)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Step 2: Section Pairing Validator", 
                 font=('Arial', 18, 'bold')).pack(pady=10)
        
        # Load course pairs
        pairs_frame = ttk.LabelFrame(frame, text="Load Course Pairs", padding=15)
        pairs_frame.pack(fill='x', pady=10)
        
        pairs_load_frame = ttk.Frame(pairs_frame)
        pairs_load_frame.pack(fill='x')
        
        ttk.Button(pairs_load_frame, text="📁 Browse Course Pairs JSON", 
                  command=self.load_course_pairs_file).pack(side='left', padx=10)
        
        self.pairs_file_label = ttk.Label(pairs_load_frame, text="No file loaded", 
                                         foreground='red')
        self.pairs_file_label.pack(side='left', padx=10)
        
        # Load CSV
        csv_frame = ttk.LabelFrame(frame, text="Load Course CSV", padding=15)
        csv_frame.pack(fill='x', pady=10)
        
        csv_load_frame = ttk.Frame(csv_frame)
        csv_load_frame.pack(fill='x')
        
        ttk.Button(csv_load_frame, text="📁 Browse Course CSV", 
                  command=self.load_csv_file).pack(side='left', padx=10)
        
        self.csv_file_label = ttk.Label(csv_load_frame, text="No file loaded", 
                                       foreground='red')
        self.csv_file_label.pack(side='left', padx=10)
        
        # Generate combinations button
        ttk.Button(frame, text="🔄 Generate Section Combinations", 
                  command=self.generate_combinations).pack(pady=20)
        
        # Auto-predict button
        ttk.Button(frame, text="🤖 Auto-Predict Correct Pairings", 
                  command=self.auto_predict_pairings).pack(pady=10)
        
        # Status display
        self.status_frame = ttk.LabelFrame(frame, text="Status", padding=15)
        self.status_frame.pack(fill='both', expand=True, pady=10)
        
        self.status_text = scrolledtext.ScrolledText(self.status_frame, height=10, wrap='word')
        self.status_text.pack(fill='both', expand=True)
    
    def setup_validate_tab(self):
        """Setup the validation tab"""
        # Main container
        main_frame = ttk.Frame(self.validate_tab)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Top frame - Course pair selection
        top_frame = ttk.LabelFrame(main_frame, text="Select Course Pair to Validate", padding=10)
        top_frame.pack(fill='x', pady=(0, 10))
        
        # Course pair selector
        selector_frame = ttk.Frame(top_frame)
        selector_frame.pack(fill='x')
        
        ttk.Label(selector_frame, text="Course Pair:").pack(side='left', padx=(0, 10))
        
        self.course_pair_var = tk.StringVar()
        self.course_pair_combo = ttk.Combobox(selector_frame, textvariable=self.course_pair_var, 
                                             width=50, state='readonly')
        self.course_pair_combo.pack(side='left', padx=(0, 10))
        self.course_pair_combo.bind('<<ComboboxSelected>>', self.on_course_pair_selected)
        
        ttk.Button(selector_frame, text="🔄 Refresh", 
                  command=self.refresh_course_pairs).pack(side='left', padx=10)
        
        ttk.Button(selector_frame, text="➡️ Next Course (Ctrl+N)", 
                  command=self.go_to_next_course).pack(side='left', padx=10)
        
        # Keyboard shortcuts info
        info_frame = ttk.Frame(top_frame)
        info_frame.pack(fill='x', pady=(10, 0))
        
        ttk.Label(info_frame, text="⌨️ Keyboard Shortcuts: T = Mark Incorrect | Y = Mark Correct | R = Move to Pending | Ctrl+N = Next Course", 
                 font=('Arial', 9), foreground='blue').pack()
        
        # Middle frame - Three columns
        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill='both', expand=True)
        
        # Left column - Pending combinations
        left_frame = ttk.LabelFrame(middle_frame, text="Pending Section Combinations", padding=10)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        self.pending_listbox = tk.Listbox(left_frame, height=20)
        pending_scrollbar = ttk.Scrollbar(left_frame, orient='vertical', command=self.pending_listbox.yview)
        self.pending_listbox.configure(yscrollcommand=pending_scrollbar.set)
        
        self.pending_listbox.pack(side='left', fill='both', expand=True)
        pending_scrollbar.pack(side='right', fill='y')
        
        # Bind keyboard shortcuts for pending listbox
        self.pending_listbox.bind('<KeyPress-t>', lambda e: self.mark_as_incorrect())
        self.pending_listbox.bind('<KeyPress-T>', lambda e: self.mark_as_incorrect())
        self.pending_listbox.bind('<KeyPress-y>', lambda e: self.mark_as_correct())
        self.pending_listbox.bind('<KeyPress-Y>', lambda e: self.mark_as_correct())
        
        # Also bind mouse click to set focus
        self.pending_listbox.bind('<Button-1>', lambda e: self.pending_listbox.focus_set())
        
        # Middle column - Action buttons
        button_frame = ttk.Frame(middle_frame)
        button_frame.pack(side='left', fill='y', padx=10)
        
        ttk.Label(button_frame, text="Move Selected:", font=('Arial', 10, 'bold')).pack(pady=(50, 10))
        
        ttk.Button(button_frame, text="✅ Mark as\nCORRECT (Y)", 
                  command=self.mark_as_correct).pack(pady=5, fill='x')
        
        ttk.Button(button_frame, text="❌ Mark as\nINCORRECT (T)", 
                  command=self.mark_as_incorrect).pack(pady=5, fill='x')
        
        ttk.Label(button_frame, text="Move Back:", font=('Arial', 10, 'bold')).pack(pady=(30, 10))
        
        ttk.Button(button_frame, text="↩️ Move from\nCORRECT (R)", 
                  command=self.move_from_correct).pack(pady=5, fill='x')
        
        ttk.Button(button_frame, text="↩️ Move from\nINCORRECT (R)", 
                  command=self.move_from_incorrect).pack(pady=5, fill='x')
        
        ttk.Button(button_frame, text="💾 Save All", 
                  command=self.save_all_validations).pack(pady=(30, 5), fill='x')
        
        # Right side - two columns for correct/incorrect
        right_frame = ttk.Frame(middle_frame)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        # Correct column
        correct_frame = ttk.LabelFrame(right_frame, text="✅ CORRECT Pairings", padding=10)
        correct_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        self.correct_listbox = tk.Listbox(correct_frame, height=20, bg='#e8f5e8')
        correct_scrollbar = ttk.Scrollbar(correct_frame, orient='vertical', command=self.correct_listbox.yview)
        self.correct_listbox.configure(yscrollcommand=correct_scrollbar.set)
        
        self.correct_listbox.pack(side='left', fill='both', expand=True)
        correct_scrollbar.pack(side='right', fill='y')
        
        # Bind keyboard shortcuts for correct listbox
        self.correct_listbox.bind('<KeyPress-r>', lambda e: self.move_from_correct())
        self.correct_listbox.bind('<KeyPress-R>', lambda e: self.move_from_correct())
        self.correct_listbox.bind('<KeyPress-t>', lambda e: self.move_correct_to_incorrect())
        self.correct_listbox.bind('<KeyPress-T>', lambda e: self.move_correct_to_incorrect())
        
        # Also bind mouse click to set focus
        self.correct_listbox.bind('<Button-1>', lambda e: self.correct_listbox.focus_set())
        
        # Incorrect column
        incorrect_frame = ttk.LabelFrame(right_frame, text="❌ INCORRECT Pairings", padding=10)
        incorrect_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        self.incorrect_listbox = tk.Listbox(incorrect_frame, height=20, bg='#ffe8e8')
        incorrect_scrollbar = ttk.Scrollbar(incorrect_frame, orient='vertical', command=self.incorrect_listbox.yview)
        self.incorrect_listbox.configure(yscrollcommand=incorrect_scrollbar.set)
        
        self.incorrect_listbox.pack(side='left', fill='both', expand=True)
        incorrect_scrollbar.pack(side='right', fill='y')
        
        # Bind keyboard shortcuts for incorrect listbox
        self.incorrect_listbox.bind('<KeyPress-r>', lambda e: self.move_from_incorrect())
        self.incorrect_listbox.bind('<KeyPress-R>', lambda e: self.move_from_incorrect())
        self.incorrect_listbox.bind('<KeyPress-y>', lambda e: self.move_incorrect_to_correct())
        self.incorrect_listbox.bind('<KeyPress-Y>', lambda e: self.move_incorrect_to_correct())
        
        # Also bind mouse click to set focus
        self.incorrect_listbox.bind('<Button-1>', lambda e: self.incorrect_listbox.focus_set())
        
        # Bottom frame - Statistics
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding=10)
        stats_frame.pack(fill='x', pady=(10, 0))
        
        self.stats_label = ttk.Label(stats_frame, text="No data loaded", font=('Arial', 10))
        self.stats_label.pack()
    
    def setup_results_tab(self):
        """Setup the results viewing tab"""
        frame = ttk.Frame(self.results_tab)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Validation Results Summary", 
                 font=('Arial', 16, 'bold')).pack(pady=10)
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill='x', pady=10)
        
        ttk.Button(button_frame, text="🔄 Refresh Results", 
                  command=self.refresh_results).pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="📤 Export Results", 
                  command=self.export_results).pack(side='left', padx=5)
        
        ttk.Button(button_frame, text="🗑️ Clear All Data", 
                  command=self.clear_all_data).pack(side='left', padx=5)
        
        # Results display
        self.results_text = scrolledtext.ScrolledText(frame, height=25, wrap='word')
        self.results_text.pack(fill='both', expand=True, pady=10)
    
    def load_data(self):
        """Load existing data files"""
        # Try to load course pairs
        try:
            if os.path.exists(self.course_pairs_file):
                with open(self.course_pairs_file, 'r', encoding='utf-8') as f:
                    self.course_pairs = json.load(f)
                self.pairs_file_label.config(text=f"✅ Loaded: {self.course_pairs_file}", 
                                           foreground='green')
        except Exception as e:
            print(f"Could not load course pairs: {e}")
        
        # Try to load validation data
        try:
            if os.path.exists(self.correct_pairings_file):
                with open(self.correct_pairings_file, 'r', encoding='utf-8') as f:
                    self.correct_pairings = json.load(f)
        except:
            self.correct_pairings = {}
        
        try:
            if os.path.exists(self.incorrect_pairings_file):
                with open(self.incorrect_pairings_file, 'r', encoding='utf-8') as f:
                    self.incorrect_pairings = json.load(f)
        except:
            self.incorrect_pairings = {}
        
        self.update_status()
    
    def load_course_pairs_file(self):
        """Load course pairs JSON file"""
        file_path = filedialog.askopenfilename(
            title="Select Course Pairs JSON file",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.course_pairs = json.load(f)
                
                self.pairs_file_label.config(text=f"✅ Loaded: {os.path.basename(file_path)}", 
                                           foreground='green')
                self.update_status()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load course pairs: {str(e)}")
    
    def load_csv_file(self):
        """Load course CSV file"""
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
                
                self.csv_file_label.config(text=f"✅ Loaded: {os.path.basename(file_path)}", 
                                         foreground='green')
                self.update_status()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load CSV: {str(e)}")
    
    def generate_combinations(self):
        """Generate all section combinations for paired courses"""
        if not self.course_pairs or self.courses_df is None:
            messagebox.showerror("Error", "Please load both course pairs and CSV files first!")
            return
        
        self.section_combinations = {}
        
        # Get unique course pairs (avoid duplicates like A->B and B->A)
        unique_pairs = set()
        for course1, course2 in self.course_pairs.items():
            pair = tuple(sorted([course1, course2]))
            unique_pairs.add(pair)
        
        total_combinations = 0
        
        for course1, course2 in unique_pairs:
            # Get sections for each course
            course1_sections = self.courses_df[self.courses_df['Course Code'] == course1]['Section'].unique()
            course2_sections = self.courses_df[self.courses_df['Course Code'] == course2]['Section'].unique()
            
            # Generate all combinations
            combinations = []
            for section1 in course1_sections:
                for section2 in course2_sections:
                    combinations.append((f"{course1} {section1}", f"{course2} {section2}"))
            
            pair_key = f"{course1} ↔ {course2}"
            self.section_combinations[pair_key] = combinations
            total_combinations += len(combinations)
        
        # Mark all as correct by default (as you requested)
        for pair_key, combinations in self.section_combinations.items():
            if pair_key not in self.correct_pairings:
                self.correct_pairings[pair_key] = []
            
            for combo in combinations:
                combo_str = f"{combo[0]} ↔ {combo[1]}"
                if combo_str not in self.correct_pairings[pair_key]:
                    self.correct_pairings[pair_key].append(combo_str)
        
        # Initialize incorrect pairings if not exists
        for pair_key in self.section_combinations.keys():
            if pair_key not in self.incorrect_pairings:
                self.incorrect_pairings[pair_key] = []
        
        messagebox.showinfo("Success", 
                          f"Generated {total_combinations} section combinations for {len(unique_pairs)} course pairs!\n\n" +
                          "All combinations have been marked as CORRECT by default.\n" +
                          "You can now move incorrect ones to the INCORRECT list.")
        
        self.refresh_course_pairs()
        self.update_status()
    
    def refresh_course_pairs(self):
        """Refresh the course pair dropdown"""
        if self.section_combinations:
            pairs = sorted(list(self.section_combinations.keys()))  # Sort in ascending order
            self.course_pair_combo['values'] = pairs
            if pairs:
                # If no current selection, select first one
                current_selection = self.course_pair_var.get()
                if not current_selection or current_selection not in pairs:
                    self.course_pair_var.set(pairs[0])
                    self.on_course_pair_selected(None)
    
    def on_course_pair_selected(self, event):
        """Handle course pair selection"""
        selected_pair = self.course_pair_var.get()
        if not selected_pair or selected_pair not in self.section_combinations:
            return
        
        self.current_course_pair = selected_pair
        self.current_combinations = self.section_combinations[selected_pair]
        
        # Clear all listboxes
        self.pending_listbox.delete(0, tk.END)
        self.correct_listbox.delete(0, tk.END)
        self.incorrect_listbox.delete(0, tk.END)
        
        # Populate correct listbox
        if selected_pair in self.correct_pairings:
            for combo in self.correct_pairings[selected_pair]:
                self.correct_listbox.insert(tk.END, combo)
        
        # Populate incorrect listbox
        if selected_pair in self.incorrect_pairings:
            for combo in self.incorrect_pairings[selected_pair]:
                self.incorrect_listbox.insert(tk.END, combo)
        
        # Set focus to correct listbox since that's where most items will be
        self.correct_listbox.focus_set()
        
        self.update_stats()
    
    def mark_as_correct(self):
        """Move selected item from pending to correct"""
        selection = self.pending_listbox.curselection()
        if not selection or not self.current_course_pair:
            messagebox.showwarning("Warning", "Please select an item from the pending list")
            return
        
        item = self.pending_listbox.get(selection[0])
        
        # Add to correct
        if self.current_course_pair not in self.correct_pairings:
            self.correct_pairings[self.current_course_pair] = []
        
        if item not in self.correct_pairings[self.current_course_pair]:
            self.correct_pairings[self.current_course_pair].append(item)
            self.correct_listbox.insert(tk.END, item)
        
        # Remove from pending
        self.pending_listbox.delete(selection[0])
        self.update_stats()
    
    def mark_as_incorrect(self):
        """Move selected item from pending to incorrect"""
        selection = self.pending_listbox.curselection()
        if not selection or not self.current_course_pair:
            messagebox.showwarning("Warning", "Please select an item from the pending list")
            return
        
        item = self.pending_listbox.get(selection[0])
        
        # Add to incorrect
        if self.current_course_pair not in self.incorrect_pairings:
            self.incorrect_pairings[self.current_course_pair] = []
        
        if item not in self.incorrect_pairings[self.current_course_pair]:
            self.incorrect_pairings[self.current_course_pair].append(item)
            self.incorrect_listbox.insert(tk.END, item)
        
        # Remove from pending
        self.pending_listbox.delete(selection[0])
        self.update_stats()
    
    def move_from_correct(self):
        """Move selected item from correct back to pending"""
        selection = self.correct_listbox.curselection()
        if not selection or not self.current_course_pair:
            messagebox.showwarning("Warning", "Please select an item from the correct list")
            return
        
        item = self.correct_listbox.get(selection[0])
        
        # Remove from correct
        if (self.current_course_pair in self.correct_pairings and 
            item in self.correct_pairings[self.current_course_pair]):
            self.correct_pairings[self.current_course_pair].remove(item)
            self.correct_listbox.delete(selection[0])
        
        # Add to pending
        self.pending_listbox.insert(tk.END, item)
        self.update_stats()
    
    def move_from_incorrect(self):
        """Move selected item from incorrect back to pending"""
        selection = self.incorrect_listbox.curselection()
        if not selection or not self.current_course_pair:
            messagebox.showwarning("Warning", "Please select an item from the incorrect list")
            return
        
        item = self.incorrect_listbox.get(selection[0])
        
        # Remove from incorrect
        if (self.current_course_pair in self.incorrect_pairings and 
            item in self.incorrect_pairings[self.current_course_pair]):
            self.incorrect_pairings[self.current_course_pair].remove(item)
            self.incorrect_listbox.delete(selection[0])
        
        # Add to pending
        self.pending_listbox.insert(tk.END, item)
        self.update_stats()
    
    def move_correct_to_incorrect(self):
        """Move selected item from correct directly to incorrect"""
        selection = self.correct_listbox.curselection()
        if not selection or not self.current_course_pair:
            return
        
        item = self.correct_listbox.get(selection[0])
        
        # Remove from correct
        if (self.current_course_pair in self.correct_pairings and 
            item in self.correct_pairings[self.current_course_pair]):
            self.correct_pairings[self.current_course_pair].remove(item)
            self.correct_listbox.delete(selection[0])
        
        # Add to incorrect
        if self.current_course_pair not in self.incorrect_pairings:
            self.incorrect_pairings[self.current_course_pair] = []
        
        if item not in self.incorrect_pairings[self.current_course_pair]:
            self.incorrect_pairings[self.current_course_pair].append(item)
            self.incorrect_listbox.insert(tk.END, item)
        
        self.update_stats()
    
    def move_incorrect_to_correct(self):
        """Move selected item from incorrect directly to correct"""
        selection = self.incorrect_listbox.curselection()
        if not selection or not self.current_course_pair:
            return
        
        item = self.incorrect_listbox.get(selection[0])
        
        # Remove from incorrect
        if (self.current_course_pair in self.incorrect_pairings and 
            item in self.incorrect_pairings[self.current_course_pair]):
            self.incorrect_pairings[self.current_course_pair].remove(item)
            self.incorrect_listbox.delete(selection[0])
        
        # Add to correct
        if self.current_course_pair not in self.correct_pairings:
            self.correct_pairings[self.current_course_pair] = []
        
        if item not in self.correct_pairings[self.current_course_pair]:
            self.correct_pairings[self.current_course_pair].append(item)
            self.correct_listbox.insert(tk.END, item)
        
        self.update_stats()

    def save_all_validations(self):
        """Save all validation data"""
        try:
            # Save correct pairings
            with open(self.correct_pairings_file, 'w', encoding='utf-8') as f:
                json.dump(self.correct_pairings, f, indent=2, ensure_ascii=False)
            
            # Save incorrect pairings
            with open(self.incorrect_pairings_file, 'w', encoding='utf-8') as f:
                json.dump(self.incorrect_pairings, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Success", "All validation data saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save validation data: {str(e)}")
    
    def update_stats(self):
        """Update statistics display"""
        if not self.current_course_pair:
            self.stats_label.config(text="No course pair selected")
            return
        
        correct_count = len(self.correct_pairings.get(self.current_course_pair, []))
        incorrect_count = len(self.incorrect_pairings.get(self.current_course_pair, []))
        pending_count = self.pending_listbox.size()
        total_count = correct_count + incorrect_count + pending_count
        
        stats_text = f"📊 {self.current_course_pair}: "
        stats_text += f"✅ {correct_count} Correct | "
        stats_text += f"❌ {incorrect_count} Incorrect | "
        stats_text += f"⏳ {pending_count} Pending | "
        stats_text += f"📈 Total: {total_count}"
        
        self.stats_label.config(text=stats_text)
    
    def update_status(self):
        """Update status display"""
        self.status_text.delete(1.0, tk.END)
        
        status = "📊 STEP 2 STATUS REPORT\n"
        status += "=" * 50 + "\n\n"
        
        # Course pairs status
        unique_pairs = len(set(tuple(sorted([k, v])) for k, v in self.course_pairs.items())) if self.course_pairs else 0
        status += f"🎓 Loaded Course Pairs: {unique_pairs}\n"
        
        # CSV status
        if self.courses_df is not None:
            status += f"📄 CSV Records: {len(self.courses_df)}\n"
            status += f"🎯 Unique Courses: {len(self.courses_df['Course Code'].unique())}\n"
        else:
            status += f"📄 CSV: Not loaded\n"
        
        # Combinations status
        if self.section_combinations:
            total_combos = sum(len(combos) for combos in self.section_combinations.values())
            status += f"🔗 Total Section Combinations: {total_combos}\n\n"
            
            # Validation status
            total_correct = sum(len(pairs) for pairs in self.correct_pairings.values())
            total_incorrect = sum(len(pairs) for pairs in self.incorrect_pairings.values())
            
            status += f"✅ Validated as CORRECT: {total_correct}\n"
            status += f"❌ Validated as INCORRECT: {total_incorrect}\n"
            status += f"⏳ Remaining to validate: {total_combos - total_correct - total_incorrect}\n\n"
            
            if total_combos > 0:
                progress = ((total_correct + total_incorrect) / total_combos) * 100
                status += f"📈 Validation Progress: {progress:.1f}%\n"
        else:
            status += f"🔗 Section Combinations: Not generated\n"
        
        self.status_text.insert(tk.END, status)
    
    def refresh_results(self):
        """Refresh results display"""
        self.results_text.delete(1.0, tk.END)
        
        results = "📊 VALIDATION RESULTS SUMMARY\n"
        results += "=" * 60 + "\n\n"
        
        if not self.section_combinations:
            results += "No data available. Please generate combinations first."
            self.results_text.insert(tk.END, results)
            return
        
        for pair_key in self.section_combinations.keys():
            results += f"🎓 {pair_key}\n"
            results += "-" * 40 + "\n"
            
            correct_count = len(self.correct_pairings.get(pair_key, []))
            incorrect_count = len(self.incorrect_pairings.get(pair_key, []))
            total_count = len(self.section_combinations[pair_key])
            
            results += f"✅ Correct: {correct_count}\n"
            results += f"❌ Incorrect: {incorrect_count}\n"
            results += f"📊 Total: {total_count}\n"
            
            if total_count > 0:
                accuracy = (correct_count / total_count) * 100
                results += f"🎯 Accuracy: {accuracy:.1f}%\n"
            
            results += "\n"
        
        self.results_text.insert(tk.END, results)
    
    def export_results(self):
        """Export results to a summary file"""
        if not self.section_combinations:
            messagebox.showwarning("Warning", "No data to export")
            return
        
        try:
            export_data = {
                "summary": {
                    "total_course_pairs": len(self.section_combinations),
                    "total_combinations": sum(len(combos) for combos in self.section_combinations.values()),
                    "total_correct": sum(len(pairs) for pairs in self.correct_pairings.values()),
                    "total_incorrect": sum(len(pairs) for pairs in self.incorrect_pairings.values())
                },
                "correct_pairings": self.correct_pairings,
                "incorrect_pairings": self.incorrect_pairings,
                "section_combinations": self.section_combinations
            }
            
            file_path = filedialog.asksaveasfilename(
                title="Export Results",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Success", f"Results exported to: {file_path}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {str(e)}")
    
    def clear_all_data(self):
        """Clear all validation data"""
        result = messagebox.askyesno("Confirm", 
                                   "This will clear ALL validation data!\n\n" +
                                   "Are you sure you want to continue?")
        if result:
            self.correct_pairings = {}
            self.incorrect_pairings = {}
            self.section_combinations = {}
            
            # Clear listboxes
            self.pending_listbox.delete(0, tk.END)
            self.correct_listbox.delete(0, tk.END)
            self.incorrect_listbox.delete(0, tk.END)
            
            self.update_status()
            self.update_stats()
            
            messagebox.showinfo("Success", "All data cleared!")
    
    def go_to_next_course(self):
        """Go to the next course pair in the dropdown"""
        if not self.section_combinations:
            messagebox.showwarning("Warning", "No course pairs available")
            return
        
        pairs = sorted(list(self.section_combinations.keys()))
        current_selection = self.course_pair_var.get()
        
        if not current_selection:
            # If no selection, go to first one
            if pairs:
                self.course_pair_var.set(pairs[0])
                self.on_course_pair_selected(None)
            return
        
        try:
            current_index = pairs.index(current_selection)
            next_index = (current_index + 1) % len(pairs)  # Wrap around to beginning if at end
            
            next_course = pairs[next_index]
            self.course_pair_var.set(next_course)
            self.on_course_pair_selected(None)
            
            # Show a brief message if we wrapped around
            if next_index == 0 and current_index == len(pairs) - 1:
                messagebox.showinfo("Info", "Reached end of list. Starting from the beginning.")
                
        except ValueError:
            # Current selection not in list, go to first one
            if pairs:
                self.course_pair_var.set(pairs[0])
                self.on_course_pair_selected(None)

    def run(self):
        """Start the application"""
        self.root.mainloop()

    def auto_predict_pairings(self):
        """Automatically predict correct pairings using the unified algorithm"""
        if not self.section_combinations:
            messagebox.showerror("Error", "Please generate section combinations first!")
            return
        
        # Ask for confirmation
        result = messagebox.askyesno("Auto-Prediction", 
                                   "This will automatically predict correct section pairings using the learned algorithm.\n\n" +
                                   "Algorithm Rules:\n" +
                                   "• If one course has 1 section → pairs with ALL sections of other course\n" +
                                   "• If both courses have equal sections → sequential matching (L1↔T1, L2↔T2...)\n\n" +
                                   "Continue?")
        if not result:
            return
        
        # Clear current pairings to start fresh
        self.correct_pairings = {}
        self.incorrect_pairings = {}
        
        total_predictions = 0
        successful_predictions = 0
        algorithm_results = []
        
        for pair_key in self.section_combinations.keys():
            # Parse the course pair
            course1_name, course2_name = pair_key.split(' ↔ ')
            
            # Get sections for each course
            course1_sections = []
            course2_sections = []
            
            for combo in self.section_combinations[pair_key]:
                section1, section2 = combo
                # Extract section from "Course Section" format
                course1_section = section1.split()[-1]  # Get last part (section)
                course2_section = section2.split()[-1]  # Get last part (section)
                
                if course1_section not in course1_sections:
                    course1_sections.append(course1_section)
                if course2_section not in course2_sections:
                    course2_sections.append(course2_section)
            
            # Sort sections for consistent ordering
            course1_sections.sort()
            course2_sections.sort()
            
            # Apply the unified algorithm
            predicted_pairs = self.predict_section_pairings(
                course1_name, course1_sections, 
                course2_name, course2_sections
            )
            
            if predicted_pairs:
                # Initialize lists
                if pair_key not in self.correct_pairings:
                    self.correct_pairings[pair_key] = []
                if pair_key not in self.incorrect_pairings:
                    self.incorrect_pairings[pair_key] = []
                
                # Mark predicted pairs as correct
                for section1, section2 in predicted_pairs:
                    pairing_str = f"{course1_name} {section1} ↔ {course2_name} {section2}"
                    self.correct_pairings[pair_key].append(pairing_str)
                
                # Mark all other combinations as incorrect
                all_combinations = [f"{combo[0]} ↔ {combo[1]}" for combo in self.section_combinations[pair_key]]
                for combo_str in all_combinations:
                    if combo_str not in self.correct_pairings[pair_key]:
                        self.incorrect_pairings[pair_key].append(combo_str)
                
                # Determine which algorithm was used
                if len(course1_sections) == 1 or len(course2_sections) == 1:
                    algorithm_used = "One-to-Many"
                elif len(course1_sections) == len(course2_sections):
                    algorithm_used = "Sequential Matching"
                else:
                    algorithm_used = "Unknown Pattern"
                
                algorithm_results.append(f"• {pair_key}: {algorithm_used} ({len(predicted_pairs)} correct)")
                successful_predictions += 1
                total_predictions += len(predicted_pairs)
        
        # Show results
        if successful_predictions > 0:
            result_text = f"Auto-prediction completed!\n\n"
            result_text += f"📊 Results:\n"
            result_text += f"• {successful_predictions} course pairs processed\n"
            result_text += f"• {total_predictions} correct pairings predicted\n\n"
            result_text += "📋 Algorithm Breakdown:\n" + "\n".join(algorithm_results)
            
            messagebox.showinfo("Auto-Prediction Results", result_text)
            
            # Refresh current view if a course pair is selected
            if self.current_course_pair:
                self.on_course_pair_selected(None)
            
            self.update_status()
        else:
            messagebox.showinfo("Auto-Prediction Results", 
                              "No predictions could be made. Please check your data.")
    
    def predict_section_pairings(self, course1_name, course1_sections, course2_name, course2_sections):
        """
        Unified algorithm for predicting section pairings
        
        Rules:
        1. If one course has 1 section → pairs with all sections of other course  
        2. If both courses have equal sections → sequential matching
        """
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
    
    def extract_section_number(self, section_str):
        """Extract numeric part from section string (L1 → 1, T5 → 5, S12 → 12)"""
        import re
        match = re.search(r'\d+', section_str)
        return int(match.group()) if match else 0

if __name__ == "__main__":
    app = SectionPairingStep2()
    app.run()