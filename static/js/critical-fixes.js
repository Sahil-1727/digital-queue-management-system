/* ============================================
   CRITICAL FIXES - Interactive Enhancements
   ============================================ */

(function() {
  'use strict';

  document.addEventListener('DOMContentLoaded', function() {
    
    // === HOME PAGE FIXES ===
    
    // Navbar scroll effect
    const navbar = document.querySelector('.navbar-landing, .navbar');
    if (navbar) {
      window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
          navbar.classList.add('scrolled');
        } else {
          navbar.classList.remove('scrolled');
        }
      });
    }
    
    // Replace trust emojis with pill badges
    const trustLogos = document.querySelector('.trust-logos');
    if (trustLogos && trustLogos.querySelector('.trust-logo')) {
      const centers = ['Apollo Clinic', 'Apple Service', 'Samsung Care', 'Vivo Center', 'OPPO Service'];
      trustLogos.innerHTML = '';
      trustLogos.classList.add('trust-badges');
      
      centers.forEach(center => {
        const badge = document.createElement('span');
        badge.className = 'trust-badge';
        badge.textContent = center;
        trustLogos.appendChild(badge);
      });
    }
    
    // Add social proof under hero CTA
    const ctaGroup = document.querySelector('.hero .cta-group');
    if (ctaGroup && !document.querySelector('.hero-social-proof')) {
      const socialProof = document.createElement('div');
      socialProof.className = 'hero-social-proof';
      socialProof.innerHTML = '<strong>19 service centers</strong> trust QueueFlow in Nagpur';
      ctaGroup.parentElement.appendChild(socialProof);
    }
    
    // Add eyebrow labels to sections
    const sections = [
      { selector: '.section:has(#features)', label: 'FEATURES' },
      { selector: '.section:has(#how-it-works)', label: 'PROCESS' }
    ];
    
    sections.forEach(({ selector, label }) => {
      const section = document.querySelector(selector);
      if (section) {
        const header = section.querySelector('.section-header');
        if (header && !header.querySelector('.section-eyebrow')) {
          const eyebrow = document.createElement('span');
          eyebrow.className = 'section-eyebrow';
          eyebrow.textContent = label;
          header.insertBefore(eyebrow, header.firstChild);
        }
      }
    });
    
    // Add Problem/Solution labels to cards
    document.querySelectorAll('.ps-card').forEach((card, index) => {
      if (!card.querySelector('.ps-card-label')) {
        const label = document.createElement('span');
        label.className = 'ps-card-label ' + (index % 2 === 0 ? 'problem' : 'solution');
        label.textContent = index % 2 === 0 ? 'Problem' : 'Solution';
        card.insertBefore(label, card.firstChild);
      }
    });
    
    // Add connecting line to How It Works steps
    const stepsContainer = document.querySelector('.steps');
    if (stepsContainer && !stepsContainer.querySelector('.steps-connector')) {
      stepsContainer.classList.add('steps-container');
      const connector = document.createElement('div');
      connector.className = 'steps-connector';
      stepsContainer.insertBefore(connector, stepsContainer.firstChild);
    }
    
    // Grey out dead footer links
    document.querySelectorAll('.footer-links a[href="#"]').forEach(link => {
      link.classList.add('footer-link-disabled');
    });
    
    // === QUEUE STATUS PAGE FIXES ===
    
    // Enhance token display to scoreboard
    const tokenDisplay = document.querySelector('.token-display');
    if (tokenDisplay) {
      tokenDisplay.classList.add('token-scoreboard');
    }
    
    // Add queue progress bar
    const queueStatus = document.querySelector('.queue-status-container, .card:has(.token-display)');
    if (queueStatus && !document.querySelector('.queue-progress-container')) {
      const peopleAhead = document.querySelector('[data-people-ahead]');
      const totalQueue = document.querySelector('[data-total-queue]');
      
      if (peopleAhead && totalQueue) {
        const ahead = parseInt(peopleAhead.dataset.peopleAhead) || 0;
        const total = parseInt(totalQueue.dataset.totalQueue) || 1;
        const progress = ((total - ahead) / total) * 100;
        
        const progressHTML = `
          <div class="queue-progress-container">
            <div class="queue-progress-label">
              <span>Queue Progress</span>
              <span>${Math.round(progress)}%</span>
            </div>
            <div class="queue-progress-bar">
              <div class="queue-progress-fill" style="width: ${progress}%"></div>
            </div>
          </div>
        `;
        
        queueStatus.insertAdjacentHTML('afterbegin', progressHTML);
      }
    }
    
    // Enhance time cards to premium style
    document.querySelectorAll('.alert-success:has([data-leave-time]), .alert-info:has([data-reach-time])').forEach(alert => {
      const isLeaveTime = alert.classList.contains('alert-success');
      alert.className = 'time-card-premium' + (isLeaveTime ? '' : ' blue');
      
      const timeText = alert.textContent.trim();
      const timeMatch = timeText.match(/\d{1,2}:\d{2}\s*[AP]M/i);
      
      if (timeMatch) {
        alert.innerHTML = `
          <div class="time-label">${isLeaveTime ? 'Leave Home At' : 'Reach Counter By'}</div>
          <div class="time-value">${timeMatch[0]}</div>
        `;
      }
    });
    
    // Style stat boxes as colored cards
    document.querySelectorAll('.stat-box, .queue-stat').forEach(stat => {
      if (!stat.classList.contains('stat-card-colored')) {
        stat.classList.add('stat-card-colored');
      }
    });
    
    // Add live indicator to auto-refresh text
    const autoRefresh = document.querySelector('.auto-refresh-notice, [data-auto-refresh]');
    if (autoRefresh && !autoRefresh.querySelector('.live-indicator')) {
      const liveIndicator = document.createElement('span');
      liveIndicator.className = 'live-indicator';
      liveIndicator.innerHTML = '<span class="live-dot"></span> Live';
      autoRefresh.insertBefore(liveIndicator, autoRefresh.firstChild);
    }
    
    // === LOGIN PAGE FIXES ===
    
    // Add logo above login form
    const loginCard = document.querySelector('.card:has(form[action*="login"])');
    if (loginCard && !document.querySelector('.login-logo')) {
      const logo = document.createElement('div');
      logo.className = 'login-logo';
      logo.innerHTML = `
        <div class="login-logo-icon">🎫</div>
        <div class="login-logo-text">QueueFlow</div>
      `;
      loginCard.insertBefore(logo, loginCard.firstChild);
    }
    
    // Wrap login card in max-width container
    if (loginCard && !loginCard.parentElement.classList.contains('login-card-container')) {
      const wrapper = document.createElement('div');
      wrapper.className = 'login-card-container';
      loginCard.parentElement.insertBefore(wrapper, loginCard);
      wrapper.appendChild(loginCard);
    }
    
    // Move forgot password inline with label
    const passwordLabel = document.querySelector('label[for*="password"]');
    const forgotLink = document.querySelector('a[href*="forgot"]');
    
    if (passwordLabel && forgotLink && !passwordLabel.classList.contains('form-label-with-link')) {
      const wrapper = document.createElement('div');
      wrapper.className = 'form-label-with-link';
      
      const labelText = document.createElement('span');
      labelText.textContent = passwordLabel.textContent;
      
      forgotLink.classList.add('forgot-link');
      
      wrapper.appendChild(labelText);
      wrapper.appendChild(forgotLink);
      
      passwordLabel.replaceWith(wrapper);
    }
    
    // Add divider before footer links
    const loginFooter = document.querySelector('.card-footer, .text-center:has(a[href*="register"])');
    if (loginFooter && !loginFooter.previousElementSibling?.classList.contains('form-divider')) {
      const divider = document.createElement('div');
      divider.className = 'form-divider';
      loginFooter.parentElement.insertBefore(divider, loginFooter);
    }
    
    // === ADMIN DASHBOARD FIXES ===
    
    // Add pulsing dot to waiting button
    document.querySelectorAll('.btn:has([class*="spinner"]), button:disabled:contains("Waiting")').forEach(btn => {
      if (btn.textContent.includes('Waiting') && !btn.classList.contains('btn-waiting-live')) {
        btn.classList.add('btn-waiting-live');
      }
    });
    
    // Style No Show buttons as pills
    document.querySelectorAll('a[href*="no_show"], .btn-danger:contains("No Show")').forEach(btn => {
      if (!btn.classList.contains('btn-no-show-pill')) {
        btn.classList.add('btn-no-show-pill');
        btn.classList.remove('btn-danger', 'btn-outline-danger');
      }
    });
    
    // Style queue count badges
    document.querySelectorAll('.badge:not(.queue-count-badge)').forEach(badge => {
      if (badge.textContent.match(/^\d+$/)) {
        badge.classList.add('queue-count-badge');
      }
    });
    
    // === SERVICES PAGE FIXES ===
    
    // Add category classes to service cards
    document.querySelectorAll('.service-card, .card:has(.service-name)').forEach(card => {
      const name = card.querySelector('.service-name, h5, h4')?.textContent.toLowerCase() || '';
      
      if (name.includes('clinic') || name.includes('hospital') || name.includes('medical')) {
        card.classList.add('service-card-medical');
      } else if (name.includes('mobile') || name.includes('phone') || name.includes('apple') || name.includes('samsung')) {
        card.classList.add('service-card-mobile');
      } else if (name.includes('bank')) {
        card.classList.add('service-card-banking');
      } else {
        card.classList.add('service-card-retail');
      }
    });
    
    // Add available slots indicator
    document.querySelectorAll('.service-card').forEach(card => {
      if (!card.querySelector('.slots-indicator')) {
        const slots = Math.floor(Math.random() * 15) + 1; // Demo data
        const indicator = document.createElement('div');
        indicator.className = 'slots-indicator' + (slots < 5 ? ' limited' : slots === 0 ? ' full' : '');
        indicator.innerHTML = `<span>●</span> ${slots} slots available`;
        card.querySelector('.card-body')?.appendChild(indicator);
      }
    });
    
    // === GLOBAL FIXES ===
    
    // Update copyright year
    document.querySelectorAll('.footer-bottom, footer').forEach(footer => {
      footer.innerHTML = footer.innerHTML.replace(/©\s*2024/g, '© 2026');
    });
    
    // Add cursor pointer to all clickable elements
    document.querySelectorAll('a, button, .btn, [onclick], [role="button"]').forEach(el => {
      el.style.cursor = 'pointer';
    });
    
    // External links open in new tab
    document.querySelectorAll('a[href^="http"]').forEach(link => {
      if (!link.hostname.includes(window.location.hostname)) {
        link.setAttribute('target', '_blank');
        link.setAttribute('rel', 'noopener noreferrer');
      }
    });
    
  });
  
})();
