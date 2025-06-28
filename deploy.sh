#!/bin/bash

# 🌊 DigitalOcean Deployment Script for University Timetable Generator
# Run this script on your Ubuntu droplet

echo "🚀 Starting deployment of University Timetable Generator..."

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install required packages
echo "🔧 Installing Python, Nginx, and Supervisor..."
apt install python3 python3-pip python3-venv nginx supervisor -y

# Create application directory
echo "📁 Setting up application directory..."
mkdir -p /var/www/timetable
cd /var/www/timetable

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📋 Installing Python dependencies..."
pip install fastapi uvicorn pandas openpyxl python-multipart jinja2 aiofiles

# Create systemd service file
echo "⚙️ Creating system service..."
cat > /etc/systemd/system/timetable.service << 'EOF'
[Unit]
Description=University Timetable Generator
After=network.target

[Service]
User=root
WorkingDirectory=/var/www/timetable
Environment=PATH=/var/www/timetable/venv/bin
ExecStart=/var/www/timetable/venv/bin/uvicorn web_scheduler:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Create Nginx configuration
echo "🌐 Setting up Nginx..."
cat > /etc/nginx/sites-available/timetable << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/timetable /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
nginx -t && systemctl reload nginx

# Start and enable services
echo "🎯 Starting services..."
systemctl daemon-reload
systemctl start timetable
systemctl enable timetable
systemctl start nginx
systemctl enable nginx

# Show status
echo "📊 Service status:"
systemctl status timetable --no-pager -l

echo ""
echo "🎉 Deployment complete!"
echo "📍 Your app should be available at: http://$(curl -s http://checkip.amazonaws.com)"
echo "📋 To check logs: journalctl -u timetable -f"
echo "🔄 To restart: systemctl restart timetable"
