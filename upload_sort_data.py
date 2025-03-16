#!/usr/bin/env python3
# upload_sort_data.py - Script to upload waste sorting data to the website
import os
import json
import requests
import time
import sqlite3
from datetime import datetime, timedelta
import logging
import argparse
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("upload.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DataUploader")

# Default paths and settings
DEFAULT_DB_PATH = './data/sorting_data.db'
DEFAULT_CONFIG_PATH = './upload_config.json'
DEFAULT_SERVER_URL = 'http://everythingyoueverwantedtoknowaboutgarbagebutwereafraidtoask.co/upload_data.php'
API_KEY = 'ws_6f28a91e7d3c4b5f8a2e9d0c7b6a5f4'  # This must match the key in upload_data.php

def load_config():
    """Load or create configuration"""
    config_path = DEFAULT_CONFIG_PATH
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                logger.info("Configuration loaded")
                return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    # Create default config
    config = {
        'server_url': DEFAULT_SERVER_URL,
        'api_key': API_KEY,
        'upload_interval_minutes': 15,
        'max_events_per_upload': 100,
        'retry_attempts': 3,
        'retry_delay_seconds': 30,
        'last_upload_time': datetime.now().isoformat()
    }
    
    # Save default config
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Default configuration created at {config_path}")
    except Exception as e:
        logger.error(f"Error creating default config: {e}")
    
    return config

def save_config(config):
    """Save configuration to file"""
    config_path = DEFAULT_CONFIG_PATH
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved")
        return True
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def get_new_events(db_path, last_upload_time, max_events=100):
    """Get new events from database since last upload"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get events newer than last upload time
        cursor.execute("""
            SELECT 
                id, timestamp, item_type, confidence, sort_destination, 
                image_id, user_id, metadata
            FROM sort_events 
            WHERE timestamp > ? 
            ORDER BY timestamp ASC 
            LIMIT ?
        """, (last_upload_time, max_events))
        
        rows = cursor.fetchall()
        events = []
        
        for row in rows:
            event = dict(row)
            
            # Parse metadata if it's a JSON string
            if event.get('metadata') and isinstance(event['metadata'], str):
                try:
                    event['metadata'] = json.loads(event['metadata'])
                except:
                    pass  # Keep as string if parsing fails
            
            events.append(event)
        
        # Get the most recent timestamp
        if events:
            most_recent = events[-1]['timestamp']
        else:
            most_recent = last_upload_time
            
        conn.close()
        logger.info(f"Found {len(events)} new events since {last_upload_time}")
        return events, most_recent
        
    except Exception as e:
        logger.error(f"Database error when getting events: {e}")
        return [], last_upload_time

def get_daily_statistics(db_path):
    """Get all daily statistics"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all statistics
        cursor.execute("""
            SELECT date, can_count, recycling_count, garbage_count, total_count, metadata  
            FROM statistics 
            ORDER BY date ASC
        """)
        
        rows = cursor.fetchall()
        stats = []
        
        for row in rows:
            stat = dict(row)
            
            # Parse metadata if it's a JSON string
            if stat.get('metadata') and isinstance(stat['metadata'], str):
                try:
                    stat['metadata'] = json.loads(stat['metadata'])
                except:
                    pass  # Keep as string if parsing fails
            
            stats.append(stat)
        
        conn.close()
        logger.info(f"Retrieved {len(stats)} daily statistics records")
        return stats
        
    except Exception as e:
        logger.error(f"Database error when getting statistics: {e}")
        return []

def upload_data(server_url, api_key, events, stats):
    """Upload data to server"""
    try:
        # Prepare payload
        payload = {
            'api_key': api_key,
            'timestamp': datetime.now().isoformat(),
            'events': events,
            'stats': stats
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'WasteSorter/1.0'
        }
        
        # Send request
        logger.info(f"Sending data to {server_url}: {len(events)} events, {len(stats)} stats")
        response = requests.post(
            server_url,
            json=payload,
            headers=headers,
            timeout=60  # Increased timeout for slow connections
        )
        
        # Check response
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    logger.info(f"Upload successful: {result.get('message', 'No message')}")
                    return True
                else:
                    logger.error(f"Upload error: {result.get('error', 'Unknown error')}")
                    logger.debug(f"Server response: {response.text}")
                    return False
            except Exception as e:
                logger.error(f"Error parsing response: {e}")
                logger.debug(f"Server response: {response.text}")
                return False
        else:
            logger.error(f"HTTP error: {response.status_code}")
            logger.debug(f"Server response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("Upload timed out")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("Connection error - check internet or server availability")
        return False
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return False

def run_upload(db_path, force=False):
    """Run the upload process"""
    # Load configuration
    config = load_config()
    server_url = config.get('server_url', DEFAULT_SERVER_URL)
    api_key = config.get('api_key', API_KEY)
    max_events = config.get('max_events_per_upload', 100)
    last_upload_time = config.get('last_upload_time', (datetime.now() - timedelta(days=30)).isoformat())
    retry_attempts = config.get('retry_attempts', 3)
    retry_delay = config.get('retry_delay_seconds', 30)
    
    logger.info(f"Starting upload (last upload: {last_upload_time})")
    
    # Get new events
    events, most_recent = get_new_events(db_path, last_upload_time, max_events)
    
    if not events and not force:
        logger.info("No new events to upload")
        return True
    
    # Get all statistics
    stats = get_daily_statistics(db_path)
    
    # Try to upload with retries
    success = False
    for attempt in range(retry_attempts):
        if attempt > 0:
            logger.info(f"Retry attempt {attempt+1}/{retry_attempts}...")
            time.sleep(retry_delay)
        
        success = upload_data(server_url, api_key, events, stats)
        if success:
            break
    
    # Update configuration
    if success:
        config['last_upload_time'] = most_recent if events else datetime.now().isoformat()
        save_config(config)
        logger.info(f"Upload complete - {len(events)} events and {len(stats)} stats processed")
        return True
    else:
        logger.warning(f"Upload failed after {retry_attempts} attempts")
        return False

def run_daemon_mode(db_path):
    """Run in daemon mode, uploading data periodically"""
    config = load_config()
    interval_minutes = config.get('upload_interval_minutes', 15)
    interval_seconds = interval_minutes * 60
    
    logger.info(f"Starting daemon mode (interval: {interval_minutes} minutes)")
    
    try:
        while True:
            start_time = time.time()
            
            # Run upload
            run_upload(db_path)
            
            # Calculate sleep time
            elapsed = time.time() - start_time
            sleep_time = max(1, interval_seconds - elapsed)
            
            logger.info(f"Next upload in {sleep_time:.1f} seconds")
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        logger.info("Daemon stopped by user")
    except Exception as e:
        logger.error(f"Daemon error: {e}")

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description='Upload waste sorting data to website')
    parser.add_argument('--db', default=DEFAULT_DB_PATH, help='Path to database file')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    parser.add_argument('--force', action='store_true', help='Force upload even if no new events')
    
    args = parser.parse_args()
    
    # Run in daemon mode or single upload
    if args.daemon:
        run_daemon_mode(args.db)
    else:
        run_upload(args.db, args.force)

if __name__ == '__main__':
    main()