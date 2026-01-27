/**
 * Admin Dashboard JavaScript
 */

// Global variables
let currentPDFPage = 1;
let currentQuizPage = 1;
let currentStudentPage = 1;
let totalPDFPages = 1;
let totalQuizPages = 1;
let totalStudentPages = 1;
let selectedPDFs = new Set();
let selectedQuizzes = new Set();
let selectedStudents = new Set();
let uploadedFiles = [];

document.addEventListener('DOMContentLoaded', function() {
    // Check authentication
    if (!API.isAuthenticated()) {
        window.location.href = 'index.html';
        return;
    }
    
    if (!API.isAdmin()) {
        Notifications.show('Access denied. Admin only.', 'error');
        setTimeout(() => {
            window.location.href = 'student.html';
        }, 2000);
        return;
    }
    
    // Initialize
    loadAdminData();
    setupEventListeners();
    
    // Load initial data
    loadDashboardStats();
    loadPDFs();
    loadQuizzes();
    loadStudents();
    loadTopics();
});

function loadAdminData() {
    const userData = API.getUserData();
    if (userData) {
        document.getElementById('adminName').textContent = userData.name || 'Admin';
    }
}

function setupEventListeners() {
    // Navigation
    setupNavigation();
    
    // PDF Management
    setupPDFManagement();
    
    // Quiz Management
    setupQuizManagement();
    
    // Student Management
    setupStudentManagement();
    
    // System Settings
    setupSystemSettings();
    
    // Logout
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    
    // Modal close buttons
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('quizModal').style.display = 'none';
        });
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        const modal = document.getElementById('quizModal');
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

function setupNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.admin-section');
    
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
                            loadDashboardStats();
                            loadRecentActivity();
                            break;
                        case 'pdf-management':
                            loadPDFs();
                            break;
                        case 'quiz-management':
                            loadQuizzes();
                            loadQuestionBank();
                            break;
                        case 'student-management':
                            loadStudents();
                            loadStudentAnalytics();
                            break;
                        case 'analytics':
                            loadAnalytics();
                            break;
                        case 'system':
                            loadSystemSettings();
                            break;
                    }
                }
            });
        });
    });
}

function setupPDFManagement() {
    // PDF Upload
    const uploadBox = document.getElementById('pdfUploadBox');
    const fileInput = document.getElementById('pdfFileInput');
    
    uploadBox.addEventListener('click', () => fileInput.click());
    
    fileInput.addEventListener('change', handleFileUpload);
    
    // Drag and drop
    uploadBox.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadBox.style.borderColor = '#4a6fa5';
        uploadBox.style.background = '#f8f9ff';
    });
    
    uploadBox.addEventListener('dragleave', () => {
        uploadBox.style.borderColor = '#e9ecef';
        uploadBox.style.background = 'white';
    });
    
    uploadBox.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadBox.style.borderColor = '#e9ecef';
        uploadBox.style.background = 'white';
        
        if (e.dataTransfer.files.length) {
            handleFileUpload(e);
        }
    });
    
    // Process Selected PDFs
    document.getElementById('processSelectedBtn').addEventListener('click', processSelectedPDFs);
    
    // Delete Selected PDFs
    document.getElementById('deleteSelectedBtn').addEventListener('click', deleteSelectedPDFs);
    
    // PDF Search
    document.getElementById('pdfSearch').addEventListener('input', debounce(() => {
        currentPDFPage = 1;
        loadPDFs();
    }, 500));
    
    // PDF Pagination
    document.getElementById('prevPageBtn').addEventListener('click', () => {
        if (currentPDFPage > 1) {
            currentPDFPage--;
            loadPDFs();
        }
    });
    
    document.getElementById('nextPageBtn').addEventListener('click', () => {
        if (currentPDFPage < totalPDFPages) {
            currentPDFPage++;
            loadPDFs();
        }
    });
    
    // Select All PDFs
    document.getElementById('selectAllPDFs').addEventListener('change', function() {
        const checkboxes = document.querySelectorAll('#pdfTableBody input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
            const pdfId = checkbox.value;
            if (this.checked) {
                selectedPDFs.add(pdfId);
            } else {
                selectedPDFs.delete(pdfId);
            }
        });
        updatePDFActionButtons();
    });
}

function setupQuizManagement() {
    // Generate Quiz Button
    document.getElementById('generateQuizBtn').addEventListener('click', () => {
        showQuizGenerationModal();
    });
    
    // Quiz Filters
    document.getElementById('quizStatusFilter').addEventListener('change', () => {
        currentQuizPage = 1;
        loadQuizzes();
    });
    
    document.getElementById('topicFilter').addEventListener('change', () => {
        currentQuizPage = 1;
        loadQuizzes();
    });
    
    // Question Search
    document.getElementById('questionSearch').addEventListener('input', debounce(() => {
        loadQuestionBank();
    }, 500));
    
    document.getElementById('questionTypeFilter').addEventListener('change', () => {
        loadQuestionBank();
    });
}

function setupStudentManagement() {
    // Add Student Button
    document.getElementById('addStudentBtn').addEventListener('click', showAddStudentModal);
    
    // Student Pagination (would be added when table is loaded)
}

function setupSystemSettings() {
    // Save AI Settings
    document.getElementById('saveAISettings').addEventListener('click', saveAISettings);
    
    // Save System Parameters
    document.getElementById('saveSystemParams').addEventListener('click', saveSystemParams);
    
    // Save Security Settings
    document.getElementById('saveSecuritySettings').addEventListener('click', saveSecuritySettings);
    
    // Maintenance Buttons
    document.getElementById('clearCacheBtn').addEventListener('click', clearCache);
    document.getElementById('rebuildIndexBtn').addEventListener('click', rebuildIndex);
    document.getElementById('systemResetBtn').addEventListener('click', confirmSystemReset);
    
    // Export Buttons
    document.querySelectorAll('.export-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const type = this.getAttribute('data-type');
            exportData(type);
        });
    });
}

async function loadDashboardStats() {
    try {
        const stats = await API.AdminAPI.getDashboardStats();
        
        // Update stat cards
        document.getElementById('totalStudents').textContent = stats.total_students || 0;
        document.getElementById('totalPDFs').textContent = stats.total_pdfs || 0;
        document.getElementById('totalQuizzes').textContent = stats.total_quizzes || 0;
        document.getElementById('avgScore').textContent = `${stats.average_score || 0}%`;
        
        // Load charts
        if (window.loadCharts) {
            window.loadCharts(stats);
        }
        
    } catch (error) {
        API.handleApiError(error);
    }
}

async function loadRecentActivity() {
    try {
        // This would come from your API
        const activity = [
            {
                icon: 'fa-file-pdf',
                title: 'PDF Uploaded',
                description: 'Machine Learning Basics.pdf was uploaded',
                time: '10 minutes ago'
            },
            {
                icon: 'fa-question-circle',
                title: 'Quiz Generated',
                description: 'New quiz created: "Intro to Python"',
                time: '30 minutes ago'
            },
            {
                icon: 'fa-user-graduate',
                title: 'Student Registered',
                description: 'John Doe registered as new student',
                time: '1 hour ago'
            },
            {
                icon: 'fa-chart-line',
                title: 'Performance Updated',
                description: 'Average score increased by 5%',
                time: '2 hours ago'
            }
        ];
        
        const container = document.getElementById('recentActivity');
        container.innerHTML = activity.map(item => `
            <div class="activity-item">
                <div class="activity-icon">
                    <i class="fas ${item.icon}"></i>
                </div>
                <div class="activity-details">
                    <h4>${item.title}</h4>
                    <p>${item.description}</p>
                    <small class="timeline-time">${item.time}</small>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading activity:', error);
    }
}

async function loadPDFs() {
    try {
        const search = document.getElementById('pdfSearch').value;
        const response = await API.AdminAPI.getPDFs(currentPDFPage, 10, search);
        
        totalPDFPages = response.total_pages || 1;
        updatePagination('pdf', currentPDFPage, totalPDFPages);
        
        renderPDFTable(response.pdfs || []);
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function renderPDFTable(pdfs) {
    const tbody = document.getElementById('pdfTableBody');
    
    if (pdfs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center">No PDFs found</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = pdfs.map(pdf => `
        <tr>
            <td>
                <input type="checkbox" value="${pdf.id}" 
                       onchange="togglePDFSelection('${pdf.id}', this.checked)">
            </td>
            <td>
                <div class="file-info">
                    <i class="fas fa-file-pdf"></i>
                    <span>${pdf.filename}</span>
                </div>
            </td>
            <td>
                <span class="status-badge status-${pdf.status}">
                    ${pdf.status || 'pending'}
                </span>
            </td>
            <td>${pdf.pages || 'N/A'}</td>
            <td>${pdf.chunks || 'N/A'}</td>
            <td>${formatDate(pdf.upload_date)}</td>
            <td>
                <div class="action-buttons">
                    ${pdf.status === 'processed' ? `
                        <button class="btn-icon" onclick="generateQuizFromPDF('${pdf.id}')" 
                                title="Generate Quiz">
                            <i class="fas fa-question-circle"></i>
                        </button>
                    ` : ''}
                    ${pdf.status === 'uploaded' ? `
                        <button class="btn-icon" onclick="processPDF('${pdf.id}')" 
                                title="Process PDF">
                            <i class="fas fa-cogs"></i>
                        </button>
                    ` : ''}
                    <button class="btn-icon btn-danger" onclick="deletePDF('${pdf.id}')" 
                            title="Delete PDF">
                        <i class="fas fa-trash"></i>
                    </button>
                    <button class="btn-icon" onclick="viewPDFDetails('${pdf.id}')" 
                            title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    // Update select all checkbox
    document.getElementById('selectAllPDFs').checked = false;
    updatePDFActionButtons();
}

async function loadQuizzes() {
    try {
        const status = document.getElementById('quizStatusFilter').value;
        const topic = document.getElementById('topicFilter').value;
        
        const response = await API.AdminAPI.getQuizzes(status, topic, currentQuizPage, 10);
        
        totalQuizPages = response.total_pages || 1;
        renderQuizTable(response.quizzes || []);
        
        // Update stats
        document.getElementById('totalQuestions').textContent = response.total_questions || 0;
        document.getElementById('activeQuizzes').textContent = response.active_quizzes || 0;
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function renderQuizTable(quizzes) {
    const tbody = document.getElementById('quizTableBody');
    
    if (quizzes.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center">No quizzes found</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = quizzes.map(quiz => `
        <tr>
            <td>${quiz.id}</td>
            <td>
                <strong>${quiz.title}</strong>
                <br><small>${quiz.description || ''}</small>
            </td>
            <td>
                <span class="topic-badge">${quiz.topic || 'General'}</span>
            </td>
            <td>${quiz.question_count || 0}</td>
            <td>
                <span class="difficulty-badge difficulty-${quiz.difficulty || 'medium'}">
                    ${quiz.difficulty || 'Medium'}
                </span>
            </td>
            <td>
                <span class="status-badge status-${quiz.status}">
                    ${quiz.status || 'draft'}
                </span>
            </td>
            <td>${formatDate(quiz.created_at)}</td>
            <td>
                <div class="action-buttons">
                    <button class="btn-icon" onclick="viewQuiz('${quiz.id}')" title="View Quiz">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-icon" onclick="editQuiz('${quiz.id}')" title="Edit Quiz">
                        <i class="fas fa-edit"></i>
                    </button>
                    ${quiz.status === 'active' ? `
                        <button class="btn-icon" onclick="deactivateQuiz('${quiz.id}')" 
                                title="Deactivate">
                            <i class="fas fa-pause"></i>
                        </button>
                    ` : `
                        <button class="btn-icon" onclick="activateQuiz('${quiz.id}')" 
                                title="Activate">
                            <i class="fas fa-play"></i>
                        </button>
                    `}
                    <button class="btn-icon btn-danger" onclick="deleteQuiz('${quiz.id}')" 
                            title="Delete Quiz">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function loadQuestionBank() {
    try {
        // This would come from your API
        const questions = [
            {
                id: 1,
                text: "What is the time complexity of binary search?",
                type: "mcq",
                difficulty: "medium",
                topic: "Algorithms",
                created: "2024-01-15"
            },
            {
                id: 2,
                text: "Python is an interpreted language.",
                type: "true_false",
                difficulty: "easy",
                topic: "Programming",
                created: "2024-01-14"
            }
        ];
        
        const search = document.getElementById('questionSearch').value.toLowerCase();
        const typeFilter = document.getElementById('questionTypeFilter').value;
        
        const filteredQuestions = questions.filter(q => {
            const matchesSearch = q.text.toLowerCase().includes(search);
            const matchesType = typeFilter === 'all' || q.type === typeFilter;
            return matchesSearch && matchesType;
        });
        
        renderQuestionBank(filteredQuestions);
        
    } catch (error) {
        console.error('Error loading question bank:', error);
    }
}

function renderQuestionBank(questions) {
    const container = document.getElementById('questionsContainer');
    
    if (questions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-question-circle"></i>
                <p>No questions found</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = questions.map(q => `
        <div class="question-item">
            <div class="question-text">${q.text}</div>
            <div class="question-meta">
                <span class="question-type">${q.type.replace('_', ' ').toUpperCase()}</span>
                <span class="question-difficulty">${q.difficulty}</span>
                <span class="question-topic">${q.topic}</span>
                <span class="question-date">${formatDate(q.created)}</span>
            </div>
            <div class="question-actions">
                <button class="btn-small" onclick="editQuestion(${q.id})">
                    <i class="fas fa-edit"></i> Edit
                </button>
                <button class="btn-small btn-danger" onclick="deleteQuestion(${q.id})">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `).join('');
}

async function loadStudents() {
    try {
        const response = await API.AdminAPI.getStudents(currentStudentPage, 10);
        
        totalStudentPages = response.total_pages || 1;
        renderStudentTable(response.students || []);
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function renderStudentTable(students) {
    const tbody = document.getElementById('studentTableBody');
    
    if (students.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center">No students found</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = students.map(student => `
        <tr>
            <td>${student.id}</td>
            <td>
                <div class="student-info">
                    <i class="fas fa-user-circle"></i>
                    <div>
                        <strong>${student.name}</strong>
                        <br><small>ID: ${student.student_id || 'N/A'}</small>
                    </div>
                </div>
            </td>
            <td>${student.email}</td>
            <td>${student.quiz_count || 0}</td>
            <td>
                <span class="score-badge">
                    ${student.average_score || 0}%
                </span>
            </td>
            <td>${formatDate(student.last_active)}</td>
            <td>
                <span class="status-badge status-${student.status}">
                    ${student.status || 'active'}
                </span>
            </td>
            <td>
                <div class="action-buttons">
                    <button class="btn-icon" onclick="viewStudent(${student.id})" 
                            title="View Student">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn-icon" onclick="editStudent(${student.id})" 
                            title="Edit Student">
                        <i class="fas fa-edit"></i>
                    </button>
                    ${student.status === 'active' ? `
                        <button class="btn-icon" onclick="deactivateStudent(${student.id})" 
                                title="Deactivate">
                            <i class="fas fa-ban"></i>
                        </button>
                    ` : `
                        <button class="btn-icon" onclick="activateStudent(${student.id})" 
                                title="Activate">
                            <i class="fas fa-check"></i>
                        </button>
                    `}
                    <button class="btn-icon btn-danger" onclick="deleteStudent('${student.id}')" 
                            title="Delete Student">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function loadTopics() {
    try {
        // This would come from your API
        const topics = [
            { id: 'all', name: 'All Topics' },
            { id: 'programming', name: 'Programming' },
            { id: 'mathematics', name: 'Mathematics' },
            { id: 'science', name: 'Science' },
            { id: 'history', name: 'History' },
            { id: 'algorithms', name: 'Algorithms' },
            { id: 'machine_learning', name: 'Machine Learning' }
        ];
        
        const topicSelects = document.querySelectorAll('#topicFilter, #topicFilterStudent');
        topicSelects.forEach(select => {
            select.innerHTML = topics.map(topic => 
                `<option value="${topic.id}">${topic.name}</option>`
            ).join('');
        });
        
    } catch (error) {
        console.error('Error loading topics:', error);
    }
}

async function loadAnalytics() {
    try {
        const analytics = await API.AdminAPI.getAnalytics('7d');
        
        // This would be handled by charts.js
        if (window.loadAnalyticsCharts) {
            window.loadAnalyticsCharts(analytics);
        }
        
        // Load system metrics
        loadSystemMetrics(analytics.system_metrics);
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function loadSystemMetrics(metrics) {
    const container = document.getElementById('systemMetrics');
    if (!metrics) return;
    
    container.innerHTML = `
        <div class="metric-item">
            <span>CPU Usage:</span>
            <span class="metric-value">${metrics.cpu_usage || 0}%</span>
        </div>
        <div class="metric-item">
            <span>Memory Usage:</span>
            <span class="metric-value">${metrics.memory_usage || 0}%</span>
        </div>
        <div class="metric-item">
            <span>Active Connections:</span>
            <span class="metric-value">${metrics.active_connections || 0}</span>
        </div>
        <div class="metric-item">
            <span>Queue Size:</span>
            <span class="metric-value">${metrics.queue_size || 0}</span>
        </div>
    `;
}

async function loadSystemSettings() {
    try {
        const settings = await API.AdminAPI.getSystemSettings();
        
        // Populate form fields
        if (settings.ai_model) {
            document.getElementById('aiModel').value = settings.ai_model;
        }
        if (settings.question_difficulty) {
            document.getElementById('questionDifficulty').value = settings.question_difficulty;
        }
        if (settings.max_questions) {
            document.getElementById('maxQuestions').value = settings.max_questions;
        }
        if (settings.chunk_size) {
            document.getElementById('chunkSize').value = settings.chunk_size;
        }
        if (settings.overlap_size) {
            document.getElementById('overlapSize').value = settings.overlap_size;
        }
        if (settings.session_timeout) {
            document.getElementById('sessionTimeout').value = settings.session_timeout;
        }
        if (settings.enable_2fa !== undefined) {
            document.getElementById('enable2FA').checked = settings.enable_2fa;
        }
        if (settings.auto_logout !== undefined) {
            document.getElementById('autoLogout').checked = settings.auto_logout;
        }
        if (settings.password_policy) {
            document.getElementById('passwordPolicy').value = settings.password_policy;
        }
        
    } catch (error) {
        API.handleApiError(error);
    }
}

// ==================== EVENT HANDLERS ====================

function handleFileUpload(event) {
    const files = event.target.files || event.dataTransfer.files;
    uploadedFiles = Array.from(files);
    
    if (uploadedFiles.length === 0) return;
    
    // Validate files
    const validFiles = uploadedFiles.filter(file => {
        if (file.type !== 'application/pdf') {
            Notifications.show(`${file.name} is not a PDF file`, 'error');
            return false;
        }
        if (file.size > 50 * 1024 * 1024) { // 50MB
            Notifications.show(`${file.name} exceeds 50MB limit`, 'error');
            return false;
        }
        return true;
    });
    
    if (validFiles.length === 0) return;
    
    // Upload files
    validFiles.forEach(async (file) => {
        try {
            Notifications.show(`Uploading ${file.name}...`, 'info');
            
            const response = await API.AdminAPI.uploadPDF(file);
            
            Notifications.show(`${file.name} uploaded successfully`, 'success');
            
            // Reload PDF list
            loadPDFs();
            
        } catch (error) {
            Notifications.show(`Failed to upload ${file.name}: ${error.message}`, 'error');
        }
    });
    
    // Reset file input
    event.target.value = '';
}

async function processSelectedPDFs() {
    if (selectedPDFs.size === 0) {
        Notifications.show('No PDFs selected', 'warning');
        return;
    }
    
    const confirmProcess = confirm(`Process ${selectedPDFs.size} selected PDF(s)?`);
    if (!confirmProcess) return;
    
    try {
        Notifications.show('Processing PDFs...', 'info');
        
        for (const pdfId of selectedPDFs) {
            await API.AdminAPI.processPDF(pdfId);
            Notifications.show(`PDF ${pdfId} processing started`, 'success');
        }
        
        // Clear selection
        selectedPDFs.clear();
        updatePDFActionButtons();
        
        // Reload PDF list after delay
        setTimeout(loadPDFs, 2000);
        
    } catch (error) {
        API.handleApiError(error);
    }
}

async function deleteSelectedPDFs() {
    if (selectedPDFs.size === 0) {
        Notifications.show('No PDFs selected', 'warning');
        return;
    }
    
    const confirmDelete = confirm(`Delete ${selectedPDFs.size} selected PDF(s)? This action cannot be undone.`);
    if (!confirmDelete) return;
    
    try {
        Notifications.show('Deleting PDFs...', 'info');
        
        for (const pdfId of selectedPDFs) {
            await API.AdminAPI.deletePDF(pdfId);
        }
        
        Notifications.show('PDFs deleted successfully', 'success');
        
        // Clear selection
        selectedPDFs.clear();
        updatePDFActionButtons();
        
        // Reload PDF list
        loadPDFs();
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function showQuizGenerationModal() {
    // First load available PDFs for selection
    loadAvailablePDFsForQuiz().then(() => {
        const modal = document.getElementById('quizModal');
        modal.style.display = 'flex';
    });
}

async function loadAvailablePDFsForQuiz() {
    try {
        const response = await API.AdminAPI.getPDFs(1, 100, '');
        const processedPDFs = (response.pdfs || []).filter(pdf => pdf.status === 'processed');
        
        const select = document.getElementById('selectPDF');
        select.innerHTML = `
            <option value="">Choose a PDF</option>
            ${processedPDFs.map(pdf => 
                `<option value="${pdf.id}">${pdf.filename}</option>`
            ).join('')}
        `;
        
    } catch (error) {
        API.handleApiError(error);
    }
}

async function handleQuizGeneration() {
    const form = document.getElementById('quizGenerationForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const quizData = {
        title: document.getElementById('quizTitle').value,
        pdf_id: document.getElementById('selectPDF').value,
        num_questions: parseInt(document.getElementById('numQuestions').value),
        difficulty: document.getElementById('quizDifficulty').value,
        question_types: Array.from(document.querySelectorAll('input[name="questionType"]:checked'))
            .map(cb => cb.value)
    };
    
    try {
        Notifications.show('Generating quiz...', 'info');
        
        const response = await API.AdminAPI.generateQuiz(quizData);
        
        Notifications.show('Quiz generated successfully!', 'success');
        
        // Close modal
        document.getElementById('quizModal').style.display = 'none';
        
        // Reset form
        form.reset();
        
        // Reload quizzes
        loadQuizzes();
        
        // Show quiz details
        viewQuiz(response.quiz_id);
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function showAddStudentModal() {
    // Create and show modal for adding student
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close-modal">&times;</span>
            <h3><i class="fas fa-user-plus"></i> Add New Student</h3>
            <form id="addStudentForm">
                <div class="form-group">
                    <label for="studentName">Full Name *</label>
                    <input type="text" id="studentName" required>
                </div>
                <div class="form-group">
                    <label for="studentEmail">Email *</label>
                    <input type="email" id="studentEmail" required>
                </div>
                <div class="form-group">
                    <label for="studentPassword">Password *</label>
                    <input type="password" id="studentPassword" required minlength="6">
                </div>
                <div class="form-group">
                    <label for="studentId">Student ID</label>
                    <input type="text" id="studentId">
                </div>
                <div class="modal-actions">
                    <button type="button" class="btn-secondary close-modal">Cancel</button>
                    <button type="submit" class="btn-primary">Add Student</button>
                </div>
            </form>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'flex';
    
    // Close modal
    const closeBtn = modal.querySelector('.close-modal');
    closeBtn.addEventListener('click', () => {
        modal.remove();
    });
    
    // Form submission
    const form = modal.querySelector('#addStudentForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const studentData = {
            name: document.getElementById('studentName').value,
            email: document.getElementById('studentEmail').value,
            password: document.getElementById('studentPassword').value,
            student_id: document.getElementById('studentId').value
        };
        
        try {
            await API.AdminAPI.addStudent(studentData);
            Notifications.show('Student added successfully', 'success');
            modal.remove();
            loadStudents();
        } catch (error) {
            API.handleApiError(error);
        }
    });
    
    // Close when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

async function saveAISettings() {
    const settings = {
        ai_model: document.getElementById('aiModel').value,
        question_difficulty: document.getElementById('questionDifficulty').value,
        max_questions: parseInt(document.getElementById('maxQuestions').value)
    };
    
    try {
        await API.AdminAPI.updateSystemSettings(settings);
        Notifications.show('AI settings saved successfully', 'success');
    } catch (error) {
        API.handleApiError(error);
    }
}

async function saveSystemParams() {
    const settings = {
        chunk_size: parseInt(document.getElementById('chunkSize').value),
        overlap_size: parseInt(document.getElementById('overlapSize').value),
        session_timeout: parseInt(document.getElementById('sessionTimeout').value)
    };
    
    try {
        await API.AdminAPI.updateSystemSettings(settings);
        Notifications.show('System parameters saved successfully', 'success');
    } catch (error) {
        API.handleApiError(error);
    }
}

async function saveSecuritySettings() {
    const settings = {
        enable_2fa: document.getElementById('enable2FA').checked,
        auto_logout: document.getElementById('autoLogout').checked,
        password_policy: document.getElementById('passwordPolicy').value
    };
    
    try {
        await API.AdminAPI.updateSystemSettings(settings);
        Notifications.show('Security settings saved successfully', 'success');
    } catch (error) {
        API.handleApiError(error);
    }
}

async function clearCache() {
    const confirmClear = confirm('Clear all system cache? This may temporarily affect performance.');
    if (!confirmClear) return;
    
    try {
        await API.AdminAPI.clearCache();
        Notifications.show('Cache cleared successfully', 'success');
    } catch (error) {
        API.handleApiError(error);
    }
}

async function rebuildIndex() {
    const confirmRebuild = confirm('Rebuild search index? This may take several minutes.');
    if (!confirmRebuild) return;
    
    try {
        Notifications.show('Rebuilding index...', 'info');
        await API.AdminAPI.rebuildIndex();
        Notifications.show('Index rebuilt successfully', 'success');
    } catch (error) {
        API.handleApiError(error);
    }
}

function confirmSystemReset() {
    const confirmReset = confirm(
        '⚠️ DANGER ⚠️\n\n' +
        'This will reset the entire system to factory defaults.\n' +
        'ALL DATA WILL BE LOST!\n\n' +
        'Type "RESET" to confirm:'
    );
    
    if (!confirmReset) return;
    
    const userInput = prompt('Type "RESET" to confirm:');
    if (userInput === 'RESET') {
        Notifications.show('System reset initiated...', 'warning');
        // This would call your backend reset endpoint
    }
}

async function exportData(type) {
    try {
        Notifications.show(`Exporting ${type.toUpperCase()} data...`, 'info');
        
        const response = await API.AdminAPI.exportData(type, {
            include: ['students', 'quizzes', 'pdfs', 'analytics']
        });
        
        // Create download link
        const blob = new Blob([response.data], { type: getMimeType(type) });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `quiz_data_${Date.now()}.${type}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        Notifications.show('Data exported successfully', 'success');
        
    } catch (error) {
        API.handleApiError(error);
    }
}

function getMimeType(type) {
    const mimeTypes = {
        pdf: 'application/pdf',
        csv: 'text/csv',
        json: 'application/json'
    };
    return mimeTypes[type] || 'application/octet-stream';
}

async function handleLogout() {
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

// ==================== UTILITY FUNCTIONS ====================

function togglePDFSelection(pdfId, isSelected) {
    if (isSelected) {
        selectedPDFs.add(pdfId);
    } else {
        selectedPDFs.delete(pdfId);
        document.getElementById('selectAllPDFs').checked = false;
    }
    updatePDFActionButtons();
}

function updatePDFActionButtons() {
    const hasSelection = selectedPDFs.size > 0;
    document.getElementById('processSelectedBtn').disabled = !hasSelection;
    document.getElementById('deleteSelectedBtn').disabled = !hasSelection;
}

function updatePagination(type, currentPage, totalPages) {
    if (type === 'pdf') {
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        const pageInfo = document.getElementById('pageInfo');
        
        prevBtn.disabled = currentPage === 1;
        nextBtn.disabled = currentPage === totalPages;
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    }
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

window.processPDF = async function(pdfId) {
    try {
        await API.AdminAPI.processPDF(pdfId);
        Notifications.show('PDF processing started', 'success');
        setTimeout(loadPDFs, 2000);
    } catch (error) {
        API.handleApiError(error);
    }
};

window.deletePDF = async function(pdfId) {
    if (!confirm('Are you sure you want to delete this PDF?')) return;
    
    try {
        await API.AdminAPI.deletePDF(pdfId);
        Notifications.show('PDF deleted successfully', 'success');
        loadPDFs();
    } catch (error) {
        API.handleApiError(error);
    }
};

window.generateQuizFromPDF = function(pdfId) {
    showQuizGenerationModal();
    // Pre-select the PDF
    setTimeout(() => {
        document.getElementById('selectPDF').value = pdfId;
    }, 100);
};

window.viewPDFDetails = function(pdfId) {
    // Show PDF details modal
    Notifications.show(`Viewing PDF ${pdfId} details...`, 'info');
    // Implement PDF details view
};

window.viewQuiz = async function(quizId) {
    try {
        const quiz = await API.AdminAPI.getQuizDetails(quizId);
        
        // Show quiz details modal
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="close-modal">&times;</span>
                <h3><i class="fas fa-question-circle"></i> ${quiz.title}</h3>
                <div class="quiz-details">
                    <p><strong>Topic:</strong> ${quiz.topic}</p>
                    <p><strong>Difficulty:</strong> ${quiz.difficulty}</p>
                    <p><strong>Questions:</strong> ${quiz.question_count}</p>
                    <p><strong>Status:</strong> ${quiz.status}</p>
                    <p><strong>Created:</strong> ${formatDate(quiz.created_at)}</p>
                </div>
                <h4>Questions:</h4>
                <div class="questions-list">
                    ${(quiz.questions || []).map((q, i) => `
                        <div class="question-item">
                            <strong>Q${i + 1}:</strong> ${q.text}
                            <div class="question-type">${q.type}</div>
                        </div>
                    `).join('')}
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

window.activateQuiz = async function(quizId) {
    try {
        await API.AdminAPI.updateQuizStatus(quizId, 'active');
        Notifications.show('Quiz activated', 'success');
        loadQuizzes();
    } catch (error) {
        API.handleApiError(error);
    }
};

window.deactivateQuiz = async function(quizId) {
    try {
        await API.AdminAPI.updateQuizStatus(quizId, 'inactive');
        Notifications.show('Quiz deactivated', 'success');
        loadQuizzes();
    } catch (error) {
        API.handleApiError(error);
    }
};

window.deleteQuiz = async function(quizId) {
    if (!confirm('Are you sure you want to delete this quiz?')) return;
    
    try {
        // This endpoint would need to be added to your backend
        await apiRequest(`/api/admin/quizzes/${quizId}`, { method: 'DELETE' });
        Notifications.show('Quiz deleted', 'success');
        loadQuizzes();
    } catch (error) {
        API.handleApiError(error);
    }
};

// Add event listener for quiz generation form
document.addEventListener('DOMContentLoaded', function() {
    const quizForm = document.getElementById('quizGenerationForm');
    if (quizForm) {
        quizForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleQuizGeneration();
        });
    }
});

// Initialize when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAdmin);
} else {
    initAdmin();
}

function initAdmin() {
    // Admin specific initialization
    console.log('Admin dashboard initialized');
}