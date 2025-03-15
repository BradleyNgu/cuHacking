// waste_sorter_arduino.ino - Servo control for waste sorting system
#include <Servo.h>

// Define pins
const int PLATFORM_SERVO_PIN = 9;     // Controls the tilting platform

// Create servo object
Servo platformServo;                  // Controls the tilting platform

// Define positions
const int PLATFORM_NEUTRAL = 90;      // Platform level
const int PLATFORM_RECYCLING = 45;    // Platform tilted left 45 degrees
const int PLATFORM_GARBAGE = 135;     // Platform tilted right 45 degrees

// Movement parameters for smooth motion
const int SERVO_SPEED = 15;           // Delay between steps (ms)
const int SERVO_STEP = 3;             // Degrees to move in each step

// State variables
bool isSorting = false;
unsigned long sortingStartTime = 0;
const unsigned long SORTING_TIMEOUT = 5000;  // 5 seconds timeout

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  
  // Attach servo to pin
  platformServo.attach(PLATFORM_SERVO_PIN);
  
  // Initialize servo position - move smoothly to avoid jerking
  moveServoSmooth(platformServo.read(), PLATFORM_NEUTRAL);
  
  // Wait for everything to initialize
  delay(1000);
  
  Serial.println("READY:Waste Sorter Arduino System v1.0");
}

void loop() {
  // Check if there's a command from the computer
  if (Serial.available() > 0) {
    char command = Serial.read();
    
    if (command == 'C') {
      // Can recycling
      Serial.println("STATUS:Sorting as can recycling");
      sortItem(true);
    }
    else if (command == 'R') {
      // Regular recycling
      Serial.println("STATUS:Sorting as regular recycling");
      sortItem(true);
    } 
    else if (command == 'G') {
      // Regular garbage
      Serial.println("STATUS:Sorting as garbage");
      sortItem(false);
    }
    else if (command == 'N') {
      // Return to neutral position
      resetSystem();
      Serial.println("STATUS:System reset to neutral");
    }
    // Platform calibration commands
    else if (command == 'P') {
      // Platform position query
      int currentPos = platformServo.read();
      Serial.print("INFO:Current platform servo position: ");
      Serial.println(currentPos);
    }
    else if (command == '+') {
      // Increase platform angle by 5 degrees
      int currentPos = platformServo.read();
      int newPos = min(currentPos + 5, 180);
      platformServo.write(newPos);
      Serial.print("INFO:Adjusted platform servo to: ");
      Serial.println(newPos);
    }
    else if (command == '-') {
      // Decrease platform angle by 5 degrees
      int currentPos = platformServo.read();
      int newPos = max(currentPos - 5, 0);
      platformServo.write(newPos);
      Serial.print("INFO:Adjusted platform servo to: ");
      Serial.println(newPos);
    }
    // Specific position command (e.g. "S90" for 90 degrees)
    else if (command == 'S') {
      // Read the numeric value that follows
      String posStr = "";
      while (Serial.available() > 0) {
        char c = Serial.read();
        if (isDigit(c)) posStr += c;
        delay(2);  // Short delay to allow serial buffer to fill
      }
      
      if (posStr.length() > 0) {
        int newPos = constrain(posStr.toInt(), 0, 180);
        moveServoSmooth(platformServo.read(), newPos);
        Serial.print("INFO:Servo moved to position: ");
        Serial.println(newPos);
      }
    }
    // Test commands
    else if (command == 'T') {
      // Run test sequence
      testSequence();
    }
    else if (command == 'V') {
      // Version info
      Serial.println("INFO:Waste Sorter Arduino System v1.0");
    }
  }
  
  // Check for timeout in sorting cycle
  if (isSorting && (millis() - sortingStartTime > SORTING_TIMEOUT)) {
    resetSystem();
    Serial.println("WARNING:Sorting timeout - system reset");
  }
}

void sortItem(bool isRecycling) {
  // Start sorting cycle
  isSorting = true;
  sortingStartTime = millis();
  
  // 1. Make sure platform starts in neutral position
  moveServoSmooth(platformServo.read(), PLATFORM_NEUTRAL);
  
  // 2. Short pause for final confirmation
  delay(300);
  
  // 3. Tilt platform to appropriate side
  if (isRecycling) {
    // Tilt platform toward recycling bin
    moveServoSmooth(platformServo.read(), PLATFORM_RECYCLING);
    Serial.println("STATUS:Platform tilted to recycling position");
  } 
  else {
    // Tilt platform toward garbage bin
    moveServoSmooth(platformServo.read(), PLATFORM_GARBAGE);
    Serial.println("STATUS:Platform tilted to garbage position");
  }
  
  // 4. Wait for item to slide off
  delay(2500);
  
  // 5. Return to neutral position
  moveServoSmooth(platformServo.read(), PLATFORM_NEUTRAL);
  
  // 6. Reset state variables
  isSorting = false;
  
  // 7. Send completion notification
  Serial.println("EVENT:SORT_COMPLETE");
}

void resetSystem() {
  // Reset servo to neutral position
  moveServoSmooth(platformServo.read(), PLATFORM_NEUTRAL);
  
  // Reset state variables
  isSorting = false;
}

void moveServoSmooth(int startPos, int endPos) {
  // Move servo smoothly from start to end position
  if (startPos < endPos) {
    // Moving clockwise
    for (int pos = startPos; pos <= endPos; pos += SERVO_STEP) {
      platformServo.write(pos);
      delay(SERVO_SPEED);
    }
  } else {
    // Moving counterclockwise
    for (int pos = startPos; pos >= endPos; pos -= SERVO_STEP) {
      platformServo.write(pos);
      delay(SERVO_SPEED);
    }
  }
  
  // Ensure we reach the exact end position
  platformServo.write(endPos);
  delay(50); // Short pause to allow servo to reach position
}

void testSequence() {
  // Perform a complete test sequence
  Serial.println("STATUS:Starting test sequence");
  
  // 1. Move to neutral
  moveServoSmooth(platformServo.read(), PLATFORM_NEUTRAL);
  Serial.println("STATUS:Test - Neutral position");
  delay(1000);
  
  // 2. Move to recycling position
  moveServoSmooth(platformServo.read(), PLATFORM_RECYCLING);
  Serial.println("STATUS:Test - Recycling position");
  delay(2000);
  
  // 3. Back to neutral
  moveServoSmooth(platformServo.read(), PLATFORM_NEUTRAL);
  Serial.println("STATUS:Test - Back to neutral");
  delay(1000);
  
  // 4. Move to garbage position
  moveServoSmooth(platformServo.read(), PLATFORM_GARBAGE);
  Serial.println("STATUS:Test - Garbage position");
  delay(2000);
  
  // 5. Back to neutral
  moveServoSmooth(platformServo.read(), PLATFORM_NEUTRAL);
  Serial.println("STATUS:Test - Back to neutral");
  delay(1000);
  
  Serial.println("STATUS:Test sequence complete");
}