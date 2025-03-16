const socket = io('/admin');
    let charts = {
        main: null,
        onlineTime: null,
        messageActivity: null,
        heatmap: null
    };

    // Destroy existing charts before reinitializing
    function destroyCharts() {
        Object.values(charts).forEach(chart => {
            if (chart) chart.destroy();
        });
    }

        function initializeCharts() {
            // Main Statistics Chart
            charts.main = new Chart(document.getElementById('mainChart').getContext('2d'), {
                type: 'bar',
                data: {
                    labels: ['Users', 'Online', 'Messages', 'Groups'],
                    datasets: [{
                        label: 'System Statistics',
                        data: [0, 0, 0, 0],
                        backgroundColor: ['#3498db', '#2ecc71', '#f1c40f', '#e74c3c']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });

            // Online Time Distribution
            charts.onlineTime = new Chart(document.getElementById('onlineTimeChart').getContext('2d'), {
                type: 'line',
                data: {
                    labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                    datasets: [{
                        label: 'Online Users by Time',
                        data: [],
                        borderColor: '#9b59b6',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });

            // Message Activity Chart
            charts.messageActivity = new Chart(document.getElementById('messageActivityChart').getContext('2d'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Messages per Hour',
                        data: [],
                        borderColor: '#e67e22',
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'hour'
                            }
                        }
                    }
                }
            });

            // User Activity Heatmap
            charts.heatmap = new Chart(document.getElementById('userActivityHeatmap').getContext('2d'), {
                type: 'bar',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'User Activity by Day',
                        data: [],
                        backgroundColor: ['#3498db', '#2ecc71', '#f1c40f', '#e74c3c', '#9b59b6', '#34495e', '#e67e22']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        function updateCharts(data) {
        // Main Chart
        charts.main.data.datasets[0].data = [
            data.total_users,
            data.online_users_count,
            data.total_messages,
            data.total_groups
        ];
        charts.main.update();

        // Online Time Distribution
        charts.onlineTime.data.datasets[0].data = data.online_time_distribution;
        charts.onlineTime.update();

        // Message Activity
        if (data.message_activity) {
            charts.messageActivity.data.labels = data.message_activity.map(a => a.hour);
            charts.messageActivity.data.datasets[0].data = data.message_activity.map(a => a.count);
            charts.messageActivity.update();
        }

        // User Activity Heatmap
        charts.heatmap.data.datasets[0].data = data.user_activity_heatmap;
        charts.heatmap.update();

        // Update statistics cards
        document.getElementById('total-users').textContent = data.total_users;
        document.getElementById('online-users-count').textContent = data.online_users_count;
        document.getElementById('daily-messages').textContent = data.daily_messages;
        document.getElementById('active-groups').textContent = data.active_groups;
    }
        async function loadAllData() {
            try {
                const res = await fetch('/admin/initial_data');
                const data = await res.json();
                updateCharts(data);
            } catch (error) {
                console.error('Initial load error:', error);
            }
        }
       
    // function setupSocketListeners() {
    //     socket.on('update_dashboard', data => {
    //         updateCharts(data);
    //     });
    // }

    // async function loadAllData() {
    //     try {
    //         const res = await fetch('/admin/initial_data');
    //         const data = await res.json();
    //         updateCharts(data);
    //     } catch (error) {
    //         console.error('Initial load error:', error);
    //     }
    // }
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            destroyCharts();
            initializeCharts();
            loadAllData();
            setupSocketListeners()
        }, 250);
    });

    document.addEventListener("DOMContentLoaded", () => {
        initializeCharts();
        loadAllData();
        setupSocketListeners();  // Now properly defined
    });

let currentSection = '#';
let currentPage = {
    users: 1,
    messages: 1,
    groups: 1,
    dashboard:1
};
let searchQuery = '';
const validSections = ['users', 'messages', 'groups', 'settings',"dashboard"];
// Add to setupSocketListeners
function setupSocketListeners() {
    socket.on('update_dashboard', data => {
        if (document.getElementById('tablesSection').style.display === 'none') {
            updateCharts(data);
        }
    });
}
setupSocketListeners()

// Add these new functions
function showSection(section) {
    currentSection = section;
    
    // Safely hide all table sections
    document.querySelectorAll('.table-section').forEach(el => {
        if (el) el.style.display = 'none';
    });

    // Safely show selected table
    const activeTable = document.getElementById(`${section}Table`);
    if (activeTable) {
        activeTable.style.display = 'block';
    }

    // Safely show tables container
    const tablesSection = document.getElementById('tablesSection');
    if (tablesSection) {
        tablesSection.style.display = 'block';
    }

    // Safely hide charts
    const chartContainers = document.querySelectorAll('.chart-container');
    if (chartContainers) {
        chartContainers.forEach(chart => {
            if (chart) chart.style.display = 'none';
        });
    }

    loadTableData(section);
}

async function loadTableData(section, page = 1, search = '') {
    try {
        const res = await fetch(`/admin/get_${section}?page=${page}&query=${search}`);
        const data = await res.json();
        renderTable(section, data);
        setupPagination(section, data);
    } catch (error) {
        console.error(`Error loading ${section}:`, error);
    }
}

function renderTable(section, data) {
    const tbody = document.getElementById(`${section}TableBody`);
    tbody.innerHTML = '';

    data[section].forEach(item => {
        const row = document.createElement('tr');
        // Customize based on your data structure
        if (section === 'users') {
            row.innerHTML = `
                <td>${item.username}</td>
                <td>${item.is_online ? 'Online' : 'Offline'}</td>
                <td>${item.last_seen || 'Never'}</td>
                <td>
                    <button class="btn btn-sm btn-primary">Edit</button>
                    <button class="btn btn-sm btn-danger">Delete</button>
                </td>
            `;
        } else if (section === 'messages') {
            row.innerHTML = `
                <td>${item.sender_id}</td>
                <td>${item.receiver_id}</td>
                <td>${item.message_text.substring(0, 30)}...</td>
                <td>${item.timestamp}</td>
            `;
        } else if (section === 'groups') {
            row.innerHTML = `
                <td>${item.group_name}</td>
                <td>${item.created_by}</td>
                <td>${item.created_at}</td>
                <td>
                    <button class="btn btn-sm btn-info">View</button>
                    <button class="btn btn-sm btn-warning">Edit</button>
                </td>
            `;
        }else if (section == 'settings'){
            row.innerHTML = `
                <td>${item.key}</td>
                <td>${item.value}</td>
                <td>${item.description || ''}</td>
                <td>${item.last_modified}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="editSetting('${item.id}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteSetting('${item.id}')">Delete</button>
                </td>
            `;
        }
        tbody.appendChild(row);
    });
}

function setupPagination(section, data) {
    const pagination = document.getElementById(`${section}Pagination`);
    pagination.innerHTML = '';

    const prevDisabled = data.current_page === 1 ? 'disabled' : '';
    const nextDisabled = data.current_page === data.total_pages ? 'disabled' : '';

    pagination.innerHTML = `
        <li class="page-item ${prevDisabled}">
            <button class="page-link" onclick="changePage(${data.current_page - 1})">Previous</button>
        </li>
        <li class="page-item active">
            <span class="page-link">${data.current_page}</span>
        </li>
        <li class="page-item ${nextDisabled}">
            <button class="page-link" onclick="changePage(${data.current_page + 1})">Next</button>
        </li>
    `;
}

function changePage(newPage) {
    currentPage[currentSection] = newPage;
    loadTableData(currentSection, newPage, searchQuery);
    setupSocketListeners()
}

// Add event listeners to sidebar
document.querySelectorAll('.sidebar-menu li').forEach((item, index) => {
    if (index > 0) {  // Skip dashboard item
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.querySelector('a').getAttribute('href').replace('#', '');
            showSection(section);
        });
    }
});

// Add search functionality
document.getElementById('searchButton').addEventListener('click', () => {
    searchQuery = document.getElementById('searchInput').value;
    currentPage[currentSection] = 1;
    loadTableData(currentSection, 1, searchQuery);
});

// Add debounced search input
let searchTimeout;
document.getElementById('searchInput').addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        searchQuery = e.target.value;
        currentPage[currentSection] = 1;
        loadTableData(currentSection, 1, searchQuery);
    }, 500);
});
// function renderTable(section, data) {
//     const tbody = document.getElementById(`${section}TableBody`);
//     tbody.innerHTML = '';

//     data[section].forEach(item => {
//         const row = document.createElement('tr');
//         if (section === 'settings') {
//             row.innerHTML = `
//                 <td>${item.key}</td>
//                 <td>${item.value}</td>
//                 <td>${item.description || ''}</td>
//                 <td>${item.last_modified}</td>
//                 <td>
//                     <button class="btn btn-sm btn-primary" onclick="editSetting('${item.id}')">Edit</button>
//                     <button class="btn btn-sm btn-danger" onclick="deleteSetting('${item.id}')">Delete</button>
//                 </td>
//             `;
//         }
//         else{
//           row.innerHTML = `
//                 <td>${item.key}</td>
//                 <td>${item.value}</td>
//                 <td>${item.description || ''}</td>
//                 <td>${item.last_modified}</td>
//                 <td>
//                     <button class="btn btn-sm btn-primary" onclick="editSetting('${item.id}')">Edit</button>
//                     <button class="btn btn-sm btn-danger" onclick="deleteSetting('${item.id}')">Delete</button>
//                 </td>
//             `;
//         }
//         // ... existing cases ...
//         tbody.appendChild(row);
//     });
// }

// Add edit/delete functions
function editSetting(id) {
    // Implement edit functionality
    console.log('Editing setting:', id);
}

function deleteSetting(id) {
    if (confirm('Are you sure you want to delete this setting?')) {
        fetch(`/admin/delete_setting/${id}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadTableData(currentSection);
                }
            });
    }
}