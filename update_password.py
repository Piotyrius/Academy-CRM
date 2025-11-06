"""
Helper script to update PostgreSQL password in .env file.
Run this script and enter your PostgreSQL password when prompted.
"""
import os
import re

def update_password():
    env_file = '.env'
    
    if not os.path.exists(env_file):
        print(f"❌ {env_file} file not found!")
        return
    
    # Read current .env
    with open(env_file, 'r') as f:
        content = f.read()
    
    # Show current password (masked)
    match = re.search(r'DB_PASSWORD=(.+)', content)
    if match:
        current = match.group(1).strip()
        print(f"Current password in .env: {current[:2]}**** (masked)")
    else:
        print("DB_PASSWORD not found in .env")
        return
    
    # Get new password
    print("\nEnter your PostgreSQL password (the one you use to connect in pgAdmin):")
    new_password = input("Password: ").strip()
    
    if not new_password:
        print("❌ Password cannot be empty!")
        return
    
    # Update password
    updated_content = re.sub(
        r'DB_PASSWORD=.*',
        f'DB_PASSWORD={new_password}',
        content
    )
    
    # Write back
    with open(env_file, 'w') as f:
        f.write(updated_content)
    
    print(f"\n✅ Password updated in .env file!")
    print("\nNext steps:")
    print("1. Test connection: python test_postgres_connection.py")
    print("2. If successful, run: python manage.py migrate")

if __name__ == '__main__':
    update_password()
