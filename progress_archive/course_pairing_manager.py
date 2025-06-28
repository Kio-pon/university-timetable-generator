import csv
import json
import os
from typing import Dict, List, Tuple

class CoursePairingManager:
    def __init__(self, csv_file_path: str, pairings_file: str = "course_pairings.json"):
        self.csv_file_path = csv_file_path
        self.pairings_file = pairings_file
        self.courses = []
        self.pairings = {}
        
        # Load courses from CSV
        self.load_courses_from_csv()
        
        # Load existing pairings
        self.load_pairings()
    
    def load_courses_from_csv(self):
        """Load course data from CSV file"""
        try:
            with open(self.csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                self.courses = []
                for row in csv_reader:
                    course_info = {
                        'code': row['Course Code'],
                        'section': row['Section'],
                        'title': row['Title'],
                        'day': row['Day'],
                        'start': row['Start'],
                        'end': row['End'],
                        'room': row['Room'],
                        'instructor': row['Instructor / Sponsor']
                    }
                    self.courses.append(course_info)
            print(f"✅ Loaded {len(self.courses)} courses from CSV")
        except FileNotFoundError:
            print(f"❌ Error: CSV file '{self.csv_file_path}' not found!")
            self.courses = []
        except Exception as e:
            print(f"❌ Error loading CSV: {e}")
            self.courses = []
    
    def load_pairings(self):
        """Load existing course pairings from JSON file"""
        try:
            if os.path.exists(self.pairings_file):
                with open(self.pairings_file, 'r', encoding='utf-8') as file:
                    self.pairings = json.load(file)
                print(f"✅ Loaded {len(self.pairings)} existing pairings")
            else:
                self.pairings = {}
                print("📝 No existing pairings file found, starting fresh")
        except Exception as e:
            print(f"❌ Error loading pairings: {e}")
            self.pairings = {}
    
    def save_pairings(self):
        """Save course pairings to JSON file"""
        try:
            with open(self.pairings_file, 'w', encoding='utf-8') as file:
                json.dump(self.pairings, file, indent=2, ensure_ascii=False)
            print(f"✅ Pairings saved to {self.pairings_file}")
        except Exception as e:
            print(f"❌ Error saving pairings: {e}")
    
    def display_courses(self):
        """Display all available courses"""
        if not self.courses:
            print("❌ No courses available!")
            return
        
        print("\n📚 Available Courses:")
        print("-" * 80)
        for i, course in enumerate(self.courses, 1):
            print(f"{i:2d}. {course['code']} ({course['section']}) - {course['title']}")
            print(f"    📅 {course['day']} | 🕒 {course['start']} - {course['end']} | 🏫 {course['room']}")
            print(f"    👨‍🏫 {course['instructor']}")
            print()
    
    def get_course_display_name(self, course):
        """Get a display name for a course"""
        return f"{course['code']} ({course['section']}) - {course['title']}"
    
    def create_pairing(self):
        """Create a new course pairing"""
        if len(self.courses) < 2:
            print("❌ Need at least 2 courses to create pairings!")
            return
        
        self.display_courses()
        
        try:
            # Select first course
            course1_idx = int(input("Enter the number of the FIRST course to pair: ")) - 1
            if course1_idx < 0 or course1_idx >= len(self.courses):
                print("❌ Invalid course number!")
                return
            
            course1 = self.courses[course1_idx]
            course1_name = self.get_course_display_name(course1)
            
            print(f"\n✅ Selected: {course1_name}")
            print("\n📚 Select a course to pair with:")
            print("-" * 50)
            
            # Show available courses for pairing (excluding the selected one)
            available_courses = []
            for i, course in enumerate(self.courses):
                if i != course1_idx:
                    available_courses.append((len(available_courses) + 1, i, course))
                    print(f"{len(available_courses):2d}. {self.get_course_display_name(course)}")
            
            # Select second course
            pair_choice = int(input("\nEnter the number of the course to pair with: ")) - 1
            if pair_choice < 0 or pair_choice >= len(available_courses):
                print("❌ Invalid course number!")
                return
            
            course2_idx = available_courses[pair_choice][1]
            course2 = self.courses[course2_idx]
            course2_name = self.get_course_display_name(course2)
            
            # Create pairing
            pairing_key = f"{course1['code']}_{course1['section']}"
            paired_course = f"{course2['code']}_{course2['section']}"
            
            # Check if pairing already exists
            if pairing_key in self.pairings:
                print(f"⚠️  {course1_name} is already paired with {self.pairings[pairing_key]}")
                overwrite = input("Do you want to overwrite this pairing? (y/N): ").lower()
                if overwrite != 'y':
                    print("❌ Pairing cancelled")
                    return
            
            # Save pairing
            self.pairings[pairing_key] = paired_course
            
            # Also create reverse pairing for easy lookup
            reverse_key = f"{course2['code']}_{course2['section']}"
            self.pairings[reverse_key] = f"{course1['code']}_{course1['section']}"
            
            print(f"\n✅ Successfully paired:")
            print(f"   {course1_name} ↔ {course2_name}")
            
            self.save_pairings()
            
        except ValueError:
            print("❌ Please enter a valid number!")
        except Exception as e:
            print(f"❌ Error creating pairing: {e}")
    
    def view_pairings(self):
        """View all existing course pairings"""
        if not self.pairings:
            print("📝 No course pairings found!")
            return
        
        print("\n🔗 Course Pairings:")
        print("-" * 60)
        
        # Group pairings to avoid duplicates
        displayed_pairs = set()
        
        for course_key, paired_key in self.pairings.items():
            # Create a sorted tuple to avoid displaying the same pair twice
            pair_tuple = tuple(sorted([course_key, paired_key]))
            
            if pair_tuple not in displayed_pairs:
                displayed_pairs.add(pair_tuple)
                
                # Find course details
                course1_details = self.find_course_by_key(course_key)
                course2_details = self.find_course_by_key(paired_key)
                
                if course1_details and course2_details:
                    print(f"• {self.get_course_display_name(course1_details)}")
                    print(f"  ↔ {self.get_course_display_name(course2_details)}")
                    print()
    
    def find_course_by_key(self, course_key):
        """Find course details by course key (code_section)"""
        try:
            code, section = course_key.split('_')
            for course in self.courses:
                if course['code'] == code and course['section'] == section:
                    return course
        except:
            pass
        return None
    
    def delete_pairing(self):
        """Delete an existing course pairing"""
        if not self.pairings:
            print("📝 No course pairings to delete!")
            return
        
        self.view_pairings()
        
        print("\n🗑️  Delete a pairing:")
        course_code = input("Enter the course code (e.g., CORE 200): ").strip()
        section = input("Enter the section (e.g., L1): ").strip()
        
        course_key = f"{course_code}_{section}"
        
        if course_key in self.pairings:
            paired_key = self.pairings[course_key]
            
            # Remove both directions of the pairing
            del self.pairings[course_key]
            if paired_key in self.pairings:
                del self.pairings[paired_key]
            
            print(f"✅ Deleted pairing for {course_code} ({section})")
            self.save_pairings()
        else:
            print(f"❌ No pairing found for {course_code} ({section})")
    
    def run(self):
        """Main program loop"""
        print("🎓 Course Pairing Manager")
        print("=" * 50)
        
        while True:
            print("\n📋 Menu:")
            print("1. View all courses")
            print("2. Create new pairing")
            print("3. View existing pairings")
            print("4. Delete a pairing")
            print("5. Reload courses from CSV")
            print("6. Exit")
            
            try:
                choice = input("\nEnter your choice (1-6): ").strip()
                
                if choice == '1':
                    self.display_courses()
                elif choice == '2':
                    self.create_pairing()
                elif choice == '3':
                    self.view_pairings()
                elif choice == '4':
                    self.delete_pairing()
                elif choice == '5':
                    self.load_courses_from_csv()
                elif choice == '6':
                    print("👋 Goodbye!")
                    break
                else:
                    print("❌ Invalid choice! Please enter 1-6.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

def main():
    # Ask user for CSV file path
    print("🎓 Course Pairing Manager Setup")
    print("-" * 40)
    
    csv_file = input("Enter the path to your courses CSV file: ").strip()
    
    # Remove quotes if user included them
    csv_file = csv_file.strip('"\'')
    
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        print("Please make sure the file path is correct.")
        return
    
    # Create and run the manager
    manager = CoursePairingManager(csv_file)
    manager.run()

if __name__ == "__main__":
    main()
