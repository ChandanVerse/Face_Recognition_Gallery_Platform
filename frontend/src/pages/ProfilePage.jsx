import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, XCircle, Loader2, Trash2, RefreshCw } from 'lucide-react';
import DashboardHeader from '../components/DashboardHeader';
import { authAPI } from '../services/api';
import useAuthStore from '../store/authStore';

export default function ProfilePage() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [files, setFiles] = useState([]);
  const [existingPhotos, setExistingPhotos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingPhotos, setLoadingPhotos] = useState(true);
  const [scanLoading, setScanLoading] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const fetchExistingPhotos = useCallback(async () => {
    try {
      console.log('[ProfilePage] Fetching existing reference photos...');
      setLoadingPhotos(true);
      const photos = await authAPI.getMyReferencePhotos();
      console.log('[ProfilePage] Successfully fetched photos:', photos);
      console.log('[ProfilePage] Photo count:', photos?.length || 0);
      setExistingPhotos(photos || []);
      if (photos && photos.length > 0) {
        setError(null); // Clear any previous errors
      }
    } catch (err) {
      console.error('[ProfilePage] Error fetching photos:', err);
      console.error('[ProfilePage] Error details:', err.message, err.response?.data);
      setError("Could not load your existing reference photos. Please try refreshing the page.");
      setExistingPhotos([]);
    } finally {
      setLoadingPhotos(false);
    }
  }, []);

  useEffect(() => {
    console.log('[ProfilePage] Component mounted, fetching photos');
    fetchExistingPhotos();
  }, [fetchExistingPhotos]);

  const onDrop = useCallback((acceptedFiles) => {
    const newFiles = acceptedFiles.map(file => Object.assign(file, {
      preview: URL.createObjectURL(file)
    }));
    setFiles(prevFiles => [...prevFiles, ...newFiles].slice(0, 10));
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
    setSuccess(null);
    try {
      const response = await authAPI.uploadReferencePhotos(files);
      setSuccess(response.message);
      setFiles([]);
      // Refresh the list of existing photos after upload
      fetchExistingPhotos();
    } catch (err) {
      setError('Upload failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePhoto = async (photoId) => {
    if (!window.confirm('Are you sure you want to delete this reference photo? This action cannot be undone.')) {
      return;
    }

    setDeletingId(photoId);
    setError(null);
    setSuccess(null);

    try {
      await authAPI.deleteReferencePhoto(photoId);
      setSuccess('Photo deleted successfully');
      fetchExistingPhotos();
    } catch (err) {
      setError('Failed to delete photo. Please try again.');
    } finally {
      setDeletingId(null);
    }
  };

  const handleTriggerScan = async () => {
    setScanLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await authAPI.triggerGalleryScan();
      setSuccess(response.message || 'Gallery scan started! Check your galleries in a few moments to see matched photos.');
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Failed to trigger gallery scan. Please try again.';
      setError(errorMessage);
    } finally {
      setScanLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-primary-50">
      <DashboardHeader />
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-5xl font-extrabold text-gray-900">Your Profile</h1>
            <p className="mt-2 text-xl text-gray-600">Upload reference photos to help us find you in galleries.</p>
          </div>

          {/* Loading State */}
          {loadingPhotos && (
            <div className="card mb-8 text-center py-12">
              <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary-500 mb-4" />
              <p className="text-gray-600">Loading your reference photos...</p>
            </div>
          )}

          {/* Error State */}
          {error && !loadingPhotos && (
            <div className="card mb-8 bg-red-50 border-2 border-red-200">
              <div className="flex items-start gap-4">
                <div className="text-red-600 font-bold text-lg">⚠️</div>
                <div>
                  <h3 className="font-bold text-red-800 mb-2">Error Loading Photos</h3>
                  <p className="text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Existing Photos Section */}
          {existingPhotos.length > 0 && !loadingPhotos && (
            <div className="card mb-8">
              <h2 className="text-2xl font-bold mb-4">Your Current Reference Photos ({existingPhotos.length})</h2>
              <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-4">
                {existingPhotos.map((photo) => (
                  <div key={photo.id} className="relative group aspect-square">
                    <img src={photo.url} alt={`Reference photo ${photo.id}`} className="w-full h-full object-cover rounded-xl shadow-md" />
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center rounded-xl">
                      <button
                        onClick={() => handleDeletePhoto(photo.id)}
                        disabled={deletingId === photo.id}
                        className="bg-red-600 hover:bg-red-700 text-white p-2 rounded-lg transition-colors disabled:opacity-50"
                        title="Delete photo"
                      >
                        {deletingId === photo.id ? (
                          <Loader2 className="w-6 h-6 animate-spin" />
                        ) : (
                          <Trash2 className="w-6 h-6" />
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Manual Gallery Scan Section */}
          {existingPhotos.length > 0 && !loadingPhotos && (
            <div className="card mb-8 bg-gradient-to-r from-primary-50 to-primary-100 border-2 border-primary-200">
              <div className="flex flex-col md:flex-row items-center gap-6">
                <div className="flex-shrink-0">
                  <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center">
                    <RefreshCw className="w-8 h-8 text-primary-600" />
                  </div>
                </div>
                <div className="flex-grow text-center md:text-left">
                  <h3 className="text-xl font-bold text-gray-900 mb-2">Find Your Photos in Galleries</h3>
                  <p className="text-gray-600 mb-2">
                    Scan all existing galleries to find photos with your face. Use this if you uploaded galleries before adding reference photos.
                  </p>
                  <p className="text-sm text-gray-500">
                    This will search through all galleries and match photos containing your face based on your reference photos.
                  </p>
                </div>
                <div className="flex-shrink-0">
                  <button
                    onClick={handleTriggerScan}
                    disabled={scanLoading}
                    className="btn-primary px-6 py-3 text-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                  >
                    {scanLoading ? (
                      <>
                        <Loader2 className="animate-spin inline-block w-5 h-5 mr-2" />
                        Scanning...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="inline-block w-5 h-5 mr-2" />
                        Scan Galleries
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="card">
             <h2 className="text-2xl font-bold mb-4 text-center">Upload New Photos</h2>
            <div {...getRootProps()} className={`relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${isDragActive ? 'border-primary-600 bg-primary-50' : 'border-gray-300 hover:border-primary-500'}`}>
              <input {...getInputProps()} />
              <div className="flex flex-col items-center justify-center">
                <UploadCloud className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                <p className="font-bold text-gray-600">Drag & drop your selfies here</p>
                <p className="text-gray-500 text-sm mt-1">or click to browse (up to 10 photos)</p>
              </div>
            </div>
            
            {error && <p className="text-red-500 mt-4 text-center">{error}</p>}
            {success && <p className="text-green-500 mt-4 text-center">{success}</p>}

            {/* Preview for new photos */}
            {files.length > 0 && (
              <div className="mt-8">
                <h3 className="text-xl font-bold mb-4">New Photos to Upload:</h3>
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-4">
                  {files.map((file, index) => (
                    <div key={index} className="relative group aspect-square">
                      <img src={file.preview} alt={file.name} className="w-full h-full object-cover rounded-xl shadow-md" onLoad={() => URL.revokeObjectURL(file.preview)} />
                      <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <button onClick={() => removeFile(file)} className="text-white"><XCircle className="w-8 h-8" /></button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-8 text-center">
              <button onClick={handleSubmit} disabled={loading || files.length === 0} className="btn-primary px-8 py-3 text-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed">
                {loading ? <Loader2 className="animate-spin inline-block w-6 h-6 mr-2" /> : null}
                {loading ? `Uploading ${files.length}...` : `Upload ${files.length} New Photo(s)`}
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}