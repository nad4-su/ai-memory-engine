/**
 * Navigation & Common UI Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    // Highlight active nav link
    highlightActiveNav();
    
    // Mobile menu toggle
    setupMobileMenu();
    
    // Theme toggle (if implemented)
    setupThemeToggle();
});

/**
 * Highlight active navigation link based on current page
 */
function highlightActiveNav() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPage || (currentPage === '' && href === 'index.html')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

/**
 * Setup mobile menu toggle
 */
function setupMobileMenu() {
    // Create mobile menu button if not exists
    if (window.innerWidth <= 768 && !document.querySelector('.mobile-menu-btn')) {
        const button = document.createElement('button');
        button.className = 'mobile-menu-btn';
        button.innerHTML = '☰';
        button.style.cssText = `
            position: fixed;
            top: 1rem;
            left: 1rem;
            z-index: 1001;
            background: var(--accent);
            color: white;
            border: none;
            padding: 0.75rem 1rem;
            border-radius: var(--radius);
            font-size: 1.5rem;
            cursor: pointer;
        `;
        
        button.addEventListener('click', () => {
            const sidebar = document.querySelector('.sidebar');
            sidebar.classList.toggle('mobile-open');
        });
        
        document.body.appendChild(button);
        
        // Close sidebar when clicking outside
        document.addEventListener('click', (e) => {
            const sidebar = document.querySelector('.sidebar');
            const button = document.querySelector('.mobile-menu-btn');
            if (sidebar.classList.contains('mobile-open') && 
                !sidebar.contains(e.target) && 
                !button.contains(e.target)) {
                sidebar.classList.remove('mobile-open');
            }
        });
    }
}

/**
 * Setup theme toggle (dark/light)
 */
function setupThemeToggle() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    // Theme toggle button (optional)
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }
}

/**
 * Create sidebar HTML (for consistency across pages)
 */
function createSidebar() {
    return `
        <nav class="sidebar">
            <div class="sidebar-header">
                <div class="logo">
                    <span class="logo-icon">🧠</span>
                    <span>Memory Engine</span>
                </div>
            </div>
            <ul class="nav-menu">
                <li class="nav-item">
                    <a href="index.html" class="nav-link">
                        <span class="nav-icon">📊</span>
                        <span>Dashboard</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a href="search.html" class="nav-link">
                        <span class="nav-icon">🔍</span>
                        <span>Search</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a href="profile.html" class="nav-link">
                        <span class="nav-icon">👤</span>
                        <span>Profile</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a href="history.html" class="nav-link">
                        <span class="nav-icon">📜</span>
                        <span>History</span>
                    </a>
                </li>
                <li class="nav-item">
                    <a href="settings.html" class="nav-link">
                        <span class="nav-icon">⚙️</span>
                        <span>Settings</span>
                    </a>
                </li>
            </ul>
        </nav>
    `;
}
