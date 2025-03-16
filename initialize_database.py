#!/usr/bin/env python3
# initialize_database.py - Standalone script to create and populate the waste sorting database
import sqlite3
import os
import json
from datetime import datetime, timedelta
import logging
import random
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("db_init.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DatabaseInitializer")

# Database path - make sure this matches your app's database path
DB_PATH = './data/sorting_data.db'

def initialize_database():
    """Initialize the database schema and sample data"""
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        logger.info(f"Initializing database at {DB_PATH}")
        
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        logger.info("Creating database tables...")
        
        # Create sort_events table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sort_events (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            item_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            sort_destination TEXT NOT NULL,
            image_id TEXT,
            user_id TEXT,
            metadata TEXT
        )
        ''')
        
        # Create images table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            image_data BLOB NOT NULL,
            thumbnail BLOB,
            metadata TEXT
        )
        ''')
        
        # Create statistics table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            date TEXT PRIMARY KEY,
            can_count INTEGER DEFAULT 0,
            recycling_count INTEGER DEFAULT 0,
            garbage_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            metadata TEXT
        )
        ''')
        
        # Check if we need to generate sample data
        cursor.execute("SELECT COUNT(*) FROM statistics")
        if cursor.fetchone()[0] == 0:
            generate_sample_data(cursor)
            
        conn.commit()
        conn.close()
        
        logger.info("Database initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def generate_sample_data(cursor):
    """Generate sample data for demonstration purposes"""
    logger.info("Generating sample data...")
    
    # Generate sample statistics for the last 30 days
    today = datetime.now()
    
    # Sample event types
    item_types = ['can', 'recycling', 'garbage']
    destinations = ['recycling', 'recycling', 'garbage']  # Cans and recycling go to recycling, garbage to garbage
    
    # Generate sample events
    logger.info("Generating sample sort events...")
    event_count = 0
    
    for i in range(30, 0, -1):
        date = (today - timedelta(days=i))
        date_str = date.strftime('%Y-%m-%d')
        
        # Generate between 5-20 events per day
        daily_events = random.randint(5, 20)
        
        # Counters for statistics
        can_count = 0
        recycling_count = 0
        garbage_count = 0
        
        for j in range(daily_events):
            # Random event timestamp within the day
            hour = random.randint(8, 17)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            event_time = date.replace(hour=hour, minute=minute, second=second)
            timestamp = event_time.isoformat()
            
            # Random item type and destination
            type_index = random.randint(0, 2)
            item_type = item_types[type_index]
            sort_destination = destinations[type_index]
            
            # Random confidence level
            confidence = random.uniform(0.6, 0.99)
            
            # Create event ID
            event_id = str(uuid.uuid4())
            
            # Metadata
            metadata = {
                "simulation": True,
                "session_id": f"sim-{date_str}"
            }
            metadata_json = json.dumps(metadata)
            
            # Insert event
            cursor.execute(
                "INSERT INTO sort_events (id, timestamp, item_type, confidence, sort_destination, image_id, metadata) "
                "VALUES (?, ?, ?, ?, ?, NULL, ?)",
                (event_id, timestamp, item_type, confidence, sort_destination, metadata_json)
            )
            
            # Update counters
            if item_type == 'can':
                can_count += 1
            elif item_type == 'recycling':
                recycling_count += 1
            else:  # garbage
                garbage_count += 1
                
            event_count += 1
        
        # Create daily statistics entry
        total_count = can_count + recycling_count + garbage_count
        
        cursor.execute(
            "INSERT INTO statistics (date, can_count, recycling_count, garbage_count, total_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (date_str, can_count, recycling_count, garbage_count, total_count)
        )
    
    logger.info(f"Generated {event_count} sample events across 30 days")

if __name__ == "__main__":
    print("===== Database Initialization Script =====")
    print(f"This will create or reset the database at: {DB_PATH}")
    print("WARNING: If the database already exists, existing data will remain but may be modified.")
    
    confirm = input("Continue? (y/n): ")
    if confirm.lower() == 'y':
        initialize_database()
        print("Database initialization complete!")
    else:
        print("Operation cancelled.")