import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { UserPlus, AlertCircle, PartyPopper } from 'lucide-react';
import useAuthStore from '../store/authStore';
import Header from '../components/Header';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register, loading, error, clearError } = useAuthStore();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();
    try {
      await register(formData);
      // Redirect to My Galleries after registration
      navigate('/my-galleries');
    } catch (err) {
      // Error is handled by the auth store
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  return (
    <div className="min-h-screen bg-primary-50">
      <Header />
      <div className="container mx-auto flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-md">
           <div className="text-center mb-8">
            <div className="inline-block bg-secondary-100 p-4 rounded-full mb-4">
              <PartyPopper className="w-10 h-10 text-secondary-600" />
            </div>
            <h1 className="text-4xl font-extrabold text-gray-900">Create Your Account</h1>
            <p className="text-gray-600 mt-2">Join the fun and find your photos instantly!</p>
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
                <label htmlFor="name" className="block text-sm font-bold text-gray-700 mb-2">
                  Full Name
                </label>
                <input type="text" id="name" name="name" value={formData.name} onChange={handleChange} className="input" placeholder="Your Name" required />
              </div>
              <div>
                <label htmlFor="email" className="block text-sm font-bold text-gray-700 mb-2">
                  Email Address
                </label>
                <input type="email" id="email" name="email" value={formData.email} onChange={handleChange} className="input" placeholder="you@example.com" required />
              </div>
              <div>
                <label htmlFor="password" className="block text-sm font-bold text-gray-700 mb-2">
                  Password
                </label>
                <input type="password" id="password" name="password" value={formData.password} onChange={handleChange} className="input" placeholder="•••••••• (8+ characters)" required minLength="8" />
              </div>
              <button type="submit" disabled={loading} className="w-full btn-primary text-lg disabled:opacity-50 disabled:cursor-not-allowed">
                {loading ? 'Creating Account...' : 'Sign Up for Free'}
              </button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-gray-600 text-sm">
                Already have an account?{' '}
                <Link to="/login" className="text-primary-600 font-bold hover:underline">
                  Login here
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}