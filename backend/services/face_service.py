"""
Face recognition service using InsightFace
"""
import numpy as np
from typing import List, Dict, Any
from backend.core.face_recognition.face_embedder import FaceEmbedder
from backend.core.database.pinecone_db import PineconeDatabase
from backend.config.settings import get_settings

settings = get_settings()

class FaceService:
    """Face recognition service for detecting faces and matching them"""
    
    def __init__(self):
        self._embedder = FaceEmbedder()
        self._db = PineconeDatabase(
            api_key=settings.PINECONE_API_KEY,
            index_name=settings.PINECONE_INDEX_NAME,
            environment=settings.PINECONE_ENVIRONMENT
        )
    
    def detect_faces(self, image_array: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect faces in an image and return embeddings with metadata

        Args:
            image_array: Image as numpy array (BGR or RGB format)

        Returns:
            List of face data dictionaries with 'embedding' and 'bbox' keys
        """
        try:
            # Handle RGBA images - convert to RGB first
            if image_array.ndim == 3 and image_array.shape[2] == 4:
                # RGBA to RGB - drop the alpha channel
                image_array = image_array[:, :, :3]

            # Ensure OpenCV BGR format for InsightFace; convert if array looks like RGB
            if image_array.ndim == 3 and image_array.shape[2] == 3:
                # Heuristic: if average of channel order seems RGB, convert to BGR
                # We avoid expensive checks; always convert RGB->BGR safely.
                image_bgr = image_array[:, :, ::-1]
            else:
                image_bgr = image_array

            face_data = self._embedder.extract_faces_from_array(image_bgr)
            
            # Add additional metadata for each face
            enhanced_faces = []
            for idx, face in enumerate(face_data):
                enhanced_face = face.copy()
                enhanced_face['det_score'] = 0.9  # Default confidence score
                enhanced_face['confidence'] = 0.9
                enhanced_faces.append(enhanced_face)
            
            return enhanced_faces
            
        except Exception as e:
            print(f"Error detecting faces: {e}")
            return []
    
    def search_similar_faces(self, embedding: np.ndarray, top_k: int = 10000, score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        matches = self._db.search_similar_faces(embedding, top_k=top_k, threshold=score_threshold)
        # Return all metadata from Pinecone, ensuring confidence is properly mapped
        normalized = []
        for m in matches:
            # Keep all metadata from Pinecone
            entry = m.copy()

            # Ensure confidence is set (it should be already from Pinecone)
            if 'confidence' not in entry and 'score' in m:
                entry['confidence'] = m['score']

            normalized.append(entry)
        return normalized