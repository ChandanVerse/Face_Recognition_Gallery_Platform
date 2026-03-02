import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';
import useSessionStore from '../store/sessionStore';

export default function Header() {
  const { sessionId, galleryToken } = useSessionStore();

  return (
    <header className="bg-primary-50/80 backdrop-blur-lg sticky top-0 z-50">
      <nav className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <img src="/virsa-logo.jpeg" alt="Virsa FaceFinder Logo" className="w-8 h-8 rounded-full object-cover" />
            <span className="text-2xl font-bold text-gray-800">Virsa FaceFinder</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/" className="text-gray-600 hover:text-primary-600 font-semibold flex items-center gap-1">
              <Home className="w-5 h-5" />
              <span className="hidden sm:inline">Home</span>
            </Link>
            {sessionId && (
              <Link
                to={`/dashboard`}
                className="text-gray-600 hover:text-primary-600 font-semibold"
              >
                Dashboard
              </Link>
            )}
            {galleryToken && sessionId && (
              <Link
                to={`/gallery/${galleryToken}?session=${sessionId}`}
                className="btn-primary text-base px-5 py-2"
              >
                View Gallery
              </Link>
            )}
          </div>
        </div>
      </nav>
    </header>
  );
}
