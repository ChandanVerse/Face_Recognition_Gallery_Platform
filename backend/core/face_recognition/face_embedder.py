"""
Core face embedding module using InsightFace
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional

# Try to import InsightFace; fall back gracefully if unavailable
try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except (ImportError, AttributeError) as e:
    print(f"Warning: InsightFace not available: {e}")
    INSIGHTFACE_AVAILABLE = False
    FaceAnalysis = None


class FaceEmbedder:
    """Singleton face embedder to avoid loading model multiple times"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            if not INSIGHTFACE_AVAILABLE:
                print("Warning: InsightFace not available. Face detection will be disabled.")
                self.face_app = None
                FaceEmbedder._initialized = True
                return
                
            print("Loading face detection model...")
            self.face_app = FaceAnalysis(
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider'],
                allowed_modules=['detection', 'recognition']
            )
            # Use larger det_size for better recall; ctx_id=0 prefers GPU if available
            self.face_app.prepare(ctx_id=0, det_size=(1024, 1024))
            print("✓ Face detection model loaded")
            FaceEmbedder._initialized = True
    
    def extract_faces_from_image(self, image_path: str | Path):
        """
        Extract face embeddings and bounding boxes from image
        
        Returns:
            tuple: (image_array, list of face_data dicts)
                   face_data: {'embedding': np.array, 'bbox': np.array}
        """
        if not INSIGHTFACE_AVAILABLE or self.face_app is None:
            return None, []
            
        image = cv2.imread(str(image_path))
        if image is None:
            return None, []
        
        try:
            detected_faces = self.face_app.get(image)
            face_data = [
                {
                    'embedding': face.embedding,
                    'bbox': face.bbox.astype(int)
                }
                for face in detected_faces
            ]
            return image, face_data
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            return image, []
    
    def extract_faces_from_array(self, image_array: np.ndarray):
        """
        Extract faces from numpy array (useful for in-memory processing)

        Args:
            image_array: BGR or RGB image as numpy array (OpenCV format)

        Returns:
            list of face_data dicts: {'embedding': np.array, 'bbox': np.array}
        """
        if not INSIGHTFACE_AVAILABLE or self.face_app is None:
            return []

        try:
            # Handle RGBA images - convert to BGR/RGB first by dropping alpha channel
            if image_array.ndim == 3 and image_array.shape[2] == 4:
                image_array = image_array[:, :, :3]

            detected_faces = self.face_app.get(image_array)
            return [
                {
                    'embedding': face.embedding,
                    'bbox': face.bbox.astype(int)
                }
                for face in detected_faces
            ]
        except Exception as e:
            print(f"Error processing image array: {e}")
            return []
    
    def get_single_face_embedding(self, image_path: str | Path) -> Optional[np.ndarray]:
        """
        Get embedding from reference photo (uses largest face if multiple detected)
        
        Args:
            image_path: Path to image file
            
        Returns:
            numpy array of embedding or None if no face found
        """
        _, face_data = self.extract_faces_from_image(image_path)
        
        if not face_data:
            print(f"No faces found in {Path(image_path).name}")
            return None
        
        if len(face_data) > 1:
            # Use largest face based on bounding box area
            largest_face = max(
                face_data,
                key=lambda f: (f['bbox'][2] - f['bbox'][0]) * (f['bbox'][3] - f['bbox'][1])
            )
            return largest_face['embedding']
        
        return face_data[0]['embedding']
    
    def compute_average_embedding(self, embeddings: list[np.ndarray]) -> np.ndarray:
        """
        Compute average embedding from multiple face embeddings
        
        Args:
            embeddings: List of face embeddings
            
        Returns:
            Average embedding as numpy array
        """
        if not embeddings:
            raise ValueError("Cannot compute average of empty embeddings list")
        
        return np.mean(embeddings, axis=0)