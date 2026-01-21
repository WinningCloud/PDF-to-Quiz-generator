import { Link, Outlet, useLocation } from 'react-router-dom';
import { LayoutDashboard, FileUp, ClipboardList, BarChart3, LogOut, ShieldCheck } from 'lucide-react';
import { useContext } from 'react';
import { AuthContext } from '../../context/AuthContext';

export default function AdminLayout() {
  const { logout } = useContext(AuthContext);
  const location = useLocation();

  const menu = [
    { name: 'Overview', path: '/admin', icon: LayoutDashboard },
    { name: 'PDF Library', path: '/admin/pdfs', icon: FileUp },
    { name: 'Quiz Management', path: '/admin/quizzes', icon: ClipboardList },
  ];

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col fixed h-full">
        <div className="p-6 text-white font-bold text-2xl flex items-center gap-2">
          <ShieldCheck className="text-indigo-400 w-8 h-8" /> Admin Panel
        </div>
        <nav className="flex-1 px-4 space-y-1 mt-4">
          {menu.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition font-medium ${
                location.pathname === item.path ? 'bg-indigo-600 text-white' : 'hover:bg-slate-800'
              }`}
            >
              <item.icon className="w-5 h-5" /> {item.name}
            </Link>
          ))}
        </nav>
        <button onClick={logout} className="m-4 flex items-center gap-3 px-4 py-3 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition">
          <LogOut className="w-5 h-5" /> Logout
        </button>
      </aside>
      <main className="flex-1 ml-64 p-10">
        <Outlet />
      </main>
    </div>
  );
}