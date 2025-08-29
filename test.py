import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Base URLs
AUTH_URL = "https://auth.quandify.com/api/auth/login"  # Fixed: Added proper endpoint
BASE_URL = "https://api.quandify.com"

# Replace with your actual credentials
ACCOUNT_ID = "your_account_id_here"  # Your account ID
PASSWORD = "your_password_here"      # Your password
ORGANIZATION_ID = "your_org_id_here" # Your organization ID

# Time range (example: Unix timestamps)
FROM_TIMESTAMP = 1700000000
TO_TIMESTAMP = 1700600000

def authenticate(account_id, password):
    """Authenticate with the API and retrieve an ID token."""
    payload = {"account_id": account_id, "password": password}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(AUTH_URL, json=payload, headers=headers)
        response.raise_for_status()  # Raises HTTPError for bad responses
        
        return response.json().get("id_token")
        
    except requests.exceptions.HTTPError as e:
        logging.error("Authentication failed with HTTP error: %s - %s", e, response.text)
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
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Raises HTTPError for bad responses
        
        data = response.json()
        
        # Check if the expected data structure exists
        if "aggregate" in data and "total" in data["aggregate"] and "totalVolume" in data["aggregate"]["total"]:
            return data["aggregate"]["total"]["totalVolume"]
        else:
            logging.error("Unexpected data structure in response: %s", data)
            return None
            
    except requests.exceptions.HTTPError as e:
        logging.error("Failed to fetch data with HTTP error: %s - %s", e, response.text if 'response' in locals() else 'No response')
        return None
    except requests.exceptions.RequestException as e:
        logging.error("Network error fetching data: %s", str(e))
        return None
    except KeyError as e:
        logging.error("Missing key in response data: %s", str(e))
        return None
    except Exception as e:
        logging.error("Unexpected error fetching data: %s", str(e))
        return None

def main():
    # Validate credentials are set
    if not all([ACCOUNT_ID != "your_account_id_here", 
                PASSWORD != "your_password_here", 
                ORGANIZATION_ID != "your_org_id_here"]):
        logging.error("Please set your actual credentials in the script")
        return
    
    # Step 1: Authenticate and get the ID token
    logging.info("Authenticating with account ID: %s", ACCOUNT_ID)
    id_token = authenticate(ACCOUNT_ID, PASSWORD)
    
    if not id_token:
        logging.error("Authentication failed. Exiting.")
        return
    
    logging.info("Authentication successful")
    
    # Step 2: Fetch the total volume
    logging.info("Fetching data for organization: %s", ORGANIZATION_ID)
    total_volume = get_aggregated_data(id_token, ORGANIZATION_ID, FROM_TIMESTAMP, TO_TIMESTAMP)
    
    if total_volume is not None:
        logging.info("Total Volume: %s", total_volume)
        print(f"Total Volume: {total_volume}")
    else:
        logging.error("Failed to fetch total volume.")

# Run the script
if __name__ == "__main__":
    main()
