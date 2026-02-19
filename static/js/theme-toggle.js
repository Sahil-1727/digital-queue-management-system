// Dark Mode Toggle Script - Enhanced
(function() {
    // Check for saved theme preference or default to 'dark'
    const currentTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
    
    // Update toggle button state if it exists
    function updateToggleButton() {
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            toggleBtn.innerHTML = isDark ? '☀️' : '🌙';
            toggleBtn.setAttribute('aria-label', isDark ? 'Switch to light mode' : 'Switch to dark mode');
            
            // Add rotation animation
            toggleBtn.style.transform = 'rotate(360deg)';
            setTimeout(() => {
                toggleBtn.style.transform = 'rotate(0deg)';
            }, 300);
        }
    }
    
    // Toggle theme function with smooth transition
    window.toggleTheme = function() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        // Add transition class
        document.documentElement.style.transition = 'background-color 0.5s cubic-bezier(0.4, 0, 0.2, 1), color 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
        
        // Create ripple effect
        const ripple = document.createElement('div');
        ripple.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            border-radius: 50%;
            background: ${newTheme === 'dark' ? 'rgba(15, 23, 42, 0.9)' : 'rgba(255, 255, 255, 0.9)'};
            transform: translate(-50%, -50%);
            transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1), height 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            pointer-events: none;
            z-index: 99999;
        `;
        document.body.appendChild(ripple);
        
        // Trigger ripple animation
        setTimeout(() => {
            ripple.style.width = '300vmax';
            ripple.style.height = '300vmax';
        }, 10);
        
        // Change theme after ripple starts
        setTimeout(() => {
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateToggleButton();
        }, 300);
        
        // Remove ripple after animation
        setTimeout(() => {
            ripple.remove();
            document.documentElement.style.transition = '';
        }, 900);
    };
    
    // Initialize on page load
    document.addEventListener('DOMContentLoaded', updateToggleButton);
})();
