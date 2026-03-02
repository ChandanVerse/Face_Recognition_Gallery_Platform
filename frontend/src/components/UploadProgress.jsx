import { CheckCircle, Loader2, AlertCircle } from 'lucide-react';

/**
 * Upload progress component with file-level tracking
 * Shows overall progress and individual file progress
 */
export default function UploadProgress({ progress, onCancel }) {
  const { totalFiles, completedFiles, currentFile, stage, message } = progress;

  // Calculate overall progress
  const overallPercentage = totalFiles > 0
    ? Math.round((completedFiles / totalFiles) * 100)
    : 0;

  // Get progress bar color based on stage
  const getProgressColor = () => {
    if (stage === 'error') return 'bg-red-600';
    if (stage === 'completed') return 'bg-green-600';
    return 'bg-primary-600';
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl p-8 max-w-2xl w-full mx-4">
        {/* Header */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            {stage === 'completed' ? '✅ Upload Complete!' : '📤 Uploading Photos'}
          </h2>
          <p className="text-gray-600">{message || 'Please wait while your photos are uploaded...'}</p>
        </div>

        {/* Overall Progress Bar */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700">
              Overall Progress
            </span>
            <span className="text-sm font-medium text-gray-900">
              {completedFiles} of {totalFiles} files ({overallPercentage}%)
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
            <div
              className={`h-full ${getProgressColor()} transition-all duration-300 ease-out`}
              style={{ width: `${overallPercentage}%` }}
            />
          </div>
        </div>

        {/* Current File Progress */}
        {currentFile && stage !== 'completed' && (
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700 truncate max-w-xs">
                {currentFile.filename}
              </span>
              <span className="text-sm text-gray-600">
                {Math.round(currentFile.percentage || 0)}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-200"
                style={{ width: `${currentFile.percentage || 0}%` }}
              />
            </div>
            <div className="mt-2 text-xs text-gray-500">
              {currentFile.uploaded_chunks || 0} of {currentFile.total_chunks || 0} chunks
            </div>
          </div>
        )}

        {/* Status Icons */}
        <div className="flex items-center justify-center mb-6">
          {stage === 'uploading' && (
            <Loader2 className="w-12 h-12 text-primary-600 animate-spin" />
          )}
          {stage === 'completed' && (
            <CheckCircle className="w-12 h-12 text-green-600" />
          )}
          {stage === 'error' && (
            <AlertCircle className="w-12 h-12 text-red-600" />
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex justify-center gap-4">
          {stage === 'uploading' && onCancel && (
            <button
              onClick={onCancel}
              className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Cancel Upload
            </button>
          )}
          {stage === 'completed' && (
            <button
              onClick={() => window.location.reload()}
              className="btn-primary px-8 py-3"
            >
              View Gallery
            </button>
          )}
        </div>

        {/* Details */}
        {stage === 'completed' && progress.result && (
          <div className="mt-6 p-4 bg-green-50 rounded-lg">
            <p className="text-sm text-green-800">
              ✅ {progress.result.processed_files} photos successfully uploaded and queued for processing.
              {progress.result.failed_files > 0 && (
                <span className="block mt-1 text-red-600">
                  ⚠ {progress.result.failed_files} files failed to process.
                </span>
              )}
            </p>
          </div>
        )}

        {stage === 'error' && progress.error && (
          <div className="mt-6 p-4 bg-red-50 rounded-lg">
            <p className="text-sm text-red-800">
              ❌ Upload failed: {progress.error.message || 'Unknown error'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
