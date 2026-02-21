"""
Update coordinates for all demo service centers
Run this once to add latitude/longitude to existing service centers
"""
from app import app, db, ServiceCenter

def update_coordinates():
    with app.app_context():
        # Coordinates mapping: name -> (latitude, longitude)
        coordinates = {
            'APOLLO CLINIC': (21.1458, 79.0882),
            'The Nagpur Clinic': (21.1466, 79.0882),
            'Nagpur Clinic': (21.1498, 79.0806),
            'MOTHER INDIA FETAL MEDICINE CENTRE': (21.1307, 79.0711),
            'Ashvatam Clinic': (21.1509, 79.0831),
            'Apna Clinic': (21.1540, 79.0849),
            'Dr.Agrawal Multispeciality Clinic': (21.1180, 79.0510),
            'Shree Clinic': (21.1220, 79.0420),
            'Sai Clinic': (21.1650, 79.0900),
            'Suyash Clinic': (21.1700, 79.0950),
            'INC CLINIC NAGPUR': (21.1350, 79.0750),
            'Apple Service - NGRT Systems': (21.1458, 79.0882),
            'Samsung Service - The Mobile Magic': (21.1498, 79.0806),
            'Samsung Service - Spectrum Marketing': (21.1466, 79.0882),
            'Samsung Service - Karuna Management': (21.1400, 79.0700),
            'Samsung CE - Akshay Refrigeration': (21.1600, 79.1000),
            'vivo India Service Center': (21.1509, 79.0831),
            'vivo & iQOO Service Center': (21.1520, 79.0840),
            'OPPO Service Center': (21.1498, 79.0806),
        }
        
        updated = 0
        for name, (lat, lng) in coordinates.items():
            center = ServiceCenter.query.filter_by(name=name).first()
            if center:
                center.latitude = lat
                center.longitude = lng
                updated += 1
                print(f"✅ Updated: {name}")
        
        db.session.commit()
        print(f"\n🎉 Successfully updated {updated} service centers with coordinates!")

if __name__ == '__main__':
    update_coordinates()
