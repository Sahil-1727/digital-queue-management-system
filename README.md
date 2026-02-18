# QueueFlow - Digital Queue Management System

A web-based queue management system for service centers in Nagpur.


## Deployment
Live Demo: https://digital-queue-management-system-1.onrender.com

## Features

### User Module
- User registration and login
- View available service centers
- Request digital tokens
- Simulated payment confirmation
- Live queue status with estimated wait time
- Smart "leave home" time suggestion
- One active token per user

### Admin Module
- Admin login per service center
- View current serving token
- View waiting queue
- Call next token
- Mark token as completed or no-show
- Real-time queue management

### Fake Queue Prevention
- One active token per user
- Queue size limit (15 tokens max)
- Mandatory payment confirmation
- Token expiry (2 hours)
- No-show tracking

## Setup Instructions

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. Open browser and navigate to:
```
http://127.0.0.1:5000
```

## Demo Credentials

### Admin Login
See `SERVICE_CENTERS.md` for complete list of all 19 service centers and their admin credentials.

**Quick Examples:**
- Medical: `apollo@admin.com` / `admin123`
- Mobile: `apple@admin.com` / `admin123`
- More: `samsung1@admin.com`, `vivo@admin.com`, `oppo@admin.com`

Each admin manages their respective service center.

### User Registration
Create your own user account through the registration page, or use demo accounts:
- Mobile: `9876543210` | Password: `demo123`

## Database

The application uses SQLite database (`database.db`) which is automatically created on first run with:
- **19 service centers** in Nagpur (11 medical clinics + 8 mobile service centers)
- **19 admin accounts** (one per service center)
- **5 demo user accounts**

See `SERVICE_CENTERS.md` for complete details.

## Technology Stack
- Backend: Flask + SQLAlchemy
- Frontend: HTML + Bootstrap 5
- Database: SQLite

## Project Structure
```
QueueFlow/
├── app.py                 # Main Flask application
├── database.db            # SQLite database (auto-created)
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── login.html
│   ├── register.html
│   ├── services.html
│   ├── payment.html
│   ├── queue_status.html
│   ├── admin_login.html
│   └── admin_dashboard.html
└── static/                # Bootstrap CSS & JS files
    ├── css/
    └── js/
```

## How It Works

1. **User Flow:**
   - Register/Login → View Services → Request Token → Simulate Payment → View Queue Status

2. **Admin Flow:**
   - Login → View Queue → Call Next Token → Complete/No-Show

3. **Queue Logic:**
   - FIFO (First In First Out)
   - Estimated wait time based on average service time
   - Smart leave-home time calculation
   - Auto-refresh for real-time updates

## Notes
- Payment is simulated (no real transactions)
- Queue auto-expires tokens after 2 hours
- Pages auto-refresh for live updates
- Mobile-responsive design
