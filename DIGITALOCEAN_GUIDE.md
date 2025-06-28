# 🌊 DIGITALOCEAN DEPLOYMENT GUIDE

## 🎯 STEP 1: CLAIM YOUR $200 CREDIT

1. Go to: https://education.github.com/pack
2. Find "DigitalOcean" in the offers list
3. Click "Get access by connecting your GitHub account on DigitalOcean"
4. This gives you $200 credit = 40 months of $5 droplets!

## 🖥️ STEP 2: CREATE A DROPLET

1. Log into DigitalOcean
2. Click "Create" → "Droplets"
3. Choose:
   - **Image:** Ubuntu 22.04 LTS
   - **Plan:** Basic ($5/month)
   - **CPU:** Regular Intel (1GB RAM)
   - **Region:** Choose closest to you
   - **Authentication:** SSH Key (recommended) or Password

## 📁 STEP 3: PREPARE YOUR FILES

Your project is already ready! Files needed:
- ✅ `web_scheduler.py` (main app)
- ✅ `requirements.txt` (dependencies)  
- ✅ `templates/` folder (HTML files)
- ✅ Deployment scripts (created below)

## 🚀 STEP 4: DEPLOY YOUR APP

### Option A: Automatic deployment script
```bash
# Upload your project files to the droplet
scp -r . root@YOUR_DROPLET_IP:/var/www/timetable/

# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Run the deployment script
cd /var/www/timetable
chmod +x deploy.sh
./deploy.sh
```

### Option B: Manual deployment
```bash
# SSH into your droplet
ssh root@YOUR_DROPLET_IP

# Update system
apt update && apt upgrade -y

# Install Python and pip
apt install python3 python3-pip python3-venv nginx supervisor -y

# Create app directory
mkdir -p /var/www/timetable
cd /var/www/timetable

# Upload your files here
# (use FileZilla, WinSCP, or scp command)

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create systemd service
# (see service file below)

# Start your app
systemctl start timetable
systemctl enable timetable
```

## 🌐 STEP 5: CONFIGURE NGINX

Your app will be available at: `http://YOUR_DROPLET_IP`

## 💡 STEP 6: ADD CUSTOM DOMAIN (OPTIONAL)

Use your free domains from Student Pack:
- **Namecheap**: Free .me domain
- **Name.com**: Free domain
- **.TECH**: Free .tech domain

## 🎉 YOUR APP IS LIVE!

Cost: $0 for 40 months with your $200 credit!
