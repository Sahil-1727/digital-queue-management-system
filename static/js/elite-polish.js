// Elite-level scroll experience
(function() {
  'use strict';
  
  // Navbar scroll effect with backdrop blur
  function initScrollEffects() {
    const navbar = document.querySelector('.navbar.sticky-top');
    const internalNavbar = document.querySelector('.internal-navbar');
    
    let lastScroll = 0;
    let ticking = false;
    
    function updateNavbar(scrollY) {
      const threshold = 10;
      
      if (navbar) {
        if (scrollY > threshold) {
          navbar.classList.add('scrolled');
        } else {
          navbar.classList.remove('scrolled');
        }
      }
      
      if (internalNavbar) {
        if (scrollY > threshold) {
          internalNavbar.classList.add('scrolled');
        } else {
          internalNavbar.classList.remove('scrolled');
        }
      }
    }
    
    function onScroll() {
      lastScroll = window.scrollY;
      
      if (!ticking) {
        window.requestAnimationFrame(() => {
          updateNavbar(lastScroll);
          ticking = false;
        });
        ticking = true;
      }
    }
    
    // Initial check
    updateNavbar(window.scrollY);
    
    // Listen to scroll
    window.addEventListener('scroll', onScroll, { passive: true });
  }
  
  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initScrollEffects);
  } else {
    initScrollEffects();
  }
})();
