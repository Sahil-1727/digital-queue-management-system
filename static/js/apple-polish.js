/* ============================================
   APPLE-LEVEL MICRO-INTERACTIONS
   Smooth animations and user feedback
   ============================================ */

(function() {
  'use strict';

  // Add fade-in animation on page load
  document.addEventListener('DOMContentLoaded', function() {
    document.body.classList.add('fade-in');
    
    // Add scrolled class to navbar on scroll
    const navbar = document.querySelector('.navbar');
    if (navbar) {
      window.addEventListener('scroll', function() {
        if (window.scrollY > 10) {
          navbar.classList.add('scrolled');
        } else {
          navbar.classList.remove('scrolled');
        }
      });
    }
    
    // Add cursor pointer to all clickable elements
    const clickableSelectors = [
      'a:not(.btn)',
      'button',
      '.btn',
      '[onclick]',
      '[role="button"]',
      '.clickable',
      '.card-link',
      'label[for]'
    ];
    
    clickableSelectors.forEach(selector => {
      document.querySelectorAll(selector).forEach(el => {
        el.style.cursor = 'pointer';
      });
    });
    
    // Add smooth transitions to all interactive elements
    const interactiveElements = document.querySelectorAll('a, button, .btn, .card, input, select, textarea');
    interactiveElements.forEach(el => {
      if (!el.style.transition) {
        el.style.transition = 'all 0.2s ease';
      }
    });
    
    // Add ripple effect to buttons on click
    document.querySelectorAll('.btn').forEach(button => {
      button.addEventListener('click', function(e) {
        const ripple = document.createElement('span');
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;
        
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';
        ripple.classList.add('ripple-effect');
        
        this.appendChild(ripple);
        
        setTimeout(() => ripple.remove(), 600);
      });
    });
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const href = this.getAttribute('href');
        if (href !== '#' && href !== '#!') {
          const target = document.querySelector(href);
          if (target) {
            e.preventDefault();
            target.scrollIntoView({
              behavior: 'smooth',
              block: 'start'
            });
          }
        }
      });
    });
    
    // Add focus-visible polyfill for better keyboard navigation
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Tab') {
        document.body.classList.add('keyboard-nav');
      }
    });
    
    document.addEventListener('mousedown', function() {
      document.body.classList.remove('keyboard-nav');
    });
    
    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
      setTimeout(() => {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        setTimeout(() => alert.remove(), 300);
      }, 5000);
    });
    
    // Add loading state to forms on submit
    document.querySelectorAll('form').forEach(form => {
      form.addEventListener('submit', function() {
        const submitBtn = this.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
          submitBtn.disabled = true;
          submitBtn.style.opacity = '0.6';
          submitBtn.style.cursor = 'not-allowed';
          
          const originalText = submitBtn.textContent;
          submitBtn.textContent = 'Processing...';
          
          // Re-enable after 3 seconds as fallback
          setTimeout(() => {
            submitBtn.disabled = false;
            submitBtn.style.opacity = '1';
            submitBtn.style.cursor = 'pointer';
            submitBtn.textContent = originalText;
          }, 3000);
        }
      });
    });
    
    // Add stagger animation to lists
    document.querySelectorAll('.table tbody tr, .list-group-item').forEach((item, index) => {
      item.style.animationDelay = (index * 0.05) + 's';
      item.classList.add('fade-in');
    });
    
    // Enhance empty states
    document.querySelectorAll('.empty-state').forEach(emptyState => {
      if (!emptyState.querySelector('.empty-state-icon')) {
        const icon = document.createElement('div');
        icon.className = 'empty-state-icon';
        icon.textContent = '📋';
        emptyState.insertBefore(icon, emptyState.firstChild);
      }
    });
  });
  
  // Add CSS for ripple effect
  const style = document.createElement('style');
  style.textContent = `
    .ripple-effect {
      position: absolute;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.6);
      transform: scale(0);
      animation: ripple 0.6s ease-out;
      pointer-events: none;
    }
    
    @keyframes ripple {
      to {
        transform: scale(2);
        opacity: 0;
      }
    }
    
    .btn {
      position: relative;
      overflow: hidden;
    }
    
    body.keyboard-nav *:focus {
      outline: 3px solid rgba(15, 76, 92, 0.3) !important;
      outline-offset: 2px;
    }
    
    body:not(.keyboard-nav) *:focus {
      outline: none;
    }
  `;
  document.head.appendChild(style);
  
})();
