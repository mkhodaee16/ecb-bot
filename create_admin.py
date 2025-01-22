from app import app, db, User
import os
from dotenv import load_dotenv

load_dotenv()

def create_or_update_admin():
    with app.app_context():
        try:
            # Create tables if not exist
            db.create_all()
            
            admin_user = os.getenv('ADMIN_USER', 'admin')
            admin_pass = os.getenv('ADMIN_PASS', 'admin')
            
            # Check if admin exists
            admin = User.query.filter_by(username=admin_user).first()
            
            if not admin:
                # Create new admin
                admin = User(username=admin_user)
                admin.set_password(admin_pass)
                db.session.add(admin)
                db.session.commit()
                print(f"Admin user created: {admin_user}")
            else:
                # Update password if changed
                if not admin.check_password(admin_pass):
                    admin.set_password(admin_pass)
                    db.session.commit()
                    print(f"Admin password updated for: {admin_user}")
                else:
                    print(f"Admin user exists: {admin_user}")
            return True
        except Exception as e:
            print(f"Error creating/updating admin: {str(e)}")
            return False

if __name__ == "__main__":
    success = create_or_update_admin()
    if not success:
        exit(1)