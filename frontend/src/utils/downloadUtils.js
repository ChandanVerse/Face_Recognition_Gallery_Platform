/**
 * Utility functions for downloading photos
 */

/**
 * Download a single photo from the gallery
 * Uses direct anchor link approach to avoid CORS issues
 * @param {string} photoUrl - The URL of the photo to download
 * @param {string} photoId - The ID of the photo
 * @param {Array} taggedPeople - Array of tagged people objects with person_name
 */
export const downloadPhoto = (photoUrl, photoId, taggedPeople = []) => {
  try {
    // Generate filename with person names
    const personNames = taggedPeople
      .map(person => person.person_name.replace(/\s+/g, '_'))
      .join('_');

    const filename = personNames
      ? `photo_${photoId}_${personNames}.jpg`
      : `photo_${photoId}.jpg`;

    // Create anchor element with direct link (avoids CORS issues with fetch)
    const link = document.createElement('a');
    link.href = photoUrl;
    link.download = filename;
    link.style.display = 'none';

    // Append to DOM, click, and remove
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    console.log(`Download started: ${filename}`);

  } catch (error) {
    console.error('Download failed:', error);
    alert(`Failed to download photo: ${error.message}`);
  }
};

/**
 * Download multiple photos as individual files
 * Initiates downloads with small delays to prevent browser blocking
 * @param {Array} photos - Array of photo objects with id, url, and tagged_people
 */
export const downloadMultiplePhotos = (photos) => {
  if (!photos || photos.length === 0) {
    alert('No photos selected for download');
    return;
  }

  try {
    photos.forEach((photo, index) => {
      // Add delay between each download to prevent browser from blocking
      setTimeout(() => {
        downloadPhoto(photo.url, photo.id, photo.tagged_people);
      }, index * 100);
    });

    console.log(`Started downloading ${photos.length} photos`);
  } catch (error) {
    console.error('Bulk download failed:', error);
    alert(`Bulk download failed: ${error.message}`);
  }
};
