/**
 * Authentication Page JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if user is already logged in
    if (API.isAuthenticated()) {
        const role = API.getUserRole();
        if (role === 'admin') {
            window.location.href = 'admin.html';
        } else if (role === 'student') {
            window.location.href = 'student.html';
        }
        return;
    }
    
    // Tab switching
    const tabButtons = document.querySelectorAll('.tab-btn');
    const authForms = document.querySelectorAll('.auth-form');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            
            // Update active tab button
            tabButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding form
            authForms.forEach(form => {
                form.classList.remove('active');
                if (form.id === tabId) {
                    form.classList.add('active');
                }
            });
        });
    });
    
    // Student Login Form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('loginEmail').value;
            const password = document.getElementById('loginPassword').value;
            
            try {
                Notifications.show('Logging in...', 'info');
                
                const response = await API.AuthAPI.studentLogin(email, password);
                
                API.setAuthData(response.access_token, 'student', response.user);
                Notifications.show('Login successful! Redirecting...', 'success');
                
                setTimeout(() => {
                    window.location.href = 'student.html';
                }, 1000);
                
            } catch (error) {
                Notifications.show(error.message || 'Login failed', 'error');
            }
        });
    }
    
    // Student Registration Form
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const name = document.getElementById('regName').value;
            const email = document.getElementById('regEmail').value;
            const password = document.getElementById('regPassword').value;
            
            try {
                Notifications.show('Creating account...', 'info');
                
                const response = await API.AuthAPI.studentRegister(name, email, password);
                
                API.setAuthData(response.access_token, 'student', response.user);
                Notifications.show('Registration successful! Redirecting...', 'success');
                
                setTimeout(() => {
                    window.location.href = 'student.html';
                }, 1000);
                
            } catch (error) {
                Notifications.show(error.message || 'Registration failed', 'error');
            }
        });
    }
    
    // Admin Login Form
    const adminForm = document.getElementById('adminForm');
    if (adminForm) {
        adminForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('adminEmail').value;
            const password = document.getElementById('adminPassword').value;
            
            try {
                Notifications.show('Admin login...', 'info');
                
                const response = await API.AuthAPI.adminLogin(email, password);
                
                API.setAuthData(response.access_token, 'admin', response.user);
                Notifications.show('Admin login successful! Redirecting...', 'success');
                
                setTimeout(() => {
                    window.location.href = 'admin.html';
                }, 1000);
                
            } catch (error) {
                Notifications.show(error.message || 'Admin login failed', 'error');
            }
        });
    }
    
    // Demo credentials auto-fill
    const demoCredentials = document.querySelectorAll('.demo-credentials p');
    demoCredentials.forEach(cred => {
        cred.addEventListener('click', function() {
            const text = this.textContent;
            const match = text.match(/([^:]+)\s*\/\s*(.+)/);
            if (match) {
                const [, email, password] = match;
                
                // Find active form and fill credentials
                const activeForm = document.querySelector('.auth-form.active');
                if (activeForm.id === 'login') {
                    document.getElementById('loginEmail').value = email.trim();
                    document.getElementById('loginPassword').value = password.trim();
                } else if (activeForm.id === 'admin') {
                    document.getElementById('adminEmail').value = email.trim();
                    document.getElementById('adminPassword').value = password.trim();
                }
                
                Notifications.show('Demo credentials filled', 'info');
            }
        });
    });
});