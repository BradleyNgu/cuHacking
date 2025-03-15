# main.py - Main application for waste sorting system
import os
import sys
import time
import threading
import cv2
import numpy as np
import tensorflow as tf
import serial
from serial.tools import list_ports
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import argparse
import logging
import subprocess
import webbrowser
from datetime import datetime

# Import our modules
from database import SortingDatabase
from train_model import WasteClassifierTrainer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("waste_sorter.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("WasteSorter")

class WasteSorterApp:
    """Main application for the waste sorting system"""
    
    def __init__(self, root):
        """Initialize the application"""
        self.root = root
        self.root.title("Waste Sorting System")
        self.root.geometry("1280x800")
        self.root.minsize(1000, 700)
        
        # Set application icon
        try:
            self.root.iconbitmap("static/img/recycle_icon.ico")
        except:
            pass  # Icon not found, continue without it
        
        # Initialize variables
        self.model = None
        self.camera = None
        self.arduino = None
        self.is_connected = False
        self.is_sorting = False
        self.current_frame = None
        self.current_classification = "Unknown"
        self.confidence = 0.0
        
        # Item counters
        self.can_count = 0
        self.recycling_count = 0
        self.garbage_count = 0
        self.total_count = 0
        
        # Database
        self.db = SortingDatabase()
        
        # Flag for auto-sorting
        self.auto_sort_active = False
        self.last_sorted_time = 0
        self.auto_sort_min_interval = 5000  # Minimum ms between auto-sorts
        self.dashboard_process = None
        
        # Create UI elements
        self.create_ui()
        
        # Initialize the system
        self.initialize_system()
        
        # Load previous counts if available
        self.load_counts()
        
        # Create a watchdog thread to monitor Arduino connection
        self.watchdog_thread = threading.Thread(target=self.connection_watchdog, daemon=True)
        self.watchdog_thread.start()
    
    def create_ui(self):
        """Create the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create menu bar
        self.create_menu()
        
        # Left panel (camera view)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        camera_frame = ttk.LabelFrame(left_frame, text="Camera View", padding="10")
        camera_frame.pack(fill=tk.BOTH, expand=True)
        
        self.camera_view = ttk.Label(camera_frame)
        self.camera_view.pack(fill=tk.BOTH, expand=True)
        
        # Stats view below camera
        stats_frame = ttk.LabelFrame(left_frame, text="Statistics", padding="10", height=200)
        stats_frame.pack(fill=tk.X, pady=10)
        
        stats_info = ttk.Frame(stats_frame)
        stats_info.pack(fill=tk.X, pady=10)
        
        # Create stats display
        ttk.Label(stats_info, text="Cans:").grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.can_label = ttk.Label(stats_info, text="0", font=("Arial", 12, "bold"))
        self.can_label.grid(row=0, column=1, sticky=tk.W, padx=10, pady=5)
        
        ttk.Label(stats_info, text="Recycling:").grid(row=0, column=2, sticky=tk.W, padx=10, pady=5)
        self.recycling_label = ttk.Label(stats_info, text="0", font=("Arial", 12, "bold"))
        self.recycling_label.grid(row=0, column=3, sticky=tk.W, padx=10, pady=5)
        
        ttk.Label(stats_info, text="Garbage:").grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)
        self.garbage_label = ttk.Label(stats_info, text="0", font=("Arial", 12, "bold"))
        self.garbage_label.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        ttk.Label(stats_info, text="Total:").grid(row=1, column=2, sticky=tk.W, padx=10, pady=5)
        self.total_label = ttk.Label(stats_info, text="0", font=("Arial", 12, "bold"))
        self.total_label.grid(row=1, column=3, sticky=tk.W, padx=10, pady=5)
        
        # Right panel (controls and status)
        control_frame = ttk.Frame(main_frame, padding="10", width=350)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        
        # Connection section
        conn_frame = ttk.LabelFrame(control_frame, text="Connections", padding="10")
        conn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(conn_frame, text="Arduino Port:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Populate available ports
        available_ports = self.get_available_ports()
        self.port_var = tk.StringVar(value=available_ports[0] if available_ports else "")
        
        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, values=available_ports, width=15)
        self.port_combo.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        refresh_btn = ttk.Button(conn_frame, text="⟳", width=2, command=self.refresh_ports)
        refresh_btn.grid(row=0, column=2, padx=2, pady=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(conn_frame, text="Camera:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.camera_var = tk.StringVar(value="0")
        
        # Get available cameras
        camera_list = self.get_available_cameras()
        self.camera_combo = ttk.Combobox(conn_frame, textvariable=self.camera_var, values=camera_list, width=15)
        self.camera_combo.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        refresh_cam_btn = ttk.Button(conn_frame, text="⟳", width=2, command=self.refresh_cameras)
        refresh_cam_btn.grid(row=1, column=2, padx=2, pady=5)
        
        # Classification section
        class_frame = ttk.LabelFrame(control_frame, text="Classification", padding="10")
        class_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(class_frame, text="Current Item:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.class_label = ttk.Label(class_frame, text="Unknown")
        self.class_label.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(class_frame, text="Confidence:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.conf_label = ttk.Label(class_frame, text="0.0%")
        self.conf_label.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(class_frame, text="Sort As:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.sort_label = ttk.Label(class_frame, text="N/A")
        self.sort_label.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Control buttons
        btn_frame = ttk.Frame(control_frame, padding="10")
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.analyze_btn = ttk.Button(btn_frame, text="Analyze Item", command=self.analyze_item)
        self.analyze_btn.pack(fill=tk.X, pady=5)
        self.analyze_btn.state(['disabled'])
        
        self.sort_btn = ttk.Button(btn_frame, text="Sort Item", command=self.sort_item)
        self.sort_btn.pack(fill=tk.X, pady=5)
        self.sort_btn.state(['disabled'])
        
        # Add auto-sort mode checkbox
        self.auto_sort_var = tk.BooleanVar(value=False)
        auto_sort_chk = ttk.Checkbutton(btn_frame, text="Auto-Sort Mode", 
                                       variable=self.auto_sort_var,
                                       command=self.toggle_auto_sort)
        auto_sort_chk.pack(fill=tk.X, pady=5)
        
        # Manual controls frame
        self.manual_frame = ttk.LabelFrame(control_frame, text="Manual Controls", padding="10")
        self.manual_frame.pack(fill=tk.X, pady=10)
        
        # Buttons for manual sorting
        can_btn = ttk.Button(self.manual_frame, text="Sort as Can", 
                           command=lambda: self.manual_sort('C'))
        can_btn.pack(fill=tk.X, pady=5)
        
        recyc_btn = ttk.Button(self.manual_frame, text="Sort as Regular Recycling", 
                              command=lambda: self.manual_sort('R'))
        recyc_btn.pack(fill=tk.X, pady=5)
        
        garbage_btn = ttk.Button(self.manual_frame, text="Sort as Garbage", 
                                command=lambda: self.manual_sort('G'))
        garbage_btn.pack(fill=tk.X, pady=5)
        
        reset_btn = ttk.Button(self.manual_frame, text="Reset to Neutral", 
                             command=self.reset_platform)
        reset_btn.pack(fill=tk.X, pady=5)
        
        # Platform calibration
        calib_frame = ttk.LabelFrame(control_frame, text="Platform Calibration", padding="10")
        calib_frame.pack(fill=tk.X, pady=10)
        
        # Slider for position
        ttk.Label(calib_frame, text="Platform Angle:").pack(anchor="w")
        
        self.position_var = tk.IntVar(value=90)
        self.position_slider = ttk.Scale(calib_frame, from_=0, to=180, 
                                       variable=self.position_var, 
                                       command=self.update_platform_position)
        self.position_slider.pack(fill=tk.X, pady=5)
        
        # Position display and buttons
        pos_frame = ttk.Frame(calib_frame)
        pos_frame.pack(fill=tk.X)
        
        self.position_label = ttk.Label(pos_frame, text="90°")
        self.position_label.pack(side=tk.LEFT, padx=5)
        
        # Preset buttons
        preset_frame = ttk.Frame(calib_frame)
        preset_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(preset_frame, text="Neutral", 
                 command=lambda: self.set_platform_position(90)).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(preset_frame, text="Recycling", 
                 command=lambda: self.set_platform_position(45)).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(preset_frame, text="Garbage", 
                 command=lambda: self.set_platform_position(135)).pack(side=tk.LEFT, padx=2)
        
        # Status bar
        self.status_var = tk.StringVar(value="System ready. Please connect to Arduino.")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_menu(self):
        """Create the application menu"""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Connect", command=self.toggle_connection)
        file_menu.add_command(label="Reset Counters", command=self.reset_counters)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.exit_application)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Model Training", command=self.open_training_dialog)
        tools_menu.add_command(label="Test Camera", command=self.test_camera)
        tools_menu.add_command(label="Test Arduino", command=self.test_arduino)
        tools_menu.add_separator()
        tools_menu.add_command(label="Start Analytics Dashboard", command=self.start_dashboard)
        tools_menu.add_command(label="Open Analytics in Browser", command=self.open_dashboard_browser)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="User Guide", command=self.show_user_guide)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
    
    def get_available_ports(self):
        """Get available serial ports"""
        ports = list_ports.comports()
        return [port.device for port in ports]
    
    def refresh_ports(self):
        """Refresh the available ports list"""
        ports = self.get_available_ports()
        self.port_combo['values'] = ports
        if ports and not self.port_var.get() in ports:
            self.port_var.set(ports[0])
    
    def get_available_cameras(self):
        """Get available cameras"""
        available_cameras = []
        # Check first 5 camera indices
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(str(i))
                cap.release()
        
        return available_cameras if available_cameras else ["0"]
    
    def refresh_cameras(self):
        """Refresh the available cameras list"""
        cameras = self.get_available_cameras()
        self.camera_combo['values'] = cameras
        if cameras and not self.camera_var.get() in cameras:
            self.camera_var.set(cameras[0])
    
    def initialize_system(self):
        """Initialize the system components"""
        # Load TensorFlow model
        self.status_var.set("Loading machine learning model...")
        
        try:
            # Check if we have a custom model first
            custom_model_path = os.path.join("models", "latest_model.h5")
            if os.path.exists(custom_model_path):
                self.model = tf.keras.models.load_model(custom_model_path)
                logger.info(f"Loaded custom model: {custom_model_path}")
                
                # Load class mapping
                mapping_path = os.path.join("models", "class_mapping.json")
                import json
                if os.path.exists(mapping_path):
                    with open(mapping_path, 'r') as f:
                        self.class_mapping = json.load(f)
                    logger.info(f"Loaded class mapping: {self.class_mapping}")
            else:
                # Use the pre-trained model
                self.model = tf.keras.applications.MobileNetV2(
                    input_shape=(224, 224, 3),
                    include_top=True,
                    weights='imagenet'
                )
                logger.info("Loaded pre-trained MobileNetV2 model")
            
            self.status_var.set("Model loaded successfully.")
        except Exception as e:
            error_msg = f"Error loading model: {str(e)}"
            logger.error(error_msg)
            self.status_var.set(error_msg)
            messagebox.showerror("Model Error", error_msg)
    
    def toggle_connection(self):
        """Connect or disconnect from Arduino"""
        if not self.is_connected:
            try:
                # Connect to Arduino
                port = self.port_var.get()
                if not port:
                    messagebox.showerror("Connection Error", "No serial port selected")
                    return
                
                self.status_var.set(f"Connecting to Arduino on {port}...")
                
                self.arduino = serial.Serial(port, 9600, timeout=1)
                time.sleep(2)  # Allow time for connection to establish
                
                # Check if Arduino is responding
                self.arduino.write(b'V')  # Request version info
                time.sleep(0.5)
                response = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                
                if not response or not ('Waste Sorter' in response or 'READY' in response):
                    self.arduino.close()
                    self.arduino = None
                    raise Exception(f"Arduino not responding or wrong firmware. Got: {response}")
                
                # Start camera
                camera_idx = int(self.camera_var.get())
                self.camera = cv2.VideoCapture(camera_idx)
                
                if not self.camera.isOpened():
                    if self.arduino:
                        self.arduino.close()
                        self.arduino = None
                    raise Exception("Could not open camera")
                
                # Configure camera resolution
                # Try to set high resolution, but fall back if not supported
                resolutions = [(3840, 2160), (1920, 1080), (1280, 720), (640, 480)]
                
                for width, height in resolutions:
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
                    actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
                    
                    if abs(actual_width - width) < 100 and abs(actual_height - height) < 100:
                        logger.info(f"Camera resolution set to {actual_width}x{actual_height}")
                        break
                
                # Start camera thread
                self.is_connected = True
                self.camera_thread = threading.Thread(target=self.update_camera)
                self.camera_thread.daemon = True
                self.camera_thread.start()
                
                # Start Arduino monitoring thread
                self.arduino_thread = threading.Thread(target=self.monitor_arduino)
                self.arduino_thread.daemon = True
                self.arduino_thread.start()
                
                # Update UI
                self.connect_btn.configure(text="Disconnect")
                self.analyze_btn.state(['!disabled'])
                self.status_var.set(f"Connected to Arduino on {port} and camera {camera_idx}")
            
            except Exception as e:
                error_msg = f"Connection error: {str(e)}"
                logger.error(error_msg)
                self.status_var.set(error_msg)
                messagebox.showerror("Connection Error", error_msg)
                
                # Ensure resources are released
                if self.arduino:
                    try:
                        self.arduino.close()
                    except:
                        pass
                    self.arduino = None
                
                if self.camera:
                    try:
                        self.camera.release()
                    except:
                        pass
                    self.camera = None
        else:
            # Disconnect
            self.is_connected = False
            
            if self.camera is not None:
                time.sleep(0.5)  # Allow threads to exit
                self.camera.release()
                self.camera = None
            
            if self.arduino is not None:
                # Reset platform to neutral position before disconnecting
                try:
                    self.arduino.write(b'N')
                    time.sleep(1)
                    self.arduino.close()
                except:
                    pass
                self.arduino = None
            
            # Update UI
            self.connect_btn.configure(text="Connect")
            self.analyze_btn.state(['disabled'])
            self.sort_btn.state(['disabled'])
            self.status_var.set("Disconnected")
            
            # Disable auto-sort mode
            self.auto_sort_active = False
            self.auto_sort_var.set(False)
    
    def connection_watchdog(self):
        """Watchdog thread to monitor Arduino connection"""
        while True:
            if self.is_connected and self.arduino:
                try:
                    # Check if Arduino is still responsive
                    if not self.arduino.is_open:
                        logger.warning("Arduino port closed unexpectedly")
                        self.handle_connection_loss()
                except Exception as e:
                    logger.error(f"Arduino connection error: {str(e)}")
                    self.handle_connection_loss()
            
            # Check every 5 seconds
            time.sleep(5)
    
    def handle_connection_loss(self):
        """Handle unexpected connection loss"""
        # Only run this on the main thread
        self.root.after(0, self._handle_connection_loss_main_thread)
    
    def _handle_connection_loss_main_thread(self):
        """Handle connection loss (called on main thread)"""
        if self.is_connected:
            logger.info("Handling connection loss")
            self.status_var.set("Connection lost. Reconnecting...")
            self.toggle_connection()  # Disconnect
            
            # Try to reconnect
            messagebox.showwarning("Connection Lost", 
                                 "Connection to Arduino was lost. Please check connections and reconnect.")
    
    def toggle_auto_sort(self):
        """Toggle auto-sort mode"""
        self.auto_sort_active = self.auto_sort_var.get()
        if self.auto_sort_active:
            self.status_var.set("Auto-sort mode enabled. Items will be sorted automatically.")
        else:
            self.status_var.set("Auto-sort mode disabled. Manual sorting required.")
    
    def update_camera(self):
        """Update camera feed continuously"""
        while self.is_connected and hasattr(self, 'camera') and self.camera is not None:
            try:
                ret, frame = self.camera.read()
                if ret:
                    # Resize for display while maintaining aspect ratio
                    display_height, display_width = 360, 640
                    h, w = frame.shape[:2]
                    
                    # Calculate new size to maintain aspect ratio
                    if h > 0 and w > 0:
                        if h / w > display_height / display_width:
                            new_h = display_height
                            new_w = int(w * (display_height / h))
                        else:
                            new_w = display_width
                            new_h = int(h * (display_width / w))
                        
                        display_frame = cv2.resize(frame, (new_w, new_h))
                    else:
                        display_frame = frame
                    
                    # Convert to RGB for tkinter
                    display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                    
                    # Store current frame for analysis
                    self.current_frame = frame
                    
                    # Display in UI
                    img = Image.fromarray(display_frame)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.camera_view.imgtk = imgtk
                    self.camera_view.configure(image=imgtk)
                    
                    # Auto-sort if enabled and enough time has passed since last sort
                    if (self.auto_sort_active and 
                        not self.is_sorting and 
                        (time.time() * 1000 - self.last_sorted_time > self.auto_sort_min_interval)):
                        # Call on main thread to avoid threading issues
                        self.root.after(0, self.auto_analyze_and_sort)
            except Exception as e:
                logger.error(f"Camera error: {str(e)}")
                time.sleep(0.1)
            
            # Slight delay to reduce CPU usage
            time.sleep(0.03)
    
    def monitor_arduino(self):
        """Monitor Arduino serial output for messages"""
        while self.is_connected and hasattr(self, 'arduino') and self.arduino is not None:
            try:
                if self.arduino.in_waiting > 0:
                    line = self.arduino.readline().decode('utf-8', errors='ignore').strip()
                    logger.debug(f"Arduino: {line}")
                    
                    # Parse different message types
                    if line.startswith("STATUS:"):
                        status_msg = line.split("STATUS:", 1)[1].strip()
                        self.status_var.set(status_msg)
                    elif line.startswith("INFO:"):
                        info_msg = line.split("INFO:", 1)[1].strip()
                        logger.info(f"Arduino info: {info_msg}")
                    elif line.startswith("WARNING:"):
                        warning_msg = line.split("WARNING:", 1)[1].strip()
                        logger.warning(f"Arduino warning: {warning_msg}")
                    elif line.startswith("ERROR:"):
                        error_msg = line.split("ERROR:", 1)[1].strip()
                        logger.error(f"Arduino error: {error_msg}")
                    elif "SORT_COMPLETE" in line:
                        # Update the UI to show sort is complete
                        self.root.after(0, self.reset_after_sort)
                        
                        # Acknowledge receipt
                        self.arduino.write(b'A')
            except Exception as e:
                logger.error(f"Arduino monitoring error: {str(e)}")
            
            # Slight delay to reduce CPU usage
            time.sleep(0.1)
    
    def auto_analyze_and_sort(self):
        """Automatically analyze the current frame and sort if confidence is high"""
        if self.current_frame is None or self.model is None:
            return
        
        try:
            # Analyze the current frame
            processed_img = self.preprocess_image(self.current_frame)
            
            # Check if we're using a custom model or the pretrained one
            if hasattr(self, 'class_mapping'):
                # Using custom model
                predictions = self.model.predict(processed_img)
                predicted_class = np.argmax(predictions[0])
                confidence = float(predictions[0][predicted_class])
                
                # Get class name from mapping
                class_name = self.class_mapping.get(str(predicted_class), f"Class {predicted_class}")
                
                # Simplified classification - just check if it's recyclable
                if "can" in class_name.lower() or "recycling" in class_name.lower():
                    sort_as = "Recycling"  # All recyclables (including cans) go to recycling
                else:
                    sort_as = "Garbage"    # Everything else goes to garbage
            else:
                # Using pretrained model
                predictions = self.model.predict(processed_img)
                predicted_class = np.argmax(predictions[0])
                confidence = float(predictions[0][predicted_class])
                
                # Combined recyclable classes (cans + recyclables)
                recyclable_classes = [482, 483, 810, 494, 440, 672, 802, 965, 611]
                
                # Simplified classification
                if predicted_class in recyclable_classes:
                    sort_as = "Recycling"  # All recyclables go to recycling
                else:
                    sort_as = "Garbage"    # Everything else goes to garbage
            
            # Only auto-sort if confidence is high
            if confidence > 0.7:  # 70% confidence threshold
                # Update UI
                self.class_label.configure(text=f"Class: {predicted_class}")
                self.conf_label.configure(text=f"{confidence:.2%}")
                self.sort_label.configure(text=sort_as)
                
                # Record the classification
                self.current_classification = sort_as
                self.confidence = confidence
                
                # Sort the item
                self.sort_item_with_classification(sort_as)
                
                # Update status
                self.status_var.set(f"Auto-sort: {sort_as} ({confidence:.2%} confidence)")
        
        except Exception as e:
            logger.error(f"Auto-sort error: {str(e)}")
    
    def preprocess_image(self, image):
        """Preprocess image for the model"""
        img = cv2.resize(image, (224, 224))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img / 255.0
        img = np.expand_dims(img, axis=0)
        return img
    
    def analyze_item(self):
        """Analyze the current item in view"""
        if self.current_frame is None or self.model is None:
            self.status_var.set("Error: No frame available or model not loaded")
            return
        
        try:
            self.status_var.set("Analyzing item...")
            
            # Preprocess the image
            processed_img = self.preprocess_image(self.current_frame)
            
            # Check if we're using a custom model or the pretrained one
            if hasattr(self, 'class_mapping'):
                # Using custom model
                predictions = self.model.predict(processed_img)
                predicted_class = np.argmax(predictions[0])
                confidence = float(predictions[0][predicted_class])
                
                # Get class name from mapping
                class_name = self.class_mapping.get(str(predicted_class), f"Class {predicted_class}")
                
                # Simplified classification - just check if it's recyclable
                if "can" in class_name.lower() or "recycling" in class_name.lower():
                    sort_as = "Recycling"  # All recyclables (including cans) go to recycling
                else:
                    sort_as = "Garbage"    # Everything else goes to garbage
            else:
                # Using pretrained model
                predictions = self.model.predict(processed_img)
                predicted_class = np.argmax(predictions[0])
                confidence = float(predictions[0][predicted_class])
                
                # Combined recyclable classes (cans + recyclables)
                recyclable_classes = [482, 483, 810, 494, 440, 672, 802, 965, 611]
                
                # Simplified classification
                if predicted_class in recyclable_classes:
                    sort_as = "Recycling"  # All recyclables go to recycling
                else:
                    sort_as = "Garbage"    # Everything else goes to garbage
            
            # Update UI
            self.class_label.configure(text=f"Class: {predicted_class}")
            self.conf_label.configure(text=f"{confidence:.2%}")
            self.sort_label.configure(text=sort_as)
            
            # Record the classification
            self.current_classification = sort_as
            self.confidence = confidence
            
            # Enable sort button
            self.sort_btn.state(['!disabled'])
            
            # Log the classification
            self.log_classification(predicted_class, confidence, sort_as)
            
            self.status_var.set(f"Analysis complete: {sort_as} ({confidence:.2%} confidence)")
            
            # Auto-sort if enabled
            if self.auto_sort_active:
                self.sort_item()
        
        except Exception as e:
            error_msg = f"Analysis error: {str(e)}"
            logger.error(error_msg)
            self.status_var.set(error_msg)
    
    def sort_item(self):
        """Send command to sort the current item"""
        self.sort_item_with_classification(self.current_classification)
    
    def sort_item_with_classification(self, classification):
        """Sort an item with a given classification"""
        if not self.is_connected or self.arduino is None:
            self.status_var.set("Error: Not connected to Arduino")
            return
        
        try:
            # Determine command based on classification
            if classification == "Recycling":
                command = 'R'
                # Check if it's specifically a can
                if "can" in self.class_label.cget("text").lower():
                    self.can_count += 1
                else:
                    self.recycling_count += 1
            else:  # Garbage
                command = 'G'
                self.garbage_count += 1
            
            self.total_count = self.can_count + self.recycling_count + self.garbage_count
            
            # Send command to Arduino
            self.arduino.write(command.encode())
            
            # Update status
            self.status_var.set(f"Sorting as {classification}...")
            
            # Disable buttons during sorting
            self.is_sorting = True
            self.sort_btn.state(['disabled'])
            self.analyze_btn.state(['disabled'])
            
            # Save image to database
            if self.current_frame is not None:
                # Create metadata
                metadata = {
                    "classification": classification,
                    "confidence": float(self.confidence),
                    "timestamp": datetime.now().isoformat()
                }
                
                # Log to database
                event_id = self.db.add_sort_event(
                    classification.lower(),
                    self.confidence,
                    "recycling" if classification == "Recycling" else "garbage",
                    self.current_frame,
                    None,  # user_id
                    metadata
                )
            
            # Update UI
            self.update_counter_display()
            
            # Save counts
            self.save_counts()
            
            # Record sort time for auto-sort interval
            self.last_sorted_time = time.time() * 1000
        
        except Exception as e:
            error_msg = f"Sorting error: {str(e)}"
            logger.error(error_msg)
            self.status_var.set(error_msg)
            self.is_sorting = False
    
    def manual_sort(self, sort_type):
        """Manually sort an item"""
        if not self.is_connected or self.arduino is None:
            self.status_var.set("Error: Not connected to Arduino")
            return
        
        try:
            # Send command to Arduino
            self.arduino.write(sort_type.encode())
            
            if sort_type == 'C':
                classification = "Can"
                self.can_count += 1
            elif sort_type == 'R':
                classification = "Regular Recycling"
                self.recycling_count += 1
            else:  # 'G'
                classification = "Garbage"
                self.garbage_count += 1
            
            self.total_count = self.can_count + self.recycling_count + self.garbage_count
            
            self.status_var.set(f"Manual sorting as {classification}...")
            
            # Save image to database if available
            if self.current_frame is not None:
                # Create metadata
                metadata = {
                    "classification": classification,
                    "confidence": 1.0,  # Manual sort, so 100% confidence
                    "manual": True,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Log to database
                event_id = self.db.add_sort_event(
                    classification.lower().replace("regular ", ""),
                    1.0,
                    "recycling" if classification != "Garbage" else "garbage",
                    self.current_frame,
                    None,  # user_id
                    metadata
                )
            
            # Update UI
            self.update_counter_display()
            
            # Save counts
            self.save_counts()
            
            # Disable buttons during sorting
            self.is_sorting = True
            self.analyze_btn.state(['disabled'])
            
            # Record sort time for auto-sort interval
            self.last_sorted_time = time.time() * 1000
        
        except Exception as e:
            error_msg = f"Manual sorting error: {str(e)}"
            logger.error(error_msg)
            self.status_var.set(error_msg)
            self.is_sorting = False
    
    def reset_platform(self):
        """Reset platform to neutral position"""
        if not self.is_connected or self.arduino is None:
            self.status_var.set("Error: Not connected to Arduino")
            return
        
        try:
            self.arduino.write(b'N')
            self.status_var.set("Resetting platform to neutral position...")
        
        except Exception as e:
            error_msg = f"Reset error: {str(e)}"
            logger.error(error_msg)
            self.status_var.set(error_msg)
    
    def update_platform_position(self, event=None):
        """Update platform position based on slider"""
        if not self.is_connected or self.arduino is None:
            return
        
        try:
            pos = int(float(self.position_var.get()))
            self.position_label.configure(text=f"{pos}°")
            
            # Send position command to Arduino
            command = f"S{pos}".encode()
            self.arduino.write(command)
        except Exception as e:
            logger.error(f"Error updating platform position: {str(e)}")
    
    def set_platform_position(self, position):
        """Set platform to a specific position"""
        self.position_var.set(position)
        self.update_platform_position()
    
    def reset_after_sort(self):
        """Reset UI after sorting complete"""
        self.is_sorting = False
        self.analyze_btn.state(['!disabled'])
        self.status_var.set("Ready for next item")
    
    def update_counter_display(self):
        """Update counter display in UI"""
        self.can_label.configure(text=str(self.can_count))
        self.recycling_label.configure(text=str(self.recycling_count))
        self.garbage_label.configure(text=str(self.garbage_count))
        self.total_label.configure(text=str(self.total_count))
    
    def reset_counters(self):
        """Reset all counters to zero"""
        # Ask for confirmation
        if not messagebox.askyesno("Reset Counters", "Are you sure you want to reset all counters to zero?"):
            return
        
        self.can_count = 0
        self.recycling_count = 0
        self.garbage_count = 0
        self.total_count = 0
        self.update_counter_display()
        self.save_counts()
        self.status_var.set("Counters reset to zero")
    
    def save_counts(self):
        """Save counter values to file"""
        try:
            counts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            os.makedirs(counts_dir, exist_ok=True)
            
            counts_file = os.path.join(counts_dir, "counts.json")
            
            import json
            counts_data = {
                "cans": self.can_count,
                "recycling": self.recycling_count,
                "garbage": self.garbage_count,
                "total": self.total_count,
                "last_updated": datetime.now().isoformat()
            }
            
            with open(counts_file, "w") as f:
                json.dump(counts_data, f, indent=4)
            
            logger.debug(f"Saved counts to {counts_file}")
            
        except Exception as e:
            logger.error(f"Error saving counts: {str(e)}")
    
    def load_counts(self):
        """Load counter values from file"""
        try:
            counts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
            counts_file = os.path.join(counts_dir, "counts.json")
            
            if os.path.exists(counts_file):
                import json
                with open(counts_file, "r") as f:
                    counts_data = json.load(f)
                
                self.can_count = counts_data.get("cans", 0)
                self.recycling_count = counts_data.get("recycling", 0)
                self.garbage_count = counts_data.get("garbage", 0)
                self.total_count = counts_data.get("total", 0)
                
                # Update UI
                self.update_counter_display()
                
                logger.info(f"Loaded counts from {counts_file}")
        
        except Exception as e:
            logger.error(f"Error loading counts: {str(e)}")
    
    def log_classification(self, class_id, confidence, sort_as):
        """Log classification results to file"""
        try:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, "classification_log.txt")
            
            with open(log_file, "a") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"{timestamp}, Class: {class_id}, " +
                       f"Confidence: {confidence:.2f}, " +
                       f"Sort As: {sort_as}\n")
        
        except Exception as e:
            logger.error(f"Logging error: {str(e)}")
    
    def open_training_dialog(self):
        """Open the model training dialog"""
        # Create the training dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Model Training")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Main frame
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(frame, text="Train Custom Waste Classification Model", font=("Arial", 14, "bold"))
        title_label.pack(pady=10)
        
        # Data directory section
        data_frame = ttk.LabelFrame(frame, text="Training Data", padding="10")
        data_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(data_frame, text="Data Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        data_dir_var = tk.StringVar(value="./training_data")
        data_dir_entry = ttk.Entry(data_frame, textvariable=data_dir_var, width=40)
        data_dir_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        browse_btn = ttk.Button(data_frame, text="Browse", 
                              command=lambda: data_dir_var.set(filedialog.askdirectory()))
        browse_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Create directory structure button
        create_dir_btn = ttk.Button(data_frame, text="Create Directory Structure", 
                                  command=lambda: self.create_training_directories(data_dir_var.get()))
        create_dir_btn.grid(row=1, column=0, columnspan=3, pady=5)
        
        # Training parameters section
        params_frame = ttk.LabelFrame(frame, text="Training Parameters", padding="10")
        params_frame.pack(fill=tk.X, pady=10)
        
        # Batch size
        ttk.Label(params_frame, text="Batch Size:").grid(row=0, column=0, sticky=tk.W, pady=5)
        batch_size_var = tk.IntVar(value=32)
        batch_size_entry = ttk.Entry(params_frame, textvariable=batch_size_var, width=10)
        batch_size_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Epochs
        ttk.Label(params_frame, text="Epochs:").grid(row=0, column=2, sticky=tk.W, pady=5, padx=10)
        epochs_var = tk.IntVar(value=20)
        epochs_entry = ttk.Entry(params_frame, textvariable=epochs_var, width=10)
        epochs_entry.grid(row=0, column=3, sticky=tk.W, pady=5)
        
        # Learning rate
        ttk.Label(params_frame, text="Learning Rate:").grid(row=1, column=0, sticky=tk.W, pady=5)
        lr_var = tk.DoubleVar(value=0.0001)
        lr_entry = ttk.Entry(params_frame, textvariable=lr_var, width=10)
        lr_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Split data checkbox
        split_data_var = tk.BooleanVar(value=True)
        split_data_chk = ttk.Checkbutton(params_frame, text="Split Data into Train/Val/Test", 
                                       variable=split_data_var)
        split_data_chk.grid(row=1, column=2, columnspan=2, sticky=tk.W, pady=5, padx=10)
        
        # Training log
        log_frame = ttk.LabelFrame(frame, text="Training Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        log_text = tk.Text(log_frame, height=10, width=60, wrap=tk.WORD)
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        log_scrollbar = ttk.Scrollbar(log_frame, command=log_text.yview)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        log_text.config(yscrollcommand=log_scrollbar.set)
        
        # Action buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        # Training progress
        progress_var = tk.DoubleVar(value=0.0)
        progress_bar = ttk.Progressbar(btn_frame, variable=progress_var, length=200)
        progress_bar.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        # Buttons
        train_btn = ttk.Button(btn_frame, text="Start Training", 
                             command=lambda: self.start_training(
                                 data_dir_var.get(),
                                 batch_size_var.get(),
                                 epochs_var.get(),
                                 lr_var.get(),
                                 split_data_var.get(),
                                 log_text,
                                 progress_var,
                                 dialog
                             ))
        train_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Information text
        info_text = """
        Instructions:
        1. Create a directory structure with folders for each class (can, recycling, garbage)
        2. Add images to each class folder
        3. Set training parameters
        4. Click 'Start Training' to train the model
        
        The trained model will be saved to the 'models' directory.
        """
        
        info_label = ttk.Label(frame, text=info_text, wraplength=560, justify=tk.LEFT)
        info_label.pack(pady=10)
    
    def create_training_directories(self, data_dir):
        """Create directory structure for training data"""
        try:
            # Create main directory
            os.makedirs(data_dir, exist_ok=True)
            
            # Create class directories
            for class_name in ['can', 'recycling', 'garbage']:
                os.makedirs(os.path.join(data_dir, class_name), exist_ok=True)
            
            # Create models directory
            os.makedirs("models", exist_ok=True)
            
            messagebox.showinfo("Success", 
                              f"Directory structure created at {data_dir}\n\n" +
                              "Please add images to each class folder.")
        
        except Exception as e:
            logger.error(f"Error creating directories: {str(e)}")
            messagebox.showerror("Error", f"Failed to create directories: {str(e)}")
    
    def start_training(self, data_dir, batch_size, epochs, learning_rate, split_data, 
                     log_text, progress_var, dialog):
        """Start the model training process"""
        # Validate parameters
        if not os.path.exists(data_dir):
            messagebox.showerror("Error", f"Data directory {data_dir} does not exist.")
            return
        
        # Check if there are images in the directories
        has_images = False
        for class_name in ['can', 'recycling', 'garbage']:
            class_dir = os.path.join(data_dir, class_name)
            if os.path.exists(class_dir):
                images = [f for f in os.listdir(class_dir) 
                         if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                if images:
                    has_images = True
                    break
        
        if not has_images:
            messagebox.showerror("Error", 
                               "No images found in class directories. Please add images first.")
            return
        
        # Create a thread for training
        training_thread = threading.Thread(
            target=self.run_training,
            args=(data_dir, batch_size, epochs, learning_rate, split_data, log_text, progress_var, dialog)
        )
        training_thread.daemon = True
        training_thread.start()
    
    def run_training(self, data_dir, batch_size, epochs, learning_rate, split_data, 
                   log_text, progress_var, dialog):
        """Run the model training process in a separate thread"""
        try:
            # Create a custom logger that writes to the log_text widget
            class TextWidgetHandler(logging.Handler):
                def __init__(self, text_widget):
                    logging.Handler.__init__(self)
                    self.text_widget = text_widget
                
                def emit(self, record):
                    msg = self.format(record)
                    
                    def append():
                        self.text_widget.configure(state='normal')
                        self.text_widget.insert(tk.END, msg + '\n')
                        self.text_widget.see(tk.END)
                        self.text_widget.configure(state='disabled')
                    
                    # Schedule the update on the main thread
                    self.text_widget.after(0, append)
            
            # Configure the text widget logger
            log_text.configure(state='normal')
            log_text.delete(1.0, tk.END)
            log_text.configure(state='disabled')
            
            handler = TextWidgetHandler(log_text)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            training_logger = logging.getLogger("TrainingLog")
            training_logger.setLevel(logging.INFO)
            training_logger.addHandler(handler)
            
            # Define a callback for model training updates
            class ProgressCallback(tf.keras.callbacks.Callback):
                def __init__(self, progress_var, epochs):
                    self.progress_var = progress_var
                    self.epochs = epochs
                
                def on_epoch_begin(self, epoch, logs=None):
                    progress = epoch / self.epochs * 100
                    # Update progress on main thread
                    self.progress_var._root.after(0, lambda: self.progress_var.set(progress))
                
                def on_epoch_end(self, epoch, logs=None):
                    progress = (epoch + 1) / self.epochs * 100
                    # Update progress on main thread
                    self.progress_var._root.after(0, lambda: self.progress_var.set(progress))
                    
                    # Log metrics
                    metrics_str = ", ".join([f"{k}: {v:.4f}" for k, v in logs.items()])
                    training_logger.info(f"Epoch {epoch+1}/{self.epochs}: {metrics_str}")
            
            # Create the trainer
            training_logger.info(f"Initializing training with data directory: {data_dir}")
            training_logger.info(f"Parameters: batch_size={batch_size}, epochs={epochs}, learning_rate={learning_rate}")
            
            trainer = WasteClassifierTrainer(
                data_dir=data_dir,
                model_dir="models",
                batch_size=batch_size,
                epochs=epochs,
                learning_rate=learning_rate
            )
            
            # Split data if requested
            if split_data:
                training_logger.info("Splitting data into train/validation/test sets...")
                trainer.split_data()
            
            # Prepare data and model
            training_logger.info("Preparing training data...")
            trainer.prepare_directories()
            trainer.create_data_generators()
            
            training_logger.info("Creating model...")
            trainer.create_model()
            
            # Create progress callback
            progress_callback = ProgressCallback(progress_var, epochs)
            
            # Override the train_model method to include our callback
            original_train = trainer.train_model
            
            def train_with_callback():
                # Get the model and generators
                if trainer.model is None:
                    trainer.create_model()
                
                if trainer.train_generator is None or trainer.validation_generator is None:
                    trainer.create_data_generators()
                
                # Create callbacks
                from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
                
                model_checkpoint = ModelCheckpoint(
                    os.path.join(trainer.model_dir, 'best_model.h5'),
                    monitor='val_accuracy',
                    save_best_only=True,
                    mode='max',
                    verbose=1
                )
                
                early_stopping = EarlyStopping(
                    monitor='val_accuracy',
                    patience=10,
                    mode='max',
                    verbose=1
                )
                
                reduce_lr = ReduceLROnPlateau(
                    monitor='val_loss',
                    factor=0.2,
                    patience=5,
                    min_lr=1e-6,
                    verbose=1
                )
                
                callbacks = [model_checkpoint, early_stopping, reduce_lr, progress_callback]
                
                # Train the model
                training_logger.info(f"Starting training with {trainer.train_generator.samples} training samples and {trainer.validation_generator.samples} validation samples")
                
                trainer.history = trainer.model.fit(
                    trainer.train_generator,
                    steps_per_epoch=trainer.train_generator.samples // trainer.batch_size,
                    epochs=trainer.epochs,
                    validation_data=trainer.validation_generator,
                    validation_steps=trainer.validation_generator.samples // trainer.batch_size,
                    callbacks=callbacks
                )
                
                # Save the final model
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                final_model_path = os.path.join(trainer.model_dir, f'waste_classifier_{timestamp}.h5')
                trainer.model.save(final_model_path)
                training_logger.info(f"Model saved to {final_model_path}")
                
                # Also save as the latest model
                trainer.model.save(os.path.join(trainer.model_dir, 'latest_model.h5'))
            
            # Replace the train_model method
            trainer.train_model = train_with_callback
            
            # Start training
            training_logger.info("Starting training...")
            trainer.train_model()
            
            # Evaluate the model
            training_logger.info("Evaluating model...")
            evaluation = trainer.evaluate_model()
            
            if evaluation:
                test_loss, test_acc = evaluation
                training_logger.info(f"Test Loss: {test_loss:.4f}")
                training_logger.info(f"Test Accuracy: {test_acc:.4f}")
            
            # Export to TFLite
            training_logger.info("Exporting model to TFLite format...")
            tflite_path = trainer.export_tflite_model()
            
            if tflite_path:
                training_logger.info(f"TFLite model saved to {tflite_path}")
            
            # Plot training history
            training_logger.info("Plotting training history...")
            trainer.plot_training_history()
            
            # Set progress to 100%
            progress_var.set(100)
            
            # Show completion message
            training_logger.info("Training complete!")
            messagebox.showinfo("Training Complete", 
                              "Model training completed successfully!\n\n" +
                              "Restart the application to use the new model.")
        
        except Exception as e:
            logger.exception(f"Error during training: {str(e)}")
            messagebox.showerror("Training Error", f"An error occurred during training: {str(e)}")
            progress_var.set(0)
    
    def test_camera(self):
        """Test the camera connection"""
        if self.camera is not None:
            messagebox.showinfo("Camera Test", "Camera is already connected and working.")
            return
        
        try:
            camera_idx = int(self.camera_var.get())
            
            # Try to open the camera
            test_camera = cv2.VideoCapture(camera_idx)
            
            if not test_camera.isOpened():
                messagebox.showerror("Camera Test", f"Failed to open camera {camera_idx}.")
                return
            
            # Try to read a frame
            ret, frame = test_camera.read()
            
            if not ret:
                test_camera.release()
                messagebox.showerror("Camera Test", f"Failed to read frame from camera {camera_idx}.")
                return
            
            # Get camera properties
            width = test_camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = test_camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            fps = test_camera.get(cv2.CAP_PROP_FPS)
            
            # Release the camera
            test_camera.release()
            
            messagebox.showinfo("Camera Test", 
                              f"Camera {camera_idx} is working!\n\n" +
                              f"Resolution: {width}x{height}\n" +
                              f"FPS: {fps}")
        
        except Exception as e:
            error_msg = f"Camera test error: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Camera Test", error_msg)
    
    def test_arduino(self):
        """Test the Arduino connection"""
        if self.arduino is not None:
            # Arduino is already connected, run the test sequence
            try:
                self.arduino.write(b'T')
                messagebox.showinfo("Arduino Test", 
                                  "Test sequence started. Arduino should move the platform through all positions.")
                return
            except Exception as e:
                error_msg = f"Arduino test error: {str(e)}"
                logger.error(error_msg)
                messagebox.showerror("Arduino Test", error_msg)
                return
        
        # Try to connect to Arduino
        port = self.port_var.get()
        if not port:
            messagebox.showerror("Arduino Test", "No serial port selected")
            return
        
        try:
            # Try to open the port
            test_arduino = serial.Serial(port, 9600, timeout=1)
            time.sleep(2)  # Allow time for connection to establish
            
            # Check if Arduino is responding
            test_arduino.write(b'V')  # Request version info
            time.sleep(0.5)
            response = test_arduino.readline().decode('utf-8', errors='ignore').strip()
            
            # Close the connection
            test_arduino.close()
            
            if not response:
                messagebox.showerror("Arduino Test", 
                                   f"No response from Arduino on port {port}. " +
                                   "Make sure the correct firmware is uploaded.")
                return
            
            if 'Waste Sorter' in response or 'READY' in response:
                messagebox.showinfo("Arduino Test", 
                                  f"Arduino on port {port} is working!\n\n" +
                                  f"Response: {response}")
            else:
                messagebox.showerror("Arduino Test", 
                                   f"Unexpected response from device on port {port}:\n\n" +
                                   f"{response}\n\n" +
                                   "Make sure the correct firmware is uploaded to the Arduino.")
        
        except Exception as e:
            error_msg = f"Arduino test error: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Arduino Test", error_msg)
    
    def start_dashboard(self):
        """Start the analytics dashboard"""
        if self.dashboard_process is not None and self.dashboard_process.poll() is None:
            # Dashboard is already running
            messagebox.showinfo("Dashboard", 
                              "Analytics dashboard is already running.\n\n" +
                              "Access it at http://localhost:5000")
            return
        
        try:
            # Get the path to the dashboard script
            dashboard_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
            
            if not os.path.exists(dashboard_script):
                messagebox.showerror("Dashboard Error", 
                                  f"Dashboard script not found at {dashboard_script}")
                return
            
            # Start the dashboard process
            self.dashboard_process = subprocess.Popen(
                [sys.executable, dashboard_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # Wait a moment for the server to start
            time.sleep(2)
            
            if self.dashboard_process.poll() is not None:
                # Process terminated
                stdout, stderr = self.dashboard_process.communicate()
                error_msg = stderr.decode('utf-8', errors='ignore')
                messagebox.showerror("Dashboard Error", 
                                  f"Failed to start dashboard:\n\n{error_msg}")
                return
            
            messagebox.showinfo("Dashboard Started", 
                              "Analytics dashboard started successfully!\n\n" +
                              "Access it at http://localhost:5000")
            
            # Open the dashboard in a browser
            webbrowser.open("http://localhost:5000")
        
        except Exception as e:
            error_msg = f"Dashboard error: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Dashboard Error", error_msg)
    
    def open_dashboard_browser(self):
        """Open the analytics dashboard in a web browser"""
        webbrowser.open("http://localhost:5000")
    
    def show_user_guide(self):
        """Show the user guide"""
        guide_text = """
        Waste Sorting System - User Guide
        
        1. Setup:
           - Connect Arduino to USB port
           - Connect webcam
           - Select correct ports and click Connect
        
        2. Operation:
           - Place item on platform
           - Click Analyze to identify the item
           - Click Sort to sort the item
           - Or enable Auto-Sort mode for automatic operation
        
        3. Manual Controls:
           - Use manual sorting buttons for specific categories
           - Use platform calibration to adjust angles
           - Reset to neutral returns platform to level position
        
        4. Analytics:
           - Go to Tools > Start Analytics Dashboard
           - View sorting statistics and history
           - Access at http://localhost:5000
        
        For more information, visit our documentation website.
        """
        
        guide_dialog = tk.Toplevel(self.root)
        guide_dialog.title("User Guide")
        guide_dialog.geometry("600x500")
        guide_dialog.transient(self.root)
        
        # Add a Text widget with scrollbar
        guide_frame = ttk.Frame(guide_dialog, padding="20")
        guide_frame.pack(fill=tk.BOTH, expand=True)
        
        text = tk.Text(guide_frame, wrap=tk.WORD)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(guide_frame, command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text.config(yscrollcommand=scrollbar.set)
        
        # Insert the guide text
        text.insert(tk.END, guide_text)
        text.config(state=tk.DISABLED)  # Make read-only
        
        # Close button
        ttk.Button(guide_dialog, text="Close", command=guide_dialog.destroy).pack(pady=10)
    
    def show_about(self):
        """Show the about dialog"""
        about_text = """
        Waste Sorting System
        Version 1.0
        
        An automated waste sorting system that uses
        computer vision and machine learning to sort
        waste items into recycling and garbage.
        
        Features:
        - Computer vision classification
        - Arduino-controlled sorting platform
        - Analytics dashboard
        
        Created: March 2025
        """
        
        messagebox.showinfo("About", about_text)
    
    def exit_application(self):
        """Exit the application"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            # Cleanup
            if self.arduino:
                try:
                    self.arduino.write(b'N')  # Reset to neutral position
                    time.sleep(0.5)
                    self.arduino.close()
                except:
                    pass
            
            if self.camera:
                try:
                    self.camera.release()
                except:
                    pass
            
            if self.dashboard_process and self.dashboard_process.poll() is None:
                try:
                    self.dashboard_process.terminate()
                except:
                    pass
            
            # Close the database
            if hasattr(self, 'db'):
                self.db.close()
            
            # Exit application
            self.root.destroy()
            sys.exit(0)


def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Waste Sorting System')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Set up logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Create the Tkinter root
    root = tk.Tk()
    
    # Set application icon if available
    try:
        import platform
        if platform.system() == "Windows":
            root.iconbitmap("static/img/recycle_icon.ico")
        else:
            logo = tk.PhotoImage(file="static/img/recycle_icon.png")
            root.iconphoto(True, logo)
    except:
        pass  # Icon not found, continue without it
    
    # Create the application
    app = WasteSorterApp(root)
    
    # Run the application
    root.mainloop()


if __name__ == "__main__":
    main()