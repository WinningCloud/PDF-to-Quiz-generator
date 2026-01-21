import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../api/axios';
import { 
  Save, Trash2, Send, ChevronLeft, 
  CheckCircle, AlertCircle, Loader2,
  FileText
} from 'lucide-react';

// Main Page Component
export default function QuizEditor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isPublishing, setIsPublishing] = useState(false);

  // 1. Fetch Quiz and Questions from Backend
  useEffect(() => {
    const fetchQuizData = async () => {
      try {
        const res = await api.get(`/admin/quiz/${id}`);
        setQuiz(res.data);
        setQuestions(res.data.questions || []);
      } catch (err) {
        console.error("Error fetching quiz:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchQuizData();
  }, [id]);

  // 2. Handle Individual Question Updates
  const handleUpdateQuestion = async (qId, updatedFields) => {
    try {
      await api.put(`/admin/question/${qId}`, updatedFields);
      // Update local state smoothly
      setQuestions(prev => prev.map(q => q.id === qId ? { ...q, ...updatedFields } : q));
    } catch (err) {
      alert("Failed to save changes. Check backend connection.");
    }
  };

  // 3. Handle Question Deletion
  const handleDeleteQuestion = async (qId) => {
    if (!window.confirm("Are you sure you want to remove this question?")) return;
    try {
      await api.delete(`/admin/question/${qId}`);
      setQuestions(prev => prev.filter(q => q.id !== qId));
    } catch (err) {
      alert("Delete failed.");
    }
  };

  // 4. Handle Publish
  const handlePublish = async () => {
    setIsPublishing(true);
    try {
      await api.post(`/admin/quiz/${id}/publish`);
      alert("Quiz successfully published to students!");
      navigate('/admin/quizzes');
    } catch (err) {
      alert("Publishing failed.");
    } finally {
      setIsPublishing(false);
    }
  };

  if (loading) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-slate-50">
        <Loader2 className="w-10 h-10 text-indigo-600 animate-spin mb-4" />
        <p className="text-slate-500 font-bold animate-pulse uppercase tracking-widest text-xs">Loading AI Questions...</p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto py-12 px-6 space-y-10 animate-fade-in">
      {/* Top Navigation Bar */}
      <div className="flex justify-between items-center">
        <button 
          onClick={() => navigate('/admin/quizzes')} 
          className="flex items-center gap-2 text-slate-400 hover:text-indigo-600 font-black transition-all group uppercase text-xs tracking-widest"
        >
          <ChevronLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" /> 
          Back to Library
        </button>
        
        <button 
          onClick={handlePublish}
          disabled={isPublishing || questions.length === 0}
          className="bg-emerald-600 text-white px-10 py-4 rounded-2xl font-black flex items-center gap-3 hover:bg-emerald-700 shadow-xl shadow-emerald-100 transition-all active:scale-95 disabled:bg-slate-200"
        >
          {isPublishing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          Publish Quiz
        </button>
      </div>

      {/* Header Card */}
      <header className="bg-white p-10 rounded-[3rem] border border-slate-200 shadow-2xl shadow-slate-200/50 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-10 opacity-5">
           <FileText className="w-32 h-32 text-indigo-600" />
        </div>
        <div className="relative z-10">
          <div className="flex gap-3 mb-4">
            <span className="bg-indigo-600 text-white px-4 py-1 rounded-full text-[10px] font-black uppercase tracking-widest">
              {questions.length} Items
            </span>
            <span className="bg-slate-100 text-slate-500 px-4 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border border-slate-200">
              Draft Mode
            </span>
          </div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">{quiz?.title}</h1>
          <p className="text-slate-500 mt-3 font-medium text-lg max-w-2xl">{quiz?.description}</p>
        </div>
      </header>

      {/* Questions List */}
      <div className="space-y-8">
        {questions.map((q, idx) => (
          <QuestionCard 
            key={q.id} 
            q={q} 
            index={idx} 
            onUpdate={handleUpdateQuestion} 
            onDelete={handleDeleteQuestion}
          />
        ))}
      </div>
      
      {questions.length === 0 && (
        <div className="text-center py-20 bg-white rounded-[3rem] border-2 border-dashed border-slate-200">
          <p className="text-slate-400 font-medium italic">No questions found for this quiz.</p>
        </div>
      )}
    </div>
  );
}

// Sub-component for individual question cards
function QuestionCard({ q, index, onUpdate, onDelete }) {
  let options = {};
  try {
    options = typeof q.options === 'string' ? JSON.parse(q.options) : (q.options || {});
  } catch (e) {
    options = {};
  }

  const isMCQ = Object.keys(options).length > 0;

  return (
    <div className="bg-white p-10 rounded-[2.5rem] border border-slate-200 shadow-xl shadow-slate-100/50 hover:border-indigo-200 transition-all group">
      <div className="flex justify-between items-start mb-8">
        <div className="flex items-center gap-4">
          <span className="w-12 h-12 bg-slate-900 text-white rounded-2xl flex items-center justify-center font-black text-xl shadow-lg">
            {index + 1}
          </span>
          <div>
            <span className="text-[10px] font-black text-indigo-600 uppercase tracking-[0.2em] block">
              {isMCQ ? "Multiple Choice Assessment" : "Short Answer Prompt"}
            </span>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              Difficulty: {q.difficulty || 'Medium'}
            </span>
          </div>
        </div>
        <button 
          onClick={() => onDelete(q.id)} 
          className="text-slate-300 hover:text-red-500 transition-colors p-3 hover:bg-red-50 rounded-xl"
        >
          <Trash2 className="w-6 h-6" />
        </button>
      </div>

      <textarea
        className="w-full text-2xl font-bold text-slate-800 border-none p-0 focus:ring-0 resize-none bg-transparent mb-8 leading-tight placeholder:text-slate-200"
        defaultValue={q.question_text}
        placeholder="Enter question text..."
        onBlur={(e) => onUpdate(q.id, { question_text: e.target.value })}
        rows={2}
      />

      {isMCQ ? (
        <div className="grid md:grid-cols-2 gap-5">
          {Object.entries(options).map(([key, value]) => (
            <div 
              key={key} 
              className={`flex items-center gap-4 p-5 rounded-2xl border-2 transition-all ${
                q.correct_answer === key ? 'border-emerald-500 bg-emerald-50/30' : 'border-slate-50 bg-slate-50/50'
              }`}
            >
              <span className={`w-9 h-9 rounded-xl flex items-center justify-center font-black ${
                q.correct_answer === key ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-200' : 'bg-white text-slate-400 border border-slate-200'
              }`}>
                {key}
              </span>
              <input 
                className="bg-transparent border-none p-0 flex-1 text-sm font-bold text-slate-700 outline-none"
                defaultValue={value}
                onBlur={(e) => {
                  const newOptions = { ...options, [key]: e.target.value };
                  onUpdate(q.id, { options: JSON.stringify(newOptions) });
                }}
              />
              {q.correct_answer === key && <CheckCircle className="w-5 h-5 text-emerald-500" />}
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          <label className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] ml-2">Correct Response Architecture</label>
          <div className="p-6 bg-emerald-50/50 border-2 border-emerald-500/20 rounded-[1.5rem]">
             <textarea 
                className="w-full bg-transparent border-none p-0 text-emerald-900 font-bold outline-none resize-none leading-relaxed"
                defaultValue={q.correct_answer}
                rows={2}
                onBlur={(e) => onUpdate(q.id, { correct_answer: e.target.value })}
             />
          </div>
        </div>
      )}

      {q.explanation && (
        <div className="mt-8 p-6 bg-slate-900 text-white rounded-[1.5rem] flex gap-4 items-start shadow-xl">
          <div className="p-2 bg-white/10 rounded-lg">
            <AlertCircle className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <span className="text-[10px] font-black text-indigo-400 uppercase tracking-widest block mb-1">AI Context & Explanation</span>
            <p className="text-sm text-slate-300 italic leading-relaxed">{q.explanation}</p>
          </div>
        </div>
      )}
    </div>
  );
}