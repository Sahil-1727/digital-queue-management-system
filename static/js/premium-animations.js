/* ============================================
   QUEUEFLOW PREMIUM ANIMATIONS
   World-Class Micro-Interactions - Refined
   ============================================ */

// Refined timing constants
const TIMING = {
  fast: 150,
  base: 200,
  slow: 300,
  slower: 400,
  cardStagger: 80
};

// Page Load Animation - Refined
document.addEventListener('DOMContentLoaded', function() {
  // Add fade-in animation to main content
  const mainContent = document.querySelector('main, .container, .admin-content');
  if (mainContent) {
    mainContent.classList.add('fade-in-up');
  }
  
  // Animate cards on load with refined stagger
  const cards = document.querySelectorAll('.card');
  cards.forEach((card, index) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(12px)';
    setTimeout(() => {
      card.style.transition = `all ${TIMING.slow}ms cubic-bezier(0.4, 0, 0.2, 1)`;
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, index * TIMING.cardStagger);
  });
  
  // Initialize all animations
  initButtonAnimations();
  initTableAnimations();
  initToastAnimations();
  initCounterAnimations();
});

// Button Click Animation - Refined
function initButtonAnimations() {
  const buttons = document.querySelectorAll('.btn');
  buttons.forEach(button => {
    button.addEventListener('click', function(e) {
      // Ripple effect with refined timing
      const ripple = document.createElement('span');
      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;
      
      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';
      ripple.style.position = 'absolute';
      ripple.style.borderRadius = '50%';
      ripple.style.background = 'rgba(255, 255, 255, 0.4)';
      ripple.style.transform = 'scale(0)';
      ripple.style.animation = 'ripple 500ms ease-out';
      ripple.style.pointerEvents = 'none';
      
      this.style.position = 'relative';
      this.style.overflow = 'hidden';
      this.appendChild(ripple);
      
      setTimeout(() => ripple.remove(), 500);
    });
  });
}

// Add ripple animation CSS
const style = document.createElement('style');
style.textContent = `
  @keyframes ripple {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

// Table Row Animations - Refined
function initTableAnimations() {
  const tableRows = document.querySelectorAll('.table tbody tr');
  tableRows.forEach(row => {
    row.style.transition = 'all 150ms cubic-bezier(0.4, 0, 0.2, 1)';
    
    row.addEventListener('mouseenter', function() {
      this.style.transform = 'scale(1.005)';
      this.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.08)';
    });
    
    row.addEventListener('mouseleave', function() {
      this.style.transform = 'scale(1)';
      this.style.boxShadow = 'none';
    });
  });
}

// Toast Notification Animations - Refined
function initToastAnimations() {
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach((alert, index) => {
    alert.style.animation = `slide-in-right ${TIMING.slower}ms ease-out ${index * 100}ms both`;
  });
}

// Counter Number Animation
function initCounterAnimations() {
  const counters = document.querySelectorAll('[data-counter]');
  counters.forEach(counter => {
    const target = parseInt(counter.getAttribute('data-counter'));
    const duration = 1000;
    const step = target / (duration / 16);
    let current = 0;
    
    const timer = setInterval(() => {
      current += step;
      if (current >= target) {
        counter.textContent = target;
        clearInterval(timer);
      } else {
        counter.textContent = Math.floor(current);
      }
    }, 16);
  });
}

// Smooth Scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      target.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }
  });
});

// Card Hover Effects - Refined
document.querySelectorAll('.card').forEach(card => {
  card.style.transition = 'all 200ms cubic-bezier(0.4, 0, 0.2, 1)';
  
  card.addEventListener('mouseenter', function() {
    this.style.transform = 'translateY(-2px)';
  });
  
  card.addEventListener('mouseleave', function() {
    this.style.transform = 'translateY(0)';
  });
});

// Real-Time Status Updates with Animation - Refined
function updateTokenStatus(tokenId, newStatus) {
  const tokenElement = document.querySelector(`[data-token-id="${tokenId}"]`);
  if (tokenElement) {
    // Refined pulse animation
    tokenElement.style.animation = 'pulse 400ms ease-in-out';
    
    // Update status badge
    const badge = tokenElement.querySelector('.badge');
    if (badge) {
      badge.style.transition = 'all 200ms ease';
      badge.style.transform = 'scale(1.08)';
      setTimeout(() => {
        badge.textContent = newStatus;
        badge.style.transform = 'scale(1)';
      }, 100);
    }
    
    // Remove animation after completion
    setTimeout(() => {
      tokenElement.style.animation = '';
    }, 400);
  }
}

// Queue Position Update Animation - Refined
function animateQueueUpdate() {
  const queueCards = document.querySelectorAll('.queue-position');
  queueCards.forEach((card, index) => {
    setTimeout(() => {
      card.style.animation = `fade-in-up ${TIMING.slower}ms ease-out`;
    }, index * TIMING.cardStagger);
  });
}

// Form Validation Animations
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', function(e) {
    const submitBtn = this.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.style.transform = 'scale(0.95)';
      setTimeout(() => {
        submitBtn.style.transform = 'scale(1)';
      }, 200);
    }
  });
});

// Input Focus Animations - Refined
document.querySelectorAll('.form-control, .form-select').forEach(input => {
  input.addEventListener('focus', function() {
    this.parentElement.style.transform = 'scale(1.005)';
    this.parentElement.style.transition = 'transform 150ms ease';
  });
  
  input.addEventListener('blur', function() {
    this.parentElement.style.transform = 'scale(1)';
  });
});

// Modal Animations
const modals = document.querySelectorAll('.modal');
modals.forEach(modal => {
  modal.addEventListener('show.bs.modal', function() {
    const modalContent = this.querySelector('.modal-content');
    modalContent.style.animation = 'modal-slide-up 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
  });
});

// Notification Bell Animation
function showNotificationBell() {
  const bell = document.getElementById('notification-bell');
  if (bell) {
    bell.style.display = 'flex';
    bell.style.animation = 'shake 0.5s ease-in-out 3';
  }
}

// Progress Bar Animation
function animateProgressBar(element, targetWidth) {
  let width = 0;
  const interval = setInterval(() => {
    if (width >= targetWidth) {
      clearInterval(interval);
    } else {
      width++;
      element.style.width = width + '%';
    }
  }, 10);
}

// Skeleton Loading Animation
function showSkeletonLoader(container) {
  container.innerHTML = `
    <div class="skeleton" style="height: 100px; margin-bottom: 16px;"></div>
    <div class="skeleton" style="height: 60px; margin-bottom: 16px;"></div>
    <div class="skeleton" style="height: 60px;"></div>
  `;
}

// Success Animation - Refined
function showSuccessAnimation(element) {
  element.style.animation = 'success-bounce 500ms ease-out';
  setTimeout(() => {
    element.style.animation = '';
  }, 500);
}

// Add success bounce animation - Refined
const successStyle = document.createElement('style');
successStyle.textContent = `
  @keyframes success-bounce {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.06); }
  }
  
  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    25% { transform: translateX(-8px); }
    75% { transform: translateX(8px); }
  }
  
  @keyframes ripple {
    to {
      transform: scale(3.5);
      opacity: 0;
    }
  }
`;
document.head.appendChild(successStyle);

// Auto-hide alerts after 5 seconds
setTimeout(() => {
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach(alert => {
    const bsAlert = new bootstrap.Alert(alert);
    setTimeout(() => {
      alert.style.animation = 'fade-out 0.3s ease-out';
      setTimeout(() => bsAlert.close(), 300);
    }, 5000);
  });
}, 100);

// Fade out animation
const fadeOutStyle = document.createElement('style');
fadeOutStyle.textContent = `
  @keyframes fade-out {
    from { opacity: 1; transform: translateY(0); }
    to { opacity: 0; transform: translateY(-20px); }
  }
`;
document.head.appendChild(fadeOutStyle);

// Export functions for use in other scripts
window.QueueFlowAnimations = {
  updateTokenStatus,
  animateQueueUpdate,
  showNotificationBell,
  animateProgressBar,
  showSkeletonLoader,
  showSuccessAnimation
};

console.log('✨ QueueFlow Premium Animations Loaded');
