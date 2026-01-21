import { Link } from 'react-router-dom';
import { BookOpen, LogIn } from 'lucide-react';

export default function Navbar() {
  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <Link to="/" className="flex items-center space-x-2 text-indigo-600 font-bold text-xl">
            <BookOpen className="w-8 h-8" />
            <span>QuizAI</span>
          </Link>
          <div className="flex items-center space-x-4">
            <Link to="/login" className="text-slate-600 hover:text-indigo-600 font-medium transition">
              Sign In
            </Link>
            <Link to="/register" className="bg-indigo-600 text-white px-5 py-2 rounded-lg font-medium hover:bg-indigo-700 transition shadow-sm">
              Get Started
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}