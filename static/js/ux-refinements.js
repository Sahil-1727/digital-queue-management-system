// Toast Notification System
class ToastManager {
  constructor() {
    this.container = this.createContainer();
  }

  createContainer() {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  show(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icons = {
      success: '✓',
      error: '✕',
      warning: '⚠',
      info: 'ℹ'
    };

    const titles = {
      success: 'Success',
      error: 'Error',
      warning: 'Warning',
      info: 'Info'
    };

    toast.innerHTML = `
      <div class="toast-icon">${icons[type]}</div>
      <div class="toast-content">
        <div class="toast-title">${titles[type]}</div>
        <div class="toast-message">${message}</div>
      </div>
      <button class="toast-close" aria-label="Close">✕</button>
    `;

    this.container.appendChild(toast);

    // Close button
    toast.querySelector('.toast-close').addEventListener('click', () => {
      this.remove(toast);
    });

    // Auto dismiss
    if (duration > 0) {
      setTimeout(() => this.remove(toast), duration);
    }

    return toast;
  }

  remove(toast) {
    toast.classList.add('toast-exit');
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }

  success(message, duration) {
    return this.show(message, 'success', duration);
  }

  error(message, duration) {
    return this.show(message, 'error', duration);
  }

  warning(message, duration) {
    return this.show(message, 'warning', duration);
  }

  info(message, duration) {
    return this.show(message, 'info', duration);
  }
}

// Initialize global toast manager
window.toast = new ToastManager();

// Convert Flask flash messages to toasts
document.addEventListener('DOMContentLoaded', () => {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    const message = alert.textContent.trim().replace('×', '');
    let type = 'info';
    
    if (alert.classList.contains('alert-success')) type = 'success';
    else if (alert.classList.contains('alert-danger')) type = 'error';
    else if (alert.classList.contains('alert-warning')) type = 'warning';
    
    toast.show(message, type);
    alert.style.display = 'none';
  });
});

// Button loading state utility
function setButtonLoading(button, loading = true) {
  if (loading) {
    button.classList.add('btn-loading');
    button.disabled = true;
    button.dataset.originalText = button.innerHTML;
  } else {
    button.classList.remove('btn-loading');
    button.disabled = false;
    if (button.dataset.originalText) {
      button.innerHTML = button.dataset.originalText;
    }
  }
}

// Form submission with loading state
document.addEventListener('DOMContentLoaded', () => {
  const forms = document.querySelectorAll('form');
  forms.forEach(form => {
    form.addEventListener('submit', (e) => {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.classList.contains('btn-loading')) {
        setButtonLoading(submitBtn, true);
      }
    });
  });
});

// Active navigation indicator
document.addEventListener('DOMContentLoaded', () => {
  const currentPath = window.location.pathname;
  const navLinks = document.querySelectorAll('.nav-link');
  
  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (href && currentPath.includes(href) && href !== '/') {
      link.classList.add('active');
    }
  });
});
