import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import Navbar from '../components/common/Navbar';
import { 
  ChevronRight, Zap, FileText, BarChart3, 
  ShieldCheck, Globe, Star, CheckCircle 
} from 'lucide-react';

export default function LandingPage() {
  const { user } = useContext(AuthContext);

  // Helper to determine where the "Dashboard" button goes
  const dashboardPath = user?.is_admin ? '/admin' : '/dashboard';

  return (
    <div className="min-h-screen bg-slate-50 font-sans selection:bg-indigo-100 selection:text-indigo-900">
      <Navbar />
      
      {/* Hero Section */}
      <section className="relative pt-20 pb-32 overflow-hidden">
        {/* Decorative Background Mesh */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full -z-10">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-200/40 blur-[120px] rounded-full"></div>
          <div className="absolute bottom-[10%] right-[-5%] w-[30%] h-[30%] bg-blue-200/30 blur-[100px] rounded-full"></div>
        </div>

        <div className="max-w-7xl mx-auto px-4 text-center">
          {/* Top Badge */}
          <div className="inline-flex items-center gap-2 bg-white px-4 py-1.5 rounded-full shadow-sm border border-slate-200 mb-8 animate-fade-in">
            <span className="flex h-2 w-2 rounded-full bg-indigo-600"></span>
            <span className="text-sm font-bold text-slate-600">Powered by OpenAI & Llama 3</span>
          </div>

          <h1 className="text-6xl md:text-7xl font-extrabold text-slate-900 leading-[1.1] mb-8 tracking-tight">
            The Intelligent Way to <br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-blue-500">Master Any Document</span>
          </h1>
          
          <p className="text-xl text-slate-600 max-w-2xl mx-auto mb-12 leading-relaxed">
            Upload PDFs and watch as our AI instantly generates curriculum-aligned 
            quizzes, flashcards, and learning analytics. Built for modern educators and high-achieving students.
          </p>

          <div className="flex flex-col sm:flex-row justify-center gap-5">
            {user ? (
              <Link to={dashboardPath} className="group bg-slate-900 text-white px-10 py-5 rounded-2xl font-bold text-lg hover:bg-slate-800 shadow-2xl flex items-center gap-2 transition-all">
                Enter Dashboard <ChevronRight className="group-hover:translate-x-1 transition-transform"/>
              </Link>
            ) : (
              <>
                <Link to="/register" className="group bg-indigo-600 text-white px-10 py-5 rounded-2xl font-bold text-lg hover:bg-indigo-700 shadow-xl shadow-indigo-200 flex items-center gap-2 transition-all active:scale-95">
                  Get Started Free <ChevronRight className="group-hover:translate-x-1 transition-transform"/>
                </Link>
                <Link to="/login" className="bg-white text-slate-700 border border-slate-200 px-10 py-5 rounded-2xl font-bold text-lg hover:bg-slate-50 transition-all active:scale-95">
                  Sign In
                </Link>
              </>
            )}
          </div>

          {/* Trust Indicators */}
          <div className="mt-20 flex flex-wrap justify-center items-center gap-8 md:gap-16 opacity-50 grayscale hover:grayscale-0 transition-all">
            <div className="flex items-center gap-2 font-bold text-slate-400 text-lg italic"><Globe className="w-6 h-6"/> GlobalEdu</div>
            <div className="flex items-center gap-2 font-bold text-slate-400 text-lg italic"><CheckCircle className="w-6 h-6"/> ProTeach</div>
            <div className="flex items-center gap-2 font-bold text-slate-400 text-lg italic"><Star className="w-6 h-6"/> EduCloud</div>
          </div>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="py-24 bg-white relative">
        <div className="max-w-7xl mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-slate-900 mb-4">Powerful AI Tools in One Place</h2>
            <div className="w-20 h-1 bg-indigo-600 mx-auto rounded-full"></div>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard 
              icon={<FileText className="w-8 h-8 text-white" />}
              iconBg="bg-indigo-600"
              title="Deep PDF Analysis"
              desc="We don't just read text; we understand concepts. Our AI identifies key learning objectives automatically."
            />
            <FeatureCard 
              icon={<Zap className="w-8 h-8 text-white" />}
              iconBg="bg-blue-600"
              title="Instant Quiz Gen"
              desc="Generate multiple-choice, true/false, and conceptual questions in seconds, not hours."
            />
            <FeatureCard 
              icon={<BarChart3 className="w-8 h-8 text-white" />}
              iconBg="bg-emerald-600"
              title="Performance Insights"
              desc="Identify knowledge gaps with detailed analytics on topic mastery and difficulty trends."
            />
          </div>
        </div>
      </section>

      {/* Professional Footer */}
      <footer className="bg-slate-900 text-slate-400 py-16 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            <div className="col-span-2">
              <div className="text-white font-bold text-2xl mb-6 flex items-center gap-2">
                <div className="w-8 h-8 bg-indigo-600 rounded-lg"></div>
                QuizAI
              </div>
              <p className="max-w-sm leading-relaxed">
                Elevating the educational experience through advanced generative AI. 
                Creating a world where learning is personalized and accessible to everyone.
              </p>
            </div>
            
            <div>
              <h4 className="text-white font-bold mb-6">Platform</h4>
              <ul className="space-y-4 text-sm">
                <li><Link to="/quizzes" className="hover:text-white transition">Available Quizzes</Link></li>
                <li><Link to="/register" className="hover:text-white transition">Student Registration</Link></li>
                <li><Link to="/login" className="hover:text-white transition">Member Login</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="text-white font-bold mb-6">Internal</h4>
              <ul className="space-y-4 text-sm">
                <li>
                  <Link to="/admin/login" className="flex items-center gap-2 hover:text-indigo-400 transition group">
                    <ShieldCheck className="w-4 h-4 group-hover:scale-110 transition" /> Admin Portal
                  </Link>
                </li>
                <li><Link to="#" className="hover:text-white transition">System Status</Link></li>
                <li><Link to="#" className="hover:text-white transition">Privacy Policy</Link></li>
              </ul>
            </div>
          </div>
          
          <div className="pt-8 border-t border-slate-800 text-center text-xs">
            © {new Date().getFullYear()} QuizAI Platform. Built for the future of education.
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, iconBg, title, desc }) {
  return (
    <div className="p-10 rounded-3xl border border-slate-100 bg-slate-50/50 hover:bg-white hover:shadow-2xl hover:shadow-indigo-100 transition-all duration-300 group">
      <div className={`${iconBg} w-14 h-14 rounded-2xl flex items-center justify-center mb-6 shadow-lg transform group-hover:-translate-y-2 transition-transform`}>
        {icon}
      </div>
      <h3 className="text-xl font-bold text-slate-900 mb-3">{title}</h3>
      <p className="text-slate-600 leading-relaxed text-sm">
        {desc}
      </p>
    </div>
  );
}