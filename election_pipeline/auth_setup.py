import os
from src.gdrive_client import get_gdrive_service

print("🚀 Starting verify account with Google Drive...")
print("Go to the popup Browser then click 'อนุญาต' (Allow)")

service = get_gdrive_service()

if os.path.exists('credentials/token.json'):
    print("✅ Successfully! Already created 'credentials/token.json' file")
    print("Now you able to run this project on Airflow !")
else:
    print("❌ Error token.json not found")