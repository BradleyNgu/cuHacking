#!/usr/bin/env python
# setup.py - Initialize database and directories for waste sorting system
import os
import sqlite3
import sys

def setup_system():
    """Set up the waste sorting system database and directories"""
    print("Setting up waste sorting system...")
    
    # Base directory is the current directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create required directories
    dirs_to_create = [
        os.path.join(base_dir, 'data'),
        os.path.join(base_dir, 'templates'),
        os.path.join(base_dir, 'static'),
        os.path.join(base_dir, 'static', 'css'),
        os.path.join(base_dir, 'static', 'js'),
        os.path.join(base_dir, 'static', 'img')
    ]
    
    for directory in dirs_to_create:
        if not os.path.exists(directory):
            print(f"Creating directory: {directory}")
            os.makedirs(directory, exist_ok=True)
    
    # Database path
    db_path = os.path.join(base_dir, 'data', 'sorting_data.db')
    print(f"Database will be created at: {db_path}")
    
    # Create database tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    print("Creating database tables...")
    
    # Sort events table
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
    
    # Images table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS images (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        image_data BLOB NOT NULL,
        thumbnail BLOB,
        metadata TEXT
    )
    ''')
    
    # Statistics table
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
    
    # Insert sample data
    print("Adding sample data to the database...")
    
    # Add sample statistics
    sample_dates = ['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-04', '2025-01-05']
    for i, date in enumerate(sample_dates):
        cursor.execute('''
        INSERT OR REPLACE INTO statistics 
        (date, can_count, recycling_count, garbage_count, total_count)
        VALUES (?, ?, ?, ?, ?)
        ''', (date, 10 + i, 15 + i*2, 5 + i, 30 + i*4))
    
    # Add current date with some data
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute('''
    INSERT OR REPLACE INTO statistics 
    (date, can_count, recycling_count, garbage_count, total_count)
    VALUES (?, ?, ?, ?, ?)
    ''', (today, 20, 25, 15, 60))
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print("Creating essential template files...")
    
    # Create events.html template if it doesn't exist
    events_template = os.path.join(base_dir, 'templates', 'events.html')
    if not os.path.exists(events_template):
        with open(events_template, 'w') as f:
            f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sorting Events - Waste Sorting Analytics</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-recycle me-2"></i>
                Waste Sorting Analytics
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/events">Sorting Events</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/stats">Statistics</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="container py-4">
        <div class="row mb-4">
            <div class="col-12">
                <h1 class="display-5 mb-4">
                    <i class="fas fa-list-alt me-2"></i>
                    Sorting Events
                </h1>
            </div>
        </div>

        <!-- Filter Controls -->
        <div class="row mb-4">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header bg-white">
                        <h5 class="card-title mb-0">Filter Events</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-3 mb-3">
                                <label for="item-type" class="form-label">Item Type</label>
                                <select class="form-select" id="item-type">
                                    <option value="">All Types</option>
                                    <option value="can">Cans</option>
                                    <option value="recycling">Recycling</option>
                                    <option value="garbage">Garbage</option>
                                </select>
                            </div>
                            <div class="col-md-3 mb-3">
                                <label for="confidence" class="form-label">Min. Confidence</label>
                                <select class="form-select" id="confidence">
                                    <option value="0">Any</option>
                                    <option value="0.5">50%</option>
                                    <option value="0.7">70%</option>
                                    <option value="0.9">90%</option>
                                </select>
                            </div>
                            <div class="col-md-3 mb-3">
                                <label for="date-from" class="form-label">Date From</label>
                                <input type="date" class="form-control" id="date-from">
                            </div>
                            <div class="col-md-3 mb-3">
                                <label for="date-to" class="form-label">Date To</label>
                                <input type="date" class="form-control" id="date-to">
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-12">
                                <button id="apply-filters" class="btn btn-primary">Apply Filters</button>
                                <button id="reset-filters" class="btn btn-secondary ms-2">Reset</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Events Table -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-white d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0">Event List</h5>
                        <span class="badge bg-primary" id="event-count">Loading...</span>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-hover mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th>ID</th>
                                        <th>Time</th>
                                        <th>Item Type</th>
                                        <th>Confidence</th>
                                        <th>Destination</th>
                                        <th>Image</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="events-tbody">
                                    <tr>
                                        <td colspan="7" class="text-center">Loading events...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="card-footer bg-white">
                        <nav aria-label="Event pagination">
                            <ul class="pagination justify-content-center mb-0" id="pagination">
                                <li class="page-item disabled">
                                    <a class="page-link" href="#" tabindex="-1">Previous</a>
                                </li>
                                <li class="page-item active"><a class="page-link" href="#">1</a></li>
                                <li class="page-item disabled">
                                    <a class="page-link" href="#">Next</a>
                                </li>
                            </ul>
                        </nav>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Event Detail Modal -->
    <div class="modal fade" id="event-modal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Event Details</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-md-6">
                            <div class="mb-3">
                                <img id="event-image" src="" alt="Item image" class="img-fluid rounded">
                            </div>
                        </div>
                        <div class="col-md-6">
                            <h6>Event Information</h6>
                            <table class="table table-sm">
                                <tr>
                                    <th>ID:</th>
                                    <td id="detail-id"></td>
                                </tr>
                                <tr>
                                    <th>Timestamp:</th>
                                    <td id="detail-timestamp"></td>
                                </tr>
                                <tr>
                                    <th>Item Type:</th>
                                    <td id="detail-item-type"></td>
                                </tr>
                                <tr>
                                    <th>Confidence:</th>
                                    <td id="detail-confidence"></td>
                                </tr>
                                <tr>
                                    <th>Destination:</th>
                                    <td id="detail-destination"></td>
                                </tr>
                            </table>
                            
                            <h6 class="mt-4">Metadata</h6>
                            <pre id="detail-metadata" class="bg-light p-2 rounded" style="max-height: 150px; overflow-y: auto;"></pre>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="footer bg-light py-3 mt-auto">
        <div class="container text-center">
            <span class="text-muted">
                Waste Sorting Analytics Dashboard &copy; 2025
            </span>
        </div>
    </footer>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- Custom JS -->
    <script>
        // Global variables
        let currentPage = 1;
        const eventsPerPage = 20;
        let totalEvents = 0;
        
        // Filter variables
        let filters = {
            itemType: '',
            confidence: 0,
            dateFrom: '',
            dateTo: ''
        };
        
        // Fetch events when the page loads
        document.addEventListener('DOMContentLoaded', function() {
            // Initialize filters
            document.getElementById('apply-filters').addEventListener('click', applyFilters);
            document.getElementById('reset-filters').addEventListener('click', resetFilters);
            
            // Load events
            fetchEvents();
        });
        
        // Fetch events with current filters and pagination
        function fetchEvents() {
            // Build query parameters
            let params = new URLSearchParams();
            params.append('page', currentPage);
            params.append('limit', eventsPerPage);
            
            // Add filters
            if (filters.itemType) params.append('item_type', filters.itemType);
            if (filters.confidence > 0) params.append('min_confidence', filters.confidence);
            if (filters.dateFrom) params.append('date_from', filters.dateFrom);
            if (filters.dateTo) params.append('date_to', filters.dateTo);
            
            // Make API request
            fetch(`/api/events/recent?${params.toString()}`)
                .then(response => response.json())
                .then(data => {
                    updateEventTable(data);
                    updatePagination();
                })
                .catch(error => {
                    console.error('Error fetching events:', error);
                    document.getElementById('events-tbody').innerHTML = 
                        `<tr><td colspan="7" class="text-center text-danger">
                            Error loading events. Please try again later.
                        </td></tr>`;
                });
        }
        
        // Update the event table with data
        function updateEventTable(events) {
            const tbody = document.getElementById('events-tbody');
            tbody.innerHTML = '';
            
            if (events.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center">No events found matching your criteria.</td></tr>`;
                document.getElementById('event-count').textContent = '0 events';
                return;
            }
            
            // Update counter
            document.getElementById('event-count').textContent = `${events.length} events`;
            
            // Add rows for each event
            events.forEach(event => {
                // Format confidence
                const confidence = parseFloat(event.confidence);
                let confidenceBadge = '';
                
                if (confidence >= 0.9) {
                    confidenceBadge = '<span class="badge bg-success">High</span>';
                } else if (confidence >= 0.7) {
                    confidenceBadge = '<span class="badge bg-warning text-dark">Medium</span>';
                } else {
                    confidenceBadge = '<span class="badge bg-danger">Low</span>';
                }
                
                // Format destination
                let destinationBadge = '';
                if (event.sort_destination === 'recycling') {
                    destinationBadge = '<span class="badge bg-info">Recycling</span>';
                } else {
                    destinationBadge = '<span class="badge bg-secondary">Garbage</span>';
                }
                
                // Create row
                const row = document.createElement('tr');
                
                // Truncate ID for display
                const shortId = event.id.substring(0, 8) + '...';
                
                row.innerHTML = `
                    <td><small>${shortId}</small></td>
                    <td>${event.formatted_time || event.timestamp}</td>
                    <td>${event.item_type}</td>
                    <td>${confidenceBadge} ${(confidence * 100).toFixed(1)}%</td>
                    <td>${destinationBadge}</td>
                    <td>
                        ${event.image_id ? 
                            `<img src="/api/thumbnail/${event.image_id}" width="50" height="50" class="rounded">` : 
                            '<span class="badge bg-secondary">No image</span>'}
                    </td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary view-event" data-id="${event.id}">
                            View
                        </button>
                    </td>
                `;
                
                tbody.appendChild(row);
            });
            
            // Add event listeners for view buttons
            document.querySelectorAll('.view-event').forEach(button => {
                button.addEventListener('click', () => viewEventDetails(button.dataset.id));
            });
        }
        
        // Update pagination controls
        function updatePagination() {
            // This is a simplified pagination for now
            const pagination = document.getElementById('pagination');
            
            // In a real implementation, you would:
            // 1. Get the total count of events matching the current filters
            // 2. Calculate the total number of pages
            // 3. Create pagination links for each page
            // 4. Add event listeners to navigate between pages
            
            // For now, just show basic previous/next buttons
            pagination.innerHTML = `
                <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                    <a class="page-link" href="#" id="prev-page">Previous</a>
                </li>
                <li class="page-item active">
                    <a class="page-link" href="#">${currentPage}</a>
                </li>
                <li class="page-item">
                    <a class="page-link" href="#" id="next-page">Next</a>
                </li>
            `;
            
            // Add event listeners
            document.getElementById('prev-page').addEventListener('click', (e) => {
                e.preventDefault();
                if (currentPage > 1) {
                    currentPage--;
                    fetchEvents();
                }
            });
            
            document.getElementById('next-page').addEventListener('click', (e) => {
                e.preventDefault();
                currentPage++;
                fetchEvents();
            });
        }
        
        // Apply filters from the form
        function applyFilters() {
            filters.itemType = document.getElementById('item-type').value;
            filters.confidence = parseFloat(document.getElementById('confidence').value);
            filters.dateFrom = document.getElementById('date-from').value;
            filters.dateTo = document.getElementById('date-to').value;
            
            // Reset to first page and fetch events
            currentPage = 1;
            fetchEvents();
        }
        
        // Reset all filters
        function resetFilters() {
            document.getElementById('item-type').value = '';
            document.getElementById('confidence').value = '0';
            document.getElementById('date-from').value = '';
            document.getElementById('date-to').value = '';
            
            // Reset filter variables
            filters = {
                itemType: '',
                confidence: 0,
                dateFrom: '',
                dateTo: ''
            };
            
            // Reset to first page and fetch events
            currentPage = 1;
            fetchEvents();
        }
        
        // View event details
        function viewEventDetails(eventId) {
            // Fetch event details
            fetch(`/api/events/${eventId}`)
                .then(response => response.json())
                .then(data => {
                    // Populate modal with event details
                    document.getElementById('detail-id').textContent = data.id;
                    document.getElementById('detail-timestamp').textContent = data.timestamp;
                    document.getElementById('detail-item-type').textContent = data.item_type;
                    document.getElementById('detail-confidence').textContent = `${(data.confidence * 100).toFixed(1)}%`;
                    document.getElementById('detail-destination').textContent = data.sort_destination;
                    
                    // Show image if available
                    if (data.image_id) {
                        document.getElementById('event-image').src = `/api/thumbnail/${data.image_id}`;
                        document.getElementById('event-image').style.display = 'block';
                    } else {
                        document.getElementById('event-image').style.display = 'none';
                    }
                    
                    // Show metadata if available
                    if (data.metadata) {
                        let metadata = data.metadata;
                        if (typeof metadata === 'string') {
                            try {
                                metadata = JSON.parse(metadata);
                            } catch (e) {
                                // Keep as string if not valid JSON
                            }
                        }
                        document.getElementById('detail-metadata').textContent = 
                            JSON.stringify(metadata, null, 2);
                    } else {
                        document.getElementById('detail-metadata').textContent = 'No metadata available';
                    }
                    
                    // Show the modal
                    const eventModal = new bootstrap.Modal(document.getElementById('event-modal'));
                    eventModal.show();
                })
                .catch(error => {
                    console.error('Error fetching event details:', error);
                    alert('Error loading event details. Please try again later.');
                });
        }
    </script>
</body>
</html>''')
    
    # Create stats.html template if it doesn't exist
    stats_template = os.path.join(base_dir, 'templates', 'stats.html')
    if not os.path.exists(stats_template):
        with open(stats_template, 'w') as f:
            f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Statistics - Waste Sorting Analytics</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-recycle me-2"></i>
                Waste Sorting Analytics
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/events">Sorting Events</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="/stats">Statistics</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="container py-4">
        <div class="row mb-4">
            <div class="col-12">
                <h1 class="display-5 mb-4">
                    <i class="fas fa-chart-bar me-2"></i>
                    Statistics
                </h1>
            </div>
        </div>

        <!-- Time Period Selector -->
        <div class="row mb-4">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header bg-white">
                        <h5 class="card-title mb-0">Time Period</h5>
                    </div>
                    <div class="card-body">
                        <div class="btn-group" role="group" aria-label="Time period selector">
                            <button type="button" class="btn btn-outline-primary period-btn active" data-days="7">Week</button>
                            <button type="button" class="btn btn-outline-primary period-btn" data-days="30">Month</button>
                            <button type="button" class="btn btn-outline-primary period-btn" data-days="90">3 Months</button>
                            <button type="button" class="btn btn-outline-primary period-btn" data-days="365">Year</button>
                            <button type="button" class="btn btn-outline-primary period-btn" data-days="0">All Time</button>
                        </div>
                        
                        <div class="float-end">
                            <a href="/api/export/csv" class="btn btn-success">
                                <i class="fas fa-download me-2"></i>
                                Export CSV
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Summary Cards -->
        <div class="row mb-4">
            <!-- Total Sorted Items -->
            <div class="col-md-3 mb-4">
                <div class="card border-primary h-100">
                    <div class="card-body text-center">
                        <h5 class="card-title text-primary">
                            <i class="fas fa-sort me-2"></i>
                            Total Sorted
                        </h5>
                        <p class="display-4 mb-0" id="total-sorted">-</p>
                        <p class="text-muted small">All-time total items sorted</p>
                    </div>
                </div>
            </div>
            
            <!-- Average Per Day -->
            <div class="col-md-3 mb-4">
                <div class="card border-success h-100">
                    <div class="card-body text-center">
                        <h5 class="card-title text-success">
                            <i class="fas fa-calendar-day me-2"></i>
                            Average Per Day
                        </h5>
                        <p class="display-4 mb-0" id="avg-per-day">-</p>
                        <p class="text-muted small">Average items sorted per day</p>
                    </div>
                </div>
            </div>
            
            <!-- Recycling Rate -->
            <div class="col-md-3 mb-4">
                <div class="card border-info h-100">
                    <div class="card-body text-center">
                        <h5 class="card-title text-info">
                            <i class="fas fa-leaf me-2"></i>
                            Recycling Rate
                        </h5>
                        <p class="display-4 mb-0" id="recycling-rate">-</p>
                        <p class="text-muted small">Percentage of items recycled</p>
                    </div>
                </div>
            </div>
            
            <!-- Most Common Item -->
            <div class="col-md-3 mb-4">
                <div class="card border-warning h-100">
                    <div class="card-body text-center">
                        <h5 class="card-title text-warning">
                            <i class="fas fa-star me-2"></i>
                            Most Common
                        </h5>
                        <p class="display-4 mb-0" id="most-common">-</p>
                        <p class="text-muted small">Most commonly sorted item</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Charts -->
        <div class="row mb-4">
            <!-- Daily Sorting Activity -->
            <div class="col-lg-8 mb-4">
                <div class="card">
                    <div class="card-header bg-white">
                        <h5 class="card-title mb-0">Daily Sorting Activity</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="daily-chart" height="300"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- Distribution by Type -->
            <div class="col-lg-4 mb-4">
                <div class="card">
                    <div class="card-header bg-white">
                        <h5 class="card-title mb-0">Distribution by Type</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="type-distribution-chart" height="300"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Trends and Analytics -->
        <div class="row mb-4">
            <!-- Weekly Trend -->
            <div class="col-md-6 mb-4">
                <div class="card">
                    <div class="card-header bg-white">
                        <h5 class="card-title mb-0">Weekly Trends</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="weekly-trend-chart" height="250"></canvas>
                    </div>
                </div>
            </div>
            
            <!-- Monthly Comparison -->
            <div class="col-md-6 mb-4">
                <div class="card">
                    <div class="card-header bg-white">
                        <h5 class="card-title mb-0">Monthly Comparison</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="monthly-comparison-chart" height="250"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="footer bg-light py-3 mt-auto">
        <div class="container text-center">
            <span class="text-muted">
                Waste Sorting Analytics Dashboard &copy; 2025
            </span>
        </div>
    </footer>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- Custom JS -->
    <script>
        // Global variables
        let dailyChart, typeDistributionChart, weeklyTrendChart, monthlyComparisonChart;
        let selectedDays = 7; // Default to week view
        
        // Fetch data when the page loads
        document.addEventListener('DOMContentLoaded', function() {
            // Add event listeners to period buttons
            document.querySelectorAll('.period-btn').forEach(button => {
                button.addEventListener('click', function() {
                    // Remove active class from all buttons
                    document.querySelectorAll('.period-btn').forEach(btn => {
                        btn.classList.remove('active');
                    });
                    
                    // Add active class to clicked button
                    this.classList.add('active');
                    
                    // Update selected days
                    selectedDays = parseInt(this.dataset.days);
                    
                    // Fetch data with new time period
                    fetchStatistics();
                });
            });
            
            // Initial data fetch
            fetchStatistics();
        });
        
        // Fetch statistics data
        function fetchStatistics() {
            // Fetch total statistics
            fetch('/api/stats/totals')
                .then(response => response.json())
                .then(data => {
                    updateSummaryCards(data);
                })
                .catch(error => console.error('Error fetching total stats:', error));
            
            // Fetch daily statistics
            const daysParam = selectedDays > 0 ? selectedDays : 1000; // Use a large number for "all time"
            fetch(`/api/stats/daily?days=${daysParam}`)
                .then(response => response.json())
                .then(data => {
                    updateCharts(data);
                })
                .catch(error => console.error('Error fetching daily stats:', error));
        }
        
        // Update summary cards
        function updateSummaryCards(data) {
            document.getElementById('total-sorted').textContent = data.grand_total || 0;
            
            // Calculate recycling rate
            const totalRecycling = (data.total_cans || 0) + (data.total_recycling || 0);
            const totalItems = (data.grand_total || 0);
            const recyclingRate = totalItems > 0 ? (totalRecycling / totalItems * 100).toFixed(1) : 0;
            document.getElementById('recycling-rate').textContent = recyclingRate + '%';
            
            // Calculate average per day (approximate)
            // In a real implementation, you would divide by the actual number of days in the dataset
            const avgPerDay = Math.round(totalItems / 30); // Assuming ~30 days of data
            document.getElementById('avg-per-day').textContent = avgPerDay;
            
            // Determine most common item
            if (data.total_cans > data.total_recycling && data.total_cans > data.total_garbage) {
                document.getElementById('most-common').textContent = "Cans";
            } else if (data.total_recycling > data.total_cans && data.total_recycling > data.total_garbage) {
                document.getElementById('most-common').textContent = "Recycling";
            } else if (data.total_garbage > 0) {
                document.getElementById('most-common').textContent = "Garbage";
            } else {
                document.getElementById('most-common').textContent = "N/A";
            }
        }
        
        // Update all charts
        function updateCharts(data) {
            updateDailyChart(data);
            updateDistributionChart(data);
            updateWeeklyTrendChart(data);
            updateMonthlyComparisonChart(data);
        }
        
        // Update daily chart
        function updateDailyChart(data) {
            const ctx = document.getElementById('daily-chart').getContext('2d');
            
            // Prepare data for the chart
            const dates = data.map(item => item.date);
            const canData = data.map(item => item.can_count || 0);
            const recyclingData = data.map(item => item.recycling_count || 0);
            const garbageData = data.map(item => item.garbage_count || 0);
            
            // Destroy existing chart if it exists
            if (dailyChart) {
                dailyChart.destroy();
            }
            
            // Create the chart
            dailyChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: dates,
                    datasets: [
                        {
                            label: 'Cans',
                            data: canData,
                            backgroundColor: 'rgba(54, 162, 235, 0.7)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        },
                        {
                            label: 'Recycling',
                            data: recyclingData,
                            backgroundColor: 'rgba(75, 192, 192, 0.7)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        },
                        {
                            label: 'Garbage',
                            data: garbageData,
                            backgroundColor: 'rgba(255, 99, 132, 0.7)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        x: {
                            stacked: true
                        },
                        y: {
                            stacked: true,
                            beginAtZero: true
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top'
                        }
                    }
                }
            });
        }
        
        // Update distribution chart
        function updateDistributionChart(data) {
            const ctx = document.getElementById('type-distribution-chart').getContext('2d');
            
            // Calculate totals
            let totalCans = 0;
            let totalRecycling = 0;
            let totalGarbage = 0;
            
            data.forEach(item => {
                totalCans += item.can_count || 0;
                totalRecycling += item.recycling_count || 0;
                totalGarbage += item.garbage_count || 0;
            });
            
            // Destroy existing chart if it exists
            if (typeDistributionChart) {
                typeDistributionChart.destroy();
            }
            
            // Create the chart
            typeDistributionChart = new Chart(ctx, {
                type: 'pie',
                data: {
                    labels: ['Cans', 'Recycling', 'Garbage'],
                    datasets: [{
                        data: [totalCans, totalRecycling, totalGarbage],
                        backgroundColor: [
                            'rgba(54, 162, 235, 0.7)', // Blue for cans
                            'rgba(75, 192, 192, 0.7)', // Teal for recycling
                            'rgba(255, 99, 132, 0.7)'  // Red for garbage
                        ],
                        borderColor: [
                            'rgba(54, 162, 235, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(255, 99, 132, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }
        
        // Update weekly trend chart
        function updateWeeklyTrendChart(data) {
            const ctx = document.getElementById('weekly-trend-chart').getContext('2d');
            
            // Group data by week
            const weeklyData = {}; // { week: { cans, recycling, garbage, total } }
            
            data.forEach(item => {
                // Parse date and get week number
                const date = new Date(item.date);
                const weekNumber = getWeekNumber(date);
                const weekLabel = `Week ${weekNumber}`;
                
                // Initialize week if it doesn't exist
                if (!weeklyData[weekLabel]) {
                    weeklyData[weekLabel] = {
                        cans: 0,
                        recycling: 0,
                        garbage: 0,
                        total: 0
                    };
                }
                
                // Add data
                weeklyData[weekLabel].cans += item.can_count || 0;
                weeklyData[weekLabel].recycling += item.recycling_count || 0;
                weeklyData[weekLabel].garbage += item.garbage_count || 0;
                weeklyData[weekLabel].total += item.total_count || 0;
            });
            
            // Convert to arrays for chart
            const weeks = Object.keys(weeklyData).sort((a, b) => {
                return parseInt(a.split(' ')[1]) - parseInt(b.split(' ')[1]);
            });
            
            const totals = weeks.map(week => weeklyData[week].total);
            
            // Destroy existing chart if it exists
            if (weeklyTrendChart) {
                weeklyTrendChart.destroy();
            }
            
            // Create the chart
            weeklyTrendChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: weeks,
                    datasets: [{
                        label: 'Total Items',
                        data: totals,
                        backgroundColor: 'rgba(153, 102, 255, 0.2)',
                        borderColor: 'rgba(153, 102, 255, 1)',
                        borderWidth: 2,
                        tension: 0.1,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        // Update monthly comparison chart
        function updateMonthlyComparisonChart(data) {
            const ctx = document.getElementById('monthly-comparison-chart').getContext('2d');
            
            // Group data by month
            const monthlyData = {}; // { month: { cans, recycling, garbage } }
            
            data.forEach(item => {
                // Parse date and get month
                const date = new Date(item.date);
                const monthLabel = date.toLocaleString('default', { month: 'short' });
                
                // Initialize month if it doesn't exist
                if (!monthlyData[monthLabel]) {
                    monthlyData[monthLabel] = {
                        cans: 0,
                        recycling: 0,
                        garbage: 0
                    };
                }
                
                // Add data
                monthlyData[monthLabel].cans += item.can_count || 0;
                monthlyData[monthLabel].recycling += item.recycling_count || 0;
                monthlyData[monthLabel].garbage += item.garbage_count || 0;
            });
            
            // Convert to arrays for chart
            const months = Object.keys(monthlyData);
            const canData = months.map(month => monthlyData[month].cans);
            const recyclingData = months.map(month => monthlyData[month].recycling);
            const garbageData = months.map(month => monthlyData[month].garbage);
            
            // Destroy existing chart if it exists
            if (monthlyComparisonChart) {
                monthlyComparisonChart.destroy();
            }
            
            // Create the chart
            monthlyComparisonChart = new Chart(ctx, {
                type: 'radar',
                data: {
                    labels: months,
                    datasets: [
                        {
                            label: 'Cans',
                            data: canData,
                            backgroundColor: 'rgba(54, 162, 235, 0.2)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 2,
                            pointBackgroundColor: 'rgba(54, 162, 235, 1)'
                        },
                        {
                            label: 'Recycling',
                            data: recyclingData,
                            backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 2,
                            pointBackgroundColor: 'rgba(75, 192, 192, 1)'
                        },
                        {
                            label: 'Garbage',
                            data: garbageData,
                            backgroundColor: 'rgba(255, 99, 132, 0.2)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 2,
                            pointBackgroundColor: 'rgba(255, 99, 132, 1)'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        r: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
        
        // Helper function to get week number from date
        function getWeekNumber(date) {
            const firstDayOfYear = new Date(date.getFullYear(), 0, 1);
            const pastDaysOfYear = (date - firstDayOfYear) / 86400000;
            return Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);
        }
    </script>
</body>
</html>''')
    
    # Create 404.html template if it doesn't exist
    error_404_template = os.path.join(base_dir, 'templates', '404.html')
    if not os.path.exists(error_404_template):
        with open(error_404_template, 'w') as f:
            f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>404 - Page Not Found</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-recycle me-2"></i>
                Waste Sorting Analytics
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/events">Sorting Events</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/stats">Statistics</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-6 text-center">
                <h1 class="display-1 text-primary mb-4">
                    <i class="fas fa-exclamation-triangle"></i>
                </h1>
                <h1 class="display-4 mb-4">404 - Page Not Found</h1>
                <p class="lead mb-4">The page you are looking for doesn't exist or has been moved.</p>
                <a href="/" class="btn btn-primary btn-lg">
                    <i class="fas fa-home me-2"></i>
                    Return to Dashboard
                </a>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="footer bg-light py-3 mt-auto">
        <div class="container text-center">
            <span class="text-muted">
                Waste Sorting Analytics Dashboard &copy; 2025
            </span>
        </div>
    </footer>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>''')
    
    # Create 500.html template if it doesn't exist
    error_500_template = os.path.join(base_dir, 'templates', '500.html')
    if not os.path.exists(error_500_template):
        with open(error_500_template, 'w') as f:
            f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>500 - Server Error</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    
    <!-- Custom CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-recycle me-2"></i>
                Waste Sorting Analytics
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Dashboard</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/events">Sorting Events</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="/stats">Statistics</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="container py-5">
        <div class="row justify-content-center">
            <div class="col-md-6 text-center">
                <h1 class="display-1 text-danger mb-4">
                    <i class="fas fa-exclamation-circle"></i>
                </h1>
                <h1 class="display-4 mb-4">500 - Server Error</h1>
                <p class="lead mb-4">Sorry, something went wrong on our end. Please try again later.</p>
                <a href="/" class="btn btn-primary btn-lg">
                    <i class="fas fa-home me-2"></i>
                    Return to Dashboard
                </a>
            </div>
        </div>
    </main>

    <!-- Footer -->
    <footer class="footer bg-light py-3 mt-auto">
        <div class="container text-center">
            <span class="text-muted">
                Waste Sorting Analytics Dashboard &copy; 2025
            </span>
        </div>
    </footer>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>''')
    
    # Create style.css file
    css_dir = os.path.join(base_dir, 'static', 'css')
    css_file = os.path.join(css_dir, 'style.css')
    if not os.path.exists(css_file):
        with open(css_file, 'w') as f:
            f.write('''/* Custom CSS for Waste Sorting Analytics Dashboard */

/* Global Styles */
body {
    display: flex;
    min-height: 100vh;
    flex-direction: column;
}

main {
    flex: 1 0 auto;
}

/* Cards */
.card {
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    border-radius: 0.5rem;
    border: none;
}

.card-header {
    border-top-left-radius: 0.5rem;
    border-top-right-radius: 0.5rem;
    border-bottom: 1px solid rgba(0, 0, 0, 0.125);
}

/* Tables */
.table th {
    font-weight: 600;
}

/* Custom Card Border Colors */
.card.border-primary {
    border-left: 4px solid #007bff !important;
}

.card.border-success {
    border-left: 4px solid #28a745 !important;
}

.card.border-info {
    border-left: 4px solid #17a2b8 !important;
}

.card.border-warning {
    border-left: 4px solid #ffc107 !important;
}

.card.border-danger {
    border-left: 4px solid #dc3545 !important;
}

.card.border-secondary {
    border-left: 4px solid #6c757d !important;
}

/* Navigation Active Link */
.nav-link.active {
    font-weight: bold;
}

/* Chart Containers */
canvas {
    max-width: 100%;
}

/* Hover Effects */
.card:hover {
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.1);
    transition: box-shadow 0.3s ease-in-out;
}

/* Responsive Font Sizes */
@media (max-width: 768px) {
    .display-4 {
        font-size: 2.5rem;
    }
}

/* Thumbnail Images */
.img-thumbnail {
    object-fit: cover;
}

/* Tables */
.table-responsive {
    overflow-x: auto;
}

/* Badges */
.badge {
    font-weight: 500;
    padding: 0.35em 0.65em;
}

/* Footer */
.footer {
    background-color: #f8f9fa;
    padding: 1rem 0;
    margin-top: auto;
}''')
    
    # Create placeholder no-image.png file
    img_dir = os.path.join(base_dir, 'static', 'img')
    no_image_file = os.path.join(img_dir, 'no-image.png')
    if not os.path.exists(no_image_file):
        try:
            from PIL import Image, ImageDraw
            
            # Create a simple placeholder image
            img = Image.new('RGB', (200, 200), color = (240, 240, 240))
            d = ImageDraw.Draw(img)
            d.text((70, 90), "No Image", fill=(80, 80, 80))
            img.save(no_image_file)
            print(f"Created placeholder image at {no_image_file}")
        except:
            print(f"Could not create placeholder image. Please create it manually at {no_image_file}")
    
    print("\nSetup completed!")
    print(f"Database created at: {db_path}")
    print("Template files created in the templates directory")
    print("Static files created in the static directory")
    print("\nNow you can run the application with:")
    print("python app.py")
    
    return True

if __name__ == "__main__":
    setup_system()