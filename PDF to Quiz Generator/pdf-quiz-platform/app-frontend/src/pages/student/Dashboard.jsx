import { useEffect, useState } from 'react';
import api from '../../api/axios';
import { Star, Trophy, Target, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function StudentDashboard() {
  const [progress, setProgress] = useState(null);
  const [recommendations, setRecommendations] = useState([]);

  useEffect(() => {
    Promise.all([
      api.get('/student/progress'),
      api.get('/student/recommendations')
    ]).then(([prog, rec]) => {
      setProgress(prog.data);
      setRecommendations(rec.data);
    });
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <header>
        <h1 className="text-3xl font-bold text-slate-900">Welcome back!</h1>
        <p className="text-slate-500">Here's how you're doing so far.</p>
      </header>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard title="Average Score" value={`${progress?.average_score || 0}%`} icon={<Trophy className="text-amber-500"/>} color="bg-amber-50" />
        <StatCard title="Quizzes Done" value={progress?.quizzes_completed || 0} icon={<Star className="text-indigo-500"/>} color="bg-indigo-50" />
        <StatCard title="Strengths" value={progress?.top_topic || "N/A"} icon={<Target className="text-emerald-500"/>} color="bg-emerald-50" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Recommendations */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
          <h2 className="text-xl font-bold mb-4">Recommended for You</h2>
          <div className="space-y-4">
            {recommendations.map(quiz => (
              <Link key={quiz.id} to={`/quiz/${quiz.id}`} className="flex items-center justify-between p-4 rounded-xl border border-slate-100 hover:border-indigo-200 hover:bg-indigo-50 transition">
                <div>
                  <div className="font-semibold text-slate-800">{quiz.title}</div>
                  <div className="text-sm text-slate-500">{quiz.topic_name}</div>
                </div>
                <ArrowRight className="w-5 h-5 text-indigo-600" />
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color }) {
  return (
    <div className={`${color} p-6 rounded-2xl flex items-center gap-4`}>
      <div className="p-3 bg-white rounded-xl shadow-sm">{icon}</div>
      <div>
        <div className="text-sm text-slate-600 font-medium">{title}</div>
        <div className="text-2xl font-bold text-slate-900">{value}</div>
      </div>
    </div>
  );
}