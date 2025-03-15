# app.py - Web analytics dashboard for waste sorting system
from flask import Flask, render_template, jsonify, request, send_file
import sqlite3
import os
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import io
import base64
from PIL import Image

# Set up the Flask application
app = Flask(__name__, template_folder='templates', static_folder='static')

# Database path
DB_PATH = './data/sorting_data.db'

# Function to get database connection
def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

# Function to get recent sort events
def get_recent_events(limit=50):
    """Get recent sort events"""
    conn = get_db_connection()
    events = conn.execute(
        'SELECT id, timestamp, item_type, confidence, sort_destination, image_id FROM sort_events ORDER BY timestamp DESC LIMIT ?',
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(event) for event in events]

# Function to get thumbnail image
def get_thumbnail(image_id):
    """Get thumbnail image data"""
    if not image_id:
        return None
    
    conn = get_db_connection()
    result = conn.execute('SELECT thumbnail FROM images WHERE id = ?', (image_id,)).fetchone()
    conn.close()
    
    if result and result['thumbnail']:
        return result['thumbnail']
    
    return None

# Function to get daily statistics
def get_daily_statistics(days=30):
    """Get daily statistics for charts"""
    conn = get_db_connection()
    stats = conn.execute(
        'SELECT date, can_count, recycling_count, garbage_count, total_count, token_rewards FROM statistics ORDER BY date ASC LIMIT ?',
        (days,)
    ).fetchall()
    conn.close()
    
    return [dict(stat) for stat in stats]

# Function to get totals statistics
def get_total_statistics():
    """Get total statistics (all time)"""
    conn = get_db_connection()
    result = conn.execute('''
        SELECT 
            SUM(can_count) as total_cans,
            SUM(recycling_count) as total_recycling,
            SUM(garbage_count) as total_garbage,
            SUM(total_count) as grand_total,
            SUM(token_rewards) as total_rewards
        FROM statistics
    ''').fetchone()
    conn.close()
    
    if result:
        return dict(result)
    else:
        return {
            'total_cans': 0,
            'total_recycling': 0,
            'total_garbage': 0,
            'grand_total': 0,
            'total_rewards': 0
        }

# Function to get token statistics
def get_token_statistics():
    """Get token statistics"""
    conn = get_db_connection()
    
    # Top users by token balance
    top_users = conn.execute('''
        SELECT username, token_balance 
        FROM users 
        ORDER BY token_balance DESC 
        LIMIT 10
    ''').fetchall()
    
    # Recent token transactions
    recent_transactions = conn.execute('''
        SELECT t.timestamp, u.username, t.amount, t.transaction_type
        FROM token_transactions t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.timestamp DESC
        LIMIT 20
    ''').fetchall()
    
    # Total tokens issued
    total_tokens = conn.execute('''
        SELECT SUM(amount) as total_tokens
        FROM token_transactions
        WHERE transaction_type = 'award'
    ''').fetchone()
    
    conn.close()
    
    return {
        'top_users': [dict(user) for user in top_users],
        'recent_transactions': [dict(tx) for tx in recent_transactions],
        'total_tokens': dict(total_tokens)['total_tokens'] if total_tokens and dict(total_tokens)['total_tokens'] else 0
    }

# Function to get user statistics
def get_user_statistics():
    """Get user statistics"""
    conn = get_db_connection()
    
    # Total users
    total_users = conn.execute('SELECT COUNT(*) as count FROM users').fetchone()
    
    # Active users (logged in within the last 7 days)
    seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
    active_users = conn.execute(
        'SELECT COUNT(*) as count FROM users WHERE last_login > ?',
        (seven_days_ago,)
    ).fetchone()
    
    # New users in the last 30 days
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    new_users = conn.execute(
        'SELECT COUNT(*) as count FROM users WHERE created_at > ?',
        (thirty_days_ago,)
    ).fetchone()
    
    conn.close()
    
    return {
        'total_users': dict(total_users)['count'] if total_users else 0,
        'active_users': dict(active_users)['count'] if active_users else 0,
        'new_users': dict(new_users)['count'] if new_users else 0
    }

# Routes
@app.route('/')
def index():
    """Render the dashboard homepage"""
    return render_template('index.html')

@app.route('/api/events/recent')
def api_recent_events():
    """API endpoint for recent sort events"""
    limit = request.args.get('limit', default=50, type=int)
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
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM sort_events WHERE id = ?', (event_id,)).fetchone()
    
    if not event:
        conn.close()
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

@app.route('/api/thumbnail/<image_id>')
def api_thumbnail(image_id):
    """API endpoint for thumbnail images"""
    thumbnail_data = get_thumbnail(image_id)
    
    if thumbnail_data:
        return send_file(
            io.BytesIO(thumbnail_data),
            mimetype='image/png'
        )
    else:
        # Return a default image or 404
        return send_file(
            os.path.join(app.static_folder, 'img', 'no-image.png'),
            mimetype='image/png'
        )

@app.route('/api/stats/daily')
def api_daily_stats():
    """API endpoint for daily statistics"""
    days = request.args.get('days', default=30, type=int)
    stats = get_daily_statistics(days)
    return jsonify(stats)

@app.route('/api/stats/totals')
def api_total_stats():
    """API endpoint for total statistics"""
    stats = get_total_statistics()
    return jsonify(stats)

@app.route('/api/stats/tokens')
def api_token_stats():
    """API endpoint for token statistics"""
    stats = get_token_statistics()
    return jsonify(stats)

@app.route('/api/stats/users')
def api_user_stats():
    """API endpoint for user statistics"""
    stats = get_user_statistics()
    return jsonify(stats)

@app.route('/events')
def events_page():
    """Render the events page"""
    return render_template('events.html')

@app.route('/stats')
def stats_page():
    """Render the statistics page"""
    return render_template('stats.html')

@app.route('/tokens')
def tokens_page():
    """Render the tokens page"""
    return render_template('tokens.html')

@app.route('/users')
def users_page():
    """Render the users page"""
    return render_template('users.html')

@app.route('/api/export/csv')
def export_csv():
    """Export statistics as CSV"""
    conn = get_db_connection()
    stats = conn.execute('SELECT * FROM statistics ORDER BY date ASC').fetchall()
    conn.close()
    
    if not stats:
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

@app.route('/debug')
def debug_page():
    """Debug page for development"""
    if app.debug:
        # Get sample data for debugging
        events = get_recent_events(5)
        daily_stats = get_daily_statistics(7)
        totals = get_total_statistics()
        token_stats = get_token_statistics()
        user_stats = get_user_statistics()
        
        debug_data = {
            'events': events,
            'daily_stats': daily_stats,
            'totals': totals,
            'token_stats': token_stats,
            'user_stats': user_stats
        }
        
        return render_template('debug.html', data=debug_data)
    else:
        return "Debug mode is disabled", 403

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# Main entry point
if __name__ == '__main__':
    # Create the database directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Create templates directory if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'templates'), exist_ok=True)
    
    # Create static directory if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'static'), exist_ok=True)
    
    # Start the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)