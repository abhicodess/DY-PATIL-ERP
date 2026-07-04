/**
 * ERP MOBILE CLIENT SIDE INTERACTIONS — Vanilla JS
 */

document.addEventListener('DOMContentLoaded', function() {
  initMobileNav();
  initDrawer();
  initAccordions();
  initRealtimeSearch();
  initToasts();
  initStudentTimetableSwipe();
  initSwipeMarking();
});

// 1. MOBILE BOTTOM NAV ACTIVE HIGHLIGHT
function initMobileNav() {
  const path = window.location.pathname;
  const navItems = document.querySelectorAll('.mob-bottom-nav .mob-nav-item');
  
  navItems.forEach(item => {
    const href = item.getAttribute('href');
    if (!href || href === '#') return;
    
    // Clean trailing slashes
    const cleanPath = path.replace(/\/$/, '');
    const cleanHref = href.replace(/\/$/, '');
    
    if (cleanHref && (cleanPath === cleanHref || (cleanHref !== '' && cleanHref !== '/admin' && cleanPath.startsWith(cleanHref + '/')))) {
      item.classList.add('active');
    } else if (href === path) {
      item.classList.add('active');
    }
  });
}

// 2. SLIDE-IN DRAWER
function initDrawer() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sbOverlay');
  const toggle = document.getElementById('sbToggle');
  const closeBtn = document.getElementById('sidebarClose');

  if (!sidebar) return;

  // Add close button to sidebar dynamically if it doesn't exist
  if (!document.getElementById('sidebarClose')) {
    const btn = document.createElement('button');
    btn.id = 'sidebarClose';
    btn.className = 'sidebar-close-btn';
    btn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
    btn.onclick = closeDrawer;
    sidebar.appendChild(btn);
  }

  // Ensure toggle button on mobile works
  if (toggle) {
    toggle.onclick = function(e) {
      e.stopPropagation();
      openDrawer();
    };
  }

  // Ensure overlay click closes drawer
  if (overlay) {
    overlay.onclick = closeDrawer;
  }

  // Close drawer if clicking outside
  document.addEventListener('click', function(e) {
    if (window.innerWidth <= 991 && sidebar.classList.contains('open')) {
      if (!sidebar.contains(e.target) && (!toggle || !toggle.contains(e.target))) {
        closeDrawer();
      }
    }
  });

  // ESC key closes drawer
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closeDrawer();
  });
}

function openDrawer() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sbOverlay');
  if (sidebar) sidebar.classList.add('open');
  if (overlay) overlay.classList.add('show');
  document.body.style.overflow = 'hidden';
}

function closeDrawer() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sbOverlay');
  if (sidebar) sidebar.classList.remove('open');
  if (overlay) overlay.classList.remove('show');
  document.body.style.overflow = '';
}

// 3. ACCORDION VIEW STATE PERSISTENCE (sessionStorage)
function initAccordions() {
  const headers = document.querySelectorAll('.tt-accordion-header');
  
  headers.forEach(header => {
    const targetId = header.dataset.target;
    const body = document.getElementById(targetId);
    if (!body) return;

    // Restore state from sessionStorage
    const isCollapsed = sessionStorage.getItem('accordion_' + targetId);
    if (isCollapsed === 'open') {
      header.classList.add('active');
      body.classList.add('open');
    } else if (isCollapsed === 'closed') {
      header.classList.remove('active');
      body.classList.remove('open');
    }

    // Toggle on click
    header.addEventListener('click', function() {
      const isOpen = body.classList.toggle('open');
      header.classList.toggle('active', isOpen);
      sessionStorage.setItem('accordion_' + targetId, isOpen ? 'open' : 'closed');
    });
  });
}

// 4. REAL-TIME CLIENT-SIDE SEARCH/FILTERING (For Tables converted to Cards)
function initRealtimeSearch() {
  const searchInput = document.getElementById('mobSearchInput');
  if (!searchInput) return;

  searchInput.addEventListener('input', function() {
    const query = this.value.toLowerCase().trim();
    const cards = document.querySelectorAll('.filterable-card');

    cards.forEach(card => {
      const text = card.textContent.toLowerCase();
      if (text.includes(query)) {
        card.style.display = '';
      } else {
        card.style.display = 'none';
      }
    });
  });
}

// 5. STACKED TOAST NOTIFICATION SYSTEM
let toastContainer = null;
function initToasts() {
  if (document.getElementById('toast-container')) return;
  toastContainer = document.createElement('div');
  toastContainer.id = 'toast-container';
  document.body.appendChild(toastContainer);
  
  // Replace existing window.toast if present
  window.toast = showToast;
  
  // Convert existing static toast if it shows up
  const staticToast = document.getElementById('toast');
  if (staticToast && staticToast.textContent.trim() !== '') {
    showToast(staticToast.textContent.replace(/[✅❌]/g, '').trim(), staticToast.className);
    staticToast.style.display = 'none';
  }
}

function showToast(message, type = 'ok') {
  if (!toastContainer) initToasts();
  
  const toastItem = document.createElement('div');
  toastItem.className = `toast-item ${type}`;
  
  const icon = type === 'err' ? '❌' : type === 'warn' ? '⚠️' : '✅';
  toastItem.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  
  toastContainer.appendChild(toastItem);
  
  // Auto dismiss after 4 seconds
  setTimeout(() => {
    toastItem.style.opacity = '0';
    toastItem.style.transform = 'translateY(-10px)';
    setTimeout(() => {
      toastItem.remove();
    }, 300);
  }, 4000);
}

// 6. STUDENT TIMETABLE SWIPE DAY NAVIGATION
function initStudentTimetableSwipe() {
  const container = document.querySelector('.st-tt-swipe-container');
  if (!container) return;
  
  const columns = document.querySelectorAll('.st-day-column');
  if (!columns.length) return;
  
  let activeIndex = 0;
  // Set current day as active index if possible
  const todayName = container.dataset.today; // e.g. "Monday"
  columns.forEach((col, idx) => {
    if (col.dataset.day === todayName) {
      activeIndex = idx;
    }
  });
  
  // Activate day
  function showDay(idx) {
    if (idx < 0 || idx >= columns.length) return;
    activeIndex = idx;
    columns.forEach((col, i) => {
      if (i === activeIndex) {
        col.classList.add('active');
      } else {
        col.classList.remove('active');
      }
    });
    
    // Update active dots/pills if any
    const indicators = document.querySelectorAll('.st-swipe-indicator');
    indicators.forEach((ind, i) => {
      ind.classList.toggle('active', i === activeIndex);
    });
  }
  
  showDay(activeIndex);
  
  // Touch event swipe logic
  let startX = 0;
  let startY = 0;
  
  container.addEventListener('touchstart', function(e) {
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
  }, { passive: true });
  
  container.addEventListener('touchend', function(e) {
    const diffX = e.changedTouches[0].clientX - startX;
    const diffY = e.changedTouches[0].clientY - startY;
    
    // Detect horizontal swipe
    if (Math.abs(diffX) > 60 && Math.abs(diffY) < 40) {
      if (diffX > 0) {
        // Swipe Right (Go to Previous Day)
        if (activeIndex > 0) showDay(activeIndex - 1);
      } else {
        // Swipe Left (Go to Next Day)
        if (activeIndex < columns.length - 1) showDay(activeIndex + 1);
      }
    }
  }, { passive: true });

  // Expose swipe changer buttons globally
  window.changeSwipeDay = function(dir) {
    if (dir === 'prev' && activeIndex > 0) {
      showDay(activeIndex - 1);
    } else if (dir === 'next' && activeIndex < columns.length - 1) {
      showDay(activeIndex + 1);
    }
  };
}

// 7. SWIPE-TO-MARK ATTENDANCE FOR FACULTY
function initSwipeMarking() {
  const cards = document.querySelectorAll('.swipe-card');
  
  cards.forEach(card => {
    let startX = 0;
    let currentX = 0;
    let isDragging = false;
    const maxSwipe = 120; // Max drag distance
    
    card.addEventListener('touchstart', function(e) {
      startX = e.touches[0].clientX;
      isDragging = true;
      card.style.transition = 'none';
    }, { passive: true });
    
    card.addEventListener('touchmove', function(e) {
      if (!isDragging) return;
      currentX = e.touches[0].clientX - startX;
      
      // Restrict swipe bounds
      if (currentX > maxSwipe) currentX = maxSwipe;
      if (currentX < -maxSwipe) currentX = -maxSwipe;
      
      card.style.transform = `translateX(${currentX}px)`;
    }, { passive: true });
    
    card.addEventListener('touchend', function(e) {
      isDragging = false;
      card.style.transition = 'transform 0.2s ease-out';
      
      const studentId = card.dataset.studentId;
      
      if (currentX > 80) {
        // Swiped Right -> Mark Present
        markStudent(studentId, 'Present', card);
      } else if (currentX < -80) {
        // Swiped Left -> Mark Absent
        markStudent(studentId, 'Absent', card);
      } else {
        // Reset position
        card.style.transform = 'translateX(0)';
      }
    }, { passive: true });
  });
}

function markStudent(studentId, status, cardElement) {
  // Find radio inputs in the desktop table row or hidden values
  const desktopRadio = document.querySelector(`input[name="bst_${studentId}"][value="${status}"]`);
  if (desktopRadio) {
    desktopRadio.checked = true;
  }
  
  // Visually style the swipe card
  cardElement.style.transform = 'translateX(0)';
  if (status === 'Present') {
    cardElement.classList.add('marked-present');
    cardElement.classList.remove('marked-absent');
    showToast(`Marked ${cardElement.dataset.studentName} Present`, 'ok');
  } else {
    cardElement.classList.add('marked-absent');
    cardElement.classList.remove('marked-present');
    showToast(`Marked ${cardElement.dataset.studentName} Absent`, 'err');
  }
}

// 8. ADMIN APPROVAL BOTTOM SHEET FUNCTIONS
window.BottomSheet = {
  open: function(sheetId) {
    const sheet = document.getElementById(sheetId);
    let backdrop = document.getElementById('bsBackdrop');
    
    if (!backdrop) {
      backdrop = document.createElement('div');
      backdrop.id = 'bsBackdrop';
      backdrop.className = 'bottom-sheet-backdrop';
      document.body.appendChild(backdrop);
    }
    
    if (sheet) {
      sheet.classList.add('open');
      backdrop.classList.add('show');
      backdrop.onclick = function() {
        BottomSheet.close(sheetId);
      };
    }
  },
  close: function(sheetId) {
    const sheet = document.getElementById(sheetId);
    const backdrop = document.getElementById('bsBackdrop');
    if (sheet) sheet.classList.remove('open');
    if (backdrop) backdrop.classList.remove('show');
  }
};
