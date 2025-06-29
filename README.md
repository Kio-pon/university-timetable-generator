# AI University Timetable Generator

A smart timetable generator with AI-powered course pairing and modern calendar visualization.

## Features

- 📚 **Smart Course Pairing**: Automatically pairs lectures with labs
- 🤖 **AI Conflict Detection**: Prevents time conflicts
- 📅 **Modern Calendar View**: Beautiful FullCalendar.js interface  
- 📊 **CSV Export**: Export timetables in clean format
- 📱 **Responsive Design**: Works on all devices
    

## Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Calendar**: FullCalendar.js
- **Data**: Pandas for CSV processing
- **Hosting**: Railway

## How to Use

1. **Upload CSV**: Upload your course data file
2. **Select Courses**: Choose courses and sections
3. **Generate**: Get conflict-free timetables
4. **Export**: Download as CSV

## Course Data Format

Your CSV should have these columns:
- Course Code
- Section  
- Title
- Day
- Start Time / Start
- End Time / End
- Instructor / Sponsor
- Room / Location

## Local Development

```bash
pip install -r requirements.txt
python web_scheduler.py

---

Made with ❤️ for students who want perfect schedules!
