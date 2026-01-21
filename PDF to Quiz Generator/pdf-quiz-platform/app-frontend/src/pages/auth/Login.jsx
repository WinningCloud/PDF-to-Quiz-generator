import { useState, useContext } from 'react';
import { AuthContext } from '../../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import AuthLayout from '../../components/layouts/AuthLayout';
import { Loader2 } from 'lucide-react';

export default function Login() {
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [isBusy, setIsBusy] = useState(false);
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
  e.preventDefault();
  setIsBusy(true);
  setError('');

  const loginData = new URLSearchParams();
  loginData.append('username', formData.username);
  loginData.append('password', formData.password);

  try {
    // login() now returns the user object directly!
    const user = await login(loginData); 

    if (user.is_admin) {
      navigate('/admin');
    } else {
      navigate('/dashboard');
    }
  } catch (err) {
    console.error("Login Error:", err);
    setError(err.response?.data?.detail || 'Invalid username or password');
  } finally {
    setIsBusy(false); // Make sure this is false so button re-enables
  }
};
  return (
    <AuthLayout title="Welcome back" subtitle="Log in to access your quizzes">
      <form className="space-y-6" onSubmit={handleLogin}>
        {error && <div className="p-3 bg-red-50 text-red-600 border border-red-100 rounded-lg text-sm">{error}</div>}
        
        <div>
          <label className="block text-sm font-medium text-slate-700">Username</label>
          <input
            type="text" required
            className="mt-1 block w-full px-4 py-3 border border-slate-300 rounded-xl shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
            onChange={(e) => setFormData({...formData, username: e.target.value})}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700">Password</label>
          <input
            type="password" required
            className="mt-1 block w-full px-4 py-3 border border-slate-300 rounded-xl shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
            onChange={(e) => setFormData({...formData, password: e.target.value})}
          />
        </div>

        <button
          type="submit" disabled={isBusy}
          className="w-full flex justify-center py-3 px-4 border border-transparent rounded-xl shadow-sm text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none transition"
        >
          {isBusy ? <Loader2 className="animate-spin" /> : 'Sign In'}
        </button>

        <div className="text-center text-sm">
          <span className="text-slate-600">New here? </span>
          <Link to="/register" className="font-bold text-indigo-600 hover:text-indigo-500">Create an account</Link>
        </div>
      </form>
    </AuthLayout>
  );
}