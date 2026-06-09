import os
from google import genai
import sys

def main():
    # User's API key is needed. We can try to get it from settings, or just use the SDK without it if it's in environment? No, need the key.
    # We will read it from QSettings in PhotoPrintApp if possible, but simpler to just write a script that instantiates QSettings.
    from PyQt5.QtCore import QSettings, QCoreApplication
    app = QCoreApplication(sys.argv)
    settings = QSettings("PhotoPrintApp", "Settings")
    api_key = settings.value("gemini_api_key", "")
    
    if not api_key:
        print("No API Key found")
        return
        
    client = genai.Client(api_key=api_key)
    try:
        # For new google-genai SDK, use client.models.list_models() or client.models.list()
        for m in client.models.list():
            if 'gemini' in m.name:
                print(m.name)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
