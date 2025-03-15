# database.py - Handles data storage for waste sorting system
import sqlite3
import os
import uuid
import json
import cv2
import numpy as np
from datetime import datetime

class SortingDatabase:
    """Database handler for waste sorting system"""
    
    def __init__(self, db_path="./data/sorting_data.db"):
        """Initialize database connection"""
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Connect to SQLite database
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
        # Create tables if they don't exist
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist"""
        # Sort events table - stores each sorting action
        self.cursor.execute('''
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
        
        # Images table - stores images for analysis
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            image_data BLOB NOT NULL,
            thumbnail BLOB,
            metadata TEXT
        )
        ''')
        
        # Statistics table - stores aggregated statistics
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS statistics (
            date TEXT PRIMARY KEY,
            can_count INTEGER DEFAULT 0,
            recycling_count INTEGER DEFAULT 0,
            garbage_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            metadata TEXT
        )
        ''')
        
        # Commit changes
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    # Sort Event Methods
    def add_sort_event(self, item_type, confidence, sort_destination, image=None, user_id=None, metadata=None):
        """Add a new sort event to the database"""
        event_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Store image if provided
        image_id = None
        if image is not None:
            image_id = self.add_image(image, {"source": "sort_event", "event_id": event_id})
        
        # Convert metadata to JSON string if provided
        metadata_json = None
        if metadata:
            metadata_json = json.dumps(metadata)
        
        # Insert sort event
        self.cursor.execute(
            "INSERT INTO sort_events (id, timestamp, item_type, confidence, sort_destination, image_id, user_id, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (event_id, timestamp, item_type, confidence, sort_destination, image_id, user_id, metadata_json)
        )
        
        # Update statistics
        self._update_statistics(item_type)
        
        # Commit changes
        self.conn.commit()
        
        return event_id
    
    def get_sort_event(self, event_id):
        """Get a sort event by ID"""
        self.cursor.execute("SELECT * FROM sort_events WHERE id = ?", (event_id,))
        event = self.cursor.fetchone()
        
        if event:
            # Convert to dictionary
            columns = [column[0] for column in self.cursor.description]
            event_dict = dict(zip(columns, event))
            
            # Parse metadata if it exists
            if event_dict["metadata"]:
                event_dict["metadata"] = json.loads(event_dict["metadata"])
            
            return event_dict
        
        return None
    
    def get_recent_sort_events(self, limit=50):
        """Get recent sort events"""
        self.cursor.execute(
            "SELECT * FROM sort_events ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        events = self.cursor.fetchall()
        
        # Convert to list of dictionaries
        columns = [column[0] for column in self.cursor.description]
        event_list = []
        
        for event in events:
            event_dict = dict(zip(columns, event))
            
            # Parse metadata if it exists
            if event_dict["metadata"]:
                event_dict["metadata"] = json.loads(event_dict["metadata"])
            
            event_list.append(event_dict)
        
        return event_list
    
    # Image Methods
    def add_image(self, image, metadata=None):
        """Add an image to the database"""
        image_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Convert image to binary data
        _, img_encoded = cv2.imencode('.png', image)
        image_data = img_encoded.tobytes()
        
        # Create thumbnail
        thumbnail_size = (100, 100)
        thumbnail = cv2.resize(image, thumbnail_size)
        _, thumb_encoded = cv2.imencode('.png', thumbnail)
        thumbnail_data = thumb_encoded.tobytes()
        
        # Convert metadata to JSON string if provided
        metadata_json = None
        if metadata:
            metadata_json = json.dumps(metadata)
        
        # Insert image
        self.cursor.execute(
            "INSERT INTO images (id, timestamp, image_data, thumbnail, metadata) VALUES (?, ?, ?, ?, ?)",
            (image_id, timestamp, image_data, thumbnail_data, metadata_json)
        )
        
        # Commit changes
        self.conn.commit()
        
        return image_id
    
    def get_image(self, image_id, as_array=True):
        """Get an image by ID"""
        self.cursor.execute("SELECT image_data, metadata FROM images WHERE id = ?", (image_id,))
        result = self.cursor.fetchone()
        
        if result:
            image_data, metadata_json = result
            
            # Convert binary data to image
            if as_array:
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            else:
                image = image_data
            
            # Parse metadata if it exists
            metadata = None
            if metadata_json:
                metadata = json.loads(metadata_json)
            
            return image, metadata
        
        return None, None
    
    def get_thumbnail(self, image_id, as_array=True):
        """Get a thumbnail by image ID"""
        self.cursor.execute("SELECT thumbnail FROM images WHERE id = ?", (image_id,))
        result = self.cursor.fetchone()
        
        if result and result[0]:
            thumbnail_data = result[0]
            
            # Convert binary data to image
            if as_array:
                nparr = np.frombuffer(thumbnail_data, np.uint8)
                thumbnail = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                return thumbnail
            else:
                return thumbnail_data
        
        return None
    
    # Statistics Methods
    def _update_statistics(self, item_type):
        """Update daily statistics based on sort event"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Check if we have a statistics entry for today
        self.cursor.execute("SELECT * FROM statistics WHERE date = ?", (today,))
        stats = self.cursor.fetchone()
        
        if not stats:
            # Create a new entry for today
            self.cursor.execute(
                "INSERT INTO statistics (date, can_count, recycling_count, garbage_count, total_count) "
                "VALUES (?, 0, 0, 0, 0)",
                (today,)
            )
        
        # Update the appropriate counter
        counter_field = ""
        if item_type.lower() == "can":
            counter_field = "can_count"
        elif item_type.lower() == "recycling":
            counter_field = "recycling_count"
        elif item_type.lower() == "garbage":
            counter_field = "garbage_count"
        else:
            return
        
        # Increment the counter
        self.cursor.execute(
            f"UPDATE statistics SET {counter_field} = {counter_field} + 1, "
            f"total_count = total_count + 1 WHERE date = ?",
            (today,)
        )
    
    def get_daily_statistics(self, days=30):
        """Get daily statistics for the specified number of days"""
        self.cursor.execute(
            "SELECT * FROM statistics ORDER BY date DESC LIMIT ?",
            (days,)
        )
        stats = self.cursor.fetchall()
        
        # Convert to list of dictionaries
        columns = [column[0] for column in self.cursor.description]
        stats_list = []
        
        for stat in stats:
            stat_dict = dict(zip(columns, stat))
            
            # Parse metadata if it exists
            if stat_dict.get("metadata"):
                stat_dict["metadata"] = json.loads(stat_dict["metadata"])
            
            stats_list.append(stat_dict)
        
        return stats_list
    
    def get_total_statistics(self):
        """Get aggregated statistics across all time"""
        self.cursor.execute("""
            SELECT 
                SUM(can_count) as total_cans,
                SUM(recycling_count) as total_recycling,
                SUM(garbage_count) as total_garbage,
                SUM(total_count) as grand_total
            FROM statistics
        """)
        
        result = self.cursor.fetchone()
        
        if result:
            # Convert to dictionary
            keys = ["total_cans", "total_recycling", "total_garbage", "grand_total"]
            return dict(zip(keys, result))
        
        return {
            "total_cans": 0,
            "total_recycling": 0,
            "total_garbage": 0,
            "grand_total": 0
        }
    
    # Backup and Restore
    def backup_database(self, backup_path="./data/backup"):
        """Backup database to JSON files"""
        os.makedirs(backup_path, exist_ok=True)
        
        # Backup sort events
        self.cursor.execute("SELECT * FROM sort_events")
        sort_events = self.cursor.fetchall()
        columns = [column[0] for column in self.cursor.description]
        sort_events_list = [dict(zip(columns, event)) for event in sort_events]
        
        with open(os.path.join(backup_path, "sort_events.json"), "w") as f:
            json.dump(sort_events_list, f, indent=2)
        
        # Backup statistics
        self.cursor.execute("SELECT * FROM statistics")
        statistics = self.cursor.fetchall()
        columns = [column[0] for column in self.cursor.description]
        statistics_list = [dict(zip(columns, stat)) for stat in statistics]
        
        with open(os.path.join(backup_path, "statistics.json"), "w") as f:
            json.dump(statistics_list, f, indent=2)
        
        return os.path.abspath(backup_path)


# Example usage
if __name__ == "__main__":
    # Create database
    db = SortingDatabase()
    
    # Add a sort event
    image = np.zeros((100, 100, 3), dtype=np.uint8)  # Black test image
    event_id = db.add_sort_event("can", 0.95, "recycling", image)
    print(f"Added sort event: {event_id}")
    
    # Get statistics
    stats = db.get_total_statistics()
    print(f"Statistics: {stats}")
    
    # Close database
    db.close()