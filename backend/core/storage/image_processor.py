"""
Image preprocessing - compression and WebP conversion
Adapted from your preprocess_imgs.py
"""
import io
from PIL import Image
from typing import Optional


class ImageProcessor:
    """Handles image preprocessing operations"""
    
    @staticmethod
    def compress_and_convert_to_webp(
        image_data: bytes,
        quality: int = 90,
        max_dimension: int = 2048
    ) -> Optional[bytes]:
        """
        Load image, compress, and convert to WebP format
        
        Args:
            image_data: Raw image bytes
            quality: WebP compression quality (1-100)
            max_dimension: Maximum width/height to resize to
            
        Returns:
            Compressed WebP image as bytes, or None on error
        """
        try:
            # Load image from bytes
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if image.mode in ('RGBA', 'P', 'LA'):
                image = image.convert('RGB')
            
            # Resize if too large (preserve aspect ratio)
            if max(image.size) > max_dimension:
                image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            # Convert to WebP
            output_buffer = io.BytesIO()
            image.save(output_buffer, format='WEBP', quality=quality, lossless=False)
            
            return output_buffer.getvalue()
            
        except Exception as e:
            print(f"❌ Error processing image: {e}")
            return None
    
    @staticmethod
    def get_image_dimensions(image_data: bytes) -> tuple[int, int] | None:
        """Get image width and height"""
        try:
            image = Image.open(io.BytesIO(image_data))
            return image.size
        except Exception as e:
            print(f"❌ Error reading image dimensions: {e}")
            return None
    
    @staticmethod
    def validate_image(image_data: bytes) -> bool:
        """Check if data is a valid image"""
        try:
            image = Image.open(io.BytesIO(image_data))
            image.verify()
            return True
        except Exception:
            return False