import { createContext, useState, useEffect } from 'react';
import api from '../api/axios';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // Inside AuthContext.jsx
const login = async (formData) => {
  // 1. Get the token
  const res = await api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
  
  const token = res.data.access_token;
  localStorage.setItem('token', token);

  // 2. Fetch user immediately using the token we just got
  // We pass the header manually here to ensure it works even if interceptor is slow
  const userRes = await api.get('/auth/me', {
    headers: { Authorization: `Bearer ${token}` }
  });

  setUser(userRes.data);
  return userRes.data; // <--- CRITICAL: Return the user object
};

// Inside src/context/AuthContext.jsx
// src/context/AuthContext.jsx
const logout = () => {
  // 1. Clear Storage
  localStorage.removeItem('token');
  
  // 2. Clear Axios Headers (Prevents any lingering authorized requests)
  delete api.defaults.headers.common['Authorization'];
  
  // 3. Update State
  setUser(null);

  // 4. Force a hard redirect to the Landing Page
  // This is better for Logout because it clears all React memory/cache
  window.location.href = '/'; 
};

    const checkUser = async () => {
        try {
            const res = await api.get('/auth/me');
            setUser(res.data);
        } catch (err) {
            setUser(null);
            localStorage.removeItem('token');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { checkUser(); }, []);

    return (
    <AuthContext.Provider value={{ user, login, logout, loading, isAdmin: user?.is_admin }}>
      {loading ? (
        <div className="min-h-screen flex items-center justify-center bg-slate-50">
          <div className="text-indigo-600 font-bold animate-pulse text-xl">
            Initializing QuizAI...
          </div>
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
};