"""
🚀 DEPLOYMENT PREPARATION SCRIPT
Prepares your AI Timetable Generator for web deployment
"""

import os
import zipfile
import shutil
from pathlib import Path

def create_deployment_package():
    """Create a clean deployment package"""
    
    print("🚀 PREPARING YOUR AI TIMETABLE GENERATOR FOR DEPLOYMENT...")
    print("=" * 60)
    
    # Get current directory
    current_dir = Path.cwd()
    deployment_dir = current_dir / "deployment_package"
    
    # Create deployment directory
    if deployment_dir.exists():
        shutil.rmtree(deployment_dir)
    deployment_dir.mkdir()
    
    # Files to include in deployment
    files_to_include = [
        "web_scheduler.py",
        "schedeuler.py", 
        "ai_config.py",
        "requirements.txt",
        "Procfile",
        "runtime.txt",
        "railway.json",
        "README.md",
        ".gitignore"
    ]
    
    # Directories to include
    dirs_to_include = [
        "templates"
    ]
    
    print("📁 COPYING FILES...")
    
    # Copy files
    for file_name in files_to_include:
        file_path = current_dir / file_name
        if file_path.exists():
            shutil.copy2(file_path, deployment_dir / file_name)
            print(f"   ✅ {file_name}")
        else:
            print(f"   ⚠️  {file_name} (missing)")
    
    # Copy directories
    for dir_name in dirs_to_include:
        dir_path = current_dir / dir_name
        if dir_path.exists():
            shutil.copytree(dir_path, deployment_dir / dir_name)
            print(f"   ✅ {dir_name}/ (directory)")
        else:
            print(f"   ⚠️  {dir_name}/ (missing)")
    
    print("\n📦 CREATING ZIP FILE...")
    
    # Create zip file for easy upload
    zip_path = current_dir / "ai-timetable-generator-deployment.zip"
    if zip_path.exists():
        zip_path.unlink()
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(deployment_dir):
            for file in files:
                file_path = Path(root) / file
                arc_name = file_path.relative_to(deployment_dir)
                zipf.write(file_path, arc_name)
    
    print(f"   ✅ Created: {zip_path.name}")
    
    # Clean up temp directory
    shutil.rmtree(deployment_dir)
    
    print("\n🎯 DEPLOYMENT READY!")
    print("=" * 60)
    print(f"📦 Package created: {zip_path.name}")
    print(f"📏 File size: {zip_path.stat().st_size / 1024:.1f} KB")
    print("\n🌐 DEPLOYMENT OPTIONS:")
    print("   1. 🚀 Railway: Upload zip to railway.app")
    print("   2. ☁️  Render: Upload to render.com") 
    print("   3. 🔮 Heroku: Extract and deploy via Git")
    print("   4. 🐍 PythonAnywhere: Upload to pythonanywhere.com")
    print("\n📖 See DEPLOYMENT_GUIDE.md for detailed instructions!")
    print("🎉 Your AI Timetable Generator is ready for the world! 🌍")

if __name__ == "__main__":
    create_deployment_package()
