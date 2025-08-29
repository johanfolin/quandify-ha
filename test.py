import requests
import logging

# Base URLs
AUTH_URL = "https://auth.quandify.com/"
BASE_URL = "https://api.quandify.com"

# Replace with your actual credentials
ACCOUNT_ID =   # Your account ID
PASSWORD =   # Your password
ORGANIZATION_ID =  # Your organization ID

# Time range (example: Unix timestamps)
FROM_TIMESTAMP = 1700000000
TO_TIMESTAMP = 1700600000


def authenticate(account_id, password):
    """Authenticate with the API and retrieve an ID token."""
    payload = {"account_id": account_id, "password": password}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(AUTH_URL, json=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get("id_token")
        else:
            logging.error("Authentication failed: %s", response.text)
            return None
    except Exception as e:
        logging.error("Error during authentication: %s", str(e))
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
        if response.status_code == 200:
            data = response.json()
            return data["aggregate"]["total"]["totalVolume"]  # Return totalVolume
        else:
            logging.error("Failed to fetch data: %s", response.text)
            return None
    except Exception as e:
        logging.error("Error fetching data: %s", str(e))
        return None


# Main Script
def main():
    # Step 1: Authenticate and get the ID token
    id_token = authenticate(ACCOUNT_ID, PASSWORD)
    if not id_token:
        logging.error("Authentication failed. Exiting.")
        return

    # Step 2: Fetch the total volume
    total_volume = get_aggregated_data(id_token, ORGANIZATION_ID, FROM_TIMESTAMP, TO_TIMESTAMP)
    if total_volume is not None:
        # Log or print the total volume (can also save to Home Assistant state)
        logging.info("Total Volume: %s", total_volume)
        print(f"Total Volume: {total_volume}")  # For debugging
    else:
        logging.error("Failed to fetch total volume.")


# Run the script
if __name__ == "__main__":
    main()
