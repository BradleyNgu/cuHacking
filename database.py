# database.py - Handles data storage for waste sorting system
import sqlite3
import os
import uuid
import json
import base64
import cv2
import numpy as np
from datetime import datetime
import hashlib

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
        
        # Users table - stores user information
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            token_balance REAL DEFAULT 0,
            created_at TEXT NOT NULL,
            last_login TEXT,
            settings TEXT
        )
        ''')
        
        # Token transactions table - stores token reward activities
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS token_transactions (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            user_id TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            reference_id TEXT,
            metadata TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
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
            token_rewards REAL DEFAULT 0,
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
    
    # User Methods
    def add_user(self, username, email=None, settings=None):
        """Add a new user to the database"""
        # Check if user already exists
        self.cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if self.cursor.fetchone():
            return None, "Username already exists"
        
        # Generate user ID
        user_id = hashlib.sha256(username.encode()).hexdigest()[:16]
        created_at = datetime.now().isoformat()
        
        # Convert settings to JSON string if provided
        settings_json = None
        if settings:
            settings_json = json.dumps(settings)
        
        # Insert user
        self.cursor.execute(
            "INSERT INTO users (id, username, email, created_at, settings) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, email, created_at, settings_json)
        )
        
        # Commit changes
        self.conn.commit()
        
        return user_id, "User created successfully"
    
    def get_user(self, username=None, user_id=None):
        """Get user by username or ID"""
        if username:
            self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        elif user_id:
            self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        else:
            return None
        
        user = self.cursor.fetchone()
        
        if user:
            # Convert to dictionary
            columns = [column[0] for column in self.cursor.description]
            user_dict = dict(zip(columns, user))
            
            # Parse settings if they exist
            if user_dict["settings"]:
                user_dict["settings"] = json.loads(user_dict["settings"])
            
            return user_dict
        
        return None
    
    def update_user_login(self, username):
        """Update user's last login time"""
        last_login = datetime.now().isoformat()
        
        self.cursor.execute(
            "UPDATE users SET last_login = ? WHERE username = ?",
            (last_login, username)
        )
        
        self.conn.commit()
    
    # Token Methods
    def add_token_transaction(self, user_id, amount, transaction_type, reference_id=None, metadata=None):
        """Add a token transaction"""
        transaction_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Convert metadata to JSON string if provided
        metadata_json = None
        if metadata:
            metadata_json = json.dumps(metadata)
        
        # Insert transaction
        self.cursor.execute(
            "INSERT INTO token_transactions (id, timestamp, user_id, amount, transaction_type, reference_id, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (transaction_id, timestamp, user_id, amount, transaction_type, reference_id, metadata_json)
        )
        
        # Update user balance
        self.cursor.execute(
            "UPDATE users SET token_balance = token_balance + ? WHERE id = ?",
            (amount, user_id)
        )
        
        # Update statistics
        today = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute(
            "UPDATE statistics SET token_rewards = token_rewards + ? WHERE date = ?",
            (amount, today)
        )
        
        # Commit changes
        self.conn.commit()
        
        return transaction_id
    
    def get_user_transactions(self, user_id, limit=50):
        """Get user's token transactions"""
        self.cursor.execute(
            "SELECT * FROM token_transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, limit)
        )
        transactions = self.cursor.fetchall()
        
        # Convert to list of dictionaries
        columns = [column[0] for column in self.cursor.description]
        transaction_list = []
        
        for transaction in transactions:
            transaction_dict = dict(zip(columns, transaction))
            
            # Parse metadata if it exists
            if transaction_dict["metadata"]:
                transaction_dict["metadata"] = json.loads(transaction_dict["metadata"])
            
            transaction_list.append(transaction_dict)
        
        return transaction_list
    
    def get_user_balance(self, user_id):
        """Get user's token balance"""
        self.cursor.execute("SELECT token_balance FROM users WHERE id = ?", (user_id,))
        result = self.cursor.fetchone()
        
        if result:
            return result[0]
        
        return 0.0
    
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
                SUM(total_count) as grand_total,
                SUM(token_rewards) as total_rewards
            FROM statistics
        """)
        
        result = self.cursor.fetchone()
        
        if result:
            # Convert to dictionary
            keys = ["total_cans", "total_recycling", "total_garbage", "grand_total", "total_rewards"]
            return dict(zip(keys, result))
        
        return {
            "total_cans": 0,
            "total_recycling": 0,
            "total_garbage": 0,
            "grand_total": 0,
            "total_rewards": 0
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
        
        # Backup users (excluding images for size reasons)
        self.cursor.execute("SELECT id, username, email, token_balance, created_at, last_login, settings FROM users")
        users = self.cursor.fetchall()
        columns = [column[0] for column in self.cursor.description]
        users_list = [dict(zip(columns, user)) for user in users]
        
        with open(os.path.join(backup_path, "users.json"), "w") as f:
            json.dump(users_list, f, indent=2)
        
        # Backup token transactions
        self.cursor.execute("SELECT * FROM token_transactions")
        transactions = self.cursor.fetchall()
        columns = [column[0] for column in self.cursor.description]
        transactions_list = [dict(zip(columns, transaction)) for transaction in transactions]
        
        with open(os.path.join(backup_path, "token_transactions.json"), "w") as f:
            json.dump(transactions_list, f, indent=2)
        
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
    
    # Add a user
    user_id, message = db.add_user("test_user", "test@example.com")
    print(f"Added user: {message}")
    
    # Add a sort event
    image = np.zeros((100, 100, 3), dtype=np.uint8)  # Black test image
    event_id = db.add_sort_event("can", 0.95, "recycling", image, user_id)
    print(f"Added sort event: {event_id}")
    
    # Add a token transaction
    transaction_id = db.add_token_transaction(user_id, 1.0, "reward", event_id)
    print(f"Added token transaction: {transaction_id}")
    
    # Get user balance
    balance = db.get_user_balance(user_id)
    print(f"User balance: {balance}")
    
    # Get statistics
    stats = db.get_total_statistics()
    print(f"Statistics: {stats}")
    
    # Close database
    db.close()