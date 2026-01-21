import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/axios';
import { 
  Upload, FileText, CheckCircle2, 
  Loader2, Play, RefreshCw, AlertCircle,
  Clock, Check
} from 'lucide-react';

export default function PDFLibrary() {
  const [pdfs, setPdfs] = useState([]);
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [generatingId, setGeneratingId] = useState(null); // Track which PDF is being turned into a quiz
  
  const navigate = useNavigate();

  const fetchPdfs = async () => {
    try {
      const res = await api.get('/admin/pdf/list');
      setPdfs(res.data);
    } catch (err) {
      console.error("Failed to fetch PDFs");
    } finally {
      setLoadingList(false);
    }
  };

  // Initial Load
  useEffect(() => { fetchPdfs(); }, []);

  // SMART POLLING: Check for updates every 3 seconds ONLY if something is processing
  useEffect(() => {
    const isProcessing = pdfs.some(p => p.status === 'uploaded' || p.status === 'processing');
    
    if (isProcessing) {
      const interval = setInterval(() => {
        fetchPdfs();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [pdfs]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setIsUploading(true);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    
    try {
      await api.post('/admin/pdf/upload', formData);
      setTitle(''); 
      setFile(null);
      fetchPdfs(); // Refresh immediately to show the 'uploaded' row
    } catch (err) {
      alert("Upload failed. Ensure you are logged in as admin.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleGenerateQuiz = async (pdf) => {
    setGeneratingId(pdf.id);
    try {
      // Prompt user for a quick title, or use a default
      const quizTitle = window.prompt("Enter a Title for this Quiz:", `Quiz: ${pdf.title}`);
      if (!quizTitle) {
        setGeneratingId(null);
        return;
      }

      await api.post(`/admin/quiz/generate/${pdf.id}`, {
        pdf_id: pdf.id,
        title: quizTitle,
        description: `Automatically generated from ${pdf.original_filename}`,
        question_count: 10
      });

      // Redirect to Quiz Management to see the generation progress
      navigate('/admin/quizzes');
    } catch (err) {
      alert(err.response?.data?.detail || "Could not start quiz generation.");
      setGeneratingId(null);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in pb-20">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-black text-slate-900 tracking-tight">PDF Library</h1>
          <p className="text-slate-500 font-medium mt-1">Convert your documents into interactive learning data.</p>
        </div>
        <button 
          onClick={fetchPdfs} 
          className="p-3 hover:bg-white hover:shadow-md rounded-2xl transition-all border border-transparent hover:border-slate-200 group"
        >
          <RefreshCw className={`w-5 h-5 text-slate-400 group-hover:text-indigo-600 ${loadingList ? 'animate-spin' : ''}`} />
        </button>
      </header>

      {/* Upload Section */}
      <div className="bg-white p-8 rounded-[2.5rem] border border-slate-200 shadow-xl shadow-slate-200/50 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-5">
           <Upload className="w-24 h-24 text-indigo-600" />
        </div>
        
        <h3 className="text-xs font-black text-indigo-600 uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
          <Upload className="w-4 h-4" /> System Ingestion
        </h3>

        <form onSubmit={handleUpload} className="grid md:grid-cols-3 gap-8 items-end relative z-10">
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase ml-1">Document Title</label>
            <input 
              value={title} 
              onChange={e => setTitle(e.target.value)} 
              className="w-full px-6 py-4 rounded-2xl bg-slate-50 border border-slate-200 focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 focus:bg-white outline-none transition-all font-medium" 
              placeholder="e.g. Cyber Security Basics" required 
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-500 uppercase ml-1">PDF Data Source</label>
            <div className="relative">
              <input 
                type="file" 
                onChange={e => setFile(e.target.files[0])} 
                accept=".pdf" 
                className="w-full text-sm text-slate-500 file:mr-4 file:py-3 file:px-6 file:rounded-xl file:border-0 file:text-xs file:font-black file:bg-indigo-600 file:text-white hover:file:bg-indigo-700 transition cursor-pointer bg-slate-50 rounded-2xl border border-slate-200 pr-4" 
                required 
              />
            </div>
          </div>
          <button 
            type="submit" 
            disabled={isUploading} 
            className="bg-slate-900 text-white px-8 py-4 rounded-2xl font-black hover:bg-slate-800 disabled:bg-slate-200 transition-all flex items-center justify-center gap-3 shadow-xl active:scale-95 h-[58px]"
          >
            {isUploading ? <Loader2 className="animate-spin w-5 h-5" /> : 'Start AI Analysis'}
          </button>
        </form>
      </div>

      {/* Documents Grid / Table */}
      <div className="bg-white rounded-[2.5rem] border border-slate-200 shadow-xl shadow-slate-200/50 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50/50 border-b border-slate-100">
              <th className="px-8 py-6 text-[10px] font-black uppercase text-slate-400 tracking-widest">Resource</th>
              <th className="px-8 py-6 text-[10px] font-black uppercase text-slate-400 tracking-widest">AI Pipeline Status</th>
              <th className="px-8 py-6 text-[10px] font-black uppercase text-slate-400 tracking-widest">Metadata</th>
              <th className="px-8 py-6 text-right text-[10px] font-black uppercase text-slate-400 tracking-widest">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {pdfs.map(pdf => (
              <tr key={pdf.id} className="hover:bg-slate-50/80 transition-colors group">
                <td className="px-8 py-6">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center text-indigo-600 group-hover:scale-110 transition-transform">
                      <FileText className="w-6 h-6"/>
                    </div>
                    <div>
                      <div className="font-bold text-slate-800 text-lg leading-tight">{pdf.title}</div>
                      <div className="text-xs text-slate-400 font-medium mt-1">{pdf.original_filename}</div>
                    </div>
                  </div>
                </td>
                <td className="px-8 py-6">
                  <StatusBadge status={pdf.status} error={pdf.error_message} />
                </td>
                <td className="px-8 py-6">
                  <div className="flex items-center gap-2 text-slate-400">
                    <Clock className="w-3.5 h-3.5" />
                    <span className="text-xs font-bold">{new Date(pdf.created_at).toLocaleDateString()}</span>
                  </div>
                </td>
                <td className="px-8 py-6 text-right">
                  {pdf.status === 'processed' ? (
                    <button 
                      onClick={() => handleGenerateQuiz(pdf)}
                      disabled={generatingId === pdf.id}
                      className="bg-indigo-600 text-white px-6 py-2.5 rounded-xl text-xs font-black hover:bg-indigo-700 transition shadow-lg shadow-indigo-200 flex items-center gap-2 ml-auto active:scale-95 disabled:bg-slate-300"
                    >
                      {generatingId === pdf.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Play className="w-3 h-3 fill-current" />
                      )}
                      Generate Quiz
                    </button>
                  ) : pdf.status === 'failed' ? (
                    <div className="text-red-400 p-2 hover:bg-red-50 rounded-lg inline-block transition cursor-help" title={pdf.error_message}>
                       <AlertCircle className="w-5 h-5" />
                    </div>
                  ) : (
                    <div className="flex items-center justify-end gap-2 text-slate-300 font-bold text-[10px] uppercase italic">
                       <Loader2 className="w-3 h-3 animate-spin" />
                       Step {pdf.status === 'uploaded' ? '1/3' : '2/3'}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {pdfs.length === 0 && !loadingList && (
          <div className="py-32 text-center">
            <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-6">
              <FileText className="w-10 h-10 text-slate-200" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Your library is empty</h3>
            <p className="text-slate-400 mt-2 max-w-xs mx-auto text-sm">Upload a textbook or notes to begin generating AI quizzes.</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Helper Component for Status Badges
function StatusBadge({ status, error }) {
  const configs = {
    processed: { color: 'bg-emerald-100 text-emerald-700', icon: <Check className="w-3 h-3"/>, label: 'Processed' },
    processing: { color: 'bg-amber-100 text-amber-700 animate-pulse', icon: <Loader2 className="w-3 h-3 animate-spin"/>, label: 'AI Thinking' },
    uploaded: { color: 'bg-blue-100 text-blue-700', icon: <Clock className="w-3 h-3"/>, label: 'In Queue' },
    failed: { color: 'bg-red-100 text-red-700', icon: <AlertCircle className="w-3 h-3"/>, label: 'Error' }
  };

  const config = configs[status] || configs.uploaded;

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[10px] font-black uppercase tracking-wider ${config.color}`}>
      {config.icon}
      {config.label}
    </div>
  );
}