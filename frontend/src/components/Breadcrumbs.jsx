import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

export default function Breadcrumbs() {
  const location = useLocation();
  const pathnames = location.pathname.split('/').filter(x => x);

  // Map route names to readable labels
  const routeLabels = {
    'dashboard': 'Dashboard',
    'profile': 'Profile',
    'upload': 'Upload Gallery',
    'my-galleries': 'My Galleries',
    'gallery': 'Gallery',
    'login': 'Login',
    'register': 'Register'
  };

  if (pathnames.length === 0) {
    return null; // Don't show breadcrumbs on home page
  }

  return (
    <nav className="flex items-center space-x-2 text-sm text-gray-600 mb-6">
      <Link to="/" className="hover:text-primary-600 transition-colors flex items-center gap-1">
        <Home className="w-4 h-4" />
        <span>Home</span>
      </Link>

      {pathnames.map((value, index) => {
        const to = `/${pathnames.slice(0, index + 1).join('/')}`;
        const isLast = index === pathnames.length - 1;
        const label = routeLabels[value] || value;

        return (
          <div key={to} className="flex items-center gap-2">
            <ChevronRight className="w-4 h-4 text-gray-400" />
            {isLast ? (
              <span className="text-gray-900 font-semibold">{label}</span>
            ) : (
              <Link to={to} className="hover:text-primary-600 transition-colors">
                {label}
              </Link>
            )}
          </div>
        );
      })}
    </nav>
  );
}
