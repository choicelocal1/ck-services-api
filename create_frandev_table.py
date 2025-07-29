#!/usr/bin/env python
"""One-time script to create the Frandev table"""

import os
from app import app, db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_frandev_table():
    """Create the Frandev table in the database"""
    
    create_table_sql = """
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE SCHEMA IF NOT EXISTS sundry;
    
    CREATE TABLE IF NOT EXISTS sundry.choicelocal_clai_frandev (
        id uuid DEFAULT uuid_generate_v4() PRIMARY KEY,
        state_token text NOT NULL,
        city_token text NOT NULL,
        clai_page_token text NOT NULL,
        meta_title text,
        meta_description text,
        page_title text,
        page_content text,
        link_label text,
        UNIQUE(state_token, city_token, clai_page_token)
    );
    """
    
    with app.app_context():
        try:
            # Execute the SQL
            db.session.execute(text(create_table_sql))
            db.session.commit()
            logger.info("Successfully created sundry.choicelocal_clai_frandev table")
            
            # Verify the table was created
            result = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'sundry' 
                AND table_name = 'choicelocal_clai_frandev'
            """))
            count = result.scalar()
            
            if count == 1:
                logger.info("Table creation verified successfully")
            else:
                logger.error("Table creation could not be verified")
                
        except Exception as e:
            logger.error(f"Error creating table: {str(e)}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    create_frandev_table()
