/* ============================================
   FINAL SAAS-LEVEL INTERACTIVITY
   All Missing Interactive Features
   ============================================ */

(function() {
  'use strict';

  document.addEventListener('DOMContentLoaded', function() {
    
    // === TOAST NOTIFICATION SYSTEM ===
    function createToastContainer() {
      if (!document.querySelector('.toast-container')) {
        const container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
      }
    }
    
    function showToast(message, type = 'info') {
      createToastContainer();
      const container = document.querySelector('.toast-container');
      
      const toast = document.createElement('div');
      toast.className = `toast ${type}`;
      toast.innerHTML = `
        <span style="font-size: 20px;">${type === 'success' ? '✓' : type === 'danger' ? '✗' : type === 'warning' ? '⚠' : 'ℹ'}</span>
        <span style="flex: 1; font-weight: 500;">${message}</span>
      `;
      
      container.appendChild(toast);
      
      setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 300);
      }, 4000);
    }
    
    // Replace Bootstrap alerts with toasts
    document.querySelectorAll('.alert').forEach(alert => {
      const message = alert.textContent.trim();
      let type = 'info';
      
      if (alert.classList.contains('alert-success')) type = 'success';
      else if (alert.classList.contains('alert-danger')) type = 'danger';
      else if (alert.classList.contains('alert-warning')) type = 'warning';
      
      showToast(message, type);
      alert.remove();
    });
    
    // Expose globally for form submissions
    window.showToast = showToast;
    
    // === SCROLL TO TOP BUTTON ===
    const scrollBtn = document.createElement('button');
    scrollBtn.className = 'scroll-to-top';
    scrollBtn.innerHTML = '↑';
    scrollBtn.setAttribute('aria-label', 'Scroll to top');
    document.body.appendChild(scrollBtn);
    
    window.addEventListener('scroll', () => {
      if (window.scrollY > 300) {
        scrollBtn.classList.add('visible');
      } else {
        scrollBtn.classList.remove('visible');
      }
    });
    
    scrollBtn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    
    // === FORM SUBMIT LOADING STATES ===
    document.querySelectorAll('form').forEach(form => {
      form.addEventListener('submit', function(e) {
        const submitBtn = this.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn && !submitBtn.disabled) {
          const originalText = submitBtn.innerHTML;
          submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
          submitBtn.disabled = true;
          
          // Re-enable after 5 seconds as fallback
          setTimeout(() => {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
          }, 5000);
        }
      });
    });
    
    // === LAZY LOADING FOR IMAGES ===
    document.querySelectorAll('img:not([loading])').forEach(img => {
      img.setAttribute('loading', 'lazy');
    });
    
    // === ACTIVE NAV LINK HIGHLIGHTING ===
    document.querySelectorAll('.nav-link, .dropdown-item').forEach(link => {
      if (link.href === window.location.href) {
        link.style.color = 'var(--color-primary)';
        link.style.fontWeight = '700';
        link.style.background = 'rgba(15,76,92,0.08)';
        link.style.borderRadius = '8px';
      }
    });
    
    // === FAQ ACCORDION ===
    document.querySelectorAll('.faq-question').forEach(question => {
      question.addEventListener('click', function() {
        const item = this.closest('.faq-item');
        const wasActive = item.classList.contains('active');
        
        // Close all
        document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('active'));
        
        // Open clicked if it wasn't active
        if (!wasActive) {
          item.classList.add('active');
        }
      });
    });
    
    // === STICKY CTA BAR ===
    const hero = document.querySelector('.hero');
    if (hero) {
      const stickyCTA = document.createElement('div');
      stickyCTA.className = 'sticky-cta-bar';
      stickyCTA.innerHTML = `
        <div class="sticky-cta-content">
          <span class="sticky-cta-text">Ready to eliminate waiting lines?</span>
          <a href="${window.location.origin}/register" class="btn btn-primary">Get Started Free</a>
        </div>
      `;
      document.body.appendChild(stickyCTA);
      
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (!entry.isIntersecting) {
            stickyCTA.classList.add('visible');
          } else {
            stickyCTA.classList.remove('visible');
          }
        },
        { threshold: 0 }
      );
      
      observer.observe(hero);
    }
    
    // === PASSWORD STRENGTH INDICATOR ===
    document.querySelectorAll('input[type="password"][name*="password"]:not([name*="confirm"])').forEach(input => {
      const strengthDiv = document.createElement('div');
      strengthDiv.className = 'password-strength';
      strengthDiv.innerHTML = '<div class="password-strength-bar"></div>';
      input.parentElement.appendChild(strengthDiv);
      
      const strengthText = document.createElement('div');
      strengthText.className = 'password-strength-text';
      input.parentElement.appendChild(strengthText);
      
      input.addEventListener('input', function() {
        const password = this.value;
        const bar = strengthDiv.querySelector('.password-strength-bar');
        
        let strength = 0;
        if (password.length >= 8) strength++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
        if (/\d/.test(password)) strength++;
        if (/[^a-zA-Z\d]/.test(password)) strength++;
        
        bar.className = 'password-strength-bar';
        if (strength <= 1) {
          bar.classList.add('weak');
          strengthText.textContent = 'Weak password';
          strengthText.style.color = '#EF4444';
        } else if (strength <= 2) {
          bar.classList.add('medium');
          strengthText.textContent = 'Medium password';
          strengthText.style.color = '#F59E0B';
        } else {
          bar.classList.add('strong');
          strengthText.textContent = 'Strong password';
          strengthText.style.color = '#10B981';
        }
        
        if (password.length === 0) {
          strengthText.textContent = '';
        }
      });
    });
    
    // === COOKIE CONSENT BANNER ===
    if (!localStorage.getItem('cookieConsent')) {
      const banner = document.createElement('div');
      banner.className = 'cookie-banner';
      banner.innerHTML = `
        <div class="cookie-content">
          <div class="cookie-text">
            We use cookies to enhance your experience. By continuing to visit this site you agree to our use of cookies.
            <a href="/terms" style="color: var(--color-primary); font-weight: 600; margin: 0 4px;">Terms</a> |
            <a href="/privacy" style="color: var(--color-primary); font-weight: 600; margin: 0 4px;">Privacy Policy</a>
          </div>
          <div class="cookie-actions">
            <button class="btn btn-outline-primary btn-sm" onclick="this.closest('.cookie-banner').remove();">Decline</button>
            <button class="btn btn-primary btn-sm" onclick="localStorage.setItem('cookieConsent', 'true'); this.closest('.cookie-banner').remove();">Accept</button>
          </div>
        </div>
      `;
      document.body.appendChild(banner);
      
      setTimeout(() => banner.classList.add('visible'), 1000);
    }
    
    // === MOBILE BOTTOM NAVIGATION ===
    if (window.innerWidth <= 768 && document.querySelector('.internal-navbar')) {
      const bottomNav = document.createElement('div');
      bottomNav.className = 'mobile-bottom-nav';
      bottomNav.innerHTML = `
        <div class="mobile-nav-items">
          <a href="/services" class="mobile-nav-item ${window.location.pathname === '/services' ? 'active' : ''}">
            <span class="mobile-nav-icon">🏪</span>
            <span>Services</span>
          </a>
          <a href="/queue_status" class="mobile-nav-item ${window.location.pathname.includes('queue') ? 'active' : ''}">
            <span class="mobile-nav-icon">🎫</span>
            <span>Queue</span>
          </a>
          <a href="/user/profile" class="mobile-nav-item ${window.location.pathname.includes('profile') ? 'active' : ''}">
            <span class="mobile-nav-icon">👤</span>
            <span>Profile</span>
          </a>
        </div>
      `;
      document.body.appendChild(bottomNav);
    }
    
    // === KEYBOARD SHORTCUTS (⌘K) ===
    document.addEventListener('keydown', function(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        // Simple search/command palette
        const search = prompt('Quick navigation:\n1. Services\n2. Queue Status\n3. Profile\n4. Admin Dashboard\n\nEnter number:');
        const routes = {
          '1': '/services',
          '2': '/queue_status',
          '3': '/user/profile',
          '4': '/admin/dashboard'
        };
        if (routes[search]) {
          window.location.href = routes[search];
        }
      }
    });
    
    // === HUMAN-READABLE WAIT TIME ===
    document.querySelectorAll('[data-wait-time]').forEach(el => {
      const minutes = parseInt(el.dataset.waitTime);
      const humanText = document.createElement('small');
      humanText.style.cssText = 'opacity:0.7;font-size:0.75rem;display:block;margin-top:4px;';
      
      if (minutes < 5) humanText.textContent = 'almost your turn';
      else if (minutes < 15) humanText.textContent = 'a short wait';
      else if (minutes < 30) humanText.textContent = 'grab a coffee';
      else humanText.textContent = 'take your time';
      
      el.appendChild(humanText);
    });
    
    // === SHARE BUTTON FOR QUEUE STATUS ===
    const tokenDisplay = document.querySelector('.token-display, .token-scoreboard');
    if (tokenDisplay && window.location.pathname.includes('queue')) {
      const shareBtn = document.createElement('button');
      shareBtn.style.cssText = 'margin-top:16px;width:100%;padding:12px;border-radius:100px;border:2px solid var(--color-primary);background:transparent;color:var(--color-primary);font-weight:600;cursor:pointer;transition:all 0.2s ease;';
      shareBtn.innerHTML = '📤 Share Queue Status';
      
      shareBtn.addEventListener('click', function() {
        const shareData = {
          title: 'My Queue Token',
          text: `Check my queue status at ${document.title}`,
          url: window.location.href
        };
        
        if (navigator.share) {
          navigator.share(shareData);
        } else {
          navigator.clipboard.writeText(window.location.href).then(() => {
            showToast('Link copied to clipboard!', 'success');
          });
        }
      });
      
      shareBtn.addEventListener('mouseenter', function() {
        this.style.background = 'var(--color-primary)';
        this.style.color = 'white';
      });
      
      shareBtn.addEventListener('mouseleave', function() {
        this.style.background = 'transparent';
        this.style.color = 'var(--color-primary)';
      });
      
      tokenDisplay.parentElement.appendChild(shareBtn);
    }
    
    // === PREVENT ZOOM ON INPUT FOCUS (iOS) ===
    document.querySelectorAll('input, select, textarea').forEach(input => {
      input.addEventListener('focus', function() {
        const viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
          viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
        }
      });
      
      input.addEventListener('blur', function() {
        const viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
          viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, viewport-fit=cover');
        }
      });
    });
    
    // === EMPTY STATE ILLUSTRATIONS ===
    document.querySelectorAll('table tbody').forEach(tbody => {
      if (tbody.children.length === 0 || (tbody.children.length === 1 && tbody.textContent.trim().includes('No'))) {
        tbody.innerHTML = `
          <tr>
            <td colspan="100%" style="text-align: center; padding: 48px 24px;">
              <div style="font-size: 48px; opacity: 0.3; margin-bottom: 16px;">📋</div>
              <div style="font-size: 16px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px;">No data yet</div>
              <div style="font-size: 14px; color: var(--text-secondary);">Items will appear here when available</div>
            </td>
          </tr>
        `;
      }
    });
    
    // === HOVER TOOLTIPS ON ICON BUTTONS ===
    document.querySelectorAll('button:not([title]), a.btn:not([title])').forEach(btn => {
      const icon = btn.textContent.trim();
      if (icon.length <= 2 && /[\u{1F300}-\u{1F9FF}]/u.test(icon)) {
        btn.setAttribute('title', btn.getAttribute('aria-label') || 'Action');
      }
    });
    
    // === LOADING SKELETON FOR SLOW PAGES ===
    if (performance.navigation.type === 1) { // Page reload
      document.body.style.opacity = '0';
      setTimeout(() => {
        document.body.style.transition = 'opacity 0.3s ease';
        document.body.style.opacity = '1';
      }, 100);
    }
    
  });
  
})();
