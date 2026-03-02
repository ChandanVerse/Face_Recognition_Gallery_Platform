/**
 * Resumable upload manager with chunking support
 * Handles large file uploads efficiently with progress tracking and error recovery
 */
import api from './api';

class UploadManager {
  constructor() {
    this.activeUploads = new Map();
    this.CHUNK_SIZE = 5 * 1024 * 1024; // 5MB chunks
    this.MAX_CONCURRENT_UPLOADS = 3; // Upload 3 files in parallel
  }

  /**
   * Initialize upload session with backend
   *
   * @param {number} galleryId - Gallery ID to upload to
   * @param {FileList|Array} files - Files to upload
   * @returns {Promise<Object>} Session data with upload URLs
   */
  async initializeSession(galleryId, files) {
    const fileList = Array.from(files).map(file => ({
      filename: file.name,
      size: file.size
    }));

    console.log(`📝 Initializing upload session for ${fileList.length} files`);

    const response = await api.post('/uploads/init', {
      gallery_id: galleryId,
      files: fileList
    });

    console.log(`✅ Session initialized: ${response.data.session_token}`);

    return response.data;
  }

  /**
   * Upload a single file in chunks
   *
   * @param {File} file - File to upload
   * @param {Object} fileInfo - File metadata from session
   * @param {Function} onProgress - Progress callback
   * @returns {Promise<void>}
   */
  async uploadFile(file, fileInfo, onProgress) {
    const { file_token, total_chunks, chunk_size } = fileInfo;

    console.log(`📤 Uploading ${file.name} in ${total_chunks} chunks`);

    for (let chunkIndex = 0; chunkIndex < total_chunks; chunkIndex++) {
      const start = chunkIndex * chunk_size;
      const end = Math.min(start + chunk_size, file.size);
      const chunk = file.slice(start, end);

      // Retry logic for failed chunks
      let retries = 3;
      let uploaded = false;

      while (retries > 0 && !uploaded) {
        try {
          // Upload chunk
          await api.put(
            `/uploads/chunk/${file_token}/${chunkIndex}`,
            chunk,
            {
              headers: {
                'Content-Type': 'application/octet-stream'
              },
              timeout: 60000 // 60 second timeout per chunk
            }
          );

          uploaded = true;

          // Report progress
          if (onProgress) {
            onProgress({
              file_token,
              filename: file.name,
              uploaded_chunks: chunkIndex + 1,
              total_chunks,
              percentage: ((chunkIndex + 1) / total_chunks) * 100,
              uploaded_size: end,
              file_size: file.size
            });
          }

        } catch (error) {
          retries--;
          if (retries === 0) {
            console.error(`❌ Failed to upload chunk ${chunkIndex} after 3 retries:`, error);
            throw new Error(`Failed to upload chunk ${chunkIndex} of ${file.name}`);
          }
          console.warn(`⚠ Retry ${3 - retries}/3 for chunk ${chunkIndex}`);
          // Wait before retry (exponential backoff)
          await new Promise(resolve => setTimeout(resolve, 1000 * (4 - retries)));
        }
      }
    }

    console.log(`✅ Completed upload of ${file.name}`);
  }

  /**
   * Upload multiple files with concurrency control
   *
   * @param {FileList|Array} files - Files to upload
   * @param {Object} session - Upload session data
   * @param {Function} onProgress - Progress callback for individual files
   * @param {Function} onFileComplete - Callback when a file completes
   * @returns {Promise<void>}
   */
  async uploadFiles(files, session, onProgress, onFileComplete) {
    const fileArray = Array.from(files);
    const uploadQueue = [];
    let completedCount = 0;

    // Create upload promises for all files
    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i];
      const fileInfo = session.files[i];

      const uploadPromise = (async () => {
        try {
          await this.uploadFile(
            file,
            fileInfo,
            (progress) => {
              if (onProgress) {
                onProgress({
                  ...progress,
                  fileIndex: i,
                  totalFiles: fileArray.length,
                  completedFiles: completedCount
                });
              }
            }
          );

          completedCount++;

          if (onFileComplete) {
            onFileComplete({
              fileIndex: i,
              filename: file.name,
              completedFiles: completedCount,
              totalFiles: fileArray.length
            });
          }
        } catch (error) {
          console.error(`❌ Error uploading ${file.name}:`, error);
          throw error;
        }
      })();

      uploadQueue.push(uploadPromise);

      // Control concurrency - only keep MAX_CONCURRENT_UPLOADS running at once
      if (uploadQueue.length >= this.MAX_CONCURRENT_UPLOADS) {
        await Promise.race(uploadQueue);
        // Remove completed promises
        uploadQueue.splice(
          uploadQueue.findIndex(p =>
            p.then === undefined || p.status === 'fulfilled'
          ),
          1
        );
      }
    }

    // Wait for all remaining uploads to complete
    await Promise.all(uploadQueue);

    console.log(`✅ All ${fileArray.length} files uploaded successfully`);
  }

  /**
   * Complete upload session (finalize and start processing)
   *
   * @param {string} sessionToken - Session token
   * @returns {Promise<Object>} Completion result
   */
  async completeSession(sessionToken) {
    console.log(`🔄 Completing upload session ${sessionToken}`);

    const response = await api.post(`/uploads/complete/${sessionToken}`);

    console.log(`✅ Session completed: ${response.data.processed_files} files queued for processing`);

    return response.data;
  }

  /**
   * Get upload session status
   *
   * @param {string} sessionToken - Session token
   * @returns {Promise<Object>} Session status
   */
  async getStatus(sessionToken) {
    const response = await api.get(`/uploads/status/${sessionToken}`);
    return response.data;
  }

  /**
   * Cancel upload session
   *
   * @param {string} sessionToken - Session token
   * @returns {Promise<Object>} Cancellation result
   */
  async cancelSession(sessionToken) {
    console.log(`🚫 Cancelling upload session ${sessionToken}`);

    const response = await api.delete(`/uploads/cancel/${sessionToken}`);

    console.log(`✅ Session cancelled`);

    return response.data;
  }

  /**
   * Main upload flow - coordinates entire upload process
   *
   * @param {number} galleryId - Gallery ID
   * @param {FileList|Array} files - Files to upload
   * @param {Object} callbacks - Progress callbacks
   * @returns {Promise<Object>} Upload result
   */
  async upload(galleryId, files, callbacks = {}) {
    const {
      onProgress,
      onFileComplete,
      onComplete,
      onError
    } = callbacks;

    try {
      // 1. Initialize session
      console.log(`🚀 Starting upload of ${files.length} files`);
      const session = await this.initializeSession(galleryId, files);

      if (onProgress) {
        onProgress({
          stage: 'initialized',
          session,
          message: 'Upload session initialized'
        });
      }

      // 2. Upload all files in chunks
      await this.uploadFiles(files, session, onProgress, onFileComplete);

      if (onProgress) {
        onProgress({
          stage: 'uploaded',
          message: 'All files uploaded, processing...'
        });
      }

      // 3. Finalize and start processing
      const result = await this.completeSession(session.session_token);

      if (onProgress) {
        onProgress({
          stage: 'completed',
          result,
          message: `Upload complete! ${result.processed_files} files queued for processing.`
        });
      }

      if (onComplete) {
        onComplete(result);
      }

      return result;

    } catch (error) {
      console.error('❌ Upload error:', error);

      if (onError) {
        onError(error);
      }

      throw error;
    }
  }
}

// Export singleton instance
export default new UploadManager();
