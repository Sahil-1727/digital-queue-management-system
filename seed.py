from werkzeug.security import generate_password_hash
from extensions import db
from models import ServiceCenter, Admin, User, SuperAdmin, ServiceCenterRegistration


def init_db(app):
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables created")
        except Exception as e:
            print(f"❌ Database init error: {e}")
            return  # Exit early if tables can't be created

        try:
            # Add service centers from approved registrations
            approved_registrations = ServiceCenterRegistration.query.filter_by(status='Approved').all()
            for reg in approved_registrations:
                # Check if service center already exists
                existing = ServiceCenter.query.filter_by(name=reg.center_name, location=f"{reg.city}, {reg.state}").first()
                if not existing:
                    new_center = ServiceCenter(
                        name=reg.center_name,
                        category=reg.organization_type,
                        location=f"{reg.city}, {reg.state}",
                        avg_service_time=15
                    )
                    db.session.add(new_center)
                    db.session.commit()

                    # Create admin for this center if credentials exist
                    if reg.admin_username and reg.admin_password:
                        admin_exists = Admin.query.filter_by(username=reg.admin_username).first()
                        if not admin_exists:
                            new_admin = Admin(
                                username=reg.admin_username,
                                email=reg.email,
                                password=reg.admin_password,  # Already hashed during approval
                                service_center_id=new_center.id
                            )
                            db.session.add(new_admin)
                            db.session.commit()
        except Exception as e:
            print(f"⚠️ Error processing approved registrations: {e}")

        # Add default service centers only if none exist
        try:
            if ServiceCenter.query.count() == 0:
                centers = [
                    # Medical Clinics (Nagpur coordinates)
                    ServiceCenter(
                        name='APOLLO CLINIC', category='Medical Clinic', location='Civil Lines, Nagpur',
                        latitude=21.1458, longitude=79.0882, avg_service_time=20,
                        description='Premier multi-specialty clinic offering comprehensive healthcare services with experienced doctors and modern facilities.',
                        phone='+91 712 2531234', email='apollo.nagpur@clinic.com', website='https://apolloclinic.com',
                        business_hours='Mon-Sat: 9:00 AM - 8:00 PM, Sun: 10:00 AM - 2:00 PM',
                        services_offered='• General Consultation\n• Pathology Lab\n• X-Ray & Ultrasound\n• Vaccination\n• Health Checkups',
                        facilities='• AC Waiting Room\n• Pharmacy\n• Wheelchair Access\n• Parking Available\n• Emergency Services'
                    ),
                    ServiceCenter(
                        name='The Nagpur Clinic', category='Medical Clinic', location='Dharampeth, Nagpur',
                        latitude=21.1466, longitude=79.0882, avg_service_time=18,
                        description='Family healthcare center providing quality medical services with a patient-first approach.',
                        phone='+91 712 2445678', email='info@nagpurclinic.com',
                        business_hours='Mon-Sat: 8:00 AM - 9:00 PM',
                        services_offered='• General Medicine\n• Pediatrics\n• Gynecology\n• Dental Care\n• Physiotherapy',
                        facilities='• Digital Records\n• Online Reports\n• Ambulance Service\n• 24/7 Pharmacy'
                    ),
                    ServiceCenter(
                        name='Nagpur Clinic', category='Medical Clinic', location='Sitabuldi, Nagpur',
                        latitude=21.1498, longitude=79.0806, avg_service_time=15,
                        description='Quick consultation clinic for routine checkups and minor ailments.',
                        phone='+91 712 2567890', email='contact@nagpurclinic.in',
                        business_hours='Mon-Sun: 7:00 AM - 10:00 PM',
                        services_offered='• Quick Consultation\n• Fever Clinic\n• BP & Sugar Monitoring\n• Injections\n• Dressing',
                        facilities='• Fast Service\n• Walk-in Welcome\n• Digital Payments\n• Free WiFi'
                    ),
                    ServiceCenter(
                        name='MOTHER INDIA FETAL MEDICINE CENTRE', category='Medical Clinic', location='Ramdaspeth, Nagpur',
                        latitude=21.1307, longitude=79.0711, avg_service_time=25,
                        description='Specialized center for women and child healthcare with advanced diagnostic facilities.',
                        phone='+91 712 2678901', email='motherindia@healthcare.com', website='https://motherindiafmc.com',
                        business_hours='Mon-Sat: 9:00 AM - 6:00 PM',
                        services_offered='• Fetal Medicine\n• Gynecology\n• Obstetrics\n• 4D Ultrasound\n• Prenatal Care',
                        facilities='• Advanced Ultrasound\n• Comfortable Waiting\n• Female Staff\n• Counseling Services'
                    ),
                    ServiceCenter(
                        name='Ashvatam Clinic', category='Medical Clinic', location='Sadar, Nagpur',
                        latitude=21.1509, longitude=79.0831, avg_service_time=18,
                        description='Holistic healthcare clinic combining modern medicine with wellness programs.',
                        phone='+91 712 2789012', email='ashvatam@clinic.com',
                        business_hours='Mon-Sat: 8:30 AM - 8:30 PM',
                        services_offered='• General Medicine\n• Diabetes Care\n• Hypertension Management\n• Wellness Programs\n• Diet Counseling',
                        facilities='• Health Monitoring\n• Yoga Classes\n• Nutrition Guidance\n• Free Parking'
                    ),
                    ServiceCenter(
                        name='Apna Clinic', category='Medical Clinic', location='Gandhibagh, Nagpur',
                        latitude=21.1540, longitude=79.0849, avg_service_time=15,
                        description='Affordable neighborhood clinic providing essential healthcare services.',
                        phone='+91 712 2890123', email='apnaclinic@gmail.com',
                        business_hours='Mon-Sun: 6:00 AM - 11:00 PM',
                        services_offered='• General Consultation\n• First Aid\n• Fever Treatment\n• Minor Procedures\n• Prescriptions',
                        facilities='• 24/7 Service\n• Home Visits\n• Affordable Rates\n• Medicine Available'
                    ),
                    ServiceCenter(
                        name='Dr.Agrawal Multispeciality Clinic', category='Medical Clinic', location='Wardha Road, Nagpur',
                        latitude=21.1180, longitude=79.0510, avg_service_time=22,
                        description='Multi-specialty clinic with expert doctors across various medical fields.',
                        phone='+91 712 2901234', email='dragrawal@multispeciality.com', website='https://agrawalclinic.com',
                        business_hours='Mon-Sat: 9:00 AM - 9:00 PM, Sun: 10:00 AM - 4:00 PM',
                        services_offered='• Cardiology\n• Orthopedics\n• ENT\n• Dermatology\n• General Surgery',
                        facilities='• Specialist Doctors\n• Diagnostic Lab\n• Minor OT\n• Insurance Accepted\n• Ample Parking'
                    ),
                    ServiceCenter(
                        name='Shree Clinic', category='Medical Clinic', location='Manish Nagar, Nagpur',
                        latitude=21.1220, longitude=79.0420, avg_service_time=15,
                        description='Community clinic serving local residents with basic healthcare needs.',
                        phone='+91 712 3012345', email='shreeclinic@yahoo.com',
                        business_hours='Mon-Sat: 7:00 AM - 10:00 PM',
                        services_offered='• OPD Services\n• Injections\n• Wound Care\n• Health Checkup\n• Referrals',
                        facilities='• Quick Service\n• Friendly Staff\n• Clean Environment\n• Nearby Pharmacy'
                    ),
                    ServiceCenter(
                        name='Sai Clinic', category='Medical Clinic', location='Pratap Nagar, Nagpur',
                        latitude=21.1650, longitude=79.0900, avg_service_time=18,
                        description='Modern clinic with focus on preventive healthcare and wellness.',
                        phone='+91 712 3123456', email='saiclinic@healthcare.in',
                        business_hours='Mon-Sat: 8:00 AM - 8:00 PM',
                        services_offered='• Preventive Care\n• Chronic Disease Management\n• Health Screening\n• Vaccination\n• Lifestyle Counseling',
                        facilities='• Health Records\n• Follow-up Care\n• Patient Education\n• Clean Facility'
                    ),
                    ServiceCenter(
                        name='Suyash Clinic', category='Medical Clinic', location='Laxmi Nagar, Nagpur',
                        latitude=21.1700, longitude=79.0950, avg_service_time=15,
                        description='Efficient clinic providing quick medical consultations and treatments.',
                        phone='+91 712 3234567', email='suyash@clinic.com',
                        business_hours='Mon-Sun: 6:30 AM - 10:30 PM',
                        services_offered='• Quick Consultation\n• Emergency Care\n• Lab Tests\n• Prescriptions\n• Medical Certificates',
                        facilities='• Fast Service\n• Digital Payments\n• Home Collection\n• 24/7 Available'
                    ),
                    ServiceCenter(
                        name='INC CLINIC NAGPUR', category='Medical Clinic', location='Dhantoli, Nagpur',
                        latitude=21.1350, longitude=79.0750, avg_service_time=20,
                        description='Integrated healthcare clinic offering comprehensive medical services.',
                        phone='+91 712 3345678', email='inc@clinicnagpur.com', website='https://incclinic.in',
                        business_hours='Mon-Sat: 9:00 AM - 7:00 PM',
                        services_offered='• General Medicine\n• Diagnostic Services\n• Physiotherapy\n• Dental Care\n• Eye Checkup',
                        facilities='• Modern Equipment\n• Experienced Doctors\n• Insurance Support\n• Parking Available'
                    ),
                    # Mobile Service Centers
                    ServiceCenter(
                        name='Apple Service - NGRT Systems', category='Mobile Service', location='Civil Lines, Nagpur',
                        latitude=21.1458, longitude=79.0882, avg_service_time=30,
                        description='Authorized Apple service center providing genuine repairs and support for all Apple products.',
                        phone='+91 712 4456789', email='ngrt@appleservice.com', website='https://ngrtsystems.com',
                        business_hours='Mon-Sat: 10:00 AM - 7:00 PM',
                        services_offered='• iPhone Repair\n• iPad Service\n• MacBook Repair\n• Watch Service\n• Genuine Parts\n• Software Support',
                        facilities='• Authorized Center\n• Trained Technicians\n• Warranty Service\n• Loaner Devices\n• AC Waiting Area'
                    ),
                    ServiceCenter(
                        name='Samsung Service - The Mobile Magic', category='Mobile Service', location='Sitabuldi, Nagpur',
                        latitude=21.1498, longitude=79.0806, avg_service_time=25,
                        description='Official Samsung service center for mobile phones and tablets with expert technicians.',
                        phone='+91 712 4567890', email='mobilemagic@samsung.com', website='https://mobilemagic.in',
                        business_hours='Mon-Sat: 10:00 AM - 8:00 PM, Sun: 11:00 AM - 5:00 PM',
                        services_offered='• Screen Replacement\n• Battery Change\n• Software Update\n• Water Damage Repair\n• Charging Port Fix',
                        facilities='• Genuine Parts\n• Quick Service\n• Warranty Support\n• Free Diagnosis\n• Comfortable Seating'
                    ),
                    ServiceCenter(
                        name='Samsung Service - Spectrum Marketing', category='Mobile Service', location='Dharampeth, Nagpur',
                        latitude=21.1466, longitude=79.0882, avg_service_time=25,
                        description='Authorized Samsung service providing comprehensive repair solutions.',
                        phone='+91 712 4678901', email='spectrum@samsungservice.com',
                        business_hours='Mon-Sat: 9:30 AM - 7:30 PM',
                        services_offered='• Mobile Repair\n• Tablet Service\n• Display Replacement\n• Camera Repair\n• Speaker Fix',
                        facilities='• Original Parts\n• Expert Technicians\n• Fast Turnaround\n• Pickup & Drop\n• WiFi Available'
                    ),
                    ServiceCenter(
                        name='Samsung Service - Karuna Management', category='Mobile Service', location='Rambagh Layout, Nagpur',
                        latitude=21.1400, longitude=79.0700, avg_service_time=25,
                        description='Trusted Samsung service center with years of experience in mobile repairs.',
                        phone='+91 712 4789012', email='karuna@samsung.in',
                        business_hours='Mon-Sat: 10:00 AM - 7:00 PM',
                        services_offered='• Hardware Repair\n• Software Issues\n• Data Recovery\n• Accessory Sales\n• Trade-in Service',
                        facilities='• Certified Center\n• Quality Service\n• Warranty Claims\n• Customer Support\n• Easy Parking'
                    ),
                    ServiceCenter(
                        name='Samsung CE - Akshay Refrigeration', category='Mobile Service', location='Somalwada, Nagpur',
                        latitude=21.1600, longitude=79.1000, avg_service_time=28,
                        description='Samsung consumer electronics service center for all Samsung products.',
                        phone='+91 712 4890123', email='akshay@samsungce.com',
                        business_hours='Mon-Sat: 9:00 AM - 6:00 PM',
                        services_offered='• Mobile Service\n• TV Repair\n• Refrigerator Service\n• AC Repair\n• Washing Machine',
                        facilities='• Multi-Product Service\n• Home Service Available\n• Spare Parts Stock\n• Extended Warranty'
                    ),
                    ServiceCenter(
                        name='vivo India Service Center', category='Mobile Service', location='Sadar, Nagpur',
                        latitude=21.1509, longitude=79.0831, avg_service_time=22,
                        description='Official vivo service center providing quality repairs and customer support.',
                        phone='+91 712 4901234', email='service@vivo.com', website='https://vivo.com/in/support',
                        business_hours='Mon-Sun: 10:00 AM - 8:00 PM',
                        services_offered='• Screen Repair\n• Battery Replacement\n• Camera Service\n• Software Update\n• Charging Issues',
                        facilities='• Authorized Service\n• Genuine Parts\n• Quick Repair\n• Warranty Service\n• Customer Lounge'
                    ),
                    ServiceCenter(
                        name='vivo & iQOO Service Center', category='Mobile Service', location='Medical Chowk, Nagpur',
                        latitude=21.1520, longitude=79.0840, avg_service_time=22,
                        description='Combined service center for vivo and iQOO smartphones with expert technicians.',
                        phone='+91 712 5012345', email='support@vivoiqoo.in',
                        business_hours='Mon-Sun: 10:00 AM - 9:00 PM',
                        services_offered='• Display Replacement\n• Battery Service\n• Software Repair\n• Hardware Issues\n• Accessories',
                        facilities='• Dual Brand Support\n• Fast Service\n• Original Parts\n• Extended Hours\n• Free WiFi'
                    ),
                    ServiceCenter(
                        name='OPPO Service Center', category='Mobile Service', location='Sitabuldi, Nagpur',
                        latitude=21.1498, longitude=79.0806, avg_service_time=22,
                        description='Official OPPO service center delivering excellent repair services and customer care.',
                        phone='+91 712 5123456', email='care@oppo.com', website='https://oppo.com/in/service',
                        business_hours='Mon-Sat: 10:00 AM - 8:00 PM, Sun: 11:00 AM - 6:00 PM',
                        services_offered='• Screen Replacement\n• Battery Change\n• Camera Repair\n• Software Support\n• Water Damage',
                        facilities='• Authorized Center\n• Trained Staff\n• Quality Parts\n• Warranty Support\n• Comfortable Waiting'
                    ),
                ]
                db.session.add_all(centers)
                db.session.commit()
                print("✅ Added default service centers")
        except Exception as e:
            print(f"⚠️ Error adding service centers: {e}")

        # Add admins
        try:
            if Admin.query.count() == 0:
                admins = [
                    Admin(username='apollo@admin.com', password=generate_password_hash('admin123'), service_center_id=1),
                    Admin(username='nagpurclinic@admin.com', password=generate_password_hash('admin123'), service_center_id=2),
                    Admin(username='localclinic@admin.com', password=generate_password_hash('admin123'), service_center_id=3),
                    Admin(username='motherindia@admin.com', password=generate_password_hash('admin123'), service_center_id=4),
                    Admin(username='ashvatam@admin.com', password=generate_password_hash('admin123'), service_center_id=5),
                    Admin(username='apna@admin.com', password=generate_password_hash('admin123'), service_center_id=6),
                    Admin(username='agrawal@admin.com', password=generate_password_hash('admin123'), service_center_id=7),
                    Admin(username='shree@admin.com', password=generate_password_hash('admin123'), service_center_id=8),
                    Admin(username='sai@admin.com', password=generate_password_hash('admin123'), service_center_id=9),
                    Admin(username='suyash@admin.com', password=generate_password_hash('admin123'), service_center_id=10),
                    Admin(username='inc@admin.com', password=generate_password_hash('admin123'), service_center_id=11),
                    Admin(username='apple@admin.com', password=generate_password_hash('admin123'), service_center_id=12),
                    Admin(username='samsung1@admin.com', password=generate_password_hash('admin123'), service_center_id=13),
                    Admin(username='samsung2@admin.com', password=generate_password_hash('admin123'), service_center_id=14),
                    Admin(username='samsung3@admin.com', password=generate_password_hash('admin123'), service_center_id=15),
                    Admin(username='samsung4@admin.com', password=generate_password_hash('admin123'), service_center_id=16),
                    Admin(username='vivo@admin.com', password=generate_password_hash('admin123'), service_center_id=17),
                    Admin(username='vivoiqoo@admin.com', password=generate_password_hash('admin123'), service_center_id=18),
                    Admin(username='oppo@admin.com', password=generate_password_hash('admin123'), service_center_id=19),
                ]
                db.session.add_all(admins)
                db.session.commit()
                print("✅ Added admin accounts")
        except Exception as e:
            print(f"⚠️ Error adding admins: {e}")

        # Add demo users
        try:
            if User.query.count() == 0:
                demo_users = [
                    User(name='Rahul Sharma', mobile='9876543210', email='rahul@demo.com', password=generate_password_hash('demo123')),
                    User(name='Priya Patel', mobile='9876543211', email='priya@demo.com', password=generate_password_hash('demo123')),
                    User(name='Amit Kumar', mobile='9876543212', email='amit@demo.com', password=generate_password_hash('demo123')),
                    User(name='Sneha Deshmukh', mobile='9876543213', email='sneha@demo.com', password=generate_password_hash('demo123')),
                    User(name='Vikram Singh', mobile='9876543214', email='vikram@demo.com', password=generate_password_hash('demo123')),
                ]
                db.session.add_all(demo_users)
                db.session.commit()
                print("✅ Added demo users")
        except Exception as e:
            print(f"⚠️ Error adding demo users: {e}")

        # Add super admin
        try:
            if SuperAdmin.query.count() == 0:
                super_admin = SuperAdmin(
                    username='superadmin@queueflow.com',
                    password=generate_password_hash('superadmin123'),
                    email='superadmin@queueflow.com'
                )
                db.session.add(super_admin)
                db.session.commit()
                print("✅ Added super admin")
        except Exception as e:
            print(f"⚠️ Error adding super admin: {e}")
