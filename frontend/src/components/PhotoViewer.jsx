import { useEffect, useCallback } from 'react';
import { X, ChevronLeft, ChevronRight, Trash2, Loader2, Download } from 'lucide-react';
import { downloadPhoto } from '../utils/downloadUtils';

export default function PhotoViewer({
  photos,
  currentIndex,
  onClose,
  onNavigate,
  onDelete,
  deletingId,
  canDelete = false
}) {
  const currentPhoto = photos[currentIndex];
  const hasPrevious = currentIndex > 0;
  const hasNext = currentIndex < photos.length - 1;

  const handlePrevious = useCallback(() => {
    if (hasPrevious) {
      onNavigate(currentIndex - 1);
    }
  }, [hasPrevious, currentIndex, onNavigate]);

  const handleNext = useCallback(() => {
    if (hasNext) {
      onNavigate(currentIndex + 1);
    }
  }, [hasNext, currentIndex, onNavigate]);

  const handleKeyDown = useCallback((e) => {
    switch (e.key) {
      case 'Escape':
        onClose();
        break;
      case 'ArrowLeft':
        handlePrevious();
        break;
      case 'ArrowRight':
        handleNext();
        break;
      default:
        break;
    }
  }, [onClose, handlePrevious, handleNext]);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    // Prevent body scroll when viewer is open
    document.body.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [handleKeyDown]);

  const handleDelete = () => {
    if (currentPhoto && onDelete) {
      onDelete(currentPhoto.id);
    }
  };

  const handleDownload = () => {
    if (currentPhoto) {
      downloadPhoto(currentPhoto.url, currentPhoto.id, currentPhoto.tagged_people);
    }
  };

  if (!currentPhoto) return null;

  return (
    <div className="fixed inset-0 bg-black/95 z-50 flex items-center justify-center">
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 left-4 text-white hover:text-gray-300 transition-colors p-2 rounded-lg bg-black/50 hover:bg-black/70"
        aria-label="Close viewer"
      >
        <X className="w-8 h-8" />
      </button>

      {/* Download and Delete buttons - top right */}
      <div className="absolute top-4 right-4 flex gap-2">
        <button
          onClick={handleDownload}
          className="text-white hover:text-blue-400 transition-colors p-2 rounded-lg bg-black/50 hover:bg-blue-600/70"
          aria-label="Download photo"
        >
          <Download className="w-8 h-8" />
        </button>

        {canDelete && (
          <button
            onClick={handleDelete}
            disabled={deletingId === currentPhoto.id}
            className="text-white hover:text-red-400 transition-colors p-2 rounded-lg bg-black/50 hover:bg-red-600/70 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Delete photo"
          >
            {deletingId === currentPhoto.id ? (
              <Loader2 className="w-8 h-8 animate-spin" />
            ) : (
              <Trash2 className="w-8 h-8" />
            )}
          </button>
        )}
      </div>

      {/* Photo counter */}
      <div className="absolute top-4 left-1/2 transform -translate-x-1/2 text-white bg-black/50 px-4 py-2 rounded-lg">
        <span className="font-semibold">{currentIndex + 1} / {photos.length}</span>
      </div>

      {/* Previous button */}
      {hasPrevious && (
        <button
          onClick={handlePrevious}
          className="absolute left-4 top-1/2 transform -translate-y-1/2 text-white hover:text-gray-300 transition-colors p-2 rounded-lg bg-black/50 hover:bg-black/70"
          aria-label="Previous photo"
        >
          <ChevronLeft className="w-10 h-10" />
        </button>
      )}

      {/* Next button */}
      {hasNext && (
        <button
          onClick={handleNext}
          className="absolute right-4 top-1/2 transform -translate-y-1/2 text-white hover:text-gray-300 transition-colors p-2 rounded-lg bg-black/50 hover:bg-black/70"
          aria-label="Next photo"
        >
          <ChevronRight className="w-10 h-10" />
        </button>
      )}

      {/* Main photo with tagged people */}
      <div className="max-w-7xl flex flex-col items-center justify-center px-20">
        <img
          src={currentPhoto.url}
          alt={`Photo ${currentPhoto.id}`}
          className="max-w-full max-h-[70vh] object-contain rounded-lg shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        />

        {/* Tagged People Overlay */}
        {currentPhoto.tagged_people && currentPhoto.tagged_people.length > 0 && (
          <div className="mt-4 bg-black/80 text-white px-6 py-4 rounded-lg max-w-2xl">
            <div className="flex flex-wrap gap-3">
              {currentPhoto.tagged_people.map((person, idx) => (
                <div
                  key={idx}
                  className="bg-blue-600/90 hover:bg-blue-700 px-4 py-2 rounded-full text-sm transition-colors"
                >
                  <span className="font-medium">{person.person_name}</span>
                  {person.linkedin_profile && (
                    <a
                      href={person.linkedin_profile}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs ml-2 opacity-90 hover:opacity-100 underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      LinkedIn
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Click backdrop to close */}
      <div
        className="absolute inset-0 -z-10"
        onClick={onClose}
        aria-label="Close viewer"
      />
    </div>
  );
}
