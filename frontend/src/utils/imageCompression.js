/**
 * Client-side image compression utility
 * Compresses images before upload to reduce network transfer time
 * Uses Canvas API for fast, native compression
 */

/**
 * Compress an image file to reduce size before upload
 *
 * @param {File} file - Original image file
 * @param {Object} options - Compression options
 * @returns {Promise<File>} - Compressed image file
 */
export async function compressImage(file, options = {}) {
  const {
    maxSizeMB = 0.8,           // Target max size in MB
    maxWidthOrHeight = 2048,    // Max dimension
    quality = 0.85,             // JPEG quality (0-1)
    fileType = 'image/jpeg'     // Output format
  } = options;

  try {
    // Skip compression for small files (already under 500KB)
    if (file.size < 500 * 1024) {
      console.log(`⚡ Skipping compression for ${file.name} (already small: ${(file.size / 1024).toFixed(0)}KB)`);
      return file;
    }

    const startSize = file.size;

    // Load image into canvas
    const image = await loadImage(file);
    const { width, height } = calculateDimensions(image, maxWidthOrHeight);

    // Create canvas and draw resized image
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');

    // Use better quality scaling
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(image, 0, 0, width, height);

    // Convert to blob with compression
    const blob = await canvasToBlob(canvas, fileType, quality);

    // Create new file with original filename
    const compressedFile = new File([blob], file.name, {
      type: fileType,
      lastModified: Date.now()
    });

    const endSize = compressedFile.size;
    const reduction = ((1 - endSize / startSize) * 100).toFixed(0);

    console.log(`📦 Compressed ${file.name}: ${(startSize / 1024).toFixed(0)}KB → ${(endSize / 1024).toFixed(0)}KB (${reduction}% reduction)`);

    return compressedFile;

  } catch (error) {
    console.error(`❌ Compression failed for ${file.name}:`, error);
    // Return original file if compression fails
    return file;
  }
}

/**
 * Compress multiple images in parallel
 *
 * @param {File[]} files - Array of image files
 * @param {Object} options - Compression options
 * @param {Function} onProgress - Progress callback
 * @returns {Promise<File[]>} - Array of compressed files
 */
export async function compressImages(files, options = {}, onProgress = null) {
  const {
    concurrency = 4  // Number of images to compress simultaneously
  } = options;

  console.log(`🚀 Starting compression of ${files.length} images (${concurrency} parallel)`);

  const results = [];
  let completed = 0;

  // Process files in chunks to control concurrency
  for (let i = 0; i < files.length; i += concurrency) {
    const chunk = files.slice(i, i + concurrency);

    const chunkResults = await Promise.all(
      chunk.map(file => compressImage(file, options))
    );

    results.push(...chunkResults);
    completed += chunkResults.length;

    if (onProgress) {
      onProgress({
        completed,
        total: files.length,
        percentage: (completed / files.length) * 100
      });
    }
  }

  const originalSize = files.reduce((sum, f) => sum + f.size, 0);
  const compressedSize = results.reduce((sum, f) => sum + f.size, 0);
  const totalReduction = ((1 - compressedSize / originalSize) * 100).toFixed(0);

  console.log(`✅ Compression complete: ${(originalSize / 1024 / 1024).toFixed(1)}MB → ${(compressedSize / 1024 / 1024).toFixed(1)}MB (${totalReduction}% reduction)`);

  return results;
}

/**
 * Load image from file
 */
function loadImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = e.target.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Calculate new dimensions maintaining aspect ratio
 */
function calculateDimensions(image, maxDimension) {
  let { width, height } = image;

  if (width <= maxDimension && height <= maxDimension) {
    return { width, height };
  }

  if (width > height) {
    height = Math.round((height / width) * maxDimension);
    width = maxDimension;
  } else {
    width = Math.round((width / height) * maxDimension);
    height = maxDimension;
  }

  return { width, height };
}

/**
 * Convert canvas to blob
 */
function canvasToBlob(canvas, type, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob);
        } else {
          reject(new Error('Canvas to Blob conversion failed'));
        }
      },
      type,
      quality
    );
  });
}
