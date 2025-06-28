"""
WEB API AND SERVER ROUTES
========================

This file contains all the FastAPI routes and web server functionality
for the University Timetable Generator.
"""

from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pandas as pd
import io
import csv
import os
import tempfile
from datetime import datetime

# Import our modular components
from timetable_generator import TimetableGenerator
from progress_archive.file_processor import (
    score_combinations_by_preferences, 
    generate_selected_sections_csv,
    check_early_morning_classes,
    check_late_evening_classes,
    count_long_gaps,
    count_unique_days,
    check_lunch_conflicts,
    get_combination_details
)

# FastAPI app setup
app = FastAPI(title="University Timetable Generator", version="2.0.0")

# Static files and templates (only mount if directories exist)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if os.path.exists("templates"):
    templates = Jinja2Templates(directory="templates")
else:
    # Create a minimal templates object for when templates directory doesn't exist
    class MinimalTemplates:
        def TemplateResponse(self, template_name, context):
            # Return a simple HTML response when templates don't exist
            return HTMLResponse(f"<h1>Template {template_name} not found</h1><p>Please create the templates directory.</p>")
    templates = MinimalTemplates()

# Global variables
current_generator = TimetableGenerator()
temp_data_file = None

# =================================================================
# MAIN ROUTES
# =================================================================

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Main page"""
    return templates.TemplateResponse("scheduler.html", {"request": request})

@app.get("/status")
async def get_status():
    """Check if data is loaded and get current state with smart features"""
    global current_generator
    status = {
        "data_loaded": current_generator.course_data is not None,
        "filename": current_generator.current_file_path,
        "total_courses": 0,
        "selected_courses": current_generator.selected_courses,
        "has_combinations": len(current_generator.valid_combinations) > 0,
        "smart_features": {
            "course_pairs_detected": len(current_generator.course_pairs) // 2,
            "section_predictions": sum(len(pairs) for pairs in current_generator.correct_pairings.values()),
            "auto_pairing_enabled": len(current_generator.course_pairs) > 0
        }
    }
    
    if current_generator.course_data is not None:
        status["total_courses"] = len(current_generator.course_data['Course Code'].unique())
    
    return status

# =================================================================
# FILE UPLOAD AND DATA MANAGEMENT
# =================================================================

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process CSV/Excel file"""
    global current_generator, temp_data_file
    
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Check file extension
    if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload a CSV or Excel file.")
    
    try:
        # Read file content
        content = await file.read()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp_file:
            tmp_file.write(content)
            temp_data_file = tmp_file.name
        
        # Load data using the generator
        success, message = current_generator.load_data(content, file.filename)
        
        if success:
            return {
                "success": True,
                "message": message,
                "filename": file.filename,
                "total_courses": len(current_generator.get_unique_courses()),
                "smart_features": {
                    "course_pairs_detected": len(current_generator.course_pairs) // 2,
                    "section_predictions": sum(len(pairs) for pairs in current_generator.correct_pairings.values())
                }
            }
        else:
            raise HTTPException(status_code=400, detail=message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/clear-data")
async def clear_all_data():
    """Clear all data"""
    global current_generator, temp_data_file
    
    # Clean up temporary file
    if temp_data_file and os.path.exists(temp_data_file):
        try:
            os.unlink(temp_data_file)
        except:
            pass
        temp_data_file = None
    
    current_generator.clear_data()
    return {"success": True, "message": "All data cleared"}

@app.post("/clear-roster")
async def clear_roster():
    """Clear selected courses roster"""
    global current_generator
    current_generator.clear_roster()
    return {"success": True, "message": "Course roster cleared"}

# =================================================================
# COURSE AND SECTION MANAGEMENT
# =================================================================

@app.get("/courses")
async def get_courses():
    """Get all available courses"""
    global current_generator
    
    if current_generator.course_data is None:
        raise HTTPException(status_code=400, detail="No course data loaded")
    
    courses = current_generator.get_courses_with_titles()
    return {"courses": courses}

@app.get("/courses/{course_code}/sections")
async def get_course_sections(course_code: str):
    """Get sections for a specific course"""
    global current_generator
    
    if current_generator.course_data is None:
        raise HTTPException(status_code=400, detail="No course data loaded")
    
    sections = current_generator.get_course_sections(course_code)
    return {"sections": sections}

@app.post("/select-sections")
async def select_sections(request: Request):
    """STEP 3: Smart auto-selection with paired course logic (handles selection AND deselection)"""
    global current_generator
    
    data = await request.json()
    course_code = data.get("course_code")
    selected_sections = data.get("selected_sections", [])
    
    if not course_code:
        raise HTTPException(status_code=400, detail="Course code is required")
    
    # Get previous selections to detect what changed
    previous_selections = current_generator.selected_courses.get(course_code, [])
    
    # Update the primary course selection
    current_generator.selected_courses[course_code] = selected_sections
    auto_paired = {}
    
    # Clean up empty selections
    if not selected_sections:
        if course_code in current_generator.selected_courses:
            del current_generator.selected_courses[course_code]
    
    # STEP 3: Smart auto-pairing logic
    if course_code in current_generator.course_pairs:
        paired_course = current_generator.course_pairs[course_code]
        
        if selected_sections:
            # Find compatible sections for the paired course
            compatible_sections = current_generator.find_compatible_sections(
                course_code, selected_sections, paired_course
            )
            
            if compatible_sections:
                # Auto-select compatible sections
                current_generator.selected_courses[paired_course] = compatible_sections
                auto_paired[paired_course] = compatible_sections
                print(f"🎯 Auto-paired {course_code} → {paired_course}: {compatible_sections}")
        else:
            # If source course is deselected, clear the paired course too
            if paired_course in current_generator.selected_courses:
                del current_generator.selected_courses[paired_course]
                auto_paired[paired_course] = []
                print(f"🧹 Auto-cleared {paired_course} (because {course_code} was deselected)")
    
    # Remove any courses with empty selections
    current_generator.selected_courses = {
        course: sections for course, sections in current_generator.selected_courses.items() 
        if sections  # Only keep non-empty selections
    }
    
    return {
        "success": True,
        "message": f"Updated sections for {course_code}",
        "selected_courses": current_generator.selected_courses,
        "auto_paired": auto_paired,
        "paired_course": current_generator.course_pairs.get(course_code, None)
    }

@app.get("/selected-courses")
async def get_selected_courses():
    """Get currently selected courses"""
    global current_generator
    return {"selected_courses": current_generator.selected_courses}

# =================================================================
# LEGACY SECTION PAIRING
# =================================================================

@app.post("/create-pair")
async def create_section_pair(request: Request):
    """Create a section pair"""
    global current_generator
    
    data = await request.json()
    course1 = data.get("course1")
    section1 = data.get("section1")
    course2 = data.get("course2")
    section2 = data.get("section2")
    
    if not all([course1, section1, course2, section2]):
        raise HTTPException(status_code=400, detail="All pair parameters are required")
    
    success, message = current_generator.create_section_pair(course1, section1, course2, section2)
    
    return {
        "success": success,
        "message": message
    }

@app.post("/remove-pair")
async def remove_section_pair(request: Request):
    """Remove a section pair"""
    global current_generator
    
    data = await request.json()
    course = data.get("course")
    section = data.get("section")
    
    if not all([course, section]):
        raise HTTPException(status_code=400, detail="Course and section are required")
    
    success, message = current_generator.remove_section_pair(course, section)
    
    return {
        "success": success,
        "message": message
    }

# =================================================================
# TIMETABLE GENERATION
# =================================================================

@app.post("/generate")
async def generate_timetables():
    """Generate all possible timetables"""
    global current_generator
    
    if not current_generator.selected_courses:
        raise HTTPException(status_code=400, detail="No courses selected")
    
    try:
        combinations = current_generator.generate_combinations()
        
        if combinations:
            return {
                "success": True,
                "message": f"Generated {len(combinations)} valid timetable combinations",
                "total_combinations": len(combinations),
                "combinations": [current_generator.format_combination(combo) for combo in combinations[:5]]  # Return first 5 for preview
            }
        else:
            return {
                "success": False,
                "message": "No valid timetables found with the selected courses. Try different section combinations.",
                "total_combinations": 0
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating timetables: {str(e)}")

# =================================================================
# AI PREFERENCES
# =================================================================

@app.get("/ai-preferences", response_class=HTMLResponse)
async def ai_preferences(request: Request):
    """AI Preferences page for intelligent timetable generation"""
    global current_generator
    
    # Check if data is loaded
    if current_generator.course_data is None:
        return templates.TemplateResponse("scheduler.html", {
            "request": request,
            "error": "No course data available. Please upload a file first."
        })
    
    # Check if courses are selected
    if not current_generator.selected_courses:
        return templates.TemplateResponse("scheduler.html", {
            "request": request,
            "error": "No courses selected. Please select courses first."
        })
    
    return templates.TemplateResponse("ai_preferences.html", {
        "request": request,
        "selected_courses": current_generator.selected_courses,
        "total_courses": len(current_generator.selected_courses)
    })

@app.post("/ai-preferences")
async def handle_ai_preferences(request: Request):
    """Handle AI timetable generation with preferences"""
    global current_generator
    
    if current_generator.course_data is None:
        raise HTTPException(status_code=400, detail="No course data available")
    
    if not current_generator.selected_courses:
        raise HTTPException(status_code=400, detail="No courses selected")
    
    try:
        # Get preferences from request body
        preferences = await request.json()
        
        # Generate combinations using current manual method
        combinations = current_generator.generate_combinations()
        
        if combinations:
            # Apply preference-based scoring/filtering
            scored_combinations = score_combinations_by_preferences(combinations, preferences)
            
            # Return top combinations based on preferences
            top_combinations = scored_combinations[:min(10, len(scored_combinations))]
            
            return {
                "success": True,
                "combinations": top_combinations,
                "total_generated": len(combinations),
                "preferences_applied": preferences,
                "message": f"Generated {len(top_combinations)} optimized timetable combinations based on your preferences"
            }
        else:
            return {
                "success": False,
                "error": "No valid combinations could be generated with your selected courses"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing AI preferences: {str(e)}")

# =================================================================
# EXPORT FUNCTIONALITY
# =================================================================

@app.get("/export/combinations")
async def get_combinations_export():
    """Get combinations export data for display"""
    global current_generator
    
    if not current_generator.valid_combinations:
        raise HTTPException(status_code=400, detail="No combinations generated yet. Please generate combinations first.")
    
    csv_content, summary = current_generator.generate_combinations_csv()
    stats = current_generator.get_combinations_stats()
    
    return {
        "csv_content": csv_content,
        "summary": summary,
        "stats": stats,
        "filename": f"timetable_combinations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    }

@app.get("/export/combinations/download")
async def download_combinations_csv():
    """Download combinations as CSV file"""
    global current_generator
    
    if not current_generator.valid_combinations:
        raise HTTPException(status_code=400, detail="No combinations generated yet")
    
    csv_content, _ = current_generator.generate_combinations_csv()
    filename = f"timetable_combinations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/export/combinations/preview", response_class=HTMLResponse)
async def preview_combinations_export(request: Request):
    """Preview combinations export in HTML format"""
    global current_generator
    
    if not current_generator.valid_combinations:
        return templates.TemplateResponse("export_preview.html", {
            "request": request,
            "error": "No combinations generated yet. Please generate combinations first."
        })
    
    csv_content, summary = current_generator.generate_combinations_csv()
    stats = current_generator.get_combinations_stats()
    
    # Convert CSV to HTML table for preview
    df = pd.read_csv(io.StringIO(csv_content))
    html_table = df.to_html(classes="table table-striped table-bordered", index=False)
    
    filename = f"timetable_combinations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return templates.TemplateResponse("export_preview.html", {
        "request": request,
        "csv_content": csv_content,
        "html_table": html_table,
        "summary": summary,
        "stats": stats,
        "filename": filename,
        "total_combinations": len(current_generator.valid_combinations)
    })

@app.get("/export/selected-sections/download")
async def download_selected_sections_csv():
    """Download selected sections as CSV file"""
    global current_generator
    
    if current_generator.course_data is None:
        raise HTTPException(status_code=400, detail="No course data available")
    
    if not current_generator.selected_courses:
        raise HTTPException(status_code=400, detail="No sections selected")
    
    # Create CSV content with only selected sections
    csv_content = generate_selected_sections_csv(current_generator.course_data, current_generator.selected_courses)
    filename = f"selected_sections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/export/selected-sections/preview", response_class=HTMLResponse)
async def preview_selected_sections_export(request: Request):
    """Preview selected sections export in HTML format"""
    global current_generator
    
    if current_generator.course_data is None:
        return templates.TemplateResponse("export_preview.html", {
            "request": request,
            "error": "No course data available. Please upload a file first."
        })
    
    if not current_generator.selected_courses:
        return templates.TemplateResponse("export_preview.html", {
            "request": request,
            "error": "No sections selected. Please select some course sections first."
        })
    
    csv_content = generate_selected_sections_csv(current_generator.course_data, current_generator.selected_courses)
    
    # Convert CSV to HTML table for preview
    df = pd.read_csv(io.StringIO(csv_content))
    html_table = df.to_html(classes="table table-striped table-bordered", index=False)
    
    filename = f"selected_sections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Create summary
    total_sections = len(df)
    selected_courses_count = len(current_generator.selected_courses)
    
    summary = f"Selected {total_sections} sections from {selected_courses_count} courses"
    
    # Create stats object for template compatibility
    sections_per_course = {}
    for course, sections in current_generator.selected_courses.items():
        sections_per_course[course] = len(sections)
    
    stats = {
        "selected_courses": current_generator.selected_courses.keys(),
        "sections_per_course": sections_per_course,
        "total_sections": total_sections,
        "total_courses": selected_courses_count
    }
    
    return templates.TemplateResponse("export_preview.html", {
        "request": request,
        "csv_content": csv_content,
        "html_table": html_table,
        "summary": summary,
        "stats": stats,
        "filename": filename,
        "total_combinations": 0,  # Not applicable for selected sections
        "is_selected_sections": True
    })

@app.get("/export/processed-file/download")
async def download_processed_file():
    """Download the processed version of the uploaded file"""
    global current_generator
    
    if current_generator.course_data is None:
        raise HTTPException(status_code=400, detail="No course data available")
    
    # Generate CSV content from the processed data
    output = io.StringIO()
    current_generator.course_data.to_csv(output, index=False)
    csv_content = output.getvalue()
    
    filename = f"processed_{current_generator.current_file_path or 'file'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# =================================================================
# SMART PAIRING API
# =================================================================

@app.get("/auto-pairs")
async def get_auto_pairs():
    """Get discovered course pairs from Step 1"""
    global current_generator
    
    if current_generator.course_data is None:
        raise HTTPException(status_code=400, detail="No data loaded")
    
    # Convert bidirectional pairs to unique pairs
    unique_pairs = []
    seen_pairs = set()
    
    for course1, course2 in current_generator.course_pairs.items():
        pair = tuple(sorted([course1, course2]))
        if pair not in seen_pairs:
            unique_pairs.append({"course1": course1, "course2": course2})
            seen_pairs.add(pair)
    
    return {
        "success": True,
        "pairs": unique_pairs,
        "total_pairs": len(unique_pairs)
    }

@app.get("/section-suggestions/{course_code}")
async def get_section_suggestions(course_code: str):
    """Get suggested sections for auto-pairing"""
    global current_generator
    
    if current_generator.course_data is None:
        raise HTTPException(status_code=400, detail="No data loaded")
    
    suggestions = {}
    
    # Check if this course has a pair
    if course_code in current_generator.course_pairs:
        paired_course = current_generator.course_pairs[course_code]
        
        # Get current selections for this course
        current_selections = current_generator.selected_courses.get(course_code, [])
        
        if current_selections:
            # Find compatible sections
            compatible_sections = current_generator.find_compatible_sections(
                course_code, current_selections, paired_course
            )
            
            suggestions[paired_course] = compatible_sections
    
    return {
        "success": True,
        "suggestions": suggestions,
        "paired_course": current_generator.course_pairs.get(course_code, None)
    }

@app.post("/validate-selection")
async def validate_selection(request: Request):
    """Validate section selection against learned pairing rules"""
    global current_generator
    
    data = await request.json()
    course_code = data.get("course_code")
    sections = data.get("sections", [])
    
    if not course_code or not sections:
        raise HTTPException(status_code=400, detail="Course code and sections are required")
    
    validation_result = {
        "is_valid": True,
        "warnings": [],
        "suggestions": [],
        "paired_course": None
    }
    
    # Check if course has a pair
    if course_code in current_generator.course_pairs:
        paired_course = current_generator.course_pairs[course_code]
        validation_result["paired_course"] = paired_course
        
        # Get compatible sections
        compatible_sections = current_generator.find_compatible_sections(
            course_code, sections, paired_course
        )
        
        if compatible_sections:
            validation_result["suggestions"] = compatible_sections
        else:
            validation_result["warnings"].append(f"No compatible sections found for {paired_course}")
    
    return validation_result

# =================================================================
# SERVER STARTUP
# =================================================================

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting University Timetable Generator with Smart Features...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📍 Alternative access: http://127.0.0.1:8000")
    print("💡 Press Ctrl+C to stop the server")
    print("🎯 New Smart Features:")
    print("   • Auto-detect course pairs on CSV upload")
    print("   • Smart section auto-pairing")
    print("   • Real-time compatibility validation")
    print("-" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
