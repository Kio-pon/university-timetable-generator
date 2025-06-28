"""
AI PREFERENCES DEVELOPMENT
==========================

This file represents the AI-powered timetable generation development.
It includes preference-based scoring and intelligent combination ranking.
Features developed:
- Preference-based scoring system
- Early morning class detection
- Late evening class detection
- Lunch break conflict checking
- Day distribution optimization

This was part of the intelligent scheduling evolution.
"""

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

class AITimetableGenerator:
    def __init__(self):
        self.preferences = {}
        self.learning_data = {}
        
    def generate_ai_timetable(self, combinations, user_preferences):
        """Generate AI-optimized timetable based on preferences"""
        print("🤖 Starting AI timetable generation...")
        
        # Apply AI scoring
        scored_combinations = score_combinations_by_preferences(combinations, user_preferences)
        
        # Return top combinations
        top_combinations = scored_combinations[:min(10, len(scored_combinations))]
        
        print(f"🎯 Generated {len(top_combinations)} AI-optimized combinations")
        return top_combinations
    
    def learn_from_user_feedback(self, combination_id, user_rating):
        """Learn from user feedback to improve future recommendations"""
        # AI learning implementation
        if combination_id not in self.learning_data:
            self.learning_data[combination_id] = []
        
        self.learning_data[combination_id].append({
            'rating': user_rating,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"📚 Learning from feedback: Combination {combination_id} rated {user_rating}")

if __name__ == "__main__":
    print("AI PREFERENCES DEVELOPMENT")
    print("This enabled intelligent timetable generation with user preferences!")
    print("Features: Smart scoring, preference learning, optimization algorithms")
