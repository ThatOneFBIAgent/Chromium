"""
Helper script to obtain a Google Drive OAuth token, base64 encode it, and optionally save it to a .env file.
This script is designed to be a generic helper for any user setting up Google Drive integration.
"""

import os
import json
import base64
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Error: 'google-auth-oauthlib' is required. Please install it using:")
    print("pip install google-auth-oauthlib")
    sys.exit(1)

# Scopes: drive.file limits to files created/opened by app in Drive.
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def get_client_secret_path():
    """Prompts the user for the client secret file path with validation."""
    print("\n--- Google Drive OAuth Helper ---")
    print("This utility will help you generate the necessary base64-encoded token for Google Drive access.")
    print("1. Go to the Google Cloud Console (https://console.cloud.google.com).")
    print("2. Create a project and enable the Google Drive API.")
    print("3. Create an OAuth 2.0 Client ID (Desktop App).")
    print("4. Download the 'client_secret.json' file.")
    
    while True:
        path = input("\nEnter the path to your downloaded 'client_secret.json' file (or 'q' to quit): ").strip()
        if path.lower() == 'q':
            return None
        
        # Remove quotes if the user copied as path
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
            
        if os.path.exists(path):
            # Basic validation to ensure it's a valid JSON file
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    if 'installed' not in data and 'web' not in data:
                        print("Warning: The file does not look like a standard client_secret.json. It usually contains 'installed' or 'web' keys.")
                        confirm = input("Continue anyway? (y/n): ").strip().lower()
                        if confirm != 'y':
                            continue
            except json.JSONDecodeError:
                print(f"Error: The file '{path}' is not a valid JSON file.")
                continue
            except Exception as e:
                print(f"Error reading file: {e}")
                continue

            return path
        else:
            print(f"Error: File not found at '{path}'. Please check the path and try again.")

def update_env_file(token_b64):
    """Updates or creates the .env file with the new token safely."""
    env_path = ".env"
    # Logic to find .env if running from a subdirectory (e.g., utils/)
    if not os.path.exists(env_path):
        parent_env = os.path.join("..", ".env")
        if os.path.exists(parent_env):
            env_path = parent_env
    
    abs_path = os.path.abspath(env_path)
    print(f"\nTarget configuration file: {abs_path}")
    
    save = input("Do you want to automatically save/update the 'DRIVE_TOKEN_B64' in this file? (y/n): ").strip().lower()
    
    if save == 'y':
        try:
            lines = []
            if os.path.exists(env_path):
                with open(env_path, "r", encoding='utf-8') as f:
                    lines = f.readlines()
            
            key = "DRIVE_TOKEN_B64"
            new_line = f"{key}={token_b64}\n"
            key_found = False
            
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{key}="):
                    lines[i] = new_line
                    key_found = True
                    break
            
            if not key_found:
                if lines and not lines[-1].endswith("\n"):
                    lines.append("\n")
                lines.append(new_line)
                
            with open(env_path, "w", encoding='utf-8') as f:
                f.writelines(lines)
                
            print(f"Successfully updated {env_path}")
            
        except Exception as e:
            print(f"Failed to update .env file: {e}")
            print("Please manually add the following line to your .env file:")
            print(f"DRIVE_TOKEN_B64={token_b64}")
    else:
        print("\nSkipping automatic file update.")
        print("Please manually add the following line to your .env file:")
        print(f"DRIVE_TOKEN_B64={token_b64}")

def main():
    try:
        client_secret_path = get_client_secret_path()
        if not client_secret_path:
            print("Setup cancelled by user.")
            return

        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        
        print("\nLaunching browser for authentication...")
        print("Please log in with the Google account you want to use for storing files.")
        print("Note: If you are verifying the app, you may need to click 'Advanced' > 'Go to {App Name} (unsafe)' since it's a personal app.")
        
        # run_local_server automatically handles the callback
        creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")
        
        print("\nAuthentication successful!")
        
        # Convert credentials to JSON
        token_json = creds.to_json()
        
        # Base64 encode
        token_b64 = base64.b64encode(token_json.encode('utf-8')).decode('utf-8')
        
        print("\n--- Generated Token (Base64) ---")
        print(token_b64)
        print("--------------------------------")
        
        update_env_file(token_b64)
        
        print("\nSetup complete!")
        print("You can now delete the 'client_secret.json' and any 'token.json' files if they were created, as the base64 string contains all necessary info.")
        
    except Exception as e:
        print(f"\nAn unrecoverable error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
