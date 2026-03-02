import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate, useParams } from 'react-router-dom';
import { UploadCloud, XCircle, Loader2 } from 'lucide-react';
import Header from '../components/Header';
import axios from 'axios';

const API_BASE = 'https://recommendations.vosmos.events:7006';

export default function ReferenceUploadPage() {
  const { sessionId, galleryToken } = useParams();
  const navigate = useNavigate();

  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

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

  const [isWaitingForProcessing, setIsWaitingForProcessing] = useState(false);

  const handleSubmit = async () => {
    if (files.length === 0) {
      setError('Please select at least one photo to upload.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const formData = new FormData();
      formData.append('session_id', sessionId);
      files.forEach(file => {
        formData.append('photos', file);
      });

      const response = await axios.post(
        `${API_BASE}/api/references/upload`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      );

      setSuccess(response.data.message);
      setFiles([]);
      setLoading(false);
      setIsWaitingForProcessing(true);

      // Poll for processing status
      const pollStatus = async () => {
        try {
          const statusResponse = await axios.get(`${API_BASE}/api/references/${sessionId}/status`);
          if (statusResponse.data.processing_status === 'completed') {
            // Trigger face matching
            const matchForm = new FormData();
            matchForm.append('gallery_token', galleryToken);
            await axios.post(
              `${API_BASE}/api/references/${sessionId}/trigger-matching`,
              matchForm
            );
            // Navigate to gallery
            navigate(`/gallery/${galleryToken}?session=${sessionId}`);
          } else {
            // Wait and poll again
            setTimeout(pollStatus, 2000);
          }
        } catch (err) {
          console.error('Failed to get status or trigger matching:', err);
          setError('Failed to start face matching. Please try again.');
          setIsWaitingForProcessing(false);
        }
      };

      // Start polling
      setTimeout(pollStatus, 2000);

    } catch (err) {
      console.error('Upload error:', err);
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-primary-50">
      <Header />
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-8">
            <h1 className="text-5xl font-extrabold text-gray-900">
              Step 2: Upload Your Photos
            </h1>
            <p className="mt-2 text-xl text-gray-600">
              Now, upload a few clear photos of yourself. These will be used to find your photos in the gallery.
            </p>
            <div className="mt-4 flex justify-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gray-300"></div>
              <div className="w-3 h-3 rounded-full bg-primary-600"></div>
            </div>
          </div>

          <div className="card text-center">
            <div {...getRootProps()} className={`relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${isDragActive ? 'border-primary-600 bg-primary-50' : 'border-gray-300 hover:border-primary-500'}`}>
              <input {...getInputProps()} />
              <div className="flex flex-col items-center justify-center">
                <UploadCloud className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                <p className="font-bold text-gray-600">Drag & drop your selfies here</p>
                <p className="text-gray-500 text-sm mt-1">or click to browse (up to 10 photos)</p>
              </div>
            </div>

            {error && <p className="text-red-500 mt-4">{error}</p>}
            {success && <p className="text-green-500 mt-4">{success}</p>}

            {files.length > 0 && (
              <div className="mt-8">
                <h3 className="text-xl font-bold mb-4">Selected Photos ({files.length})</h3>
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-4">
                  {files.map((file, index) => (
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
              </div>
            )}

            {isWaitingForProcessing && (
              <div className="mt-8 text-center">
                <Loader2 className="animate-spin inline-block w-8 h-8 mr-2 text-primary-600" />
                <p className="text-xl text-gray-600">Analyzing your photos and finding matches...</p>
                <p className="text-sm text-gray-500">This may take a moment. You will be redirected automatically.</p>
              </div>
            )}

            <div className="mt-8 text-center">
              <button
                onClick={handleSubmit}
                disabled={loading || files.length === 0}
                className="btn-primary px-8 py-3 text-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin inline-block w-6 h-6 mr-2" />
                    Uploading {files.length} photo{files.length !== 1 ? 's' : ''}...
                  </>
                ) : (
                  `Upload ${files.length} Photo${files.length !== 1 ? 's' : ''} & Find My Photos`
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
