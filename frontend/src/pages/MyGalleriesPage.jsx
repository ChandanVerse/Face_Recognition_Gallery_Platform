import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { galleryAPI } from '../services/api';
import useAuthStore from '../store/authStore';
import DashboardHeader from '../components/DashboardHeader';
import { Image, Clock, CheckCircle, Loader2, Plus } from 'lucide-react';

export default function MyGalleriesPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuthStore();
  const [galleries, setGalleries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    const fetchMyGalleries = async () => {
      try {
        setLoading(true);
        const userGalleries = await galleryAPI.getMyGalleries();
        setGalleries(userGalleries);
      } catch (err) {
        setError('Failed to fetch your galleries.');
        console.error('Error fetching galleries:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchMyGalleries();
  }, [isAuthenticated, navigate]);

  return (
    <div className="min-h-screen bg-primary-50">
      <DashboardHeader />
      <div className="container mx-auto px-4 py-12">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-5xl font-extrabold text-gray-900">My Galleries</h1>
          <Link
            to="/upload"
            className="btn-primary flex items-center gap-2 px-6 py-3 shadow-lg hover:shadow-xl transition-shadow"
            title="Create new gallery"
          >
            <Plus className="w-5 h-5" />
            <span className="font-semibold">New Gallery</span>
          </Link>
        </div>
        {loading && <div className="text-center"><Loader2 className="w-8 h-8 animate-spin mx-auto text-primary-600" /></div>}
        {error && <p className="text-red-500 text-center">{error}</p>}
        
        {!loading && galleries.length === 0 && (
          <div className="text-center py-16">
            <h2 className="text-2xl font-bold">You haven't created any galleries yet.</h2>
            <p className="text-gray-600 mt-2">
              <Link to="/upload" className="text-primary-600 font-bold hover:underline">Upload some photos</Link> to get started!
            </p>
          </div>
        )}

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {galleries.map(gallery => (
            <Link to={`/gallery/${gallery.share_token}`} key={gallery.id} className="card block hover:shadow-xl transition-shadow duration-300">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xl font-bold text-gray-800 truncate">{gallery.name || 'Untitled Gallery'}</h2>
                <div className={`flex items-center gap-2 text-sm font-semibold ${gallery.processing_status === 'completed' ? 'text-green-600' : 'text-blue-600'}`}>
                  {gallery.processing_status === 'completed' ? <CheckCircle className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
                  <span>{gallery.processing_status}</span>
                </div>
              </div>
              <div className="text-gray-500 text-sm space-y-1">
                <p className="flex items-center"><Image className="w-4 h-4 inline-block mr-2" />{gallery.total_photos} photos</p>
                <p>Created on: {new Date(gallery.created_at).toLocaleDateString()}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}