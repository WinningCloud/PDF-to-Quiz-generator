import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import AuthLayout from '../../components/layouts/AuthLayout';
import api from '../../api/axios';

export default function Register() {
  const [form, setForm] = useState({ username: '', email: '', password: '', full_name: '', is_admin: false });
  const navigate = useNavigate();

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      await api.post('/auth/register', form);
      navigate('/login');
    } catch (err) {
      alert(err.response?.data?.detail || "Registration failed");
    }
  };

  return (
    <AuthLayout title="Create account" subtitle="Join the smart learning platform">
      <form className="space-y-4" onSubmit={handleRegister}>
        <input 
          placeholder="Full Name" required className="w-full px-4 py-3 border border-slate-300 rounded-xl"
          onChange={(e) => setForm({...form, full_name: e.target.value})} 
        />
        <input 
          placeholder="Username" required className="w-full px-4 py-3 border border-slate-300 rounded-xl"
          onChange={(e) => setForm({...form, username: e.target.value})} 
        />
        <input 
          placeholder="Email" type="email" required className="w-full px-4 py-3 border border-slate-300 rounded-xl"
          onChange={(e) => setForm({...form, email: e.target.value})} 
        />
        <input 
          placeholder="Password" type="password" required className="w-full px-4 py-3 border border-slate-300 rounded-xl"
          onChange={(e) => setForm({...form, password: e.target.value})} 
        />
        
        <button type="submit" className="w-full py-3 px-4 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-700 transition">
          Register
        </button>

        <p className="text-center text-sm text-slate-600">
          Already have an account? <Link to="/login" className="font-bold text-indigo-600">Log in</Link>
        </p>
      </form>
    </AuthLayout>
  );
}