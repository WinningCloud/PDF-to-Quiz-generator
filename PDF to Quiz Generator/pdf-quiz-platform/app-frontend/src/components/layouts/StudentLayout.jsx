import { Link, useNavigate, useLocation, Outlet } from 'react-router-dom';
import { LayoutDashboard, BookOpen, History, LogOut, User } from 'lucide-react';
import { useContext } from 'react';
import { AuthContext } from '../../context/AuthContext';

export default function StudentLayout() {
  const { user, logout } = useContext(AuthContext);
  const location = useLocation();
  const navigate = useNavigate(); // Added for redirection

  const menuItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Available Quizzes', path: '/quizzes', icon: BookOpen },
    { name: 'My History', path: '/history', icon: History },
  ];

  // Professional Logout Handler
 // Inside StudentLayout.jsx
const handleLogout = () => {
  if (window.confirm("Are you sure you want to log out?")) {
    logout(); 
    // No need for navigate('/') here because window.location.href 
    // inside logout() handles it more reliably.
  }
};

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col sticky top-0 h-screen">
        <div className="p-6 border-b border-slate-100 font-bold text-2xl text-indigo-600 flex items-center gap-2">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg shadow-lg shadow-indigo-100"></div>
          <span>QuizAI</span>
        </div>

        <nav className="flex-1 p-4 space-y-1 mt-4">
          {menuItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 font-medium ${
                location.pathname === item.path 
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-100' 
                  : 'text-slate-600 hover:bg-slate-50 hover:text-indigo-600'
              }`}
            >
              <item.icon className={`w-5 h-5 ${location.pathname === item.path ? 'text-white' : 'text-slate-400'}`} />
              {item.name}
            </Link>
          ))}
        </nav>

        {/* User Profile & Logout Section */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-3 px-4 py-3 mb-2 bg-white rounded-xl border border-slate-100 shadow-sm">
            <div className="w-9 h-9 rounded-full bg-indigo-100 flex items-center justify-center border border-indigo-200">
              <User className="w-5 h-5 text-indigo-600"/>
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-bold truncate text-slate-800">{user?.full_name || 'Student'}</div>
              <div className="text-[10px] text-slate-400 uppercase font-bold tracking-wider">Student Account</div>
            </div>
          </div>
          
          <button 
            onClick={handleLogout} 
            className="w-full flex items-center gap-3 px-4 py-3 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all duration-200 font-bold text-sm group"
          >
            <LogOut className="w-5 h-5 text-slate-400 group-hover:text-red-600 transition-colors" /> 
            Logout Session
          </button>
        </div>
      </aside>

      {/* Content Area */}
      <main className="flex-1 overflow-y-auto p-10">
        <div className="max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}