/**
 * Student Portal JavaScript
 */

// Global variables for student portal
let currentQuizPage = 1;
let currentAttemptPage = 1;
let totalQuizPages = 1;
let totalAttemptPages = 1;
let currentQuiz = null;
let currentAttempt = null;
let quizAnswers = {};
let timerInterval = null;
let quizTimeRemaining = 0;

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    if (!API.isAuthenticated()) {
        window.location.href = 'index.html';
        return;
    }
    
    if (!API.isStudent()) {
        Notifications.show('Access denied. Student only.', 'error');
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 2000);
        return;
    }
    
    // Initialize
    loadStudentData();
    setupStudentEventListeners();
    
    // Load initial data
    loadStudentDashboard();
    loadAvailableQuizzes();
    loadStudentAttempts();
    loadPerformanceData();
    loadResources();
});

function loadStudentData() {
    const userData = API.getUserData();
    if (userData) {
        document.getElementById('studentName').textContent = userData.name || 'Student';
        document.getElementById('studentEmail').textContent = userData.email || '';
        document.getElementById('welcomeName').textContent = userData.name || 'Student';
    }
}

function setupStudentEventListeners() {
    // Navigation
    setupStudentNavigation();
    
    // Quiz taking
    setupQuizTaking();
    
    // Resources and actions
    setupStudentActions();
    
    // Logout
    document.getElementById('studentLogoutBtn').addEventListener('click', handleStudentLogout);
    
    // Quiz filters
    document.getElementById('quizSearch').addEventListener('input', debounce(() => {
        currentQuizPage = 1;
        loadAvailableQuizzes();
    }, 500));
    
    document.getElementById('topicFilterStudent').addEventListener('change', () => {
        currentQuizPage = 1;
        loadAvailableQuizzes();
    });
    
    document.getElementById('difficultyFilter').addEventListener('change', () => {
        currentQuizPage = 1;
        loadAvailableQuizzes();
    });
    
    // Attempt tabs
    document.querySelectorAll('.attempt-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.attempt-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            const status = this.getAttribute('data-status');
            loadStudentAttempts(status);
        });
    });
    
    // Quiz pagination
    document.getElementById('prevQuizPageBtn').addEventListener('click', () => {
        if (currentQuizPage > 1) {
            currentQuizPage--;
            loadAvailableQuizzes();
        }
    });
    
    document.getElementById('nextQuizPageBtn').addEventListener('click', () => {
        if (currentQuizPage < totalQuizPages) {
            currentQuizPage++;
            loadAvailableQuizzes();
        }
    });
}

function setupStudentNavigation() {
    const navLinks = document.querySelectorAll('.student-nav .nav-link');
    const sections = document.querySelectorAll('.student-section');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const sectionId = this.getAttribute('data-section');
            
            // Update active nav link
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding section
            sections.forEach(section => {
                section.classList.remove('active');
                if (section.id === sectionId) {
                    section.classList.add('active');
                    
                    // Load data for the section if needed
                    switch(sectionId) {
                        case 'dashboard':
                            loadStudentDashboard();
                            break;
                        case 'available-quizzes':
                            loadAvailableQuizzes();
                            break;
                        case 'my-quizzes':
                            loadStudentAttempts();
                            break;
                        case 'performance':
                            loadPerformanceData();
                            break;
                        case 'resources':
                            loadResources();
                            break;
                    }
                }
            });
        });
    });
}

function setupQuizTaking() {
    // Quiz modal close buttons
    document.querySelectorAll('.close-quiz-modal, .close-results-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('quizModal').style.display = 'none';
            document.getElementById('resultsModal').style.display = 'none';
            stopQuizTimer();
        });
    });
    
    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target.id === 'quizModal') {
            document.getElementById('quizModal').style.display = 'none';
            stopQuizTimer();
        }
        if (e.target.id === 'resultsModal') {
            document.getElementById('resultsModal').style.display = 'none';
        }
    });
    
    // Quiz navigation
    document.getElementById('prevQuestionBtn').addEventListener('click', showPreviousQuestion);
    document.getElementById('nextQuestionBtn').addEventListener('click', showNextQuestion);
    document.getElementById('submitQuizBtn').addEventListener('click', submitQuiz);
    
    // Results modal buttons
    document.getElementById('retryQuizBtn').addEventListener('click', retryQuiz);
    document.getElementById('viewAnswersBtn').addEventListener('click', viewDetailedAnswers);
    document.getElementById('closeResultsBtn').addEventListener('click', () => {
        document.getElementById('resultsModal').style.display = 'none';
        loadStudentDashboard();
        loadStudentAttempts();
    });
}

function setupStudentActions() {
    // Quick action buttons
    document.getElementById('downloadCertBtn').addEventListener('click', downloadCertificate);
    document.getElementById('exportResultsBtn').addEventListener('click', exportStudentResults);
    document.getElementById('requestQuizBtn').addEventListener('click', requestNewQuiz);
    document.getElementById('feedbackBtn').addEventListener('click', submitFeedback);
}

async function loadStudentDashboard() {
    try {
        const dashboard = await API.StudentAPI.getDashboard();
        
        // Update quick stats
        document.getElementById('completedQuizzes').textContent = dashboard.completed_quizzes || 0;
        document.getElementById('avgStudentScore').textContent = `${dashboard.average_score || 0}%`;
        document.getElementById('totalTime').textContent = `${dashboard.total_time_minutes || 0}m`;
        
        // Load recommended quizzes
        loadRecommendedQuizzes(dashboard.recommended_quizzes || []);
        
        // Load recent activity
        loadStudentActivity(dashboard.recent_activity || []);
        
        // Load progress chart
        if (window.loadStudentProgressChart) {
            window.loadStudentProgressChart(dashboard.progress_data);
        }
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function loadRecommendedQuizzes(quizzes) {
    const container = document.getElementById('recommendedQuizzes');
    
    if (quizzes.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-lightbulb"></i>
                <p>No recommended quizzes yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = quizzes.map(quiz => `
        <div class="quiz-card">
            <div class="quiz-header">
                <div class="quiz-title">${quiz.title}</div>
                <span class="difficulty-badge difficulty-${quiz.difficulty}">
                    ${quiz.difficulty}
                </span>
            </div>
            <div class="quiz-meta">
                <span><i class="fas fa-tag"></i> ${quiz.topic}</span>
                <span><i class="fas fa-question-circle"></i> ${quiz.question_count} questions</span>
                <span><i class="fas fa-clock"></i> ${quiz.duration || 30}m</span>
            </div>
            <div class="quiz-actions">
                <button class="btn-primary" onclick="startQuiz('${quiz.id}')">
                    <i class="fas fa-play"></i> Start Quiz
                </button>
                <button class="btn-secondary" onclick="viewQuizDetails('${quiz.id}')">
                    <i class="fas fa-info-circle"></i> Details
                </button>
            </div>
        </div>
    `).join('');
}

function loadStudentActivity(activities) {
    const container = document.getElementById('studentActivity');
    
    if (activities.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-history"></i>
                <p>No recent activity</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = activities.map(activity => `
        <div class="timeline-item">
            <div class="timeline-content">
                <h4>${activity.title}</h4>
                <p>${activity.description}</p>
                <small class="timeline-time">${activity.time}</small>
            </div>
        </div>
    `).join('');
}

async function loadAvailableQuizzes() {
    try {
        const topic = document.getElementById('topicFilterStudent').value;
        const difficulty = document.getElementById('difficultyFilter').value;
        
        const response = await API.StudentAPI.getAvailableQuizzes(topic, difficulty, currentQuizPage, 9);
        
        totalQuizPages = response.total_pages || 1;
        updateQuizPagination(currentQuizPage, totalQuizPages);
        
        renderAvailableQuizzes(response.quizzes || []);
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function renderAvailableQuizzes(quizzes) {
    const container = document.getElementById('availableQuizzesGrid');
    
    if (quizzes.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-question-circle"></i>
                <p>No quizzes available</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = quizzes.map(quiz => `
        <div class="quiz-card">
            <div class="quiz-header">
                <div class="quiz-title">${quiz.title}</div>
                <span class="difficulty-badge difficulty-${quiz.difficulty}">
                    ${quiz.difficulty}
                </span>
            </div>
            <p class="quiz-description">${quiz.description || 'Test your knowledge'}</p>
            <div class="quiz-meta">
                <span><i class="fas fa-tag"></i> ${quiz.topic}</span>
                <span><i class="fas fa-question-circle"></i> ${quiz.question_count} questions</span>
                <span><i class="fas fa-clock"></i> ${quiz.duration || 30} minutes</span>
            </div>
            <div class="quiz-stats">
                <div class="stat">
                    <i class="fas fa-users"></i>
                    <span>${quiz.total_attempts || 0} attempts</span>
                </div>
                <div class="stat">
                    <i class="fas fa-star"></i>
                    <span>${quiz.average_score || 0}% avg</span>
                </div>
            </div>
            <div class="quiz-actions">
                <button class="btn-primary" onclick="startQuiz('${quiz.id}')">
                    <i class="fas fa-play"></i> Start Quiz
                </button>
                <button class="btn-secondary" onclick="viewQuizDetails('${quiz.id}')">
                    <i class="fas fa-info-circle"></i> Details
                </button>
            </div>
        </div>
    `).join('');
}

async function loadStudentAttempts(status = 'all') {
    try {
        const response = await API.StudentAPI.getAttempts(status, currentAttemptPage, 10);
        
        totalAttemptPages = response.total_pages || 1;
        renderAttemptsTable(response.attempts || []);
        
        // Update performance summary
        updatePerformanceSummary(response.summary || {});
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function renderAttemptsTable(attempts) {
    const tbody = document.getElementById('attemptsTableBody');
    
    if (attempts.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">No quiz attempts found</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = attempts.map(attempt => `
        <tr>
            <td>
                <strong>${attempt.quiz_title}</strong>
            </td>
            <td>
                <span class="topic-badge">${attempt.topic}</span>
            </td>
            <td>
                ${attempt.status === 'completed' ? `
                    <span class="score-badge score-${getScoreCategory(attempt.score)}">
                        ${attempt.score || 0}%
                    </span>
                ` : 'N/A'}
            </td>
            <td>${formatTime(attempt.time_spent_minutes)}</td>
            <td>
                <span class="status-badge status-${attempt.status}">
                    ${attempt.status}
                </span>
            </td>
            <td>${attempt.completed_at ? formatDate(attempt.completed_at) : 'N/A'}</td>
            <td>
                <div class="action-buttons">
                    ${attempt.status === 'completed' ? `
                        <button class="btn-icon" onclick="viewQuizResults('${attempt.id}')" 
                                title="View Results">
                            <i class="fas fa-chart-bar"></i>
                        </button>
                        <button class="btn-icon" onclick="reviewQuiz('${attempt.id}')" 
                                title="Review Answers">
                            <i class="fas fa-eye"></i>
                        </button>
                    ` : attempt.status === 'in_progress' ? `
                        <button class="btn-icon" onclick="resumeQuiz('${attempt.id}')" 
                                title="Resume Quiz">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="btn-icon btn-danger" onclick="abandonQuiz('${attempt.id}')" 
                                title="Abandon Quiz">
                            <i class="fas fa-times"></i>
                        </button>
                    ` : ''}
                    ${attempt.status === 'completed' ? `
                        <button class="btn-icon" onclick="retryQuizFromHistory('${attempt.quiz_id}')" 
                                title="Retry Quiz">
                            <i class="fas fa-redo"></i>
                        </button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');
}

function updatePerformanceSummary(summary) {
    document.getElementById('highestScore').textContent = `${summary.highest_score || 0}%`;
    document.getElementById('highestScoreQuiz').textContent = summary.highest_score_quiz || '-';
    document.getElementById('avgTime').textContent = `${summary.average_time || 0}m`;
    document.getElementById('topicsMastered').textContent = summary.topics_mastered || 0;
    document.getElementById('improvementRate').textContent = `${summary.improvement_rate || 0}%`;
}

async function loadPerformanceData() {
    try {
        const analytics = await API.StudentAPI.getPerformanceAnalytics();
        
        // Load charts
        if (window.loadStudentAnalyticsCharts) {
            window.loadStudentAnalyticsCharts(analytics);
        }
        
        // Load strengths and weaknesses
        loadStrengthsWeaknesses(analytics.strengths || [], analytics.weaknesses || []);
        
        // Load recommendations
        loadRecommendations(analytics.recommendations || []);
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function loadStrengthsWeaknesses(strengths, weaknesses) {
    const strengthsList = document.getElementById('strengthsList');
    const weaknessesList = document.getElementById('weaknessesList');
    
    strengthsList.innerHTML = strengths.map(item => `
        <div class="sw-item">
            <span>${item.topic}</span>
            <span class="sw-score">${item.score}%</span>
        </div>
    `).join('') || '<p>No strengths identified yet</p>';
    
    weaknessesList.innerHTML = weaknesses.map(item => `
        <div class="sw-item">
            <span>${item.topic}</span>
            <span class="sw-score">${item.score}%</span>
        </div>
    `).join('') || '<p>No weaknesses identified yet</p>';
}

function loadRecommendations(recommendations) {
    const container = document.getElementById('recommendationsList');
    
    container.innerHTML = recommendations.map(rec => `
        <div class="recommendation-item">
            <i class="fas fa-lightbulb"></i>
            <div>
                <h4>${rec.title}</h4>
                <p>${rec.description}</p>
                ${rec.action ? `
                    <button class="btn-small" onclick="${rec.action}">
                        ${rec.action_text || 'Take Action'}
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('') || '<p>No recommendations available</p>';
}

async function loadResources() {
    try {
        const resources = await API.StudentAPI.getResources();
        
        // Load PDF resources
        loadPDFResources(resources.pdfs || []);
        
        // Load study guides
        loadStudyGuides(resources.study_guides || []);
        
        // Load topic coverage chart
        if (window.loadTopicCoverageChart) {
            window.loadTopicCoverageChart(resources.topic_coverage || []);
        }
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function loadPDFResources(pdfs) {
    const container = document.getElementById('pdfResourcesList');
    
    container.innerHTML = pdfs.map(pdf => `
        <div class="resource-item">
            <div class="resource-info">
                <h4>${pdf.title}</h4>
                <small>${pdf.topic} • ${pdf.pages} pages</small>
            </div>
            <div class="resource-actions">
                <button class="btn-icon" onclick="viewPDF('${pdf.id}')" title="View PDF">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn-icon" onclick="downloadPDF('${pdf.id}')" title="Download PDF">
                    <i class="fas fa-download"></i>
                </button>
            </div>
        </div>
    `).join('') || '<p>No PDF resources available</p>';
}

function loadStudyGuides(guides) {
    const container = document.getElementById('studyGuides');
    
    container.innerHTML = guides.map(guide => `
        <div class="guide-item">
            <h4>${guide.title}</h4>
            <p>${guide.description}</p>
            <div class="guide-tags">
                ${(guide.tags || []).map(tag => `<span class="tag">${tag}</span>`).join('')}
            </div>
            ${guide.quiz_id ? `
                <button class="btn-small" onclick="startQuiz('${guide.quiz_id}')">
                    <i class="fas fa-play"></i> Practice Quiz
                </button>
            ` : ''}
        </div>
    `).join('') || '<p>No study guides available</p>';
}

// ==================== QUIZ TAKING FUNCTIONS ====================

window.startQuiz = async function(quizId) {
    try {
        Notifications.show('Loading quiz...', 'info');
        
        // Start quiz attempt
        const attemptResponse = await API.StudentAPI.startQuizAttempt(quizId);
        currentAttempt = attemptResponse.attempt;
        
        // Get quiz questions
        const quizResponse = await API.StudentAPI.getQuizForTaking(quizId);
        currentQuiz = quizResponse;
        
        // Initialize quiz state
        quizAnswers = {};
        quizTimeRemaining = currentQuiz.duration * 60; // Convert minutes to seconds
        
        // Show quiz modal
        showQuizModal();
        
        // Start timer
        startQuizTimer();
        
        // Load first question
        showQuestion(0);
        
        Notifications.show('Quiz started! Good luck!', 'success');
        
    } catch (error) {
        API.handleApiError(error);
    }
};

function showQuizModal() {
    const modal = document.getElementById('quizModal');
    const title = document.getElementById('quizModalTitle');
    
    title.textContent = currentQuiz.title;
    document.getElementById('totalQuestions').textContent = currentQuiz.questions.length;
    
    // Generate navigation buttons
    const navContainer = document.querySelector('.quiz-navigation');
    navContainer.innerHTML = currentQuiz.questions.map((_, index) => `
        <button class="nav-btn" data-question="${index + 1}" onclick="showQuestion(${index})">
            ${index + 1}
        </button>
    `).join('');
    
    modal.style.display = 'flex';
}

function showQuestion(index) {
    const questions = currentQuiz.questions;
    if (index < 0 || index >= questions.length) return;
    
    // Hide all questions
    document.querySelectorAll('.question-container').forEach(q => {
        q.classList.remove('active');
    });
    
    // Show selected question
    const questionContainer = document.getElementById('questionContainer');
    questionContainer.innerHTML = renderQuestion(questions[index], index);
    
    // Show the container
    const questionDiv = questionContainer.querySelector('.question-container');
    questionDiv.classList.add('active');
    
    // Update progress
    updateProgress(index + 1);
    
    // Update navigation
    updateQuestionNavigation(index);
    
    // Restore saved answer
    if (quizAnswers[index]) {
        restoreAnswer(index, quizAnswers[index]);
    }
}

function renderQuestion(question, index) {
    let optionsHtml = '';
    
    switch (question.type) {
        case 'mcq':
            optionsHtml = question.options.map((option, optIndex) => `
                <div class="option" onclick="selectOption(${index}, ${optIndex})">
                    <span class="option-letter">${String.fromCharCode(65 + optIndex)}.</span>
                    <span class="option-text">${option}</span>
                </div>
            `).join('');
            break;
            
        case 'true_false':
            optionsHtml = `
                <div class="option" onclick="selectOption(${index}, 'true')">
                    <span class="option-text">True</span>
                </div>
                <div class="option" onclick="selectOption(${index}, 'false')">
                    <span class="option-text">False</span>
                </div>
            `;
            break;
            
        case 'short_answer':
            optionsHtml = `
                <textarea class="short-answer" 
                          placeholder="Type your answer here..." 
                          oninput="saveShortAnswer(${index}, this.value)"
                          rows="4">${quizAnswers[index] || ''}</textarea>
            `;
            break;
    }
    
    return `
        <div class="question-container" data-index="${index}">
            <div class="question-text">
                Q${index + 1}: ${question.text}
            </div>
            <div class="options-container">
                ${optionsHtml}
            </div>
        </div>
    `;
}

function updateProgress(currentQuestion) {
    const totalQuestions = currentQuiz.questions.length;
    const progress = (currentQuestion / totalQuestions) * 100;
    
    document.getElementById('quizProgressFill').style.width = `${progress}%`;
    document.getElementById('currentQuestion').textContent = currentQuestion;
    document.getElementById('totalQuestions').textContent = totalQuestions;
    
    // Update navigation buttons
    document.querySelectorAll('.nav-btn').forEach((btn, index) => {
        btn.classList.remove('active', 'answered');
        if (index === currentQuestion - 1) {
            btn.classList.add('active');
        }
        if (quizAnswers[index]) {
            btn.classList.add('answered');
        }
    });
}

function updateQuestionNavigation(currentIndex) {
    const prevBtn = document.getElementById('prevQuestionBtn');
    const nextBtn = document.getElementById('nextQuestionBtn');
    const submitBtn = document.getElementById('submitQuizBtn');
    
    prevBtn.style.display = currentIndex === 0 ? 'none' : 'block';
    
    if (currentIndex === currentQuiz.questions.length - 1) {
        nextBtn.style.display = 'none';
        submitBtn.style.display = 'block';
    } else {
        nextBtn.style.display = 'block';
        submitBtn.style.display = 'none';
    }
}

function showPreviousQuestion() {
    const currentIndex = parseInt(document.querySelector('.question-container.active').getAttribute('data-index'));
    showQuestion(currentIndex - 1);
}

function showNextQuestion() {
    const currentIndex = parseInt(document.querySelector('.question-container.active').getAttribute('data-index'));
    showQuestion(currentIndex + 1);
}

window.selectOption = function(questionIndex, optionIndex) {
    const question = currentQuiz.questions[questionIndex];
    
    // Clear previous selection
    document.querySelectorAll(`.question-container[data-index="${questionIndex}"] .option`).forEach(opt => {
        opt.classList.remove('selected');
    });
    
    // Mark selected option
    if (question.type === 'mcq') {
        document.querySelectorAll(`.question-container[data-index="${questionIndex}"] .option`)[optionIndex]
            .classList.add('selected');
    } else if (question.type === 'true_false') {
        const selectedOption = document.querySelector(`.question-container[data-index="${questionIndex}"] .option:${optionIndex === 'true' ? 'first-child' : 'last-child'}`);
        selectedOption.classList.add('selected');
    }
    
    // Save answer
    if (question.type === 'mcq') {
        quizAnswers[questionIndex] = optionIndex;
    } else if (question.type === 'true_false') {
        quizAnswers[questionIndex] = optionIndex;
    }
    
    // Mark as answered in navigation
    document.querySelector(`.nav-btn[data-question="${questionIndex + 1}"]`).classList.add('answered');
};

window.saveShortAnswer = function(questionIndex, answer) {
    quizAnswers[questionIndex] = answer.trim();
    if (answer.trim()) {
        document.querySelector(`.nav-btn[data-question="${questionIndex + 1}"]`).classList.add('answered');
    } else {
        document.querySelector(`.nav-btn[data-question="${questionIndex + 1}"]`).classList.remove('answered');
    }
};

function restoreAnswer(questionIndex, answer) {
    const question = currentQuiz.questions[questionIndex];
    
    if (question.type === 'mcq') {
        document.querySelectorAll(`.question-container[data-index="${questionIndex}"] .option`)[answer]
            .classList.add('selected');
    } else if (question.type === 'true_false') {
        const selectedOption = document.querySelector(`.question-container[data-index="${questionIndex}"] .option:${answer === 'true' ? 'first-child' : 'last-child'}`);
        if (selectedOption) {
            selectedOption.classList.add('selected');
        }
    } else if (question.type === 'short_answer') {
        const textarea = document.querySelector(`.question-container[data-index="${questionIndex}"] .short-answer`);
        if (textarea) {
            textarea.value = answer;
        }
    }
}

async function submitQuiz() {
    const unanswered = currentQuiz.questions.filter((_, index) => !quizAnswers[index]).length;
    
    if (unanswered > 0) {
        const confirmSubmit = confirm(`You have ${unanswered} unanswered question(s). Are you sure you want to submit?`);
        if (!confirmSubmit) return;
    }
    
    try {
        Notifications.show('Submitting quiz...', 'info');
        stopQuizTimer();
        
        const response = await API.StudentAPI.submitQuizAnswers(currentAttempt.id, quizAnswers);
        
        // Show results
        showQuizResults(response.results);
        
        Notifications.show('Quiz submitted successfully!', 'success');
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function showQuizResults(results) {
    // Close quiz modal
    document.getElementById('quizModal').style.display = 'none';
    
    // Update results modal
    document.getElementById('finalScore').textContent = `${results.score}%`;
    document.getElementById('finalScore').parentElement.setAttribute('data-score', results.score);
    document.getElementById('correctAnswers').textContent = results.correct_answers;
    document.getElementById('incorrectAnswers').textContent = results.incorrect_answers;
    document.getElementById('timeTaken').textContent = formatTime(results.time_taken_minutes);
    
    // Load review
    loadReview(results.review || []);
    
    // Show results modal
    document.getElementById('resultsModal').style.display = 'flex';
}

function loadReview(reviewItems) {
    const container = document.getElementById('reviewList');
    
    container.innerHTML = reviewItems.map((item, index) => `
        <div class="review-item ${item.correct ? 'correct' : 'incorrect'}">
            <div class="review-question">
                Q${index + 1}: ${item.question}
            </div>
            <div class="review-answer">
                <strong>Your answer:</strong> ${item.user_answer || 'Not answered'}<br>
                <strong>Correct answer:</strong> ${item.correct_answer}<br>
                ${item.explanation ? `<em>${item.explanation}</em>` : ''}
            </div>
        </div>
    `).join('');
}

// ==================== TIMER FUNCTIONS ====================

function startQuizTimer() {
    updateTimerDisplay();
    timerInterval = setInterval(() => {
        quizTimeRemaining--;
        updateTimerDisplay();
        
        if (quizTimeRemaining <= 0) {
            stopQuizTimer();
            autoSubmitQuiz();
        }
    }, 1000);
}

function stopQuizTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function updateTimerDisplay() {
    const minutes = Math.floor(quizTimeRemaining / 60);
    const seconds = quizTimeRemaining % 60;
    document.getElementById('quizTimer').textContent = 
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    
    // Change color when time is running low
    if (quizTimeRemaining <= 300) { // 5 minutes
        document.getElementById('quizTimer').style.color = '#e74c3c';
    }
}

async function autoSubmitQuiz() {
    Notifications.show('Time\'s up! Auto-submitting quiz...', 'warning');
    await submitQuiz();
}

// ==================== STUDENT ACTION FUNCTIONS ====================

async function downloadCertificate() {
    try {
        Notifications.show('Generating certificate...', 'info');
        
        // This would call your certificate generation endpoint
        // For now, we'll simulate it
        setTimeout(() => {
            const link = document.createElement('a');
            link.href = '#'; // Your certificate URL
            link.download = 'certificate.pdf';
            link.click();
            Notifications.show('Certificate downloaded', 'success');
        }, 2000);
        
    } catch (error) {
        API.handleApiError(error);
    }
}

async function exportStudentResults() {
    try {
        const format = prompt('Enter export format (csv/json):', 'csv');
        if (!format || !['csv', 'json'].includes(format.toLowerCase())) {
            Notifications.show('Invalid format', 'error');
            return;
        }
        
        Notifications.show('Exporting results...', 'info');
        await API.StudentAPI.exportResults(format);
        Notifications.show('Results exported successfully', 'success');
        
    } catch (error) {
        API.handleApiError(error);
    }
}

async function requestNewQuiz() {
    const topic = prompt('Enter topic for new quiz:');
    if (!topic) return;
    
    const description = prompt('Enter description (optional):');
    
    try {
        await API.StudentAPI.requestNewQuiz(topic, description);
        Notifications.show('Quiz request submitted to admin', 'success');
    } catch (error) {
        API.handleApiError(error);
    }
}

async function submitFeedback() {
    const feedback = prompt('Enter your feedback:');
    if (!feedback) return;
    
    try {
        await API.StudentAPI.submitFeedback({ feedback });
        Notifications.show('Thank you for your feedback!', 'success');
    } catch (error) {
        API.handleApiError(error);
    }
}

// ==================== UTILITY FUNCTIONS ====================

function formatTime(minutes) {
    if (!minutes) return '0m';
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
}

function getScoreCategory(score) {
    if (score >= 90) return 'excellent';
    if (score >= 80) return 'good';
    if (score >= 70) return 'average';
    if (score >= 60) return 'below-average';
    return 'poor';
}

function updateQuizPagination(currentPage, totalPages) {
    const prevBtn = document.getElementById('prevQuizPageBtn');
    const nextBtn = document.getElementById('nextQuizPageBtn');
    const pageInfo = document.getElementById('quizPageInfo');
    
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ==================== ACTION FUNCTIONS (called from HTML) ====================

window.viewQuizDetails = async function(quizId) {
    try {
        // Show quiz details in a modal
        const response = await apiRequest(`/api/student/quizzes/${quizId}/details`);
        
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="close-modal">&times;</span>
                <h3>${response.title}</h3>
                <div class="quiz-details">
                    <p><strong>Topic:</strong> ${response.topic}</p>
                    <p><strong>Difficulty:</strong> ${response.difficulty}</p>
                    <p><strong>Questions:</strong> ${response.question_count}</p>
                    <p><strong>Duration:</strong> ${response.duration} minutes</p>
                    <p><strong>Description:</strong> ${response.description || 'No description'}</p>
                </div>
                <div class="quiz-stats">
                    <div class="stat">
                        <i class="fas fa-users"></i>
                        <span>${response.total_attempts} total attempts</span>
                    </div>
                    <div class="stat">
                        <i class="fas fa-star"></i>
                        <span>${response.average_score}% average score</span>
                    </div>
                </div>
                <div class="modal-actions">
                    <button class="btn-primary" onclick="startQuiz('${quizId}')">
                        <i class="fas fa-play"></i> Start Quiz
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        modal.style.display = 'flex';
        
        modal.querySelector('.close-modal').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
        
    } catch (error) {
        API.handleApiError(error);
    }
};

window.viewQuizResults = async function(attemptId) {
    try {
        const results = await API.StudentAPI.getQuizResults(attemptId);
        showQuizResults(results);
    } catch (error) {
        API.handleApiError(error);
    }
};

window.reviewQuiz = async function(attemptId) {
    // This would show a detailed review of the quiz
    Notifications.show('Loading quiz review...', 'info');
    // Implementation would be similar to viewQuizResults but with more details
};

window.resumeQuiz = async function(attemptId) {
    try {
        // Get the quiz from attempt
        const attempt = await apiRequest(`/api/student/quizzes/attempt/${attemptId}`);
        
        // Load the quiz and continue
        currentQuiz = await API.StudentAPI.getQuizForTaking(attempt.quiz_id);
        currentAttempt = attempt;
        
        // Load saved answers
        quizAnswers = attempt.answers || {};
        quizTimeRemaining = attempt.time_remaining || (currentQuiz.duration * 60);
        
        showQuizModal();
        startQuizTimer();
        
        // Show current question
        const currentQuestion = attempt.current_question || 0;
        showQuestion(currentQuestion);
        
        Notifications.show('Quiz resumed', 'success');
        
    } catch (error) {
        API.handleApiError(error);
    }
};

window.abandonQuiz = async function(attemptId) {
    if (!confirm('Are you sure you want to abandon this quiz? Your progress will be lost.')) return;
    
    try {
        await apiRequest(`/api/student/quizzes/attempt/${attemptId}/abandon`, { method: 'POST' });
        Notifications.show('Quiz abandoned', 'success');
        loadStudentAttempts();
    } catch (error) {
        API.handleApiError(error);
    }
};

window.retryQuizFromHistory = function(quizId) {
    if (confirm('Start new attempt of this quiz?')) {
        startQuiz(quizId);
    }
};

window.viewPDF = function(pdfId) {
    // Open PDF in new tab or modal
    window.open(`${API_BASE_URL}/api/student/resources/pdf/${pdfId}`, '_blank');
};

window.downloadPDF = function(pdfId) {
    // Trigger PDF download
    const link = document.createElement('a');
    link.href = `${API_BASE_URL}/api/student/resources/pdf/${pdfId}/download`;
    link.download = 'document.pdf';
    link.click();
};

async function handleStudentLogout() {
    try {
        await API.AuthAPI.logout();
        API.clearAuthData();
        Notifications.show('Logged out successfully', 'success');
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1000);
    } catch (error) {
        API.handleApiError(error);
        // Still redirect even if API call fails
        API.clearAuthData();
        window.location.href = 'index.html';
    }
}

// Initialize student portal
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initStudent);
} else {
    initStudent();
}

function initStudent() {
    console.log('Student portal initialized');
}