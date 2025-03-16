import cv2
import numpy as np
import tensorflow as tf
from tensorflow import keras
from time import sleep

confidence_time = 5

# Use keras from TensorFlow instead of tensorflow.keras
load_model = keras.models.load_model
import json

# Load the trained model
model_path = "./models/latest_model.h5"  # Update if your model has a different name
model = load_model(model_path)

# Load class mapping
with open("./models/class_mapping.json", "r") as f:
    class_mapping = json.load(f)
    class_mapping = {int(k): v for k, v in class_mapping.items()}  # Convert keys to integers

# Define image size (same as training)
IMAGE_SIZE = (224, 224)

# Open webcam
cap = cv2.VideoCapture(0)  # 0 for default camera

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

print("Press 'q' to exit.")

while True:
    # Capture frame from webcam
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        break

    # Preprocess the frame for model
    img = cv2.resize(frame, IMAGE_SIZE)  # Resize
    img = img / 255.0  # Normalize
    img = np.expand_dims(img, axis=0)  # Add batch dimension

    # Make prediction
    predictions = model.predict(img, verbose = 0)
    predicted_class = np.argmax(predictions[0])  # Get highest probability class
    confidence = predictions[0][predicted_class] * 100  # Confidence score

    if confidence > 90:
        print("Wait 5 seconds")
    #if confidence > 90:
    #    print(f"Predicted class: {predicted_class}")
    # Get class label
    class_label = class_mapping.get(predicted_class, "Unknown")

    # Display result on frame
    label = f"{class_label} ({confidence:.2f}%)"
    cv2.putText(frame, label, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

    # Show the webcam feed with classification
    cv2.imshow("Waste Classifier", frame)

    # Press 'q' to exit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
