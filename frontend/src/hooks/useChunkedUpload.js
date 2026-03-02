import { useState, useCallback, useRef } from 'react';
import uploadManager from '../services/uploadManager';

/**
 * React hook for chunked file uploads with progress tracking
 * Handles upload state, progress, and error management
 */
export function useChunkedUpload() {
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState({
    totalFiles: 0,
    completedFiles: 0,
    currentFile: null,
    stage: 'idle',
    message: ''
  });
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const sessionTokenRef = useRef(null);

  /**
   * Start chunked upload
   */
  const startUpload = useCallback(async (galleryId, files) => {
    setIsUploading(true);
    setError(null);
    setResult(null);
    setProgress({
      totalFiles: files.length,
      completedFiles: 0,
      currentFile: null,
      stage: 'initializing',
      message: 'Initializing upload...'
    });

    try {
      const uploadResult = await uploadManager.upload(galleryId, files, {
        // Progress callback for chunk uploads
        onProgress: (progressData) => {
          if (progressData.stage === 'initialized') {
            sessionTokenRef.current = progressData.session.session_token;
            setProgress(prev => ({
              ...prev,
              stage: 'uploading',
              message: `Uploading ${progressData.session.total_files} files...`
            }));
          } else if (progressData.stage === 'uploaded') {
            setProgress(prev => ({
              ...prev,
              stage: 'processing',
              message: 'Processing files...'
            }));
          } else if (progressData.stage === 'completed') {
            setProgress(prev => ({
              ...prev,
              stage: 'completed',
              message: progressData.message,
              result: progressData.result
            }));
          } else if (progressData.filename) {
            // Individual file/chunk progress
            setProgress(prev => ({
              ...prev,
              currentFile: {
                filename: progressData.filename,
                percentage: progressData.percentage,
                uploaded_chunks: progressData.uploaded_chunks,
                total_chunks: progressData.total_chunks
              },
              completedFiles: progressData.completedFiles || prev.completedFiles
            }));
          }
        },

        // Callback when a file completes
        onFileComplete: (fileData) => {
          setProgress(prev => ({
            ...prev,
            completedFiles: fileData.completedFiles,
            message: `Uploaded ${fileData.completedFiles} of ${fileData.totalFiles} files`
          }));
        },

        // Completion callback
        onComplete: (uploadResult) => {
          setResult(uploadResult);
          setIsUploading(false);
        },

        // Error callback
        onError: (err) => {
          console.error('Upload error:', err);
          setError(err);
          setProgress(prev => ({
            ...prev,
            stage: 'error',
            message: err.message || 'Upload failed',
            error: err
          }));
          setIsUploading(false);
        }
      });

      return uploadResult;

    } catch (err) {
      console.error('Upload failed:', err);
      setError(err);
      setProgress(prev => ({
        ...prev,
        stage: 'error',
        message: err.message || 'Upload failed',
        error: err
      }));
      setIsUploading(false);
      throw err;
    }
  }, []);

  /**
   * Cancel current upload
   */
  const cancelUpload = useCallback(async () => {
    if (sessionTokenRef.current) {
      try {
        await uploadManager.cancelSession(sessionTokenRef.current);
        setIsUploading(false);
        setProgress(prev => ({
          ...prev,
          stage: 'cancelled',
          message: 'Upload cancelled'
        }));
      } catch (err) {
        console.error('Failed to cancel upload:', err);
      }
    }
  }, []);

  /**
   * Reset upload state
   */
  const reset = useCallback(() => {
    setIsUploading(false);
    setError(null);
    setResult(null);
    setProgress({
      totalFiles: 0,
      completedFiles: 0,
      currentFile: null,
      stage: 'idle',
      message: ''
    });
    sessionTokenRef.current = null;
  }, []);

  return {
    isUploading,
    progress,
    error,
    result,
    startUpload,
    cancelUpload,
    reset
  };
}
