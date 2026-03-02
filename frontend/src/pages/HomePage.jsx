import { Link } from 'react-router-dom';
import { Upload, Users, Search, Zap } from 'lucide-react';
import Header from '../components/Header';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-primary-50">
      <Header />

      {/* Hero Section */}
      <section className="container mx-auto px-6 py-24 text-center">
        <h1 className="text-5xl md:text-7xl font-extrabold text-gray-900 mb-6 leading-tight">
          Discover Your Photos,
          <span className="text-primary-500"> Instantly</span>
        </h1>
        <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
          Stop scrolling endlessly. Upload your event photos, and let our friendly AI find every picture you're in!
        </p>
        <div className="flex gap-4 justify-center">
          <Link to="/upload" className="btn-primary text-lg">
            Create a Gallery
          </Link>
          <Link to="/register" className="btn-secondary text-lg">
            Find My Photos
          </Link>
        </div>
      </section>

      {/* How It Works */}
      <section className="container mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-extrabold text-gray-900">It's as easy as...</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-10">
          <FeatureCard
            icon={<Upload className="w-12 h-12 text-white" />}
            title="1. Upload Photos"
            description="Hosts create a shared gallery by uploading all the photos from an event."
            bgColor="bg-secondary-500"
          />
          <FeatureCard
            icon={<Users className="w-12 h-12 text-white" />}
            title="2. Create Your Profile"
            description="You and your friends sign up and upload a few selfies so our AI can recognize you."
            bgColor="bg-primary-500"
          />
          <FeatureCard
            icon={<Search className="w-12 h-12 text-white" />}
            title="3. Find Your Moments"
            description="Instantly see every photo you appear in. It's like magic!"
            bgColor="bg-yellow-500"
          />
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8">
        <div className="container mx-auto px-6 text-center">
          <p className="text-gray-500">&copy; 2024 Virsa FaceFinder. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description, bgColor }) {
  return (
    <div className="card text-center transform hover:-translate-y-2 transition-transform duration-300">
      <div className={`mx-auto w-24 h-24 rounded-full flex items-center justify-center mb-6 ${bgColor}`}>
        {icon}
      </div>
      <h3 className="text-2xl font-bold mb-3">{title}</h3>
      <p className="text-gray-600">{description}</p>
    </div>
  );
}