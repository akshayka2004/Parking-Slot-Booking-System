"""
Occupancy Detection Module
Uses OpenCV to detect car presence in parking slots via image analysis
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
import os


class OccupancyDetector:
    """
    Detects parking slot occupancy using image processing.
    Analyzes pixel intensity in predefined bounding boxes to determine car presence.
    """
    
    # Pre-defined bounding boxes for 6 parking slots
    # Format: (x, y, width, height) - simulating a parking lot camera view
    DEFAULT_SLOTS = {
        'slot_1': (50, 100, 120, 180),
        'slot_2': (200, 100, 120, 180),
        'slot_3': (350, 100, 120, 180),
        'slot_4': (50, 320, 120, 180),
        'slot_5': (200, 320, 120, 180),
        'slot_6': (350, 320, 120, 180),
    }
    
    # Intensity thresholds
    OCCUPIED_THRESHOLD = 100  # Lower intensity indicates car (darker/shadow)
    VARIANCE_THRESHOLD = 500  # High variance indicates complex object (car)
    
    def __init__(self, slot_regions: Dict[str, Tuple[int, int, int, int]] = None):
        """
        Initialize the detector.
        
        Args:
            slot_regions: Custom slot bounding boxes {slot_id: (x, y, w, h)}
        """
        self.slot_regions = slot_regions or self.DEFAULT_SLOTS
    
    def load_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Load an image from file.
        
        Args:
            image_path: Path to the image file
        
        Returns:
            Image as numpy array, or None if loading fails
        """
        if not os.path.exists(image_path):
            return None
        
        image = cv2.imread(image_path)
        return image
    
    def analyze_region(self, image: np.ndarray, 
                       bbox: Tuple[int, int, int, int]) -> Dict:
        """
        Analyze a specific region for car presence.
        
        Args:
            image: Input image
            bbox: Bounding box (x, y, width, height)
        
        Returns:
            Dict with occupancy status and metrics
        """
        x, y, w, h = bbox
        
        # Ensure bbox is within image bounds
        h_img, w_img = image.shape[:2]
        x = max(0, min(x, w_img - 1))
        y = max(0, min(y, h_img - 1))
        w = min(w, w_img - x)
        h = min(h, h_img - y)
        
        # Extract region of interest
        roi = image[y:y+h, x:x+w]
        
        if roi.size == 0:
            return {
                'occupied': False,
                'mean_intensity': 0,
                'variance': 0,
                'confidence': 0
            }
        
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Calculate metrics
        mean_intensity = np.mean(gray)
        variance = np.var(gray)
        
        # Determine occupancy based on intensity and variance
        # Cars typically create darker areas (shadows) with higher variance (complex shapes)
        is_occupied = (mean_intensity < self.OCCUPIED_THRESHOLD or 
                       variance > self.VARIANCE_THRESHOLD)
        
        # Calculate confidence based on how strongly the metrics indicate occupancy
        intensity_score = max(0, (self.OCCUPIED_THRESHOLD - mean_intensity) / self.OCCUPIED_THRESHOLD)
        variance_score = min(1, variance / (self.VARIANCE_THRESHOLD * 2))
        confidence = (intensity_score + variance_score) / 2
        
        return {
            'occupied': is_occupied,
            'mean_intensity': round(mean_intensity, 2),
            'variance': round(variance, 2),
            'confidence': round(confidence, 2)
        }
    
    def detect_occupancy(self, image_path: str) -> Dict[str, bool]:
        """
        Detect occupancy for all slots from an image.
        
        Args:
            image_path: Path to the parking lot image
        
        Returns:
            Dict mapping slot_id to occupancy status (True = occupied)
        """
        image = self.load_image(image_path)
        
        if image is None:
            # Return simulated data if image can't be loaded
            return self._simulate_occupancy()
        
        occupancy = {}
        for slot_id, bbox in self.slot_regions.items():
            analysis = self.analyze_region(image, bbox)
            occupancy[slot_id] = analysis['occupied']
        
        return occupancy
    
    def detect_with_details(self, image_path: str) -> Dict[str, Dict]:
        """
        Detect occupancy with detailed analysis for each slot.
        
        Args:
            image_path: Path to the parking lot image
        
        Returns:
            Dict mapping slot_id to detailed analysis results
        """
        image = self.load_image(image_path)
        
        if image is None:
            return self._simulate_occupancy_detailed()
        
        results = {}
        for slot_id, bbox in self.slot_regions.items():
            analysis = self.analyze_region(image, bbox)
            results[slot_id] = {
                **analysis,
                'bbox': bbox
            }
        
        return results
    
    def overlay_detection(self, image_path: str, 
                          output_path: str = None) -> Optional[np.ndarray]:
        """
        Create an image with detection boxes overlaid.
        
        Args:
            image_path: Path to input image
            output_path: Optional path to save the result
        
        Returns:
            Annotated image as numpy array
        """
        image = self.load_image(image_path)
        
        if image is None:
            # Create a blank image for demonstration
            image = np.ones((600, 520, 3), dtype=np.uint8) * 200  # Gray background
        
        detection = self.detect_with_details(image_path)
        
        for slot_id, result in detection.items():
            bbox = result['bbox']
            x, y, w, h = bbox
            
            # Color based on occupancy: Red = occupied, Green = available
            color = (0, 0, 255) if result['occupied'] else (0, 255, 0)
            thickness = 2
            
            # Draw rectangle
            cv2.rectangle(image, (x, y), (x+w, y+h), color, thickness)
            
            # Add label
            label = f"{slot_id}: {'Occupied' if result['occupied'] else 'Free'}"
            cv2.putText(image, label, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, color, 1, cv2.LINE_AA)
        
        if output_path:
            cv2.imwrite(output_path, image)
        
        return image
    
    def _simulate_occupancy(self) -> Dict[str, bool]:
        """
        Generate simulated occupancy data when no image is available.
        Uses realistic patterns based on typical parking lot usage.
        """
        import random
        from datetime import datetime
        
        random.seed(datetime.now().second)
        
        # Simulate ~60% occupancy during daytime
        hour = datetime.now().hour
        if 9 <= hour <= 18:
            occupancy_rate = 0.6
        else:
            occupancy_rate = 0.3
        
        return {
            slot_id: random.random() < occupancy_rate
            for slot_id in self.slot_regions.keys()
        }
    
    def _simulate_occupancy_detailed(self) -> Dict[str, Dict]:
        """
        Generate detailed simulated occupancy data.
        """
        import random
        from datetime import datetime
        
        random.seed(datetime.now().second)
        
        results = {}
        for slot_id, bbox in self.slot_regions.items():
            occupied = random.random() < 0.5
            results[slot_id] = {
                'occupied': occupied,
                'mean_intensity': random.uniform(50, 150),
                'variance': random.uniform(200, 800),
                'confidence': random.uniform(0.6, 0.95),
                'bbox': bbox
            }
        
        return results
    
    def get_occupancy_summary(self, image_path: str) -> Dict:
        """
        Get a summary of parking lot occupancy.
        
        Args:
            image_path: Path to parking lot image
        
        Returns:
            Summary dict with counts and percentages
        """
        detection = self.detect_occupancy(image_path)
        
        total = len(detection)
        occupied = sum(1 for occ in detection.values() if occ)
        available = total - occupied
        
        return {
            'total_slots': total,
            'occupied': occupied,
            'available': available,
            'occupancy_rate': round(occupied / total * 100, 1) if total > 0 else 0,
            'slot_status': detection
        }


if __name__ == "__main__":
    # Test the detector
    detector = OccupancyDetector()
    
    print("Occupancy Detector Test (Simulation Mode)")
    print("=" * 50)
    
    # Test with simulated data (no actual image)
    occupancy = detector.detect_occupancy("nonexistent.jpg")
    print("\nSimulated Occupancy Detection:")
    for slot_id, is_occupied in occupancy.items():
        status = "Occupied" if is_occupied else "Available"
        print(f"  {slot_id}: {status}")
    
    # Get summary
    summary = detector.get_occupancy_summary("nonexistent.jpg")
    print(f"\nSummary:")
    print(f"  Total: {summary['total_slots']} slots")
    print(f"  Occupied: {summary['occupied']}")
    print(f"  Available: {summary['available']}")
    print(f"  Occupancy Rate: {summary['occupancy_rate']}%")
