import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import UploadPage from './pages/UploadPage';
import UploadMorePage from './pages/UploadMorePage';
import GalleryPage from './pages/GalleryPage';
import MyGalleriesPage from './pages/MyGalleriesPage';
import ProfilePage from './pages/ProfilePage';
import useAuthStore from './store/authStore';

function App() {
  const initialize = useAuthStore((state) => state.initialize);

  useEffect(() => {
    initialize();
  }, [initialize]);

  return (
    <div className="min-h-screen">
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/upload-more/:galleryToken" element={<UploadMorePage />} />
        <Route path="/gallery/:shareToken" element={<GalleryPage />} />
        <Route path="/my-galleries" element={<MyGalleriesPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Routes>
    </div>
  );
}

export default App;