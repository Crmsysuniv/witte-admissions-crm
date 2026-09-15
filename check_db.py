import os
import sys
import django
from django.db import connection

def check_connection():
    print("Checking database connection...")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "witte_crm.settings")
    try:
        django.setup()
        db_settings = connection.settings_dict
        print(f"Target Database Engine: {db_settings.get('ENGINE')}")
        print(f"Target Database Name:   {db_settings.get('NAME')}")
        print(f"Target Database Host:   {db_settings.get('HOST')}:{db_settings.get('PORT')}")
        print(f"Target Database User:   {db_settings.get('USER')}")

        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION();")
            version = cursor.fetchone()
            print("\n[SUCCESS] Successfully connected to MySQL database!")
            print(f"MySQL Version: {version[0]}")
        return True
    except Exception as exc:
        print(f"\n[ERROR] Failed to connect to MySQL database:")
        print(exc)
        return False

if __name__ == "__main__":
    success = check_connection()
    sys.exit(0 if success else 1)
