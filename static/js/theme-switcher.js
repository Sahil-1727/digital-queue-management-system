/**
 * QUEUEFLOW GLOBAL THEME SYSTEM
 * Theme set on landing page applies across entire website
 * Persists via localStorage
 */

// Initialize theme from localStorage or default to 'midnight'
function initTheme() {
  const savedTheme = localStorage.getItem('queueflow-theme') || 'midnight';
  document.documentElement.setAttribute('data-theme', savedTheme);
  document.body.setAttribute('data-theme', savedTheme);
  updateThemeIcon(savedTheme);
}

// Switch theme globally
function switchTheme(themeName) {
  document.documentElement.setAttribute('data-theme', themeName);
  document.body.setAttribute('data-theme', themeName);
  localStorage.setItem('queueflow-theme', themeName);
  updateThemeIcon(themeName);
}

// Toggle between midnight and dark
function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'midnight';
  const newTheme = currentTheme === 'dark' ? 'midnight' : 'dark';
  switchTheme(newTheme);
}

// Update theme toggle button icon (if exists)
function updateThemeIcon(theme) {
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.innerHTML = theme === 'dark' ? '☀️' : '🌙';
  }
  
  // Update landing page toggle if exists
  const landingToggle = document.querySelector('.theme-toggle-landing');
  if (landingToggle) {
    landingToggle.innerHTML = theme === 'dark' ? '☀️' : '🌙';
  }
}

// Auto-initialize on page load
(function() {
  initTheme();
})();

// Also initialize on DOMContentLoaded for safety
document.addEventListener('DOMContentLoaded', initTheme);}
