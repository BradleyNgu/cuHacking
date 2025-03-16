# app.py - Web analytics dashboard for waste sorting system
from flask import Flask, render_template, jsonify, request, send_file
import sqlite3
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import io
import logging
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("WasteSorterDashboard")

# Database path
DB_PATH = './data/sorting_data.db'

# Create necessary directories - MOVED OUTSIDE MAIN BLOCK
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)

# Create or check database schema
def initialize_database():
    """Initialize database if it doesn't exist"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create sort_events table if it doesn't exist
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
        
        # Create images table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS images (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            image_data BLOB NOT NULL,
            thumbnail BLOB,
            metadata TEXT
        )
        ''')
        
        # Create statistics table if it doesn't exist
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
        
        # Insert sample data if tables are empty
        cursor.execute("SELECT COUNT(*) FROM statistics")
        if cursor.fetchone()[0] == 0:
            logger.info("Inserting sample statistics data")
            # Insert sample data for the last 30 days
            today = datetime.now()
            for i in range(30, 0, -1):
                date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
                can_count = i + 5
                recycling_count = i + 3
                garbage_count = i
                total_count = can_count + recycling_count + garbage_count
                
                cursor.execute(
                    "INSERT INTO statistics (date, can_count, recycling_count, garbage_count, total_count) VALUES (?, ?, ?, ?, ?)",
                    (date, can_count, recycling_count, garbage_count, total_count)
                )
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

# Initialize database right away
try:
    initialize_database()
    logger.info("Database checked and initialized")
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")

# Set up the Flask application
app = Flask(__name__, template_folder='templates', static_folder='static')

# Function to get database connection
def get_db_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

# Function to get recent sort events
def get_recent_events(limit=50):
    """Get recent sort events"""
    try:
        conn = get_db_connection()
        events = conn.execute(
            'SELECT id, timestamp, item_type, confidence, sort_destination, image_id FROM sort_events ORDER BY timestamp DESC LIMIT ?',
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(event) for event in events]
    except Exception as e:
        logger.error(f"Error getting recent events: {str(e)}")
        return []

# Function to get thumbnail image
def get_thumbnail(image_id):
    """Get thumbnail image data"""
    if not image_id:
        return None
    
    try:
        conn = get_db_connection()
        result = conn.execute('SELECT thumbnail FROM images WHERE id = ?', (image_id,)).fetchone()
        conn.close()
        
        if result and result['thumbnail']:
            return result['thumbnail']
    except Exception as e:
        logger.error(f"Error getting thumbnail: {str(e)}")
    
    return None

# Function to get daily statistics
def get_daily_statistics(days=30):
    """Get daily statistics for charts"""
    try:
        conn = get_db_connection()
        stats = conn.execute(
            'SELECT date, can_count, recycling_count, garbage_count, total_count FROM statistics ORDER BY date ASC LIMIT ?',
            (days,)
        ).fetchall()
        conn.close()
        
        return [dict(stat) for stat in stats]
    except Exception as e:
        logger.error(f"Error getting daily statistics: {str(e)}")
        return []

# Function to get totals statistics
def get_total_statistics():
    """Get total statistics (all time)"""
    try:
        conn = get_db_connection()
        result = conn.execute('''
            SELECT 
                SUM(can_count) as total_cans,
                SUM(recycling_count) as total_recycling,
                SUM(garbage_count) as total_garbage,
                SUM(total_count) as grand_total
            FROM statistics
        ''').fetchone()
        conn.close()
        
        if result:
            return dict(result)
    except Exception as e:
        logger.error(f"Error getting total statistics: {str(e)}")
    
    return {
        'total_cans': 0,
        'total_recycling': 0,
        'total_garbage': 0,
        'grand_total': 0
    }

# Routes
@app.route('/')
def index():
    """Render the dashboard homepage"""
    logger.info("Homepage accessed")
    return render_template('index.html')

@app.route('/api/events/recent')
def api_recent_events():
    """API endpoint for recent sort events"""
    limit = request.args.get('limit', default=50, type=int)
    logger.info(f"Recent events API called with limit={limit}")
    events = get_recent_events(limit)
    
    # Format timestamps
    for event in events:
        try:
            dt = datetime.fromisoformat(event['timestamp'])
            event['formatted_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            event['formatted_time'] = event['timestamp']
    
    return jsonify(events)

@app.route('/api/events/<event_id>')
def api_event_detail(event_id):
    """API endpoint for event details"""
    logger.info(f"Event detail API called for event_id={event_id}")
    try:
        conn = get_db_connection()
        event = conn.execute('SELECT * FROM sort_events WHERE id = ?', (event_id,)).fetchone()
        
        if not event:
            conn.close()
            logger.warning(f"Event {event_id} not found")
            return jsonify({'error': 'Event not found'}), 404
        
        event_dict = dict(event)
        
        # Convert metadata JSON if it exists
        if event_dict.get('metadata'):
            try:
                event_dict['metadata'] = json.loads(event_dict['metadata'])
            except:
                pass
        
        conn.close()
        return jsonify(event_dict)
    except Exception as e:
        logger.error(f"Error getting event detail: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/thumbnail/<image_id>')
def api_thumbnail(image_id):
    """API endpoint for thumbnail images"""
    logger.info(f"Thumbnail API called for image_id={image_id}")
    try:
        thumbnail_data = get_thumbnail(image_id)
        
        if thumbnail_data:
            return send_file(
                io.BytesIO(thumbnail_data),
                mimetype='image/png'
            )
        else:
            # Return a default image or 404
            default_img_path = os.path.join(app.static_folder, 'img', 'no-image.png')
            if os.path.exists(default_img_path):
                return send_file(default_img_path, mimetype='image/png')
            else:
                logger.warning(f"No thumbnail found for {image_id} and no default image available")
                return jsonify({'error': 'No image found'}), 404
    except Exception as e:
        logger.error(f"Error serving thumbnail: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats/daily')
def api_daily_stats():
    """API endpoint for daily statistics"""
    days = request.args.get('days', default=30, type=int)
    logger.info(f"Daily stats API called with days={days}")
    stats = get_daily_statistics(days)
    return jsonify(stats)

@app.route('/api/stats/totals')
def api_total_stats():
    """API endpoint for total statistics"""
    logger.info("Total stats API called")
    stats = get_total_statistics()
    return jsonify(stats)

@app.route('/events')
def events_page():
    """Render the events page"""
    logger.info("Events page accessed")
    return render_template('events.html')

@app.route('/stats')
def stats_page():
    """Render the statistics page"""
    logger.info("Stats page accessed")
    return render_template('stats.html')

@app.route('/api/export/csv')
def export_csv():
    """Export statistics as CSV"""
    logger.info("CSV export API called")
    try:
        conn = get_db_connection()
        stats = conn.execute('SELECT * FROM statistics ORDER BY date ASC').fetchall()
        conn.close()
        
        if not stats:
            logger.warning("No data available for CSV export")
            return jsonify({'error': 'No data to export'}), 404
        
        # Convert to pandas DataFrame
        stats_dict = [dict(stat) for stat in stats]
        df = pd.DataFrame(stats_dict)
        
        # Create a CSV string
        output = io.StringIO()
        df.to_csv(output, index=False)
        
        # Create response
        return app.response_class(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=waste_sorting_stats.csv'}
        )
    except Exception as e:
        logger.error(f"Error exporting CSV: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/debug')
def debug_page():
    """Debug page for development"""
    logger.info("Debug page accessed")
    if app.debug:
        # Get sample data for debugging
        events = get_recent_events(5)
        daily_stats = get_daily_statistics(7)
        totals = get_total_statistics()
        
        debug_data = {
            'events': events,
            'daily_stats': daily_stats,
            'totals': totals
        }
        
        return render_template('debug.html', data=debug_data)
    else:
        return "Debug mode is disabled", 403

# Route to verify application is running
@app.route('/status')
def status():
    """Simple status check endpoint"""
    logger.info("Status check called")
    return jsonify({
        'status': 'online',
        'database': os.path.exists(DB_PATH),
        'timestamp': datetime.now().isoformat()
    })

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    logger.warning(f"404 error: {request.path}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 error: {str(e)}")
    return render_template('500.html'), 500

# Main entry point
if __name__ == '__main__':
    # Start the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)