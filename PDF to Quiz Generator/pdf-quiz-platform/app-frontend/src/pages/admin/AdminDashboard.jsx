import { useEffect, useState } from 'react';
import api from '../../api/axios';
import { 
  Users, 
  FileText, 
  ClipboardCheck, 
  Activity, 
  TrendingUp, 
  Clock,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/admin/analytics/overview')
      .then(res => {
        setStats(res.data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-pulse space-y-8">
    <div className="h-10 w-48 bg-slate-200 rounded"></div>
    <div className="grid grid-cols-4 gap-6">
      {[1,2,3,4].map(i => <div key={i} className="h-32 bg-slate-100 rounded-2xl"></div>)}
    </div>
  </div>;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl font-bold text-slate-900 font-display">System Overview</h1>
        <p className="text-slate-500">Monitor platform activity and AI generation status.</p>
      </header>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <SummaryCard 
          title="Total Students" 
          value={stats?.total_users || 0} 
          icon={<Users className="w-6 h-6 text-indigo-600" />} 
          trend="+12% this month"
        />
        <SummaryCard 
          title="PDFs Processed" 
          value={stats?.total_pdfs || 0} 
          icon={<FileText className="w-6 h-6 text-blue-600" />} 
          trend="85% success rate"
        />
        <SummaryCard 
          title="Quizzes Generated" 
          value={stats?.total_quizzes || 0} 
          icon={<ClipboardCheck className="w-6 h-6 text-emerald-600" />} 
          trend="AI Driven"
        />
        <SummaryCard 
          title="Total Attempts" 
          value={stats?.total_attempts || 0} 
          icon={<Activity className="w-6 h-6 text-amber-600" />} 
          trend="Active now"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Activity Feed */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-slate-100 flex justify-between items-center">
            <h3 className="font-bold text-slate-800 flex items-center gap-2">
              <Clock className="w-5 h-5 text-slate-400" /> Recent System Activity
            </h3>
            <button className="text-indigo-600 text-sm font-bold hover:underline">View All</button>
          </div>
          <div className="divide-y divide-slate-50">
            {(Array.isArray(stats?.recent_activity) ? stats.recent_activity : []).map((activity, idx) => (
              <div key={idx} className="p-4 flex items-center gap-4 hover:bg-slate-50 transition">
                <div className={`p-2 rounded-lg ${activity.type === 'success' ? 'bg-emerald-50' : 'bg-blue-50'}`}>
                  {activity.type === 'success' ? 
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" /> : 
                    <TrendingUp className="w-5 h-5 text-blue-600" />
                  }
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-slate-800">{activity.message}</p>
                  <p className="text-xs text-slate-400">{activity.time_ago}</p>
                </div>
              </div>
            )) || <p className="p-10 text-center text-slate-400">No recent activity detected.</p>}
          </div>
        </div>

        {/* System Health / Status */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6">
          <h3 className="font-bold text-slate-800">AI Pipeline Status</h3>
          <div className="space-y-4">
            <StatusIndicator label="PDF Embedding Engine" status="Operational" />
            <StatusIndicator label="LLM Question Generator" status="Operational" />
            <StatusIndicator label="Vector Database (Redis/Pg)" status="Operational" />
            <StatusIndicator label="Background Workers" status="Idle" isIdle />
          </div>
          
          <div className="pt-6 border-t border-slate-100">
             <div className="bg-indigo-50 p-4 rounded-xl border border-indigo-100">
                <h4 className="text-indigo-900 font-bold text-sm mb-1">Admin Tip</h4>
                <p className="text-indigo-700 text-xs leading-relaxed">
                  Make sure to review AI-generated questions in the "Quiz Management" section before publishing them to students.
                </p>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ title, value, icon, trend }) {
  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition group">
      <div className="flex justify-between items-start mb-4">
        <div className="p-3 bg-slate-50 rounded-xl group-hover:bg-indigo-50 transition-colors">
          {icon}
        </div>
        <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-1 rounded-md uppercase">
          {trend}
        </span>
      </div>
      <div>
        <h4 className="text-slate-500 text-sm font-medium">{title}</h4>
        <p className="text-3xl font-bold text-slate-900 mt-1">{value}</p>
      </div>
    </div>
  );
}

function StatusIndicator({ label, status, isIdle }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-slate-600">{label}</span>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${isIdle ? 'bg-slate-300' : 'bg-emerald-500'}`}></div>
        <span className={`text-xs font-bold ${isIdle ? 'text-slate-400' : 'text-emerald-600'}`}>
          {status}
        </span>
      </div>
    </div>
  );
}