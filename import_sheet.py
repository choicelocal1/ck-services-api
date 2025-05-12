#!/usr/bin/env python
# import_sheet.py

import os
import pandas as pd
import requests
import logging
from app import app, db, OfficePage
from datetime import datetime
from sqlalchemy.exc import IntegrityError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('import_sheet')

def get_sheet_data(sheet_id, api_key):
    """
    Download a Google Sheet using the Google Sheets API with API key authentication.
    """
    logger.info(f"Fetching data from Google Sheet ID: {sheet_id}")
    base_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Sheet1"
    params = {
        "key": api_key,
        "valueRenderOption": "FORMATTED_VALUE",
        "dateTimeRenderOption": "FORMATTED_STRING"
    }
    
    response = requests.get(base_url, params=params)
    
    if response.status_code != 200:
        error_msg = f"Failed to download sheet: {response.status_code}, {response.text}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    data = response.json()
    
    if 'values' not in data:
        error_msg = "No values found in the sheet response"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    # Extract headers and rows
    headers = [h.strip().lower().replace(' ', '_') for h in data['values'][0]]
    rows = data['values'][1:]
    
    # Convert to dataframe
    df = pd.DataFrame(rows, columns=headers)
    logger.info(f"Fetched {len(df)} rows from Google Sheet")
    
    return df

def deduplicate_data(df):
    """
    Remove completely duplicate entries from dataframe (checking all columns)
    """
    logger.info(f"Checking for exact duplicates, starting with {len(df)} rows")
    # Check for duplicates across all columns
    duplicate_count = df.duplicated().sum()
    
    if duplicate_count > 0:
        logger.warning(f"Found {duplicate_count} completely duplicate entries in Google Sheet data")
        # Keep only unique rows (checking all columns)
        df = df.drop_duplicates()
        logger.info(f"After removing exact duplicates, {len(df)} rows remain")
    else:
        logger.info("No exact duplicates found in the data")
    
    # Also log info about constraint duplicates (important for debugging database errors)
    constraint_dupes = df.duplicated(subset=['state_office_token', 'area_served_token', 'service_token']).sum()
    if constraint_dupes > 0:
        logger.warning(f"Warning: {constraint_dupes} rows have duplicate key constraints (state_office_token, area_served_token, service_token)")
        logger.warning("These may cause database errors during import if not handled individually")
    
    return df

def import_sheet_to_db():
    """Import Google Sheet data into the database."""
    logger.info(f"Starting import at {datetime.now()}")
    
    # Google Sheet ID from the URL
    sheet_id = "1zGndhNnFpoBFIlh41yh9cEZ7ML4miWRGyuKNuNNlGrs"
    
    # Get API key from environment
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        error_msg = "GOOGLE_API_KEY environment variable is not set"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
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
            error_msg = f"Missing required columns in Google Sheet: {', '.join(missing_columns)}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # Deduplicate the data before importing
        df = deduplicate_data(df)
        
        with app.app_context():
            # Start a transaction
            try:
                # Delete all existing pages
                logger.info("Deleting existing pages...")
                OfficePage.query.delete()
                
                # Insert new pages
                logger.info(f"Importing {len(df)} pages...")
                success_count = 0
                error_count = 0
                
                # Process in smaller batches to avoid issues with very large sheets
                batch_size = 100
                total_batches = (len(df) + batch_size - 1) // batch_size
                
                for batch_num in range(total_batches):
                    start_idx = batch_num * batch_size
                    end_idx = min(start_idx + batch_size, len(df))
                    batch = df.iloc[start_idx:end_idx]
                    
                    logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({start_idx}-{end_idx})")
                    
                    for _, row in batch.iterrows():
                        try:
                            # Convert any NaN values to empty strings
                            row = row.fillna('')
                            
                            office_page = OfficePage(
                                state_office_token=str(row['state_office_token']),
                                area_served_token=str(row['area_served_token']),
                                service_token=str(row['service_token']),
                                meta_title=str(row['meta_title']),
                                meta_description=str(row['meta_description']),
                                page_title=str(row['page_title']),
                                page_content=str(row['page_content'])
                            )
                            db.session.add(office_page)
                            db.session.flush()  # Check constraints without committing
                            success_count += 1
                        except IntegrityError as e:
                            # If there's a constraint violation, log it and continue
                            db.session.rollback()
                            logger.warning(f"Skipping duplicate entry: {row['state_office_token']}, {row['area_served_token']}, {row['service_token']}")
                            error_count += 1
                        except Exception as e:
                            db.session.rollback()
                            logger.error(f"Error processing row: {str(e)}")
                            error_count += 1
                    
                    # Commit each batch
                    db.session.commit()
                    logger.info(f"Committed batch {batch_num + 1}")
                
                logger.info(f"Import completed successfully: {success_count} pages imported, {error_count} errors")
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Transaction error: {str(e)}")
                raise
            
    except Exception as e:
        logger.error(f"Error during import: {str(e)}")
        return False
    
    logger.info(f"Import process finished at {datetime.now()}")
    return True

if __name__ == "__main__":
    import_sheet_to_db()
