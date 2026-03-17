# QueueFlow — Smart Queue Management System

A full-stack web application that digitizes and automates queue management for service centers. Users book digital tokens online, track their live queue position, and receive smart travel-time suggestions so they arrive exactly when it's their turn — eliminating physical waiting lines entirely.

**Live Demo:** https://digital-queue-management-system-1.onrender.com

---

## Project Description

QueueFlow serves service centers (medical clinics, mobile repair shops, banks, government offices) and their customers through three distinct portals:

- **User Portal** — Book tokens, track queue status, manage profile & history
- **Admin Portal** — Manage queues per service center, handle walk-ins, view analytics
- **Super Admin Portal** — Approve/reject new service center registrations, manage all admins and centers system-wide

---

## Key Features & Functionality

### User Module
- Register and login via mobile number + password
- Browse all service centers filtered by category (Medical, Mobile Service, etc.)
- View service center details: description, contact info, business hours, services offered, facilities, and an embedded Google Maps location map
- Book a digital token with simulated payment confirmation
- Real-time queue status page showing:
  - Current token being served
  - Your position in queue
  - Estimated wait time
  - Smart "Leave Home By" time suggestion
  - "Reach Counter By" time (calculated using OpenRouteService API + traffic multiplier)
- Email notification on token confirmation with timing details (via Brevo API)
- Token cancellation with automatic queue recalculation for remaining users
- View token history (completed and expired tokens)
- User profile management with GPS-based location capture for travel time calculation
- Password reset via email link
- One active token per user enforced at all times
- QR code generation for walk-in token tracking

### Admin Module
- Dedicated login per service center
- Dual-counter dashboard:
  - **Counter 1 (Online Queue)** — manages digitally booked tokens
  - **Counter 2 (Walk-In Queue)** — manages physically added walk-in customers
- Real-time queue table with arrival status badges: Travelling / Arrived / Late
- Call Next Token (only enabled when next user has arrived)
- Auto-skip tokens that are more than 15 minutes late
- Mark token as Completed or No-Show (with reason logging)
- Add walk-in customers directly from the dashboard
- Admin profile page to update service center details, contact info, business hours, and GPS coordinates
- Analytics dashboard (Chart.js) with:
  - Today's customer count
  - 7-day activity trend (line chart)
  - Online vs Walk-in booking split (doughnut chart)
  - Token status breakdown: Completed / No-Show / Expired (bar chart)
  - Peak hours analysis (horizontal bar chart)
- Token history with full audit trail
- Demo data generator for analytics testing
- Page auto-refreshes every 15 seconds

### Super Admin Module
- Separate login at `/superadmin/login`
- Review pending service center registration applications
- Approve or reject registrations (auto-creates ServiceCenter + Admin account on approval)
- Manage all admins: edit credentials, service center details, reset passwords
- Manage all service centers: view, edit, delete
- System-wide analytics dashboard (same Chart.js layout, aggregated across all centers)

### Service Center Registration Flow
- Public registration form at `/register-center` with full business details
- GPS coordinate capture (auto-detect or manual entry) — required for travel time calculation
- Simulated registration fee payment (₹500)
- Owner dashboard to track application status (Pending / Approved / Rejected)
- On approval: service center goes live and admin credentials are auto-generated

### Fake Queue Prevention
- One active token per user at any time
- Queue size hard limit: 15 tokens per center
- Mandatory payment confirmation before token activation
- Token auto-expiry after 2 hours (PendingPayment tokens)
- Auto-expiry for users who don't arrive within 15 minutes of their expected time
- No-show tracking with reason logging and user no-show counter

### Travel Time & Smart Timing System
- Integrates with **OpenRouteService (ORS) API** for real driving-route travel time
- Traffic multiplier applied based on time of day:
  - Peak hours (9–11 AM, 4–8 PM): ×2.0
  - Normal hours: ×1.8
  - Night hours (10 PM–6 AM): ×1.2
- Leave time and reach time calculated at payment and stored permanently in the database
- Queue times recalculated for all remaining users when a token is cancelled or skipped

### API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/analytics` | JSON analytics data for admin center |
| GET | `/api/superadmin/analytics` | JSON system-wide analytics data |
| GET | `/admin/queue-state` | Real-time queue state for auto-refresh |
| GET | `/admin/update-all-coordinates` | One-time migration: sets GPS coordinates for all 19 demo service centers |
| GET | `/migrate-db-add-column` | Manual DB migration: adds missing columns to live PostgreSQL DB |
| GET | `/test-send-email` | Tests Brevo email delivery |
| GET | `/test-ors-api` | Tests OpenRouteService API + traffic adjustment |
| GET | `/debug/verify-timing-system` | Verifies timing data across all service centers |
| GET | `/track/<token_number>` | Public token tracking page (no login required) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10, Flask 3.0 |
| ORM | Flask-SQLAlchemy 3.1 |
| Database | PostgreSQL (production via Render), SQLite (local dev) |
| Frontend | Jinja2 templates, Bootstrap 5, Chart.js 4.4 |
| CSS Architecture | 7-layer custom design system (theme → enhancements → ux-refinements → apple-refinement → elite-polish → global-consistency → saas-final) |
| Auth | Werkzeug password hashing, Flask sessions |
| Email | Brevo (Sendinblue) API — 300 free emails/day |
| Travel Time | OpenRouteService API (driving directions) |
| QR Codes | `qrcode` + `Pillow` (base64 PNG generation) |
| Timezone | `pytz` — all DB times stored in UTC, displayed in IST (Asia/Kolkata) |
| Deployment | Gunicorn + Render (PaaS), `Procfile` configured |
| Environment | `python-dotenv` for local `.env` loading |

---

## Prerequisites & Installation

### Requirements
- Python 3.10+
- pip
- (Optional) PostgreSQL for production-like local setup; SQLite works out of the box

### Environment Variables
Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///database.db

# Brevo (email)
BREVO_API_KEY=your-brevo-api-key
BREVO_SENDER_EMAIL=your-verified-sender@email.com

# OpenRouteService (travel time)
OPENROUTESERVICE_API_KEY=your-ors-api-key
```

> Travel time calculation and email notifications require valid API keys. The app runs without them but those features will be disabled.

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Usage / Running the Application

```bash
python app.py
```

Then open: `http://127.0.0.1:5000`

The database is created automatically on first run with all 19 demo service centers, 19 admin accounts, 5 demo users, and 1 super admin.

---

## Demo Credentials

### User Login
| Mobile | Password |
|--------|----------|
| `9876543210` | `demo123` |

### Admin Login (examples)
| Email | Password | Service Center |
|-------|----------|----------------|
| `apollo@admin.com` | `admin123` | Apollo Clinic |
| `apple@admin.com` | `admin123` | Apple Service - NGRT Systems |
| `samsung1@admin.com` | `admin123` | Samsung Service - The Mobile Magic |
| `vivo@admin.com` | `admin123` | vivo India Service Center |
| `oppo@admin.com` | `admin123` | OPPO Service Center |

See `SERVICE_CENTERS.md` for the full list of all 19 admin credentials.

### Super Admin
| Username | Password |
|----------|----------|
| `superadmin@queueflow.com` | `superadmin123` |

---

## Project Structure

```
QueueFlow/
├── app.py                        # Main Flask app: models, routes, business logic
├── config.py                     # Environment-based config (Dev/Prod)
├── requirements.txt              # Python dependencies
├── Procfile                      # Gunicorn command for Render deployment
├── runtime.txt                   # Python version pin (3.10.12)
├── .env                          # Local environment variables (not committed)
│
├── templates/
│   ├── base.html                 # Base layout with CSS/JS includes
│   ├── home.html                 # Public landing page
│   ├── login.html / register.html
│   ├── services.html             # Service center listing
│   ├── service_details.html      # Center detail page with Google Maps embed
│   ├── payment.html              # Token payment confirmation
│   ├── queue_status.html         # Live queue tracking for user
│   ├── user_profile.html         # User profile + GPS location update
│   ├── user_history.html         # Past token history
│   ├── track_token.html          # Public token lookup
│   ├── track_status.html         # Public token status (no login)
│   ├── admin_login.html
│   ├── admin_dashboard.html      # Dual-counter queue management
│   ├── admin_analytics.html      # Chart.js analytics dashboard
│   ├── admin_profile.html        # Service center profile editor
│   ├── admin_history.html        # Token audit trail
│   ├── add_walkin.html           # Walk-in customer form
│   ├── no_show_form.html         # No-show reason form
│   ├── token_qr.html             # QR code display for walk-in tokens
│   ├── superadmin_login.html
│   ├── superadmin_dashboard.html # Registration review panel
│   ├── superadmin_admins.html    # Admin management
│   ├── superadmin_manage_centers.html
│   ├── superadmin_analytics.html # System-wide analytics
│   ├── register_center.html      # Service center registration form
│   ├── registration_payment.html # Registration fee payment
│   ├── owner_dashboard.html      # Registration status tracker
│   ├── pricing.html              # Pricing plans (Free/Pro/Enterprise)
│   ├── terms.html / privacy.html
│   ├── forgot_password.html / reset_password.html
│   └── includes/
│       └── internal_navbar.html  # Shared navbar for admin/user pages
│
├── static/
│   ├── css/
│   │   ├── bootstrap.min.css
│   │   ├── theme.css             # Design tokens: colors, spacing, shadows, transitions
│   │   ├── enhancements.css      # Skeleton loaders, stat cards, hover effects, empty states
│   │   ├── ux-refinements.css    # Toast notifications, focus states, button hierarchy
│   │   ├── apple-refinement.css  # 8pt grid enforcement, typography precision, motion minimalism
│   │   ├── elite-polish.css      # Scroll experience, layout discipline, micro-alignment
│   │   ├── global-consistency.css# System-wide spacing, typography, shadow enforcement
│   │   └── saas-final.css        # Final SaaS polish layer
│   ├── js/
│   │   ├── bootstrap.bundle.min.js
│   │   ├── ux-refinements.js     # Toast manager, button loading states, active nav detection
│   │   ├── elite-polish.js       # Scroll-based navbar backdrop blur (rAF)
│   │   └── saas-final.js         # Final interaction layer
│   ├── images/                   # Hero images, dashboard screenshots
│   ├── videos/                   # Demo video (demoDA.mov)
│   ├── manifest.json             # PWA manifest
│   ├── robots.txt
│   └── sitemap.xml
│
└── instance/
    └── database.db               # SQLite DB (auto-created locally)
```

---

## Database Models

| Model | Description |
|-------|-------------|
| `User` | Registered users with mobile, email, GPS coordinates, no-show count |
| `ServiceCenter` | Centers with category, location, GPS coordinates, contact info, avg service time |
| `Admin` | One admin per service center, with password reset support |
| `Token` | Queue tokens with full time-chain: leave_time, reach_time, estimated/actual service start/end |
| `SuperAdmin` | Platform-level administrator |
| `ServiceCenterRegistration` | Registration applications with payment and approval workflow |

---

## Design System

The frontend uses a 7-layer CSS architecture loaded in order:

1. `bootstrap.min.css` — base grid and components
2. `theme.css` — design tokens (colors, spacing scale, shadows, transitions)
3. `enhancements.css` — product-level UI components
4. `ux-refinements.css` — premium UX patterns
5. `apple-refinement.css` — 8pt grid, typography hierarchy, 200ms motion
6. `elite-polish.css` — scroll effects, layout discipline, icon consistency
7. `global-consistency.css` — system-wide enforcement layer

Key design tokens:
- Spacing: strict 8pt scale (8 / 16 / 24 / 32 / 48 / 64px)
- Shadows: 3-level system (soft / hover / elevated)
- Motion: unified 200ms `cubic-bezier(0.4, 0, 0.2, 1)` easing
- Typography: Display (40px) → Title (28px) → Heading (20px) → Body (15px) → Meta (13px)
- Dark mode: full support via `data-theme="dark"` on `<html>`, persisted in `localStorage`

---

## Deployment (Render)

The app is deployed on [Render](https://render.com) with:
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120` (via `Procfile`)
- **Database:** PostgreSQL (Render managed), URL injected via `DATABASE_URL` env var
- **Python version:** 3.10.12 (pinned via `runtime.txt`)

Required environment variables on Render:
```
SECRET_KEY
DATABASE_URL          (auto-set by Render PostgreSQL addon)
BREVO_API_KEY
BREVO_SENDER_EMAIL
OPENROUTESERVICE_API_KEY
```

After first deployment, run the coordinate migration once:
```
https://your-app.onrender.com/admin/update-all-coordinates
```

---

## Notes

- Payment is fully simulated — no real transactions occur
- Token timing is calculated once at payment and stored permanently; it does not shift as the queue moves
- All datetime values are stored in UTC in the database and converted to IST (Asia/Kolkata) for display
- The `before_request` hook handles DB initialization and column migrations automatically on first request
- Walk-in tokens use a `W` prefix (e.g., `W001`); online tokens use `T` prefix (e.g., `T001`)
