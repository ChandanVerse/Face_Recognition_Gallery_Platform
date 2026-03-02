import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AlertCircle, Sparkles } from 'lucide-react';
import useAuthStore from '../store/authStore';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, loading, error, clearError, user } = useAuthStore();

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  useEffect(() => {
    // After successful login, redirect to My Galleries
    if (user) {
      navigate('/my-galleries');
    }
  }, [user, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();

    try {
      await login({
        email: formData.email,
        password: formData.password
      });
      // Navigation handled by useEffect above
    } catch (err) {
      // Error is handled by the auth store
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen bg-primary-50 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-block bg-primary-100 p-4 rounded-full mb-4">
             <Sparkles className="w-10 h-10 text-primary-600" />
          </div>
          <h1 className="text-4xl font-extrabold text-gray-900">Welcome Back!</h1>
          <p className="text-gray-600 mt-2">Let's find some photos of you.</p>
        </div>

        <div className="card">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <p className="text-red-800 text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="email" className="block text-sm font-bold text-gray-700 mb-2">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="input"
                placeholder="you@example.com"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-bold text-gray-700 mb-2">
                Password
              </label>
              <input
                type="password"
                id="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="input"
                placeholder="••••••••"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary text-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing In...' : 'Sign In'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-gray-600 text-sm">
              Don't have an account?{' '}
              <Link to="/register" className="text-primary-600 font-bold hover:underline">
                Sign up
              </Link>
            </p>
          </div>
        </div>
        <div className="mt-6 text-center">
          <Link to="/" className="text-gray-500 text-sm hover:underline">
            ← Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}