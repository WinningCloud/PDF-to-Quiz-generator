import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../api/axios';
import { Loader2, ChevronRight, CheckCircle } from 'lucide-react';

export default function TakeQuiz() {
  const { quizId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get(`/student/quiz/${quizId}`).then(res => setData(res.data));
  }, [quizId]);

  if (!data) return <div className="h-full flex items-center justify-center"><Loader2 className="animate-spin text-indigo-600" /></div>;

  const currentQuestion = data.questions[currentIdx];
  const progress = ((currentIdx + 1) / data.questions.length) * 100;

  const handleNext = async () => {
    if (selectedOption === null) return;
    setSubmitting(true);
    
    // Save answer to backend
    await api.post(`/student/attempt/${data.attempt_id}/answer`, {
      question_id: currentQuestion.id,
      selected_option: selectedOption
    });

    if (currentIdx < data.questions.length - 1) {
      setCurrentIdx(currentIdx + 1);
      setSelectedOption(null);
      setSubmitting(false);
    } else {
      // Complete Quiz
      const result = await api.post(`/student/attempt/${data.attempt_id}/complete`);
      navigate(`/quiz/result/${data.attempt_id}`, { state: result.data });
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-10">
      <div className="mb-8">
        <div className="flex justify-between items-end mb-2">
          <h2 className="text-sm font-bold text-indigo-600 uppercase tracking-widest">Question {currentIdx + 1} of {data.questions.length}</h2>
          <span className="text-sm text-slate-500 font-medium">{Math.round(progress)}% Complete</span>
        </div>
        <div className="w-full h-2 bg-slate-200 rounded-full">
          <div className="h-full bg-indigo-600 rounded-full transition-all" style={{ width: `${progress}%` }}></div>
        </div>
      </div>

      <div className="bg-white p-10 rounded-3xl shadow-xl border border-slate-100">
        <h1 className="text-2xl font-bold text-slate-900 mb-8 leading-relaxed">
          {currentQuestion.question_text}
        </h1>

        <div className="space-y-4">
          {['A', 'B', 'C', 'D'].map((opt) => {
            const optionText = currentQuestion[`option_${opt.toLowerCase()}`];
            if (!optionText) return null;
            return (
              <button
                key={opt}
                onClick={() => setSelectedOption(opt)}
                className={`w-full text-left p-5 rounded-2xl border-2 transition-all flex items-center justify-between group ${
                  selectedOption === opt 
                    ? 'border-indigo-600 bg-indigo-50' 
                    : 'border-slate-100 hover:border-slate-200 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-center gap-4">
                   <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold transition ${
                     selectedOption === opt ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-500'
                   }`}>{opt}</div>
                   <span className={`font-medium ${selectedOption === opt ? 'text-indigo-900' : 'text-slate-700'}`}>{optionText}</span>
                </div>
                {selectedOption === opt && <CheckCircle className="w-6 h-6 text-indigo-600" />}
              </button>
            );
          })}
        </div>

        <button
          onClick={handleNext}
          disabled={selectedOption === null || submitting}
          className="mt-10 w-full bg-slate-900 text-white py-4 rounded-2xl font-bold text-lg hover:bg-slate-800 disabled:bg-slate-200 transition flex justify-center items-center gap-2"
        >
          {submitting ? <Loader2 className="animate-spin" /> : (currentIdx === data.questions.length - 1 ? 'Finish Quiz' : 'Next Question')}
          {!submitting && <ChevronRight className="w-5 h-5" />}
        </button>
      </div>
    </div>
  );
}