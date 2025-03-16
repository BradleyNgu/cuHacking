<?php
/**
 * api.php - Unified API endpoint for Waste Sorting Analytics Dashboard
 * 
 * This file handles all API requests for the dashboard by using the 'action' parameter.
 * Example: api.php?action=get_totals
 */

// Configuration
$config = [
    'db_path' => './data/sorting_data.db',
    'log_path' => './logs/api.log'
];

// Enable error reporting but don't display errors
error_reporting(E_ALL);
ini_set('display_errors', 0);

// Set no-cache headers for all responses
header('Cache-Control: no-cache, no-store, must-revalidate');
header('Pragma: no-cache');
header('Expires: 0');

// Setup logging
function log_message($message, $level = 'INFO') {
    global $config;
    
    $date = date('Y-m-d H:i:s');
    $log_line = "[$date] [$level] $message\n";
    
    // Make sure log directory exists
    $log_dir = dirname($config['log_path']);
    if (!is_dir($log_dir)) {
        mkdir($log_dir, 0755, true);
    }
    
    // Append to log file
    file_put_contents($config['log_path'], $log_line, FILE_APPEND);
    
    // Also log to error log if it's an error
    if ($level == 'ERROR') {
        error_log("Waste Sorter API: $message");
    }
}

// Get database connection
function get_db_connection() {
    global $config;
    
    try {
        // Make sure database exists
        if (!file_exists($config['db_path'])) {
            log_message("Database file not found: " . $config['db_path'], 'ERROR');
            return null;
        }
        
        // Connect to database
        $db = new SQLite3($config['db_path']);
        $db->busyTimeout(5000); // Set busy timeout for busy database
        
        return $db;
    } catch (Exception $e) {
        log_message("Database connection error: " . $e->getMessage(), 'ERROR');
        return null;
    }
}

// Convert database results to array
function fetch_all($result) {
    $rows = [];
    while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
        // Parse metadata if it's a JSON string
        if (isset($row['metadata']) && is_string($row['metadata'])) {
            try {
                $metadata = json_decode($row['metadata'], true);
                if ($metadata !== null) {
                    $row['metadata'] = $metadata;
                }
            } catch (Exception $e) {
                // Keep as string if parsing fails
            }
        }
        
        $rows[] = $row;
    }
    return $rows;
}

// Format timestamp
function format_timestamp($timestamp) {
    try {
        $date = new DateTime($timestamp);
        return $date->format('M j, Y, g:i A');
    } catch (Exception $e) {
        return $timestamp;
    }
}

// Main request handler
function handle_request() {
    // Get action parameter
    $action = isset($_GET['action']) ? $_GET['action'] : '';
    
    // Set default content type to JSON
    header('Content-Type: application/json');
    
    try {
        // Connect to database
        $db = get_db_connection();
        if (!$db) {
            throw new Exception("Could not connect to database");
        }
        
        // Handle different actions
        switch ($action) {
            case 'get_totals':
                return handle_get_totals($db);
                
            case 'get_daily_stats':
                return handle_get_daily_stats($db);
                
            case 'get_events':
                return handle_get_events($db);
                
            case 'get_thumbnail':
                return handle_get_thumbnail($db);
                
            case 'export_csv':
                return handle_export_csv($db);
                
            default:
                throw new Exception("Unknown action: $action");
        }
    } catch (Exception $e) {
        log_message("API error: " . $e->getMessage(), 'ERROR');
        
        // Return error response
        http_response_code(500);
        return [
            'error' => 'Internal server error',
            'message' => $e->getMessage()
        ];
    } finally {
        // Close database connection if it exists
        if (isset($db) && $db) {
            $db->close();
        }
    }
}

// Handle get_totals action
function handle_get_totals($db) {
    // Query total statistics
    $query = '
        SELECT 
            COALESCE(SUM(can_count), 0) as total_cans,
            COALESCE(SUM(recycling_count), 0) as total_recycling,
            COALESCE(SUM(garbage_count), 0) as total_garbage,
            COALESCE(SUM(total_count), 0) as grand_total 
        FROM statistics
    ';
    
    $result = $db->query($query);
    if (!$result) {
        throw new Exception("Query failed: " . $db->lastErrorMsg());
    }
    
    $totals = $result->fetchArray(SQLITE3_ASSOC);
    
    // Default values if no data
    if (!$totals) {
        $totals = [
            'total_cans' => 0,
            'total_recycling' => 0,
            'total_garbage' => 0,
            'grand_total' => 0
        ];
    }
    
    return $totals;
}

// Handle get_daily_stats action
function handle_get_daily_stats($db) {
    // Get days parameter (default: 30)
    $days = isset($_GET['days']) ? intval($_GET['days']) : 30;
    
    // Query daily statistics
    $query = 'SELECT * FROM statistics ORDER BY date ASC';
    
    // Apply days filter if provided
    if ($days > 0) {
        $date = date('Y-m-d', strtotime("-$days days"));
        $query = "SELECT * FROM statistics WHERE date >= '$date' ORDER BY date ASC";
    }
    
    $result = $db->query($query);
    if (!$result) {
        throw new Exception("Query failed: " . $db->lastErrorMsg());
    }
    
    return fetch_all($result);
}

// Handle get_events action
function handle_get_events($db) {
    // Get query parameters
    $item_type = isset($_GET['item_type']) ? $_GET['item_type'] : '';
    $min_confidence = isset($_GET['confidence']) ? floatval($_GET['confidence']) : 0;
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
    
    // Build query with filters
    $query = '
        SELECT id, timestamp, item_type, confidence, sort_destination, image_id, metadata
        FROM sort_events
        WHERE 1=1
    ';
    
    // Add filters
    if (!empty($item_type) && $item_type != 'all') {
        $query .= " AND item_type = '" . SQLite3::escapeString($item_type) . "'";
    }
    
    if ($min_confidence > 0) {
        $query .= " AND confidence >= " . $min_confidence;
    }
    
    // Add ordering and limit
    $query .= " ORDER BY timestamp DESC LIMIT " . $limit;
    
    $result = $db->query($query);
    if (!$result) {
        throw new Exception("Query failed: " . $db->lastErrorMsg());
    }
    
    $events = fetch_all($result);
    
    // Add formatted time for display
    foreach ($events as &$event) {
        if (isset($event['timestamp'])) {
            $event['formatted_time'] = format_timestamp($event['timestamp']);
        }
    }
    
    return $events;
}

// Handle get_thumbnail action
function handle_get_thumbnail($db) {
    // Get image ID
    $image_id = isset($_GET['id']) ? $_GET['id'] : '';
    
    if (empty($image_id)) {
        // Set image headers but return error image
        header('Content-Type: image/png');
        readfile('./static/img/no-image.png');
        exit;
    }
    
    // Get image data
    $stmt = $db->prepare('SELECT thumbnail FROM images WHERE id = :id');
    $stmt->bindValue(':id', $image_id, SQLITE3_TEXT);
    
    $result = $stmt->execute();
    if (!$result) {
        throw new Exception("Query failed: " . $db->lastErrorMsg());
    }
    
    $row = $result->fetchArray(SQLITE3_ASSOC);
    
    // Override content type for image
    header('Content-Type: image/png');
    
    if ($row && isset($row['thumbnail'])) {
        // Output image data
        echo $row['thumbnail'];
    } else {
        // Default image
        readfile('./static/img/no-image.png');
    }
    
    // Exit to prevent any other output
    exit;
}

// Handle export_csv action
function handle_export_csv($db) {
    // Set headers for CSV download
    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="waste_sorting_stats.csv"');
    
    // Query statistics data
    $result = $db->query('SELECT * FROM statistics ORDER BY date ASC');
    if (!$result) {
        throw new Exception("Query failed: " . $db->lastErrorMsg());
    }
    
    $stats = fetch_all($result);
    
    if (empty($stats)) {
        throw new Exception("No data available for export");
    }
    
    // Create output stream
    $output = fopen('php://output', 'w');
    
    // Write CSV header
    fputcsv($output, array_keys($stats[0]));
    
    // Write data rows
    foreach ($stats as $row) {
        // Convert metadata object back to string for CSV
        if (isset($row['metadata']) && is_array($row['metadata'])) {
            $row['metadata'] = json_encode($row['metadata']);
        }
        
        fputcsv($output, $row);
    }
    
    fclose($output);
    
    // Exit to prevent any other output
    exit;
}

// Execute request and output response
$response = handle_request();

// Output JSON response (if not already sent by a specific handler)
if (!headers_sent()) {
    echo json_encode($response);
}
?>