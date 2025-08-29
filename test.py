import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# API Configuration
AUTH_URL = "https://auth.quandify.com/"
BASE_URL = "https://api.quandify.com"

# Your credentials - Replace with your actual values
ACCOUNT_ID = "your-guid-account-id-here"     # Your GUID account ID
PASSWORD = "your_password_here"              # Your password
ORGANIZATION_ID = "your-organization-id-here"  # Your organization ID

# Time range (Unix timestamps)
FROM_TIMESTAMP = 1700000000  # Adjust as needed
TO_TIMESTAMP = 1700600000    # Adjust as needed

def authenticate(account_id, password):
    """Authenticate with the Quandify API and retrieve an ID token."""
    payload = {"account_id": account_id, "password": password}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(AUTH_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        
        token = response.json().get("id_token")
        if token:
            logging.info("Authentication successful")
            return token
        else:
            logging.error("No token received in response")
            return None
            
    except requests.exceptions.HTTPError as e:
        logging.error("Authentication failed: HTTP %s - %s", e.response.status_code, e.response.text)
        return None
    except requests.exceptions.RequestException as e:
        logging.error("Network error during authentication: %s", str(e))
        return None
    except Exception as e:
        logging.error("Unexpected error during authentication: %s", str(e))
        return None

def get_aggregated_data(id_token, organization_id, from_ts, to_ts):
    """Fetch aggregated consumption data (totalVolume)."""
    url = f"{BASE_URL}/organization/{organization_id}/nodes/detailed-consumption"
    params = {
        "from": from_ts,
        "to": to_ts,
        "truncate": "day"
    }
    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Navigate to the totalVolume data
        if "aggregate" in data and "total" in data["aggregate"] and "totalVolume" in data["aggregate"]["total"]:
            return data["aggregate"]["total"]["totalVolume"]
        else:
            logging.error("Expected data structure not found in response")
            logging.debug("Response structure: %s", list(data.keys()) if isinstance(data, dict) else type(data))
            return None
            
    except requests.exceptions.HTTPError as e:
        logging.error("Failed to fetch data: HTTP %s - %s", e.response.status_code, e.response.text)
        return None
    except requests.exceptions.RequestException as e:
        logging.error("Network error fetching data: %s", str(e))
        return None
    except Exception as e:
        logging.error("Unexpected error fetching data: %s", str(e))
        return None

def timestamp_to_date(timestamp):
    """Convert Unix timestamp to readable date."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def main():
    """Main function to fetch Quandify consumption data."""
    
    # Validate credentials are set
    if any(cred.startswith("your_") for cred in [ACCOUNT_ID, PASSWORD, ORGANIZATION_ID]):
        logging.error("Please set your actual credentials in the script")
        print("Error: Update ACCOUNT_ID, PASSWORD, and ORGANIZATION_ID with your actual values")
        return
    
    # Show time range for clarity
    logging.info("Fetching data from %s to %s", 
                timestamp_to_date(FROM_TIMESTAMP), 
                timestamp_to_date(TO_TIMESTAMP))
    
    # Step 1: Authenticate
    id_token = authenticate(ACCOUNT_ID, PASSWORD)
    if not id_token:
        logging.error("Authentication failed. Exiting.")
        return
    
    # Step 2: Fetch consumption data
    total_volume = get_aggregated_data(id_token, ORGANIZATION_ID, FROM_TIMESTAMP, TO_TIMESTAMP)
    
    if total_volume is not None:
        logging.info("Successfully retrieved consumption data")
        print(f"Total Volume: {total_volume}")
        return total_volume
    else:
        logging.error("Failed to fetch consumption data")
        return None

if __name__ == "__main__":
    main()
