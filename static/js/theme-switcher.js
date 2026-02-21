/**
 * QUEUEFLOW THEME SYSTEM
 * Minimal theme initialization - no toggle functionality
 */

// Initialize theme from localStorage or default
function initTheme() {
  const savedTheme = localStorage.getItem('queueflow-theme');
  if (savedTheme) {
    document.documentElement.setAttribute('data-theme', savedTheme);
    document.body.setAttribute('data-theme', savedTheme);
  }
}

// Auto-initialize on page load
(function() {
  initTheme();
})();

// Also initialize on DOMContentLoaded for safety
document.addEventListener('DOMContentLoaded', initTheme);
