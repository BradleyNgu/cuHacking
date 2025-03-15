# Waste Sorting System

A comprehensive automated waste sorting system that uses computer vision, machine learning, and robotics to sort waste items into recycling and garbage. The system includes a crypto-based rewards program for recycling cans, a web analytics dashboard, and a database for tracking sorting history.

## Features

- **Computer Vision Classification**: Automatically identifies cans, recyclables, and garbage
- **Automatic Sorting**: Mechanically sorts items into appropriate bins
- **Token Rewards**: Earn crypto tokens for recycling cans (valued at $0.05 per can)
- **Analytics Dashboard**: Web interface to view statistics and sorting history
- **Custom Model Training**: Train your own classification model for better accuracy
- **Data Tracking**: Store images and sorting data for analysis

## System Requirements

### Hardware
- Arduino Uno or compatible board
- High-torque servo motor (at least 15-20 kg-cm torque)
- Logitech Brio 4K webcam (or similar high-resolution camera)
- Computer with USB ports (Windows/Mac/Linux)
- 5V 3A power supply for servo
- Wood and acrylic materials for the physical platform

### Software
- Python 3.8 or newer
- TensorFlow 2.x
- OpenCV
- SQLite
- Flask (for web dashboard)
- Arduino IDE (for uploading firmware)

## Directory Structure

```
waste-sorting-system/
├── arduino/                  # Arduino firmware
│   └── waste_sorter_arduino.ino
├── data/                     # Data storage directory
│   ├── counts.json           # Counter values
│   └── sorting_data.db       # SQLite database
├── logs/                     # Log files
├── models/                   # Trained models
│   ├── latest_model.h5       # Latest model
│   └── class_mapping.json    # Class mapping
├── static/                   # Static web files
│   ├── css/
│   ├── js/
│   └── img/
├── templates/                # HTML templates
├── training_data/            # Data for model training
│   ├── can/
│   ├── recycling/
│   └── garbage/
├── app.py                    # Web dashboard Flask app
├── database.py               # Database module
├── crypto_rewards.py         # Token reward system
├── main.py                   # Main application
└── train_model.py            # Model training script
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/waste-sorting-system.git
cd waste-sorting-system
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or manually install the following packages:

```bash
pip install tensorflow opencv-python numpy pillow pyserial flask matplotlib qrcode
```

### 3. Set Up Arduino

1. Open Arduino IDE
2. Load the firmware from `arduino/waste_sorter_arduino.ino`
3. Connect your Arduino via USB
4. Upload the firmware to the board

### 4. Create Directory Structure

```bash
mkdir -p data logs models static/css static/js static/img templates training_data/can training_data/recycling training_data/garbage
```

## Building the Hardware

### Materials List

- **Wood**:
  - Base: 24" x 24" x 3/4" plywood
  - Sides: 2x 24" x 16" x 1/4" plywood
  - Back: 1x 24" x 16" x 1/4" plywood

- **Acrylic**:
  - Platform: 12" x 10" x 1/8" clear acrylic
  - Side Rails: 2x 10" x 2" x 1/8" clear acrylic

- **Hardware**:
  - Metal Axle: 1/4" diameter steel rod, 14" long
  - Ball Bearings: 2x flanged ball bearings for 1/4" shaft
  - Mounting Brackets: 2x metal L-brackets for bearings
  - Shaft Collars: 2x for securing axle
  - Servo Horn: Extended servo horn (6-8")
  - Screws, nuts, bolts, washers

- **Bins**:
  - 2x plastic bins (approximately 10" x 10" x 12")

### Assembly Instructions

1. **Build the Frame**:
   - Assemble the U-shaped frame using the plywood pieces
   - Secure with wood screws
   - Ensure corners are square

2. **Install the Pivot Mechanism**:
   - Mount the bearing brackets at the center height on both sides
   - Insert the axle through both bearings
   - Secure with shaft collars

3. **Create the Tilting Platform**:
   - Cut the acrylic platform and side rails
   - Attach side rails to the platform
   - Mount platform on the axle

4. **Install the Servo**:
   - Create a sturdy mount for the servo
   - Attach the extended servo horn to the underside of the platform
   - Position ~5" from the pivot point for best leverage

5. **Mount the Camera**:
   - Create a bracket to hold the webcam above the platform
   - Position it for a clear view of items

6. **Connect Electronics**:
   - Connect the Arduino to your computer via USB
   - Connect the servo to the Arduino (signal wire to pin 9)
   - Connect servo power to external 5V power supply

## Running the System

### 1. Start the Main Application

```bash
python main.py
```

### 2. Connect to Hardware

- Select the Arduino port from the dropdown
- Select the camera from the dropdown
- Click "Connect"

### 3. Begin Sorting

For manual operation:
- Place item on the platform
- Click "Analyze Item"
- Click "Sort Item" once analysis is complete

For automatic operation:
- Check "Auto-Sort Mode"
- Place items on the platform one at a time

### 4. Start the Analytics Dashboard

From the application menu:
- Go to Tools > Start Analytics Dashboard

Or start it separately:
```bash
python app.py
```

Access the dashboard at http://localhost:5000

## Training Your Own Model

1. Collect images for each category:
   - Place images in the appropriate folders under `training_data/`
   - Aim for at least 50-100 images per category

2. Launch the training dialog:
   - From the main application, go to Tools > Model Training
   - Set parameters and click "Start Training"

3. Restart the application to use the new model

## Token Rewards System

1. Open the Token Rewards window:
   - Click "Token Rewards" button in the main application

2. Create an account:
   - Enter a username and email
   - Click "Register"

3. Earn tokens:
   - Recycle cans to earn tokens (0.05 USD value per can)
   - Enable "Automatically reward tokens for cans" for automatic crediting

## Troubleshooting

### Arduino Connection Issues
- Ensure the correct port is selected
- Verify the Arduino has the correct firmware
- Check the USB cable connection
- Test with Tools > Test Arduino

### Camera Issues
- Verify the camera is connected
- Try a different USB port
- Test with Tools > Test Camera
- Check for other applications using the camera

### Sorting Problems
- Calibrate the platform angles using the slider
- Ensure the servo has enough power (use external power supply)
- Make sure the platform surface is smooth
- Check if items are within the weight limit of the servo

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- TensorFlow team for the machine learning framework
- OpenCV community for the computer vision library
- Flask team for the web framework
- Arduino community for the hardware platform