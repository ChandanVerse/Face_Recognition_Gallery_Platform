import { useEffect, useState, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { galleryAPI } from '../services/api';
import useAuthStore from '../store/authStore';
import DashboardHeader from '../components/DashboardHeader';
import PhotoViewer from '../components/PhotoViewer';
import Pagination from '../components/Pagination';
import { Image, Users, CheckCircle, Clock, Loader2, PartyPopper, Trash2, Plus, Tag, Linkedin, Download } from 'lucide-react';
import { downloadPhoto } from '../utils/downloadUtils';

export default function GalleryPage() {
  const { shareToken } = useParams();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuthStore();

  const [gallery, setGallery] = useState(null);
  const [photos, setPhotos] = useState([]);
  const [view, setView] = useState('all');
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState(null);
  const [deleteError, setDeleteError] = useState(null);
  const [deleteSuccess, setDeleteSuccess] = useState(null);
  const [status, setStatus] = useState(null);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [viewerIndex, setViewerIndex] = useState(0);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalPhotos, setTotalPhotos] = useState(0);
  const [pageSize] = useState(50);

  // Tagging state
  const [taggingInProgress, setTaggingInProgress] = useState(false);
  const [tagSuccess, setTagSuccess] = useState(null);
  const [tagError, setTagError] = useState(null);

  const fetchPhotos = useCallback(async (currentView, page = 1) => {
    setLoading(true);
    console.log(`[fetchPhotos] Fetching view=${currentView}, page=${page}`);
    try {
      const response = (currentView === 'my' && isAuthenticated)
        ? await galleryAPI.getMyPhotos(shareToken, page, pageSize)
        : await galleryAPI.getAllPhotos(shareToken, page, pageSize);

      console.log(`[fetchPhotos] Response received:`, response.pagination);

      // Extract photos and pagination from response
      setPhotos(response.photos || []);
      setTotalPages(response.pagination?.total_pages || 1);
      setTotalPhotos(response.pagination?.total_photos || 0);
      // Only update currentPage if it's different to avoid unnecessary re-renders
      const receivedPage = response.pagination?.current_page || 1;
      console.log(`[fetchPhotos] Setting currentPage to ${receivedPage}`);
      setCurrentPage(receivedPage);
    } catch (err) {
      console.error('[fetchPhotos] Error:', err);
      setError('Could not load photos.');
    } finally {
      setLoading(false);
    }
  }, [shareToken, isAuthenticated, pageSize]);

  const fetchGalleryDetails = useCallback(async () => {
    try {
      const galleryData = await galleryAPI.getByToken(shareToken);
      setGallery(galleryData);
      return galleryData;
    } catch (err) {
      setError('Could not load gallery. The link may be invalid or expired.');
      setLoading(false);
      return null;
    }
  }, [shareToken]);

  useEffect(() => {
    const initialLoad = async () => {
      setLoading(true);
      await fetchGalleryDetails();
      await fetchPhotos(view, 1); // Always start at page 1 when view changes
      setLoading(false);
    };
    initialLoad();
    setCurrentPage(1); // Reset to page 1 when view changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shareToken, view, isAuthenticated]);

  useEffect(() => {
    if (gallery && gallery.processing_status !== 'completed') {
      const interval = setInterval(async () => {
        try {
          const statusData = await galleryAPI.getStatus(shareToken);
          setStatus(statusData);
          if (statusData.processing_status === 'completed') {
            clearInterval(interval);
            // Refetch photos to get the latest data after processing is complete
            fetchPhotos(view, currentPage);
          }
        } catch (err) {
          console.error('Failed to fetch status');
        }
      }, 5000);

      return () => clearInterval(interval);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gallery, shareToken, view, currentPage]);

  const handleDeletePhoto = async (photoId) => {
    if (!window.confirm('Are you sure you want to delete this photo? This will remove it from the gallery permanently.')) {
      return;
    }

    setDeletingId(photoId);
    setDeleteError(null);
    setDeleteSuccess(null);

    try {
      await galleryAPI.deletePhoto(shareToken, photoId);
      setDeleteSuccess('Photo deleted successfully');

      // If viewer is open and we're deleting the current photo
      if (viewerOpen) {
        const newPhotos = photos.filter(p => p.id !== photoId);
        if (newPhotos.length === 0) {
          // No more photos, close viewer
          setViewerOpen(false);
        } else if (viewerIndex >= newPhotos.length) {
          // Current index is out of bounds, move to last photo
          setViewerIndex(newPhotos.length - 1);
        }
      }

      // Refresh photos after deletion
      fetchPhotos(view, currentPage);
      // Clear success message after 3 seconds
      setTimeout(() => setDeleteSuccess(null), 3000);
    } catch (err) {
      setDeleteError('Failed to delete photo. Please try again.');
      setTimeout(() => setDeleteError(null), 5000);
    } finally {
      setDeletingId(null);
    }
  };

  const handlePhotoClick = (index) => {
    setViewerIndex(index);
    setViewerOpen(true);
  };

  const handleCloseViewer = () => {
    setViewerOpen(false);
  };

  const handleNavigateViewer = (newIndex) => {
    setViewerIndex(newIndex);
  };

  // Check if current user is the gallery owner
  const isGalleryOwner = gallery && user && gallery.host_user_id === user.id;

  const handleAddMorePhotos = () => {
    navigate(`/upload-more/${shareToken}`);
  };

  const handleTagKnownPeople = async () => {
    setTaggingInProgress(true);
    setTagError(null);
    setTagSuccess(null);

    try {
      const response = await galleryAPI.tagKnownPeople(shareToken);
      setTagSuccess('Tagging known people started! Names will appear shortly.');

      // Clear success message after 5 seconds
      setTimeout(() => setTagSuccess(null), 5000);

      // Refetch photos after a delay to show updated tags
      setTimeout(() => {
        fetchPhotos(view, currentPage);
      }, 3000);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Failed to tag known people. Please try again.';
      setTagError(errorMessage);
      setTimeout(() => setTagError(null), 5000);
    } finally {
      setTaggingInProgress(false);
    }
  };

  const handlePageChange = (newPage) => {
    console.log(`[handlePageChange] Changing to page ${newPage}`);
    setCurrentPage(newPage);
    fetchPhotos(view, newPage);
    // Scroll to top when page changes
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-primary-50">
      <DashboardHeader />
      <div className="container mx-auto px-4 py-12">
        {loading && photos.length === 0 && <div className="text-center py-20"><Loader2 className="w-16 h-16 animate-spin mx-auto text-primary-600" /></div>}
        {error && <div className="text-center text-red-500 text-lg py-20">{error}</div>}
        {deleteError && (
          <div className="max-w-md mx-auto mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {deleteError}
          </div>
        )}
        {deleteSuccess && (
          <div className="max-w-md mx-auto mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded-lg">
            {deleteSuccess}
          </div>
        )}
        {tagError && (
          <div className="max-w-md mx-auto mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {tagError}
          </div>
        )}
        {tagSuccess && (
          <div className="max-w-md mx-auto mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded-lg">
            {tagSuccess}
          </div>
        )}

        {gallery && (
          <>
            <div className="text-center mb-12">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1"></div>
                <h1 className="text-5xl font-extrabold text-gray-900 flex-1 text-center">{gallery.name || 'Event Gallery'}</h1>
                <div className="flex-1 flex justify-end gap-2">
                  {isGalleryOwner && (
                    <>
                      <button
                        onClick={handleAddMorePhotos}
                        className="btn-primary flex items-center gap-2 px-4 py-2 shadow-lg hover:shadow-xl transition-shadow"
                        title="Add more photos to this gallery"
                      >
                        <Plus className="w-5 h-5" />
                        <span className="font-semibold">Add Photos</span>
                      </button>
                      <button
                        onClick={handleTagKnownPeople}
                        disabled={taggingInProgress}
                        className="btn-secondary flex items-center gap-2 px-4 py-2 shadow-lg hover:shadow-xl transition-shadow disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Tag known people in gallery photos"
                      >
                        {taggingInProgress ? (
                          <>
                            <Loader2 className="w-5 h-5 animate-spin" />
                            <span className="font-semibold">Tagging...</span>
                          </>
                        ) : (
                          <>
                            <Tag className="w-5 h-5" />
                            <span className="font-semibold">Tag Known People</span>
                          </>
                        )}
                      </button>
                    </>
                  )}
                </div>
              </div>
              <div className="mt-4 inline-flex items-center gap-3 p-2 px-4 rounded-full bg-white shadow-md">
                {gallery.processing_status === 'completed' || status?.processing_status === 'completed' ? (
                  <><CheckCircle className="w-5 h-5 text-green-500" /> <span className="text-green-700 font-semibold">Ready!</span></>
                ) : (
                  <><Clock className="w-5 h-5 text-blue-500" /> <span className="text-blue-700 font-semibold">Processing... ({status?.progress_percentage || 0}%)</span></>
                )}
              </div>
            </div>
            
            <div className="flex justify-center items-center gap-2 mb-10 bg-primary-100 p-2 rounded-full max-w-sm mx-auto">
              <button 
                onClick={() => setView('all')} 
                className={`w-full text-center px-4 py-2 rounded-full font-bold transition-colors ${view === 'all' ? 'bg-white text-primary-700 shadow' : 'text-gray-600'}`}
              >
                <Image className="w-5 h-5 mr-2 inline-block" /> All Photos
              </button>
              {isAuthenticated ? (
                <button 
                  onClick={() => setView('my')} 
                  className={`w-full text-center px-4 py-2 rounded-full font-bold transition-colors ${view === 'my' ? 'bg-white text-primary-700 shadow' : 'text-gray-600'}`}
                >
                  <Users className="w-5 h-5 mr-2 inline-block" /> My Photos
                </button>
              ) : (
                <Link to="/login" className="w-full text-center px-4 py-2 rounded-full font-bold bg-white text-primary-700 shadow">
                  <Users className="w-5 h-5 mr-2 inline-block" /> Login to Find Yours
                </Link>
              )}
            </div>

            {/* Photo Grid with Loading Overlay */}
            <div className="relative">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {photos.map((photo, index) => (
                  <div key={photo.id} className="flex flex-col">
                    <div
                      className="group relative aspect-square cursor-pointer"
                      onClick={() => handlePhotoClick(index)}
                    >
                      <img
                        src={photo.url}
                        alt={`Photo ${photo.id}`}
                        className="w-full h-full object-cover rounded-xl shadow-md transition-all transform group-hover:scale-105 group-hover:brightness-75"
                      />
                      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all rounded-xl flex items-center justify-center">
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                          <div className="bg-white/90 rounded-full p-3 shadow-lg">
                            <Image className="w-6 h-6 text-gray-800" />
                          </div>
                        </div>
                      </div>

                      {/* Download button - bottom right corner */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          downloadPhoto(photo.url, photo.id, photo.tagged_people);
                        }}
                        className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-lg shadow-lg"
                        aria-label="Download photo"
                      >
                        <Download className="w-5 h-5" />
                      </button>
                    </div>

                    {/* Tagged People Under Photo */}
                    {photo.tagged_people && photo.tagged_people.length > 0 && (
                      <div className="mt-3 space-y-2 flex flex-col items-center">
                        {photo.tagged_people.map((person, idx) => (
                          <div key={idx} className="text-xs flex items-center justify-center gap-2">
                            <span className="font-medium text-gray-700 truncate max-w-xs">
                              {person.person_name}
                            </span>
                            {person.linkedin_profile && (
                              <a
                                href={person.linkedin_profile}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800 transition-colors flex-shrink-0"
                                title={person.linkedin_profile}
                                onClick={(e) => e.stopPropagation()}
                              >
                                <Linkedin className="w-4 h-4" />
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Loading Overlay - Shows when fetching new photos while grid has existing photos */}
              {loading && photos.length > 0 && (
                <div className="absolute inset-0 bg-white/60 backdrop-blur-sm rounded-xl flex flex-col items-center justify-center z-40">
                  <Loader2 className="w-12 h-12 animate-spin text-primary-500 mb-4" />
                  <p className="text-gray-700 font-semibold">Loading photos...</p>
                </div>
              )}
            </div>

            {/* Pagination */}
            <Pagination
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={handlePageChange}
              totalItems={totalPhotos}
              pageSize={pageSize}
            />

            {/* Photo Viewer */}
            {viewerOpen && (
              <PhotoViewer
                photos={photos}
                currentIndex={viewerIndex}
                onClose={handleCloseViewer}
                onNavigate={handleNavigateViewer}
                onDelete={handleDeletePhoto}
                deletingId={deletingId}
                canDelete={isGalleryOwner}
              />
            )}

            {view === 'my' && isAuthenticated && photos.length === 0 && !loading && (
                <div className="text-center py-24">
                    <div className="inline-block bg-yellow-100 p-4 rounded-full mb-4">
                        <PartyPopper className="w-10 h-10 text-yellow-600" />
                    </div>
                    <h2 className="text-2xl font-bold">No photos of you found... yet!</h2>
                    <p className="text-gray-600 mt-2 max-w-lg mx-auto">
                        Make sure you have uploaded reference photos to your profile. If you just did, our AI might still be looking for you. Check back in a few minutes!
                    </p>
                </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}