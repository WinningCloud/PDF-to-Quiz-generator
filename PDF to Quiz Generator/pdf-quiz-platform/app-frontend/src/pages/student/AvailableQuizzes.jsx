import { useEffect, useState } from 'react';
import api from '../../api/axios';
import { Link } from 'react-router-dom';

export default function AvailableQuizzes() {
  const [quizzes, setQuizzes] = useState([]);

  useEffect(() => {
    api.get('/student/quizzes/available').then(res => setQuizzes(res.data));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Ready to learn?</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {quizzes.map(quiz => (
          <div key={quiz.id} className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition flex flex-col">
            <div className="mb-4">
              <span className="bg-indigo-100 text-indigo-700 text-xs font-bold px-2 py-1 rounded uppercase tracking-wider">
                {quiz.difficulty || 'Normal'}
              </span>
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-2">{quiz.title}</h3>
            <p className="text-slate-500 text-sm mb-6 flex-1">{quiz.description}</p>
            <div className="flex items-center justify-between border-t pt-4 border-slate-50">
              <span className="text-sm font-medium text-slate-600">{quiz.total_questions} Questions</span>
              <Link to={`/quiz/${quiz.id}`} className="bg-indigo-600 text-white px-4 py-2 rounded-lg font-bold hover:bg-indigo-700 transition">
                Start Quiz
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}