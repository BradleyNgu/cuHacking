<?php
/**
 * create_json_files.php - Simple JSON File Generator for Waste Sorting Analytics
 * 
 * This script creates the basic JSON files required for the dashboard to function.
 * Use this if your dashboard shows no data and you need to initialize the files.
 */

// Configuration
$config = [
    'json_dir' => 'static/api',
    'days_of_data' => 30,
    'events_count' => 20
];

// Check if we should modify existing files or create new ones
$mode = isset($_GET['mode']) ? $_GET['mode'] : 'create';
echo '<h1>JSON File Generator</h1>';

if ($mode === 'update') {
    updateJsonFiles($config);
} else {
    createJsonFiles($config);
}

// Create JSON files
function createJsonFiles($config) {
    // Make sure the directory exists
    if (!is_dir($config['json_dir'])) {
        if (!mkdir($config['json_dir'], 0755, true)) {
            die("<p>Error: Failed to create directory {$config['json_dir']}</p>");
        }
        echo "<p>Created directory: {$config['json_dir']}</p>";
    }
    
    // Check if the directory is writable
    if (!is_writable($config['json_dir'])) {
        die("<p>Error: Directory {$config['json_dir']} is not writable</p>");
    }
    
    // 1. Create totals.json
    $totals = [
        'total_cans' => 246,
        'total_recycling' => 183,
        'total_garbage' => 129,
        'grand_total' => 558
    ];
    
    $totals_file = $config['json_dir'] . '/totals.json';
    if (file_put_contents($totals_file, json_encode($totals, JSON_PRETTY_PRINT)) === false) {
        die("<p>Error: Failed to write totals.json</p>");
    }
    echo "<p>Created totals.json</p>";
    
    // 2. Create daily.json
    $daily_data = [];
    $today = new DateTime();
    
    for ($i = $config['days_of_data'] - 1; $i >= 0; $i--) {
        $date = clone $today;
        $date->modify("-$i days");
        $date_str = $date->format('Y-m-d');
        
        $daily_data[] = [
            'date' => $date_str,
            'can_count' => rand(5, 15),
            'recycling_count' => rand(3, 10),
            'garbage_count' => rand(2, 8),
            'total_count' => rand(15, 30)
        ];
    }
    
    $daily_file = $config['json_dir'] . '/daily.json';
    if (file_put_contents($daily_file, json_encode($daily_data, JSON_PRETTY_PRINT)) === false) {
        die("<p>Error: Failed to write daily.json</p>");
    }
    echo "<p>Created daily.json</p>";
    
    // 3. Create events.json
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
            'id' => generateUuid(),
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
    
    $events_file = $config['json_dir'] . '/events.json';
    if (file_put_contents($events_file, json_encode($events, JSON_PRETTY_PRINT)) === false) {
        die("<p>Error: Failed to write events.json</p>");
    }
    echo "<p>Created events.json</p>";
    
    echo "<p>JSON files created successfully! <a href='debug.html'>View Debug Page</a> | <a href='index.html'>View Dashboard</a></p>";
}

// Update JSON files with random new data
function updateJsonFiles($config) {
    // Check if files exist
    $totals_file = $config['json_dir'] . '/totals.json';
    $daily_file = $config['json_dir'] . '/daily.json';
    $events_file = $config['json_dir'] . '/events.json';
    
    if (!file_exists($totals_file) || !file_exists($daily_file) || !file_exists($events_file)) {
        echo "<p>Some files don't exist. Creating new files instead.</p>";
        createJsonFiles($config);
        return;
    }
    
    // 1. Update totals.json
    $totals = json_decode(file_get_contents($totals_file), true);
    
    // Add random new items
    $new_cans = rand(1, 5);
    $new_recycling = rand(1, 3);
    $new_garbage = rand(1, 4);
    
    $totals['total_cans'] += $new_cans;
    $totals['total_recycling'] += $new_recycling;
    $totals['total_garbage'] += $new_garbage;
    $totals['grand_total'] = $totals['total_cans'] + $totals['total_recycling'] + $totals['total_garbage'];
    
    if (file_put_contents($totals_file, json_encode($totals, JSON_PRETTY_PRINT)) === false) {
        die("<p>Error: Failed to update totals.json</p>");
    }
    echo "<p>Updated totals.json: Added $new_cans cans, $new_recycling recycling, $new_garbage garbage</p>";
    
    // 2. Update daily.json
    $daily_data = json_decode(file_get_contents($daily_file), true);
    
    // Add today's data if not already present
    $today = (new DateTime())->format('Y-m-d');
    $today_exists = false;
    
    foreach ($daily_data as &$day) {
        if ($day['date'] === $today) {
            // Update today's counts
            $day['can_count'] += $new_cans;
            $day['recycling_count'] += $new_recycling;
            $day['garbage_count'] += $new_garbage;
            $day['total_count'] = $day['can_count'] + $day['recycling_count'] + $day['garbage_count'];
            $today_exists = true;
            break;
        }
    }
    
    if (!$today_exists) {
        // Add today
        $daily_data[] = [
            'date' => $today,
            'can_count' => $new_cans,
            'recycling_count' => $new_recycling,
            'garbage_count' => $new_garbage,
            'total_count' => $new_cans + $new_recycling + $new_garbage
        ];
    }
    
    // Sort by date
    usort($daily_data, function($a, $b) {
        return strcmp($a['date'], $b['date']);
    });
    
    if (file_put_contents($daily_file, json_encode($daily_data, JSON_PRETTY_PRINT)) === false) {
        die("<p>Error: Failed to update daily.json</p>");
    }
    echo "<p>Updated daily.json: " . ($today_exists ? "Updated" : "Added") . " entry for $today</p>";
    
    // 3. Update events.json
    $events = json_decode(file_get_contents($events_file), true);
    
    // Add a few new events
    $item_types = ['can', 'recycling', 'garbage'];
    $sort_destinations = ['recycling', 'recycling', 'garbage'];
    $new_events_count = $new_cans + $new_recycling + $new_garbage;
    
    for ($i = 0; $i < $new_events_count; $i++) {
        $time = new DateTime();
        $time->modify("-" . rand(0, 3600) . " seconds"); // Random time in the last hour
        
        // Determine type based on distribution of new items
        $type_index = 0;
        $rand = rand(1, $new_events_count);
        if ($rand <= $new_cans) {
            $type_index = 0; // can
        } else if ($rand <= $new_cans + $new_recycling) {
            $type_index = 1; // recycling
        } else {
            $type_index = 2; // garbage
        }
        
        $item_type = $item_types[$type_index];
        $destination = $sort_destinations[$type_index];
        $confidence = round(0.7 + (rand(0, 30) / 100), 2);
        
        $events[] = [
            'id' => generateUuid(),
            'timestamp' => $time->format('Y-m-d\TH:i:s.000\Z'),
            'formatted_time' => $time->format('M j, Y, g:i A'),
            'item_type' => $item_type,
            'confidence' => $confidence,
            'sort_destination' => $destination,
            'metadata' => [
                'simulation' => true,
                'generated' => (new DateTime())->format('Y-m-d\TH:i:s\Z'),
                'update' => true
            ]
        ];
    }
    
    // Sort by timestamp descending (newest first)
    usort($events, function($a, $b) {
        return strcmp($b['timestamp'], $a['timestamp']);
    });
    
    if (file_put_contents($events_file, json_encode($events, JSON_PRETTY_PRINT)) === false) {
        die("<p>Error: Failed to update events.json</p>");
    }
    echo "<p>Updated events.json: Added $new_events_count new events</p>";
    
    echo "<p>JSON files updated successfully! <a href='debug.html'>View Debug Page</a> | <a href='index.html'>View Dashboard</a></p>";
    echo "<p><a href='create_json_files.php?mode=update'>Update Again</a></p>";
}

// Generate a UUID v4
function generateUuid() {
    $data = random_bytes(16);
    $data[6] = chr(ord($data[6]) & 0x0f | 0x40);
    $data[8] = chr(ord($data[8]) & 0x3f | 0x80);
    
    return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($data), 4));
}