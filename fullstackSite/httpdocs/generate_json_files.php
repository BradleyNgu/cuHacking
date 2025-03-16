<?php
/**
 * generate_json_files.php - Simple JSON Generator for Waste Sorting Analytics
 * 
 * This script generates sample JSON files for the dashboard when no real data is available.
 * Place this file in the root directory of your website and access it once to generate sample JSON.
 * 
 * IMPORTANT: After generating the files, either delete this script or move it to a secure location
 * to prevent potential security issues.
 */

// Configuration
$config = [
    'json_dir' => './static/api',
    'days_of_data' => 30,
    'events_count' => 50
];

// Setup basic error handling
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Define function to log messages
function log_message($message) {
    echo "<p>$message</p>";
}

// Generate JSON files
function generate_json_files($config) {
    // Make sure the directory exists
    if (!is_dir($config['json_dir'])) {
        if (!mkdir($config['json_dir'], 0755, true)) {
            log_message("Error: Failed to create directory {$config['json_dir']}");
            return false;
        }
    }
    
    // Check if directory is writable
    if (!is_writable($config['json_dir'])) {
        log_message("Error: Directory {$config['json_dir']} is not writable");
        return false;
    }
    
    // Generate totals.json
    $total_cans = 0;
    $total_recycling = 0;
    $total_garbage = 0;
    
    // Generate daily.json
    $daily_data = [];
    $today = new DateTime();
    
    for ($i = $config['days_of_data'] - 1; $i >= 0; $i--) {
        $date = clone $today;
        $date->modify("-$i days");
        $date_str = $date->format('Y-m-d');
        
        // Generate random counts
        $can_count = rand(5, 15);
        $recycling_count = rand(3, 10);
        $garbage_count = rand(2, 8);
        $total_count = $can_count + $recycling_count + $garbage_count;
        
        // Add to totals
        $total_cans += $can_count;
        $total_recycling += $recycling_count;
        $total_garbage += $garbage_count;
        
        // Add to daily data
        $daily_data[] = [
            'date' => $date_str,
            'can_count' => $can_count,
            'recycling_count' => $recycling_count,
            'garbage_count' => $garbage_count,
            'total_count' => $total_count
        ];
    }
    
    // Calculate grand total
    $grand_total = $total_cans + $total_recycling + $total_garbage;
    
    // Create totals.json
    $totals = [
        'total_cans' => $total_cans,
        'total_recycling' => $total_recycling,
        'total_garbage' => $total_garbage,
        'grand_total' => $grand_total
    ];
    
    $totals_file = $config['json_dir'] . '/totals.json';
    if (file_put_contents($totals_file, json_encode($totals, JSON_PRETTY_PRINT)) === false) {
        log_message("Error: Failed to write totals.json");
        return false;
    } else {
        log_message("Successfully generated totals.json");
    }
    
    // Write daily.json
    $daily_file = $config['json_dir'] . '/daily.json';
    if (file_put_contents($daily_file, json_encode($daily_data, JSON_PRETTY_PRINT)) === false) {
        log_message("Error: Failed to write daily.json");
        return false;
    } else {
        log_message("Successfully generated daily.json");
    }
    
    // Generate events.json
    $events = [];
    $item_types = ['can', 'recycling', 'garbage'];
    $sort_destinations = ['recycling', 'recycling', 'garbage'];
    
    for ($i = 0; $i < $config['events_count']; $i++) {
        $time = new DateTime();
        $time->modify("-" . rand(0, 24 * 7) . " hours"); // Random time in the last week
        
        $type_index = rand(0, 2);
        $item_type = $item_types[$type_index];
        $destination = $sort_destinations[$type_index];
        $confidence = round(0.7 + (rand(0, 30) / 100), 2); // Random confidence between 0.70 and 0.99
        
        $events[] = [
            'id' => generate_uuid(),
            'timestamp' => $time->format('Y-m-d\TH:i:s.000\Z'),
            'formatted_time' => $time->format('M j, Y, g:i A'),
            'item_type' => $item_type,
            'confidence' => $confidence,
            'sort_destination' => $destination,
            'metadata' => [
                'simulation' => true,
                'generated' => (new DateTime())->format('Y-m-d\TH:i:s\Z')
            ]
        ];
    }
    
    // Sort by timestamp descending (newest first)
    usort($events, function($a, $b) {
        return strcmp($b['timestamp'], $a['timestamp']);
    });
    
    // Write events.json
    $events_file = $config['json_dir'] . '/events.json';
    if (file_put_contents($events_file, json_encode($events, JSON_PRETTY_PRINT)) === false) {
        log_message("Error: Failed to write events.json");
        return false;
    } else {
        log_message("Successfully generated events.json");
    }
    
    return true;
}

// Generate a UUID v4
function generate_uuid() {
    $data = random_bytes(16);
    $data[6] = chr(ord($data[6]) & 0x0f | 0x40);
    $data[8] = chr(ord($data[8]) & 0x3f | 0x80);
    
    return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($data), 4));
}

// Display simple HTML page
echo '<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JSON Generator for Waste Sorting Analytics</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        .success { color: green; }
        .error { color: red; }
        pre {
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow: auto;
        }
        .warning {
            background: #fffacd;
            padding: 15px;
            border-radius: 5px;
            border-left: 5px solid #ffd700;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <h1>JSON Generator for Waste Sorting Analytics</h1>
    <div class="warning">
        <strong>Important:</strong> After generating the files, delete this script or move it to a secure location to prevent security issues.
    </div>
    <h2>Generating sample JSON files...</h2>';

// Generate the files
$result = generate_json_files($config);

// Show status
if ($result) {
    echo '<div class="success">
        <h2>✅ Success!</h2>
        <p>Sample JSON files have been generated in the ' . htmlspecialchars($config['json_dir']) . ' directory:</p>
        <ul>
            <li>totals.json</li>
            <li>daily.json</li>
            <li>events.json</li>
        </ul>
        <p>Your dashboard should now display this sample data.</p>
    </div>';
    
    // Preview of the files
    echo '<h3>Preview of generated files:</h3>';
    
    echo '<h4>totals.json</h4>';
    echo '<pre>' . htmlspecialchars(file_get_contents($config['json_dir'] . '/totals.json')) . '</pre>';
    
    echo '<h4>Sample of daily.json</h4>';
    $daily_content = file_get_contents($config['json_dir'] . '/daily.json');
    echo '<pre>' . htmlspecialchars(substr($daily_content, 0, 500)) . '...</pre>';
    
    echo '<h4>Sample of events.json</h4>';
    $events_content = file_get_contents($config['json_dir'] . '/events.json');
    echo '<pre>' . htmlspecialchars(substr($events_content, 0, 500)) . '...</pre>';
    
} else {
    echo '<div class="error">
        <h2>❌ Error!</h2>
        <p>Failed to generate sample JSON files. Please check the error messages above.</p>
    </div>';
}

echo '<div class="warning">
    <strong>Final reminder:</strong> Delete this script now to prevent security issues!
</div>
</body>
</html>';