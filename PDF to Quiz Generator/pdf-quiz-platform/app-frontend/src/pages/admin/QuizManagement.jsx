import { useState, useEffect } from 'react';
import api from '../../api/axios';
import { ClipboardList, Plus, Search, Filter, Eye, Send, Trash2, CheckCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function QuizManagement() {
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/admin/quiz/list')
      .then(res => setQuizzes(res.data))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-8 animate-fade-in">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-black text-slate-900">Quiz Management</h1>
          <p className="text-slate-500 font-medium">Review AI generations and publish to students.</p>
        </div>
        <button 
          onClick={() => navigate('/admin/pdfs')} // Send them to PDF library to start a new one
          className="bg-indigo-600 text-white px-6 py-3 rounded-2xl font-black hover:bg-indigo-700 transition shadow-xl shadow-indigo-100 flex items-center gap-2"
        >
          <Plus className="w-5 h-5" /> Create New Quiz
        </button>
      </header>

      {/* Filter Bar */}
      <div className="flex gap-4 bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex-1 relative">
          <Search className="absolute left-4 top-3 w-5 h-5 text-slate-400" />
          <input className="w-full pl-12 pr-4 py-2.5 bg-slate-50 border-none rounded-xl outline-none focus:ring-2 focus:ring-indigo-500/20" placeholder="Search quizzes..." />
        </div>
        <button className="px-4 py-2 border border-slate-200 rounded-xl font-bold text-slate-600 flex items-center gap-2 hover:bg-slate-50">
          <Filter className="w-4 h-4" /> Filter
        </button>
      </div>

      {/* Quiz Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {quizzes.map(quiz => (
          <div key={quiz.id} className="bg-white p-6 rounded-[2rem] border border-slate-200 shadow-xl shadow-slate-100 flex flex-col group hover:border-indigo-300 transition-all">
            <div className="flex justify-between items-start mb-4">
              <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${
                quiz.status === 'published' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
              }`}>
                {quiz.status}
              </span>
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                <button className="p-2 text-slate-400 hover:text-red-600 transition"><Trash2 className="w-4 h-4"/></button>
              </div>
            </div>

            <h3 className="text-xl font-bold text-slate-900 mb-2 line-clamp-1">{quiz.title}</h3>
            <p className="text-slate-500 text-sm mb-6 line-clamp-2">{quiz.description || 'No description provided.'}</p>

            <div className="mt-auto pt-6 border-t border-slate-50 flex items-center justify-between">
              <div className="text-xs font-bold text-slate-400">
                {quiz.total_questions} Questions
              </div>
              <div className="flex gap-2">
                <button 
                  onClick={() => navigate(`/admin/quiz-editor/${quiz.id}`)}
                  className="p-2 bg-slate-100 text-slate-600 rounded-xl hover:bg-indigo-600 hover:text-white transition"
                >
                  <Eye className="w-5 h-5" />
                </button>
                {quiz.status !== 'published' && (
                  <button className="bg-emerald-500 text-white px-4 py-2 rounded-xl text-xs font-black hover:bg-emerald-600 transition flex items-center gap-2">
                    <Send className="w-3 h-3" /> Publish
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
        
        {quizzes.length === 0 && !loading && (
          <div className="col-span-full py-20 text-center">
            <div className="inline-flex p-6 bg-slate-100 rounded-full mb-4">
               <ClipboardList className="w-10 h-10 text-slate-300" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">No quizzes yet</h3>
            <p className="text-slate-500">Generate a quiz from your PDF library to see it here.</p>
          </div>
        )}
      </div>
    </div>
  );
}