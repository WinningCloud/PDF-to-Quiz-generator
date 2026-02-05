/**
 * Charts and Graphs JavaScript for Analytics
 */

// Initialize charts when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize charts if we're on a page that needs them
    if (document.getElementById('dailyActivityChart') || 
        document.getElementById('progressChart')) {
        loadCharts();
    }
});

function loadCharts(data) {
    // Load admin dashboard charts
    loadAdminCharts(data);
    
    // Load student charts if on student page
    if (document.getElementById('progressChart')) {
        loadStudentCharts(data);
    }
}

function loadAdminCharts(stats) {
    // Daily Activity Chart
    const dailyCtx = document.getElementById('dailyActivityChart');
    if (dailyCtx) {
        new Chart(dailyCtx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Quizzes Taken',
                    data: stats.daily_activity || [12, 19, 8, 15, 12, 18, 14],
                    borderColor: '#4a6fa5',
                    backgroundColor: 'rgba(74, 111, 165, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'PDFs Uploaded',
                    data: stats.pdf_uploads || [3, 5, 2, 4, 3, 6, 2],
                    borderColor: '#4fc3a1',
                    backgroundColor: 'rgba(79, 195, 161, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Count'
                        }
                    }
                }
            }
        });
    }
    
    // Question Type Distribution Chart
    const questionTypeCtx = document.getElementById('questionTypeChart');
    if (questionTypeCtx) {
        new Chart(questionTypeCtx, {
            type: 'doughnut',
            data: {
                labels: ['Multiple Choice', 'True/False', 'Short Answer', 'Matching', 'Fill-in'],
                datasets: [{
                    data: stats.question_types || [45, 25, 15, 10, 5],
                    backgroundColor: [
                        '#4a6fa5',
                        '#4fc3a1',
                        '#ff9800',
                        '#9c27b0',
                        '#e74c3c'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right',
                    },
                    title: {
                        display: false
                    }
                }
            }
        });
    }
    
    // Score Distribution Chart (Student Management)
    const scoreDistCtx = document.getElementById('scoreDistributionChart');
    if (scoreDistCtx) {
        new Chart(scoreDistCtx, {
            type: 'bar',
            data: {
                labels: ['0-20%', '21-40%', '41-60%', '61-80%', '81-100%'],
                datasets: [{
                    label: 'Number of Students',
                    data: stats.score_distribution || [2, 5, 12, 20, 15],
                    backgroundColor: '#4a6fa5',
                    borderColor: '#166088',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Score Distribution'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Students'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Score Range'
                        }
                    }
                }
            }
        });
    }
    
    // Improvement Chart
    const improvementCtx = document.getElementById('improvementChart');
    if (improvementCtx) {
        new Chart(improvementCtx, {
            type: 'line',
            data: {
                labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [{
                    label: 'Average Score',
                    data: stats.improvement_trend || [65, 68, 72, 75],
                    borderColor: '#4fc3a1',
                    backgroundColor: 'rgba(79, 195, 161, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Student Improvement Over Time'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        min: 0,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Average Score (%)'
                        }
                    }
                }
            }
        });
    }
}

function loadAnalyticsCharts(analytics) {
    // Usage Trends Chart
    const usageCtx = document.getElementById('usageTrendsChart');
    if (usageCtx) {
        new Chart(usageCtx, {
            type: 'line',
            data: {
                labels: analytics.time_labels || ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Active Users',
                    data: analytics.active_users || [150, 180, 200, 220, 240, 260],
                    borderColor: '#4a6fa5',
                    backgroundColor: 'rgba(74, 111, 165, 0.1)',
                    borderWidth: 2,
                    fill: true
                }, {
                    label: 'Quizzes Generated',
                    data: analytics.quizzes_generated || [45, 60, 75, 80, 90, 100],
                    borderColor: '#4fc3a1',
                    backgroundColor: 'rgba(79, 195, 161, 0.1)',
                    borderWidth: 2,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                }
            }
        });
    }
    
    // Peak Hours Chart
    const peakCtx = document.getElementById('peakHoursChart');
    if (peakCtx) {
        new Chart(peakCtx, {
            type: 'bar',
            data: {
                labels: analytics.hour_labels || Array.from({length: 24}, (_, i) => i + ':00'),
                datasets: [{
                    label: 'Activity',
                    data: analytics.peak_hours || Array(24).fill(0).map(() => Math.floor(Math.random() * 100)),
                    backgroundColor: '#ff9800',
                    borderColor: '#f57c00',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Activities'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Hour of Day'
                        }
                    }
                }
            }
        });
    }
    
    // Topic Popularity Chart
    const topicCtx = document.getElementById('topicPopularityChart');
    if (topicCtx) {
        new Chart(topicCtx, {
            type: 'horizontalBar',
            data: {
                labels: analytics.topics || ['Programming', 'Mathematics', 'Science', 'History', 'Languages'],
                datasets: [{
                    label: 'Quiz Attempts',
                    data: analytics.topic_popularity || [120, 85, 70, 45, 30],
                    backgroundColor: [
                        '#4a6fa5',
                        '#4fc3a1',
                        '#ff9800',
                        '#9c27b0',
                        '#e74c3c'
                    ]
                }]
            },
            options: {
                responsive: true,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Attempts'
                        }
                    }
                }
            }
        });
    }
}

function loadStudentCharts(data) {
    // Student Progress Chart
    const progressCtx = document.getElementById('progressChart');
    if (progressCtx) {
        new Chart(progressCtx, {
            type: 'line',
            data: {
                labels: data.progress_labels || ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5'],
                datasets: [{
                    label: 'Your Score',
                    data: data.progress_scores || [65, 70, 72, 78, 82],
                    borderColor: '#4a6fa5',
                    backgroundColor: 'rgba(74, 111, 165, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Class Average',
                    data: data.class_average || [68, 69, 71, 72, 74],
                    borderColor: '#4fc3a1',
                    backgroundColor: 'rgba(79, 195, 161, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    borderDash: [5, 5]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Learning Progress'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        min: 0,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Score (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                }
            }
        });
    }
}

function loadStudentAnalyticsCharts(analytics) {
    // Score Chart
    const scoreCtx = document.getElementById('scoreChart');
    if (scoreCtx) {
        new Chart(scoreCtx, {
            type: 'radar',
            data: {
                labels: analytics.skill_labels || ['Knowledge', 'Application', 'Analysis', 'Synthesis', 'Evaluation'],
                datasets: [{
                    label: 'Your Skills',
                    data: analytics.skill_scores || [85, 78, 92, 65, 88],
                    backgroundColor: 'rgba(74, 111, 165, 0.2)',
                    borderColor: '#4a6fa5',
                    borderWidth: 2
                }, {
                    label: 'Class Average',
                    data: analytics.class_skills || [75, 72, 80, 70, 76],
                    backgroundColor: 'rgba(79, 195, 161, 0.2)',
                    borderColor: '#4fc3a1',
                    borderWidth: 2,
                    borderDash: [5, 5]
                }]
            },
            options: {
                responsive: true,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            stepSize: 20
                        }
                    }
                }
            }
        });
    }
    
    // Time Management Chart
    const timeCtx = document.getElementById('timeChart');
    if (timeCtx) {
        new Chart(timeCtx, {
            type: 'bar',
            data: {
                labels: analytics.quiz_labels || ['Quiz 1', 'Quiz 2', 'Quiz 3', 'Quiz 4', 'Quiz 5'],
                datasets: [{
                    label: 'Time Taken (min)',
                    data: analytics.time_taken || [25, 30, 22, 35, 28],
                    backgroundColor: '#4fc3a1',
                    borderColor: '#3da888',
                    borderWidth: 1
                }, {
                    label: 'Time Limit (min)',
                    data: analytics.time_limits || [30, 30, 30, 30, 30],
                    backgroundColor: '#ff9800',
                    borderColor: '#f57c00',
                    borderWidth: 1,
                    type: 'line',
                    fill: false
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Time (minutes)'
                        }
                    }
                }
            }
        });
    }
    
    // Topic Performance Chart
    const topicPerfCtx = document.getElementById('topicPerformanceChart');
    if (topicPerfCtx) {
        new Chart(topicPerfCtx, {
            type: 'horizontalBar',
            data: {
                labels: analytics.topics || ['Algorithms', 'Data Structures', 'OOP', 'Databases', 'Networking'],
                datasets: [{
                    label: 'Your Score',
                    data: analytics.topic_scores || [85, 78, 92, 65, 88],
                    backgroundColor: '#4a6fa5'
                }, {
                    label: 'Class Average',
                    data: analytics.topic_averages || [75, 72, 80, 70, 76],
                    backgroundColor: '#4fc3a1'
                }]
            },
            options: {
                responsive: true,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Score (%)'
                        }
                    }
                }
            }
        });
    }
    
    // Weekly Progress Chart
    const weeklyCtx = document.getElementById('weeklyProgressChart');
    if (weeklyCtx) {
        new Chart(weeklyCtx, {
            type: 'line',
            data: {
                labels: analytics.weekly_labels || ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                datasets: [{
                    label: 'Quizzes Completed',
                    data: analytics.weekly_completed || [3, 5, 4, 6],
                    borderColor: '#4a6fa5',
                    backgroundColor: 'rgba(74, 111, 165, 0.1)',
                    borderWidth: 2,
                    yAxisID: 'y',
                    fill: true
                }, {
                    label: 'Average Score',
                    data: analytics.weekly_scores || [65, 70, 75, 78],
                    borderColor: '#4fc3a1',
                    backgroundColor: 'rgba(79, 195, 161, 0.1)',
                    borderWidth: 2,
                    yAxisID: 'y1',
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Quizzes Completed'
                        },
                        beginAtZero: true
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Average Score (%)'
                        },
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
    }
}

function loadTopicCoverageChart(coverage) {
    const topicCovCtx = document.getElementById('topicCoverageChart');
    if (topicCovCtx) {
        new Chart(topicCovCtx, {
            type: 'polarArea',
            data: {
                labels: coverage.labels || ['Algorithms', 'Data Structures', 'OOP', 'Databases', 'Networking'],
                datasets: [{
                    label: 'Topic Coverage',
                    data: coverage.data || [85, 70, 90, 60, 75],
                    backgroundColor: [
                        'rgba(74, 111, 165, 0.7)',
                        'rgba(79, 195, 161, 0.7)',
                        'rgba(255, 152, 0, 0.7)',
                        'rgba(156, 39, 176, 0.7)',
                        'rgba(231, 76, 60, 0.7)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right',
                    },
                    title: {
                        display: true,
                        text: 'Topic Coverage (%)'
                    }
                }
            }
        });
    }
}

// Utility function to update charts with new data
function updateChart(chartId, newData) {
    const chart = Chart.getChart(chartId);
    if (chart) {
        chart.data = newData;
        chart.update();
    }
}

// Export chart functions for use in other modules
window.loadCharts = loadCharts;
window.loadAnalyticsCharts = loadAnalyticsCharts;
window.loadStudentProgressChart = loadStudentCharts;
window.loadStudentAnalyticsCharts = loadStudentAnalyticsCharts;
window.loadTopicCoverageChart = loadTopicCoverageChart;
window.updateChart = updateChart;