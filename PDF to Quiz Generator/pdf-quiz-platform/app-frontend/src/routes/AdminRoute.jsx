import { Navigate, Outlet } from 'react-router-dom';
import useAuth from '../hooks/useAuth';

const AdminRoute = () => {
  const { user, loading } = useAuth();

  if (loading) return <div>Loading...</div>;
  // Checks both: is logged in AND is an admin
  return user && user.is_admin ? <Outlet /> : <Navigate to="/dashboard" />;
};

export default AdminRoute;