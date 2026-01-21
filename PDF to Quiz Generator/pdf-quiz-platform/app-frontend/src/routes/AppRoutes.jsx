import { Routes, Route } from 'react-router-dom';
import LandingPage from '../pages/LandingPage.jsx';
import Login from '../pages/auth/Login.jsx';
import Register from '../pages/auth/Register';
import PrivateRoute from './PrivateRoute';
import AdminRoute from './AdminRoute';
import StudentLayout from '../components/layouts/StudentLayout.jsx';
import AvailableQuizzes from '../pages/student/AvailableQuizzes.jsx';
import TakeQuiz from '../pages/student/TakeQuiz.jsx';
import StudentDashboard from '../pages/student/Dashboard.jsx';
import AdminLayout from '../components/layouts/AdminLayout';
import AdminDashboard from '../pages/admin/AdminDashboard';
import PDFLibrary from '../pages/admin/PDFLibrary';
import QuizManagement from '../pages/admin/QuizManagement';
import QuizEditor from '../pages/admin/QuizEditor';
import AdminLogin from '../pages/auth/AdminLogin.jsx';

// Temporary components for testing - replace these later with your real pages
// const StudentDashboard = () => <div className="p-8"><h1>Student Dashboard</h1></div>;
// const AdminDashboard = () => <div className="p-8"><h1>Admin Dashboard</h1></div>;

const AppRoutes = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/admin-login" element={<AdminLogin />} />

      {/* Protected Student/User Routes */}
      <Route element={<PrivateRoute />}>
        {/* <Route path="/dashboard" element={<StudentDashboard />} /> */}
        <Route element={<StudentLayout />}>
        <Route path="/dashboard" element={<StudentDashboard />} />
        <Route path="/quizzes" element={<AvailableQuizzes />} />
        <Route path="/quiz/:quizId" element={<TakeQuiz />} />
        {/* <Route path="/history" element={<AttemptHistory />} /> */}
    </Route>
      </Route>

      {/* Protected Admin Routes */}
      <Route element={<AdminRoute />}>
      <Route element={<AdminLayout />}>
        <Route path="/admin" element={<AdminDashboard />} />
         {/* <Route path="/admin" element={<AdminDashboard />} /> */}
        <Route path="/admin/pdfs" element={<PDFLibrary />} />
        <Route path="/admin/quizzes" element={<QuizManagement />} />
        <Route path="/admin/quiz-editor/:id" element={<QuizEditor />} />
        
        </Route>
        {/* Add more admin routes here later */}
      </Route>

      

      {/* 404 Catch-all */}
      <Route path="*" element={<div className="p-20 text-center">404 - Page Not Found</div>} />
    </Routes>
  );
};

export default AppRoutes;