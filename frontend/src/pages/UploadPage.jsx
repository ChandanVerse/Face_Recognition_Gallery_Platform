import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, XCircle, Loader2 } from 'lucide-react';
import DashboardHeader from '../components/DashboardHeader';
import { galleryAPI } from '../services/api';
import useAuthStore from '../store/authStore';
import { UploadBatcher } from '../utils/uploadBatcher';

export default function UploadPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore(); // Added this line

  // FIX: Redirect to login if user is not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [compressionProgress, setCompressionProgress] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    const newFiles = acceptedFiles.map(file => Object.assign(file, {
      preview: URL.createObjectURL(file)
    }));
    setFiles(prevFiles => [...prevFiles, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.webp'] },
  });

  const removeFile = (fileToRemove) => {
    setFiles(files.filter(file => file !== fileToRemove));
  };

  const handleSubmit = async () => {
    if (files.length === 0) {
      setError('Please select at least one photo to upload.');
      return;
    }
    setLoading(true);
    setError(null);
    setUploadProgress(null);
    setCompressionProgress(null);

    try {
      // Step 1: Create empty gallery
      const gallery = await galleryAPI.createEmpty();
      const galleryId = gallery.id;
      const shareToken = gallery.share_token;

      // Step 2: Upload photos without compression
      const batcher = new UploadBatcher(
        files,
        (batch) => galleryAPI.addPhotosToGallery(galleryId, batch),
        (progress) => {
          setUploadProgress(progress);
        }
      );

      const results = await batcher.uploadAll();

      // Step 4: Navigate to gallery when complete
      if (results.uploadedCount > 0) {
        navigate(`/gallery/${shareToken}`);
      } else {
        setError('All uploads failed. Please try again.');
        setLoading(false);
      }
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message || 'Upload failed. Please try again.');
      setLoading(false);
      setUploadProgress(null);
      setCompressionProgress(null);
    }
  };

  return (
    <div className="min-h-screen bg-primary-50">
      <DashboardHeader />
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-5xl font-extrabold text-gray-900">Create a New Gallery</h1>
            <p className="mt-2 text-xl text-gray-600">Upload unlimited photos from your event. Large uploads are automatically processed in batches of 100.</p>
          </div>

          <div className="card text-center">
            <div {...getRootProps()} className={`relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${isDragActive ? 'border-primary-600 bg-primary-50' : 'border-gray-300 hover:border-primary-500'}`}>
              <input {...getInputProps()} />
              <div className="flex flex-col items-center justify-center">
                <UploadCloud className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                <p className="font-bold text-gray-600">Drag & drop files here</p>
                <p className="text-gray-500 text-sm mt-1">or click to browse</p>
              </div>
            </div>
            
            {error && <p className="text-red-500 mt-4">{error}</p>}

            {compressionProgress && (
              <div className="mt-4 bg-purple-50 border border-purple-200 rounded-lg p-4">
                <p className="font-semibold text-purple-900">
                  🔄 Compressing images for faster upload...
                </p>
                <p className="text-sm text-purple-700 mt-1">
                  {compressionProgress.completed} / {compressionProgress.total} photos compressed ({compressionProgress.percentage.toFixed(0)}%)
                </p>
                <div className="w-full bg-purple-200 rounded-full h-2 mt-2">
                  <div
                    className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${compressionProgress.percentage}%` }}
                  />
                </div>
              </div>
            )}

            {uploadProgress && (
              <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p className="font-semibold text-blue-900">
                  Uploading batch {uploadProgress.currentBatch} of {uploadProgress.totalBatches}
                </p>
                <p className="text-sm text-blue-700 mt-1">
                  {uploadProgress.uploadedSoFar} / {uploadProgress.totalFiles} photos uploaded
                </p>
                <div className="w-full bg-blue-200 rounded-full h-2 mt-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${(uploadProgress.uploadedSoFar / uploadProgress.totalFiles) * 100}%` }}
                  />
                </div>
              </div>
            )}

            <div className="mt-8 text-center">
              <button onClick={handleSubmit} disabled={loading || files.length === 0} className="btn-primary px-8 py-3 text-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed">
                {loading ? <Loader2 className="animate-spin inline-block w-6 h-6 mr-2" /> : null}
                {loading ? `Uploading ${files.length} photos...` : `Create Gallery with ${files.length} Photos`}
              </button>
            </div>
          </div>

          {files.length > 0 && (
            <div className="mt-12">
              <h2 className="text-2xl font-bold mb-4">Selected Photos ({files.length})</h2>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-4">
                {files.slice(0, 24).map((file, index) => (
                  <div key={index} className="relative group aspect-square">
                    <img
                      src={file.preview}
                      alt={file.name}
                      className="w-full h-full object-cover rounded-xl shadow-md"
                      onLoad={() => URL.revokeObjectURL(file.preview)}
                    />
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <button onClick={() => removeFile(file)} className="text-white">
                        <XCircle className="w-8 h-8" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              {files.length > 24 && (
                <p className="text-center mt-4 text-gray-600">
                  ... and {files.length - 24} more photos
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}