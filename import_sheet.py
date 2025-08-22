#!/usr/bin/env python
# import_sheet.py

import os
import pandas as pd
import requests
import logging
from app import app, db, OfficePage, FrandevPage
from datetime import datetime
from sqlalchemy.exc import IntegrityError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('import_sheet')

# Global error and success tracking
import_summary = {
    'office': {
        'success_count': 0,
        'error_count': 0,
        'errors': []
    },
    'frandev': {
        'success_count': 0,
        'error_count': 0,
        'errors': []
    }
}

def get_sheet_data(sheet_id, api_key, sheet_name="Sheet1"):
    """
    Download a Google Sheet using the Google Sheets API with API key authentication.
    """
    logger.info(f"Fetching data from Google Sheet ID: {sheet_id}, Sheet: {sheet_name}")
    base_url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{sheet_name}"
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

def deduplicate_data(df, constraint_columns):
    """
    Remove completely duplicate entries from dataframe (checking all columns)
    """
    logger.info(f"Checking for exact duplicates, starting with {len(df)} rows")
    # Check for duplicates across all columns
    duplicate_count = df.duplicated().sum()
    
    if duplicate_count > 0:
        logger.warning(f"Found {duplicate_count} completely duplicate entries in Google Sheet data")
        # Log some examples of duplicate rows
        duplicate_rows = df[df.duplicated(keep=False)]
        for idx, row in duplicate_rows.head(5).iterrows():
            logger.warning(f"Duplicate row {idx + 2}: {', '.join([str(row[col]) for col in constraint_columns])}")
        
        # Keep only unique rows (checking all columns)
        df = df.drop_duplicates()
        logger.info(f"After removing exact duplicates, {len(df)} rows remain")
    else:
        logger.info("No exact duplicates found in the data")
    
    # Also log info about constraint duplicates (important for debugging database errors)
    constraint_dupes = df.duplicated(subset=constraint_columns).sum()
    if constraint_dupes > 0:
        logger.warning(f"Warning: {constraint_dupes} rows have duplicate key constraints ({', '.join(constraint_columns)})")
        
        # Log detailed information about constraint duplicates
        constraint_duplicate_rows = df[df.duplicated(subset=constraint_columns, keep=False)]
        logger.warning("Constraint duplicate details:")
        for idx, row in constraint_duplicate_rows.head(10).iterrows():
            logger.warning(f"  Row {idx + 2}: {' | '.join([str(row[col]) for col in constraint_columns])}")
        
        if len(constraint_duplicate_rows) > 10:
            logger.warning(f"  ... and {len(constraint_duplicate_rows) - 10} more duplicate constraint rows")
        
        logger.warning("These may cause database errors during import if not handled individually")
    
    return df

def import_office_sheet(sheet_id, api_key):
    """Import the original office sheet data (Sheet1)"""
    logger.info("Importing office sheet data...")
    
    try:
        # Get data from Google Sheets API
        df = get_sheet_data(sheet_id, api_key, "Sheet1")
        
        # Reset index to have consistent row numbering
        df = df.reset_index(drop=True)
        
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
            logger.error(f"Available columns: {', '.join(df.columns.tolist())}")
            raise Exception(error_msg)
        
        # Deduplicate the data before importing
        df = deduplicate_data(df, ['state_office_token', 'area_served_token', 'service_token'])
        
        with app.app_context():
            # Start a transaction
            try:
                # Delete all existing pages
                logger.info("Deleting existing office pages...")
                deleted_count = OfficePage.query.count()
                OfficePage.query.delete()
                logger.info(f"Deleted {deleted_count} existing office pages")
                
                # Insert new pages
                logger.info(f"Importing {len(df)} office pages...")
                success_count = 0
                error_count = 0
                error_details = []
                
                # Process in smaller batches to avoid issues with very large sheets
                batch_size = 50
                total_batches = (len(df) + batch_size - 1) // batch_size
                
                for batch_num in range(total_batches):
                    start_idx = batch_num * batch_size
                    end_idx = min(start_idx + batch_size, len(df))
                    batch = df.iloc[start_idx:end_idx]
                    
                    logger.info(f"Processing batch {batch_num + 1}/{total_batches} (rows {start_idx + 2}-{end_idx + 1} in sheet)")
                    
                    batch_success = 0
                    batch_errors = 0
                    
                    for df_idx, row in batch.iterrows():
                        sheet_row_num = df_idx + 2  # +2 because: +1 for 0-based index, +1 for header row
                        try:
                            # Convert any NaN values to empty strings
                            row = row.fillna('')
                            
                            # Validate that required fields are not empty
                            empty_required_fields = []
                            for field in required_columns:
                                if not str(row[field]).strip():
                                    empty_required_fields.append(field)
                            
                            if empty_required_fields:
                                error_msg = f"Row {sheet_row_num}: Empty required fields: {', '.join(empty_required_fields)}"
                                logger.error(error_msg)
                                error_details.append({
                                    'row': sheet_row_num,
                                    'type': 'Empty Required Fields',
                                    'message': error_msg,
                                    'details': f"Fields: {', '.join(empty_required_fields)}"
                                })
                                batch_errors += 1
                                error_count += 1
                                continue
                            
                            office_page = OfficePage(
                                state_office_token=str(row['state_office_token']).strip(),
                                area_served_token=str(row['area_served_token']).strip(),
                                service_token=str(row['service_token']).strip(),
                                meta_title=str(row['meta_title']).strip(),
                                meta_description=str(row['meta_description']).strip(),
                                page_title=str(row['page_title']).strip(),
                                page_content=str(row['page_content']).strip()
                            )
                            db.session.add(office_page)
                            db.session.flush()  # Check constraints without committing
                            batch_success += 1
                            success_count += 1
                            
                        except IntegrityError as e:
                            # If there's a constraint violation, log detailed information
                            db.session.rollback()
                            error_msg = f"Row {sheet_row_num}: Duplicate key constraint violation"
                            detailed_msg = f"state_office_token: '{row['state_office_token']}', area_served_token: '{row['area_served_token']}', service_token: '{row['service_token']}'"
                            
                            logger.error(error_msg)
                            logger.error(f"  - {detailed_msg}")
                            error_details.append({
                                'row': sheet_row_num,
                                'type': 'Duplicate Key Constraint',
                                'message': error_msg,
                                'details': detailed_msg
                            })
                            batch_errors += 1
                            error_count += 1
                            
                        except Exception as e:
                            db.session.rollback()
                            error_msg = f"Row {sheet_row_num}: Unexpected error during processing"
                            detailed_msg = f"Error: {str(e)} (Type: {type(e).__name__})"
                            
                            logger.error(error_msg)
                            logger.error(f"  - {detailed_msg}")
                            error_details.append({
                                'row': sheet_row_num,
                                'type': 'Unexpected Error',
                                'message': error_msg,
                                'details': detailed_msg
                            })
                            batch_errors += 1
                            error_count += 1
                    
                    # Commit each batch
                    try:
                        db.session.commit()
                        logger.info(f"Committed batch {batch_num + 1}: {batch_success} successful, {batch_errors} errors")
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Failed to commit batch {batch_num + 1}: {str(e)}")
                        error_count += batch_success  # Count successful ones as errors since they weren't committed
                        success_count -= batch_success
                
                # Update global summary
                import_summary['office']['success_count'] = success_count
                import_summary['office']['error_count'] = error_count
                import_summary['office']['errors'] = error_details
                
                logger.info(f"Office import completed: {success_count} pages imported successfully, {error_count} errors encountered")
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Transaction error: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                raise
            
    except Exception as e:
        logger.error(f"Error during office import: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        raise

def import_frandev_sheet(sheet_id, api_key):
    """Import the Frandev sheet data (Fran Dev tab)"""
    logger.info("Importing Frandev sheet data...")
    
    try:
        # Get data from Google Sheets API
        df = get_sheet_data(sheet_id, api_key, "Fran Dev")
        
        # Reset index to have consistent row numbering
        df = df.reset_index(drop=True)
        
        # Verify required columns exist
        required_columns = [
            'state_token', 'city_token', 'clai_page_token',
            'meta_title', 'meta_description', 'page_title', 'page_content', 'link_label'
        ]
        
        # Check if all required columns exist in the dataframe
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            error_msg = f"Missing required columns in Frandev sheet: {', '.join(missing_columns)}"
            logger.error(error_msg)
            logger.error(f"Available columns: {', '.join(df.columns.tolist())}")
            raise Exception(error_msg)
        
        # Deduplicate the data before importing
        df = deduplicate_data(df, ['state_token', 'city_token', 'clai_page_token'])
        
        with app.app_context():
            # Start a transaction
            try:
                # Delete all existing Frandev pages
                logger.info("Deleting existing Frandev pages...")
                deleted_count = FrandevPage.query.count()
                FrandevPage.query.delete()
                logger.info(f"Deleted {deleted_count} existing Frandev pages")
                
                # Insert new pages
                logger.info(f"Importing {len(df)} Frandev pages...")
                success_count = 0
                error_count = 0
                error_details = []
                
                # Process in smaller batches
                batch_size = 50
                total_batches = (len(df) + batch_size - 1) // batch_size
                
                for batch_num in range(total_batches):
                    start_idx = batch_num * batch_size
                    end_idx = min(start_idx + batch_size, len(df))
                    batch = df.iloc[start_idx:end_idx]
                    
                    logger.info(f"Processing batch {batch_num + 1}/{total_batches} (rows {start_idx + 2}-{end_idx + 1} in sheet)")
                    
                    batch_success = 0
                    batch_errors = 0
                    
                    for df_idx, row in batch.iterrows():
                        sheet_row_num = df_idx + 2
                        try:
                            # Convert any NaN values to empty strings
                            row = row.fillna('')
                            
                            # Validate that required fields are not empty
                            empty_required_fields = []
                            for field in ['state_token', 'city_token', 'clai_page_token']:
                                if not str(row[field]).strip():
                                    empty_required_fields.append(field)
                            
                            if empty_required_fields:
                                error_msg = f"Row {sheet_row_num}: Empty required fields: {', '.join(empty_required_fields)}"
                                logger.error(error_msg)
                                error_details.append({
                                    'row': sheet_row_num,
                                    'type': 'Empty Required Fields',
                                    'message': error_msg,
                                    'details': f"Fields: {', '.join(empty_required_fields)}"
                                })
                                batch_errors += 1
                                error_count += 1
                                continue
                            
                            frandev_page = FrandevPage(
                                state_token=str(row['state_token']).strip(),
                                city_token=str(row['city_token']).strip(),
                                clai_page_token=str(row['clai_page_token']).strip(),
                                meta_title=str(row['meta_title']).strip() if row.get('meta_title') else '',
                                meta_description=str(row['meta_description']).strip() if row.get('meta_description') else '',
                                page_title=str(row['page_title']).strip() if row.get('page_title') else '',
                                page_content=str(row['page_content']).strip() if row.get('page_content') else '',
                                link_label=str(row['link_label']).strip() if row.get('link_label') else ''
                            )
                            db.session.add(frandev_page)
                            db.session.flush()
                            batch_success += 1
                            success_count += 1
                            
                        except IntegrityError as e:
                            db.session.rollback()
                            error_msg = f"Row {sheet_row_num}: Duplicate key constraint violation"
                            detailed_msg = f"state_token: '{row['state_token']}', city_token: '{row['city_token']}', clai_page_token: '{row['clai_page_token']}'"
                            
                            logger.error(error_msg)
                            logger.error(f"  - {detailed_msg}")
                            error_details.append({
                                'row': sheet_row_num,
                                'type': 'Duplicate Key Constraint',
                                'message': error_msg,
                                'details': detailed_msg
                            })
                            batch_errors += 1
                            error_count += 1
                            
                        except Exception as e:
                            db.session.rollback()
                            error_msg = f"Row {sheet_row_num}: Unexpected error during processing"
                            detailed_msg = f"Error: {str(e)} (Type: {type(e).__name__})"
                            
                            logger.error(error_msg)
                            logger.error(f"  - {detailed_msg}")
                            error_details.append({
                                'row': sheet_row_num,
                                'type': 'Unexpected Error',
                                'message': error_msg,
                                'details': detailed_msg
                            })
                            batch_errors += 1
                            error_count += 1
                    
                    # Commit each batch
                    try:
                        db.session.commit()
                        logger.info(f"Committed batch {batch_num + 1}: {batch_success} successful, {batch_errors} errors")
                    except Exception as e:
                        db.session.rollback()
                        logger.error(f"Failed to commit batch {batch_num + 1}: {str(e)}")
                        error_count += batch_success
                        success_count -= batch_success
                
                # Update global summary
                import_summary['frandev']['success_count'] = success_count
                import_summary['frandev']['error_count'] = error_count
                import_summary['frandev']['errors'] = error_details
                
                logger.info(f"Frandev import completed: {success_count} pages imported successfully, {error_count} errors encountered")
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Transaction error: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                raise
            
    except Exception as e:
        logger.error(f"Error during Frandev import: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        raise

def print_final_summary():
    """Print a comprehensive summary of the entire import process"""
    total_success = import_summary['office']['success_count'] + import_summary['frandev']['success_count']
    total_errors = import_summary['office']['error_count'] + import_summary['frandev']['error_count']
    
    logger.info("\n" + "="*80)
    logger.info("FINAL IMPORT SUMMARY")
    logger.info("="*80)
    
    logger.info(f"\nTOTAL PAGES SUCCESSFULLY UPLOADED: {total_success}")
    logger.info(f"  - Office Pages: {import_summary['office']['success_count']}")
    logger.info(f"  - Frandev Pages: {import_summary['frandev']['success_count']}")
    
    logger.info(f"\nTOTAL ERRORS: {total_errors}")
    logger.info(f"  - Office Errors: {import_summary['office']['error_count']}")
    logger.info(f"  - Frandev Errors: {import_summary['frandev']['error_count']}")
    
    # Print all Office errors
    if import_summary['office']['errors']:
        logger.info("\n" + "-"*40)
        logger.info("OFFICE SHEET ERRORS:")
        logger.info("-"*40)
        for i, error in enumerate(import_summary['office']['errors'], 1):
            logger.info(f"\n{i}. {error['message']}")
            logger.info(f"   Type: {error['type']}")
            logger.info(f"   Details: {error['details']}")
    
    # Print all Frandev errors
    if import_summary['frandev']['errors']:
        logger.info("\n" + "-"*40)
        logger.info("FRANDEV SHEET ERRORS:")
        logger.info("-"*40)
        for i, error in enumerate(import_summary['frandev']['errors'], 1):
            logger.info(f"\n{i}. {error['message']}")
            logger.info(f"   Type: {error['type']}")
            logger.info(f"   Details: {error['details']}")
    
    logger.info("\n" + "="*80)
    logger.info(f"Import process completed with {total_success} successful uploads and {total_errors} errors")
    logger.info("="*80)

def import_sheet_to_db():
    """Import both Google Sheet tabs into the database."""
    logger.info(f"Starting full import at {datetime.now()}")
    
    # Google Sheet ID from the URL
    sheet_id = "1zGndhNnFpoBFIlh41yh9cEZ7ML4miWRGyuKNuNNlGrs"
    
    # Get API key from environment
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        error_msg = "GOOGLE_API_KEY environment variable is not set"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    overall_success = True
    
    # Import office sheet
    try:
        import_office_sheet(sheet_id, api_key)
    except Exception as e:
        logger.error(f"Failed to import office sheet: {str(e)}")
        overall_success = False
    
    # Import Frandev sheet
    try:
        import_frandev_sheet(sheet_id, api_key)
    except Exception as e:
        logger.error(f"Failed to import Frandev sheet: {str(e)}")
        overall_success = False
    
    logger.info(f"Import process finished at {datetime.now()}")
    
    # Print comprehensive final summary
    print_final_summary()
    
    return overall_success

if __name__ == "__main__":
    import_sheet_to_db()
