/**
 * API Configuration and Utility Functions
 */

// API Base URL - Point to your Docker backend (adjust if needed)
const API_BASE_URL = 'http://localhost:8080';
// For production with Nginx, you might use: 'http://localhost:81/api'

// Get authentication token from localStorage
function getAuthToken() {
    return localStorage.getItem('auth_token');
}

// Get user role from localStorage
function getUserRole() {
    return localStorage.getItem('user_role');
}

// Get user data from localStorage
function getUserData() {
    const userData = localStorage.getItem('user_data');
    return userData ? JSON.parse(userData) : null;
}

// Set authentication data
function setAuthData(token, role, userData) {
    localStorage.setItem('auth_token', token);
    localStorage.setItem('user_role', role);
    localStorage.setItem('user_data', JSON.stringify(userData));
}

// Clear authentication data
function clearAuthData() {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('user_data');
}

// Check if user is authenticated
function isAuthenticated() {
    return !!getAuthToken();
}

// Check if user is admin
function isAdmin() {
    return getUserRole() === 'admin';
}

// Check if user is student
function isStudent() {
    return getUserRole() === 'student';
}

// API Request Helper
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const token = getAuthToken();
    
    const defaultHeaders = {
        'Content-Type': 'application/json',
    };
    
    if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
    }
    
    const config = {
        headers: {
            ...defaultHeaders,
            ...options.headers,
        },
        ...options,
    };
    
    try {
        const response = await fetch(url, config);
        
        // Handle 401 Unauthorized
        if (response.status === 401) {
            clearAuthData();
            window.location.href = 'index.html';
            throw new Error('Session expired. Please login again.');
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || `API Error: ${response.status}`);
        }
        
        return data;
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

// Auth API Functions
const AuthAPI = {
    // Student Login
    async studentLogin(email, password) {
        return await apiRequest('/api/auth/login/student', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
    },
    
    // Admin Login
    async adminLogin(email, password) {
        return await apiRequest('/api/auth/login/admin', {
            method: 'POST',
            body: JSON.stringify({ email, password }),
        });
    },
    
    // Student Registration
    async studentRegister(name, email, password) {
        return await apiRequest('/api/auth/register/student', {
            method: 'POST',
            body: JSON.stringify({ name, email, password }),
        });
    },
    
    // Logout
    async logout() {
        return await apiRequest('/api/auth/logout', {
            method: 'POST',
        });
    },
    
    // Get current user
    async getCurrentUser() {
        return await apiRequest('/api/auth/me');
    },
};

// Admin API Functions
const AdminAPI = {
    // Dashboard Stats
    async getDashboardStats() {
        return await apiRequest('/api/admin/dashboard/stats');
    },
    
    // Get all PDFs
    async getPDFs(page = 1, limit = 10, search = '') {
        const params = new URLSearchParams({
            page: page.toString(),
            limit: limit.toString(),
            search,
        }).toString();
        return await apiRequest(`/api/admin/pdfs?${params}`);
    },
    
    // Upload PDF
    async uploadPDF(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        return await apiRequest('/api/admin/pdfs/upload', {
            method: 'POST',
            headers: {},
            body: formData,
        });
    },
    
    // Process PDF
    async processPDF(pdfId) {
        return await apiRequest(`/api/admin/pdfs/${pdfId}/process`, {
            method: 'POST',
        });
    },
    
    // Delete PDF
    async deletePDF(pdfId) {
        return await apiRequest(`/api/admin/pdfs/${pdfId}`, {
            method: 'DELETE',
        });
    },
    
    // Get all quizzes
    async getQuizzes(status = 'all', topic = 'all', page = 1, limit = 10) {
        const params = new URLSearchParams({
            status,
            topic,
            page: page.toString(),
            limit: limit.toString(),
        }).toString();
        return await apiRequest(`/api/admin/quizzes?${params}`);
    },
    
    // Generate quiz
    async generateQuiz(data) {
        return await apiRequest('/api/admin/quizzes/generate', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    },
    
    // Get quiz details
    async getQuizDetails(quizId) {
        return await apiRequest(`/api/admin/quizzes/${quizId}`);
    },
    
    // Update quiz status
    async updateQuizStatus(quizId, status) {
        return await apiRequest(`/api/admin/quizzes/${quizId}/status`, {
            method: 'PUT',
            body: JSON.stringify({ status }),
        });
    },
    
    // Get all students
    async getStudents(page = 1, limit = 10) {
        const params = new URLSearchParams({
            page: page.toString(),
            limit: limit.toString(),
        }).toString();
        return await apiRequest(`/api/admin/students?${params}`);
    },
    
    // Add student
    async addStudent(studentData) {
        return await apiRequest('/api/admin/students', {
            method: 'POST',
            body: JSON.stringify(studentData),
        });
    },
    
    // Update student
    async updateStudent(studentId, studentData) {
        return await apiRequest(`/api/admin/students/${studentId}`, {
            method: 'PUT',
            body: JSON.stringify(studentData),
        });
    },
    
    // Delete student
    async deleteStudent(studentId) {
        return await apiRequest(`/api/admin/students/${studentId}`, {
            method: 'DELETE',
        });
    },
    
    // Get analytics
    async getAnalytics(timeRange = '7d') {
        return await apiRequest(`/api/admin/analytics?range=${timeRange}`);
    },
    
    // Export data
    async exportData(type, data) {
        return await apiRequest('/api/admin/export', {
            method: 'POST',
            body: JSON.stringify({ type, data }),
        });
    },
    
    // Get system settings
    async getSystemSettings() {
        return await apiRequest('/api/admin/settings');
    },
    
    // Update system settings
    async updateSystemSettings(settings) {
        return await apiRequest('/api/admin/settings', {
            method: 'PUT',
            body: JSON.stringify(settings),
        });
    },
    
    // Clear cache
    async clearCache() {
        return await apiRequest('/api/admin/system/clear-cache', {
            method: 'POST',
        });
    },
    
    // Rebuild index
    async rebuildIndex() {
        return await apiRequest('/api/admin/system/rebuild-index', {
            method: 'POST',
        });
    },
};

// Student API Functions
const StudentAPI = {
    // Get student dashboard
    async getDashboard() {
        return await apiRequest('/api/student/dashboard');
    },
    
    // Get available quizzes
    async getAvailableQuizzes(topic = 'all', difficulty = 'all', page = 1, limit = 9) {
        const params = new URLSearchParams({
            topic,
            difficulty,
            page: page.toString(),
            limit: limit.toString(),
        }).toString();
        return await apiRequest(`/api/student/quizzes/available?${params}`);
    },
    
    // Get quiz for taking
    async getQuizForTaking(quizId) {
        return await apiRequest(`/api/student/quizzes/${quizId}/take`);
    },
    
    // Start quiz attempt
    async startQuizAttempt(quizId) {
        return await apiRequest(`/api/student/quizzes/${quizId}/attempt`, {
            method: 'POST',
        });
    },
    
    // Submit quiz answers
    async submitQuizAnswers(attemptId, answers) {
        return await apiRequest(`/api/student/quizzes/attempt/${attemptId}/submit`, {
            method: 'POST',
            body: JSON.stringify({ answers }),
        });
    },
    
    // Get quiz results
    async getQuizResults(attemptId) {
        return await apiRequest(`/api/student/quizzes/attempt/${attemptId}/results`);
    },
    
    // Get student attempts
    async getAttempts(status = 'all', page = 1, limit = 10) {
        const params = new URLSearchParams({
            status,
            page: page.toString(),
            limit: limit.toString(),
        }).toString();
        return await apiRequest(`/api/student/quizzes/attempts?${params}`);
    },
    
    // Get performance analytics
    async getPerformanceAnalytics() {
        return await apiRequest('/api/student/analytics/performance');
    },
    
    // Get resources
    async getResources() {
        return await apiRequest('/api/student/resources');
    },
    
    // Request new quiz
    async requestNewQuiz(topic, description) {
        return await apiRequest('/api/student/quizzes/request', {
            method: 'POST',
            body: JSON.stringify({ topic, description }),
        });
    },
    
    // Submit feedback
    async submitFeedback(feedback) {
        return await apiRequest('/api/student/feedback', {
            method: 'POST',
            body: JSON.stringify(feedback),
        });
    },
    
    // Export results
    async exportResults(format) {
        return await apiRequest('/api/student/export', {
            method: 'POST',
            body: JSON.stringify({ format }),
        });
    },
};

// Notification System
class NotificationSystem {
    constructor() {
        this.container = document.getElementById('notificationContainer');
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'notificationContainer';
            this.container.className = 'notification-container';
            document.body.appendChild(this.container);
        }
    }
    
    show(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        const icon = this.getIcon(type);
        notification.innerHTML = `
            ${icon}
            <span>${message}</span>
        `;
        
        this.container.appendChild(notification);
        
        // Auto remove after duration
        setTimeout(() => {
            this.remove(notification);
        }, duration);
        
        // Click to dismiss
        notification.addEventListener('click', () => this.remove(notification));
        
        return notification;
    }
    
    getIcon(type) {
        const icons = {
            success: '<i class="fas fa-check-circle"></i>',
            error: '<i class="fas fa-exclamation-circle"></i>',
            warning: '<i class="fas fa-exclamation-triangle"></i>',
            info: '<i class="fas fa-info-circle"></i>',
        };
        return icons[type] || icons.info;
    }
    
    remove(notification) {
        if (notification.parentNode === this.container) {
            notification.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => {
                this.container.removeChild(notification);
            }, 300);
        }
    }
    
    clear() {
        while (this.container.firstChild) {
            this.container.removeChild(this.container.firstChild);
        }
    }
}

// Export the API and utilities
window.API = {
    AuthAPI,
    AdminAPI,
    StudentAPI,
    isAuthenticated,
    isAdmin,
    isStudent,
    getUserData,
    getAuthToken,
    clearAuthData,
};

// Initialize notification system
window.Notifications = new NotificationSystem();

// Error handler for API requests
window.handleApiError = (error) => {
    console.error('API Error:', error);
    Notifications.show(error.message || 'An error occurred', 'error');
};

// Export function to check auth and redirect
window.checkAuthAndRedirect = () => {
    if (!isAuthenticated()) {
        window.location.href = 'index.html';
        return false;
    }
    
    const currentPage = window.location.pathname.split('/').pop();
    const role = getUserRole();
    
    if (role === 'admin' && currentPage !== 'admin.html') {
        window.location.href = 'admin.html';
        return false;
    }
    
    if (role === 'student' && currentPage !== 'student.html') {
        window.location.href = 'student.html';
        return false;
    }
    
    return true;
};