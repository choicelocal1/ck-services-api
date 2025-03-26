import os
import pandas as pd
import requests
from app import app, db, OfficePage
from datetime import datetime

def get_sheet_data(sheet_id, api_key):
    """
    Download a Google Sheet using the Google Sheets API with API key authentication.
    """
    base_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1"
    params = {
        "key": api_key,
        "valueRenderOption": "FORMATTED_VALUE",
        "dateTimeRenderOption": "FORMATTED_STRING"
    }
    
    response = requests.get(base_url, params=params)
    
    if response.status_code != 200:
        raise Exception(f"Failed to download sheet: {response.status_code}, {response.text}")
    
    data = response.json()
    
    if 'values' not in data:
        raise Exception("No values found in the sheet response")
    
    # Extract headers and rows
    headers = [h.strip().lower().replace(' ', '_') for h in data['values'][0]]
    rows = data['values'][1:]
    
    # Convert to dataframe
    df = pd.DataFrame(rows, columns=headers)
    
    return df

def import_sheet_to_db():
    """Import Google Sheet data into the database."""
    print(f"Starting import at {datetime.now()}")
    
    # Google Sheet ID from the URL
    sheet_id = "1zGndhNnFpoBFIlh41yh9cEZ7ML4miWRGyuKNuNNlGrs"
    
    # Get API key from environment
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set")
    
    try:
        # Get data from Google Sheets API
        df = get_sheet_data(sheet_id, api_key)
        
        # Verify required columns exist
        required_columns = [
            'state_office_token', 'area_served_token', 'service_token',
            'meta_title', 'meta_description', 'page_title', 'page_content'
        ]
        
        # Check if all required columns exist in the dataframe
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise Exception(f"Missing required columns in Google Sheet: {', '.join(missing_columns)}")
        
        with app.app_context():
            # Delete all existing pages
            print("Deleting existing pages...")
            OfficePage.query.delete()
            
            # Insert new pages
            print(f"Importing {len(df)} pages...")
            for _, row in df.iterrows():
                # Convert any NaN values to empty strings
                row = row.fillna('')
                
                office_page = OfficePage(
                    state_office_token=row['state_office_token'],
                    area_served_token=row['area_served_token'],
                    service_token=row['service_token'],
                    meta_title=row['meta_title'],
                    meta_description=row['meta_description'],
                    page_title=row['page_title'],
                    page_content=row['page_content']
                )
                db.session.add(office_page)
            
            # Commit changes
            db.session.commit()
            print(f"Import completed successfully at {datetime.now()}. Imported {len(df)} records.")
            
    except Exception as e:
        print(f"Error during import: {e}")
        return False
    
    return True

if __name__ == "__main__":
    import_sheet_to_db()
