# train_model.py - Train a custom waste classification model
import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import matplotlib.pyplot as plt
import cv2
import shutil
from datetime import datetime
import argparse
import json

class WasteClassifierTrainer:
    """Trainer for waste classification model"""
    
    def __init__(self, 
                 data_dir="./training_data",
                 model_dir="./models",
                 image_size=(224, 224),
                 batch_size=32,
                 epochs=50,
                 learning_rate=0.0001,
                 fine_tune_layers=20):
        """Initialize the trainer"""
        self.data_dir = data_dir
        self.model_dir = model_dir
        self.image_size = image_size
        self.batch_size = batch_size
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.fine_tune_layers = fine_tune_layers
        
        # Create directories if they don't exist
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(model_dir, exist_ok=True)
        
        # Default class mapping
        self.class_mapping = {
            'can': 0,
            'recycling': 1,
            'garbage': 2
        }
        
        # Data generators
        self.train_generator = None
        self.validation_generator = None
        self.test_generator = None
        
        # Model
        self.model = None
        self.history = None
    
    def prepare_directories(self):
        """Prepare the directory structure for training data"""
        # Create main directories if they don't exist
        for phase in ['train', 'validation', 'test']:
            for class_name in self.class_mapping.keys():
                os.makedirs(os.path.join(self.data_dir, phase, class_name), exist_ok=True)
    
    def create_data_generators(self, validation_split=0.2, test_split=0.1):
        """Create data generators for training, validation, and testing"""
        # Data augmentation for training
        train_datagen = ImageDataGenerator(
            rescale=1./255,
            rotation_range=20,
            width_shift_range=0.2,
            height_shift_range=0.2,
            shear_range=0.2,
            zoom_range=0.2,
            horizontal_flip=True,
            fill_mode='nearest',
            validation_split=validation_split if not os.path.exists(os.path.join(self.data_dir, 'validation')) else 0
        )
        
        # Only rescaling for validation and testing
        validation_datagen = ImageDataGenerator(rescale=1./255)
        test_datagen = ImageDataGenerator(rescale=1./255)
        
        # Check if we have separate validation and test directories
        has_separate_dirs = (
            os.path.exists(os.path.join(self.data_dir, 'train')) and
            os.path.exists(os.path.join(self.data_dir, 'validation'))
        )
        
        if has_separate_dirs:
            # Use separate directories
            self.train_generator = train_datagen.flow_from_directory(
                os.path.join(self.data_dir, 'train'),
                target_size=self.image_size,
                batch_size=self.batch_size,
                class_mode='categorical'
            )
            
            self.validation_generator = validation_datagen.flow_from_directory(
                os.path.join(self.data_dir, 'validation'),
                target_size=self.image_size,
                batch_size=self.batch_size,
                class_mode='categorical'
            )
            
            # Test set if available
            if os.path.exists(os.path.join(self.data_dir, 'test')):
                self.test_generator = test_datagen.flow_from_directory(
                    os.path.join(self.data_dir, 'test'),
                    target_size=self.image_size,
                    batch_size=self.batch_size,
                    class_mode='categorical',
                    shuffle=False
                )
        else:
            # Use validation_split
            self.train_generator = train_datagen.flow_from_directory(
                self.data_dir,
                target_size=self.image_size,
                batch_size=self.batch_size,
                class_mode='categorical',
                subset='training'
            )
            
            self.validation_generator = train_datagen.flow_from_directory(
                self.data_dir,
                target_size=self.image_size,
                batch_size=self.batch_size,
                class_mode='categorical',
                subset='validation'
            )
        
        # Update class mapping from the training generator
        self.class_mapping = {v: k for k, v in self.train_generator.class_indices.items()}
        print(f"Class mapping: {self.class_mapping}")
        
        # Save class mapping to file
        with open(os.path.join(self.model_dir, 'class_mapping.json'), 'w') as f:
            json.dump(self.class_mapping, f)
    
    def create_model(self):
        """Create a fine-tuned model starting from MobileNetV2"""
        # Use MobileNetV2 as the base model
        base_model = MobileNetV2(
            input_shape=(*self.image_size, 3),
            include_top=False,
            weights='imagenet'
        )
        
        # Freeze most of the base model layers
        for layer in base_model.layers[:-self.fine_tune_layers]:
            layer.trainable = False
        
        # Add custom classification layers
        x = base_model.output
        x = GlobalAveragePooling2D()(x)
        x = Dense(128, activation='relu')(x)
        predictions = Dense(len(self.class_mapping), activation='softmax')(x)
        
        self.model = Model(inputs=base_model.input, outputs=predictions)
        
        # Compile the model
        self.model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        # Print model summary
        self.model.summary()
    
    def train_model(self):
        """Train the model"""
        if self.model is None:
            self.create_model()
        
        if self.train_generator is None or self.validation_generator is None:
            self.create_data_generators()
        
        # Create callbacks
        model_checkpoint = ModelCheckpoint(
            os.path.join(self.model_dir, 'best_model.h5'),
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
        
        callbacks = [model_checkpoint, early_stopping, reduce_lr]
        
        # Train the model
        print(f"Starting training with {self.train_generator.samples} training samples and {self.validation_generator.samples} validation samples")
        
        self.history = self.model.fit(
            self.train_generator,
            steps_per_epoch=self.train_generator.samples // self.batch_size,
            epochs=self.epochs,
            validation_data=self.validation_generator,
            validation_steps=self.validation_generator.samples // self.batch_size,
            callbacks=callbacks
        )
        
        # Save the final model
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_model_path = os.path.join(self.model_dir, f'waste_classifier_{timestamp}.h5')
        self.model.save(final_model_path)
        print(f"Model saved to {final_model_path}")
        
        # Also save as the latest model
        self.model.save(os.path.join(self.model_dir, 'latest_model.h5'))
    
    def evaluate_model(self):
        """Evaluate the model on the test set"""
        if self.model is None:
            print("No model to evaluate. Please train or load a model first.")
            return None
        
        if self.test_generator is None:
            print("No test generator available. Creating one from validation set.")
            self.test_generator = self.validation_generator
        
        # Evaluate the model
        print("Evaluating model...")
        evaluation = self.model.evaluate(self.test_generator)
        
        # Print results
        print(f"Test Loss: {evaluation[0]:.4f}")
        print(f"Test Accuracy: {evaluation[1]:.4f}")
        
        # If we have a test generator with filenames, we can get predictions for specific images
        if hasattr(self.test_generator, 'filenames') and len(self.test_generator.filenames) > 0:
            # Get predictions
            predictions = self.model.predict(self.test_generator)
            predicted_classes = np.argmax(predictions, axis=1)
            
            # Get true classes
            true_classes = self.test_generator.classes
            
            # Get filenames
            filenames = self.test_generator.filenames
            
            # Print some example predictions
            print("\nExample predictions:")
            for i in range(min(10, len(filenames))):
                true_class = self.class_mapping[true_classes[i]]
                pred_class = self.class_mapping[predicted_classes[i]]
                confidence = predictions[i][predicted_classes[i]] * 100
                
                print(f"File: {filenames[i]}")
                print(f"True class: {true_class}")
                print(f"Predicted class: {pred_class} (Confidence: {confidence:.2f}%)")
                print("-" * 50)
        
        return evaluation
    
    def plot_training_history(self):
        """Plot the training history"""
        if self.history is None:
            print("No training history available.")
            return
        
        # Create plot
        plt.figure(figsize=(12, 5))
        
        # Plot accuracy
        plt.subplot(1, 2, 1)
        plt.plot(self.history.history['accuracy'], label='Training Accuracy')
        plt.plot(self.history.history['val_accuracy'], label='Validation Accuracy')
        plt.title('Model Accuracy')
        plt.xlabel('Epoch')
        plt.ylabel('Accuracy')
        plt.legend()
        
        # Plot loss
        plt.subplot(1, 2, 2)
        plt.plot(self.history.history['loss'], label='Training Loss')
        plt.plot(self.history.history['val_loss'], label='Validation Loss')
        plt.title('Model Loss')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.legend()
        
        # Save plot
        plt.tight_layout()
        plt.savefig(os.path.join(self.model_dir, 'training_history.png'))
        plt.show()
    
    def load_model(self, model_path=None):
        """Load a saved model"""
        if model_path is None:
            # Try to load the latest model
            latest_model_path = os.path.join(self.model_dir, 'latest_model.h5')
            if os.path.exists(latest_model_path):
                model_path = latest_model_path
            else:
                # Try to find any model in the model directory
                models = [f for f in os.listdir(self.model_dir) if f.endswith('.h5')]
                if models:
                    model_path = os.path.join(self.model_dir, models[0])
                else:
                    print("No model found to load.")
                    return False
        
        # Load the model
        try:
            self.model = load_model(model_path)
            print(f"Model loaded from {model_path}")
            
            # Load class mapping if available
            mapping_path = os.path.join(self.model_dir, 'class_mapping.json')
            if os.path.exists(mapping_path):
                with open(mapping_path, 'r') as f:
                    self.class_mapping = json.load(f)
                print(f"Class mapping loaded: {self.class_mapping}")
            
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def predict_single_image(self, image_path):
        """Predict class for a single image"""
        if self.model is None:
            print("No model available. Please train or load a model first.")
            return None
        
        try:
            # Load and preprocess the image
            img = cv2.imread(image_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, self.image_size)
            img = img / 255.0
            img = np.expand_dims(img, axis=0)
            
            # Make prediction
            prediction = self.model.predict(img)
            predicted_class = np.argmax(prediction[0])
            confidence = prediction[0][predicted_class] * 100
            
            # Get class name
            class_name = self.class_mapping.get(str(predicted_class), f"Class {predicted_class}")
            
            print(f"Predicted class: {class_name}")
            print(f"Confidence: {confidence:.2f}%")
            
            return class_name, confidence
        except Exception as e:
            print(f"Error predicting image: {e}")
            return None
    
    def predict_image_array(self, image_array):
        """Predict class for an image array (e.g., from a webcam)"""
        if self.model is None:
            print("No model available. Please train or load a model first.")
            return None, 0.0
        
        try:
            # Preprocess the image
            img = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
            img = cv2.resize(img, self.image_size)
            img = img / 255.0
            img = np.expand_dims(img, axis=0)
            
            # Make prediction
            prediction = self.model.predict(img)
            predicted_class = np.argmax(prediction[0])
            confidence = prediction[0][predicted_class]
            
            # Get class name
            class_name = self.class_mapping.get(str(predicted_class), f"Class {predicted_class}")
            
            return class_name, confidence
        except Exception as e:
            print(f"Error predicting image: {e}")
            return None, 0.0
    
    def split_data(self, test_size=0.1, val_size=0.2, random_seed=42):
        """Split data into train, validation, and test sets"""
        np.random.seed(random_seed)
        
        # Create directories if they don't exist
        for split in ['train', 'validation', 'test']:
            for class_name in os.listdir(self.data_dir):
                class_dir = os.path.join(self.data_dir, class_name)
                if os.path.isdir(class_dir) and not class_name in ['train', 'validation', 'test']:
                    os.makedirs(os.path.join(self.data_dir, split, class_name), exist_ok=True)
        
        # Process each class
        for class_name in os.listdir(self.data_dir):
            class_dir = os.path.join(self.data_dir, class_name)
            
            # Skip non-directory items and special directories
            if not os.path.isdir(class_dir) or class_name in ['train', 'validation', 'test']:
                continue
            
            # Get all image files
            image_files = [f for f in os.listdir(class_dir) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            # Shuffle the files
            np.random.shuffle(image_files)
            
            # Calculate split indices
            n_files = len(image_files)
            n_test = max(1, int(n_files * test_size))
            n_val = max(1, int(n_files * val_size))
            n_train = n_files - n_test - n_val
            
            # Split the files
            train_files = image_files[:n_train]
            val_files = image_files[n_train:n_train+n_val]
            test_files = image_files[n_train+n_val:]
            
            print(f"Splitting class {class_name}: {n_train} train, {n_val} validation, {n_test} test")
            
            # Copy files to respective directories
            for files, split in [(train_files, 'train'), (val_files, 'validation'), (test_files, 'test')]:
                target_dir = os.path.join(self.data_dir, split, class_name)
                for file in files:
                    src = os.path.join(class_dir, file)
                    dst = os.path.join(target_dir, file)
                    shutil.copy2(src, dst)
    
    def export_tflite_model(self, quantize=True):
        """Export the model to TFLite format"""
        if self.model is None:
            print("No model available. Please train or load a model first.")
            return None
        
        # Create TFLite converter
        converter = tf.lite.TFLiteConverter.from_keras_model(self.model)
        
        # Set optimization flag
        if quantize:
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        # Convert the model
        tflite_model = converter.convert()
        
        # Save the model
        tflite_path = os.path.join(self.model_dir, 'waste_classifier.tflite')
        with open(tflite_path, 'wb') as f:
            f.write(tflite_model)
        
        print(f"TFLite model saved to {tflite_path}")
        
        # Save class mapping if not already saved
        mapping_path = os.path.join(self.model_dir, 'class_mapping.json')
        if not os.path.exists(mapping_path):
            with open(mapping_path, 'w') as f:
                json.dump(self.class_mapping, f)
        
        return tflite_path


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Train a waste classification model')
    parser.add_argument('--data_dir', type=str, default='./training_data',
                        help='Directory containing training data')
    parser.add_argument('--model_dir', type=str, default='./models',
                        help='Directory to save models')
    parser.add_argument('--batch_size', type=int, default=32,
                        help='Batch size for training')
    parser.add_argument('--epochs', type=int, default=50,
                        help='Number of epochs for training')
    parser.add_argument('--learning_rate', type=float, default=0.0001,
                        help='Learning rate for training')
    parser.add_argument('--image_size', type=int, default=224,
                        help='Image size for training (square)')
    parser.add_argument('--split_data', action='store_true',
                        help='Split data into train/validation/test sets')
    parser.add_argument('--load_model', type=str, default=None,
                        help='Path to model to load (optional)')
    parser.add_argument('--evaluate', action='store_true',
                        help='Evaluate model after training')
    parser.add_argument('--export_tflite', action='store_true',
                        help='Export trained model to TFLite format')
    
    args = parser.parse_args()
    
    # Create trainer
    trainer = WasteClassifierTrainer(
        data_dir=args.data_dir,
        model_dir=args.model_dir,
        image_size=(args.image_size, args.image_size),
        batch_size=args.batch_size,
        epochs=args.epochs,
        learning_rate=args.learning_rate
    )
    
    # Split data if requested
    if args.split_data:
        trainer.split_data()
    
    # Load model if specified
    if args.load_model:
        trainer.load_model(args.load_model)
    
    # Prepare directories
    trainer.prepare_directories()
    
    # Create data generators
    trainer.create_data_generators()
    
    # Train model
    trainer.train_model()
    
    # Plot training history
    trainer.plot_training_history()
    
    # Evaluate model if requested
    if args.evaluate:
        trainer.evaluate_model()
    
    # Export to TFLite if requested
    if args.export_tflite:
        trainer.export_tflite_model()


if __name__ == "__main__":
    main()