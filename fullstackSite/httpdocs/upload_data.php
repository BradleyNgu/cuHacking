<?php
/**
 * upload_data.php - Waste Sorting Data Receiver
 * 
 * This script receives sort events and statistics from the waste sorting computer
 * and updates both the database and the static JSON files used by the website.
 */

// Configuration - DO NOT CHANGE THE API KEY HERE, IT MUST MATCH YOUR PYTHON SCRIPT
$config = [
    'api_key' => 'ws_6f28a91e7d3c4b5f8a2e9d0c7b6a5f4', // Pre-configured secure key
    'db_path' => './data/sorting_data.db',
    'log_path' => './logs/upload.log',
    'json_dir' => './static/api' // This is the path where JSON files are stored
];

// Enable error reporting but don't display errors
error_reporting(E_ALL);
ini_set('display_errors', 0);

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

// Process uploaded data
function process_data($data) {
    global $config;
    
    try {
        // Make sure directories exist
        $db_dir = dirname($config['db_path']);
        if (!is_dir($db_dir)) {
            if (!mkdir($db_dir, 0755, true)) {
                throw new Exception("Failed to create database directory: " . $db_dir);
            }
        }
        
        if (!is_dir($config['json_dir'])) {
            if (!mkdir($config['json_dir'], 0755, true)) {
                throw new Exception("Failed to create JSON directory: " . $config['json_dir']);
            }
        }
        
        // Connect to database
        $db = new SQLite3($config['db_path']);
        $db->busyTimeout(5000); // Set busy timeout to 5 seconds
        $db->exec('PRAGMA journal_mode = WAL;');
        
        // Create tables if they don't exist
        create_tables($db);
        
        // Begin transaction
        $db->exec('BEGIN TRANSACTION');
        
        // Process events
        $events_processed = 0;
        if (isset($data['events']) && is_array($data['events'])) {
            $events_processed = process_events($db, $data['events']);
        }
        
        // Process stats
        $stats_processed = 0;
        if (isset($data['stats']) && is_array($data['stats'])) {
            $stats_processed = process_stats($db, $data['stats']);
        }
        
        // Commit transaction
        $db->exec('COMMIT');
        
        // Generate JSON files
        $json_generated = generate_json_files($db);
        
        // Close database
        $db->close();
        
        // Log success
        log_message("Processed $events_processed events and $stats_processed statistics records");
        
        return [
            'success' => true,
            'message' => "Processed $events_processed events and $stats_processed statistics records",
            'json_generated' => $json_generated
        ];
    } catch (Exception $e) {
        // Try to rollback transaction if there was an error
        try {
            if (isset($db) && $db) {
                $db->exec('ROLLBACK');
                $db->close();
            }
        } catch (Exception $ex) {
            // Ignore rollback errors
        }
        
        // Log error
        log_message("Error processing data: " . $e->getMessage(), 'ERROR');
        
        return [
            'success' => false,
            'error' => "Database error: " . $e->getMessage()
        ];
    }
}

// Create database tables if they don't exist
function create_tables($db) {
    // Sort events table
    $db->exec('
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
    ');
    
    // Statistics table
    $db->exec('
        CREATE TABLE IF NOT EXISTS statistics (
            date TEXT PRIMARY KEY,
            can_count INTEGER DEFAULT 0,
            recycling_count INTEGER DEFAULT 0,
            garbage_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            metadata TEXT
        )
    ');
    
    // Create index on timestamp for better performance
    $db->exec('CREATE INDEX IF NOT EXISTS idx_sort_events_timestamp ON sort_events(timestamp)');
}

// Process events data
function process_events($db, $events) {
    $stmt = $db->prepare('
        INSERT OR REPLACE INTO sort_events 
        (id, timestamp, item_type, confidence, sort_destination, image_id, user_id, metadata) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ');
    
    $count = 0;
    foreach ($events as $event) {
        if (!isset($event['id']) || !isset($event['timestamp']) || !isset($event['item_type']) || 
            !isset($event['confidence']) || !isset($event['sort_destination'])) {
            continue;
        }
        
        $stmt->bindValue(1, $event['id'], SQLITE3_TEXT);
        $stmt->bindValue(2, $event['timestamp'], SQLITE3_TEXT);
        $stmt->bindValue(3, $event['item_type'], SQLITE3_TEXT);
        $stmt->bindValue(4, $event['confidence'], SQLITE3_FLOAT);
        $stmt->bindValue(5, $event['sort_destination'], SQLITE3_TEXT);
        
        // Optional fields
        $image_id = isset($event['image_id']) ? $event['image_id'] : null;
        $user_id = isset($event['user_id']) ? $event['user_id'] : null;
        
        // Metadata is optional
        $metadata = isset($event['metadata']) ? json_encode($event['metadata']) : null;
        
        $stmt->bindValue(6, $image_id, SQLITE3_TEXT);
        $stmt->bindValue(7, $user_id, SQLITE3_TEXT);
        $stmt->bindValue(8, $metadata, SQLITE3_TEXT);
        
        $result = $stmt->execute();
        if ($result) {
            $count++;
        }
        $stmt->reset();
    }
    
    return $count;
}

// Process statistics data
function process_stats($db, $stats) {
    $stmt = $db->prepare('
        INSERT OR REPLACE INTO statistics 
        (date, can_count, recycling_count, garbage_count, total_count, metadata) 
        VALUES (?, ?, ?, ?, ?, ?)
    ');
    
    $count = 0;
    foreach ($stats as $stat) {
        if (!isset($stat['date'])) {
            continue;
        }
        
        $can_count = isset($stat['can_count']) ? intval($stat['can_count']) : 0;
        $recycling_count = isset($stat['recycling_count']) ? intval($stat['recycling_count']) : 0;
        $garbage_count = isset($stat['garbage_count']) ? intval($stat['garbage_count']) : 0;
        $total_count = $can_count + $recycling_count + $garbage_count;
        
        // Metadata is optional
        $metadata = isset($stat['metadata']) ? json_encode($stat['metadata']) : null;
        
        $stmt->bindValue(1, $stat['date'], SQLITE3_TEXT);
        $stmt->bindValue(2, $can_count, SQLITE3_INTEGER);
        $stmt->bindValue(3, $recycling_count, SQLITE3_INTEGER);
        $stmt->bindValue(4, $garbage_count, SQLITE3_INTEGER);
        $stmt->bindValue(5, $total_count, SQLITE3_INTEGER);
        $stmt->bindValue(6, $metadata, SQLITE3_TEXT);
        
        $result = $stmt->execute();
        if ($result) {
            $count++;
        }
        $stmt->reset();
    }
    
    return $count;
}

// Generate JSON files for the static website
function generate_json_files($db) {
    global $config;
    
    try {
        // Make sure directory is writable
        if (!is_writable($config['json_dir'])) {
            throw new Exception("JSON directory is not writable: " . $config['json_dir']);
        }
        
        // Generate totals.json
        $totals = [];
        $result = $db->query('
            SELECT 
                COALESCE(SUM(can_count), 0) as total_cans,
                COALESCE(SUM(recycling_count), 0) as total_recycling,
                COALESCE(SUM(garbage_count), 0) as total_garbage,
                COALESCE(SUM(total_count), 0) as grand_total 
            FROM statistics
        ');
        
        if ($row = $result->fetchArray(SQLITE3_ASSOC)) {
            $totals = $row;
        }
        
        // Default values in case of empty database
        if (!isset($totals['total_cans'])) $totals['total_cans'] = 0;
        if (!isset($totals['total_recycling'])) $totals['total_recycling'] = 0;
        if (!isset($totals['total_garbage'])) $totals['total_garbage'] = 0;
        if (!isset($totals['grand_total'])) $totals['grand_total'] = 0;
        
        // Write totals.json
        $totals_file = $config['json_dir'] . '/totals.json';
        if (file_put_contents($totals_file, json_encode($totals, JSON_PRETTY_PRINT)) === false) {
            throw new Exception("Failed to write totals.json");
        }
        
        // Generate daily.json
        $daily = [];
        $result = $db->query('SELECT * FROM statistics ORDER BY date ASC');
        while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
            // Parse metadata if it exists
            if (isset($row['metadata']) && $row['metadata']) {
                $row['metadata'] = json_decode($row['metadata'], true);
            }
            $daily[] = $row;
        }
        
        // Write daily.json
        $daily_file = $config['json_dir'] . '/daily.json';
        if (file_put_contents($daily_file, json_encode($daily, JSON_PRETTY_PRINT)) === false) {
            throw new Exception("Failed to write daily.json");
        }
        
        // Generate events.json
        $events = [];
        $result = $db->query('
            SELECT id, timestamp, item_type, confidence, sort_destination, image_id, user_id, metadata 
            FROM sort_events 
            ORDER BY timestamp DESC 
            LIMIT 100
        ');
        
        while ($row = $result->fetchArray(SQLITE3_ASSOC)) {
            // Format timestamp for display
            $timestamp = $row['timestamp'];
            $date = new DateTime($timestamp);
            $row['formatted_time'] = $date->format('M j, Y, g:i A');
            
            // Parse metadata if it's a JSON string
            if (isset($row['metadata']) && is_string($row['metadata'])) {
                $metadata = json_decode($row['metadata'], true);
                if ($metadata !== null) {
                    $row['metadata'] = $metadata;
                }
            }
            
            $events[] = $row;
        }
        
        // Write events.json
        $events_file = $config['json_dir'] . '/events.json';
        if (file_put_contents($events_file, json_encode($events, JSON_PRETTY_PRINT)) === false) {
            throw new Exception("Failed to write events.json");
        }
        
        log_message("Generated JSON files successfully");
        return true;
    } catch (Exception $e) {
        log_message("Error generating JSON files: " . $e->getMessage(), 'ERROR');
        return false;
    }
}

// Main execution
header('Content-Type: application/json');

// Check request method
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    echo json_encode([
        'success' => false,
        'error' => 'Invalid request method. Use POST.'
    ]);
    exit;
}

// Get JSON data
$input = file_get_contents('php://input');
$data = json_decode($input, true);

if (!$data) {
    echo json_encode([
        'success' => false,
        'error' => 'Invalid JSON data'
    ]);
    exit;
}

// Validate API key
if (!isset($data['api_key']) || $data['api_key'] !== $config['api_key']) {
    log_message("Invalid API key provided", 'ERROR');
    echo json_encode([
        'success' => false,
        'error' => 'Invalid API key'
    ]);
    exit;
}

// Process data
$result = process_data($data);
echo json_encode($result);