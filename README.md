<script>
    // ── Scroll-reveal ────────────────────────────────────────
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
    document.querySelectorAll('[data-reveal]').forEach(el => observer.observe(el));

    // ── Smooth scroll ────────────────────────────────────────
    function scrollToSection(id) {
      const el = document.getElementById(id);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // ── Language toggle ──────────────────────────────────────
    let currentLang = 'en';
    function setLang(lang) {
      currentLang = lang;
      document.querySelectorAll('[data-en]').forEach(el => {
        el.innerHTML = el.getAttribute('data-' + lang) || el.getAttribute('data-en');
      });
      // Toggle button styles
      document.getElementById('btnEng').className = lang === 'en'
        ? 'px-4 py-1.5 rounded-full text-xs font-bold bg-white text-blue-700 shadow-sm transition-all'
        : 'px-4 py-1.5 rounded-full text-xs font-bold text-slate-500 hover:text-slate-800 transition-all';
      document.getElementById('btnCeb').className = lang === 'ceb'
        ? 'px-4 py-1.5 rounded-full text-xs font-bold bg-white text-blue-700 shadow-sm transition-all'
        : 'px-4 py-1.5 rounded-full text-xs font-bold text-slate-500 hover:text-slate-800 transition-all';
      showToast(lang === 'en' ? 'Switched to English' : 'Gibag-o sa Cebuano', 'success');
    }

    // ── Modal helpers ────────────────────────────────────────
    function openModal(id) {
      document.getElementById(id).classList.add('active');
      document.body.style.overflow = 'hidden';
    }
    function closeModal(id) {
      document.getElementById(id).classList.remove('active');
      document.body.style.overflow = '';
    }
    // Close on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', function(e) {
        if (e.target === this) closeModal(this.id);
      });
    });
    // Close on Escape
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.active').forEach(m => closeModal(m.id));
      }
    });

    // ── Signup form ──────────────────────────────────────────
    function handleSignup() {
      const inputs = document.querySelectorAll('#signupModal .inp');
      let valid = true;
      inputs.forEach(inp => {
        inp.style.borderColor = '';
        if (!inp.value.trim()) { inp.style.borderColor = '#f87171'; valid = false; }
      });
      if (!valid) { showToast('Please fill in all fields.', 'error'); return; }
      const emailEl = document.querySelector('#signupModal input[type="email"]');
      if (emailEl && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailEl.value)) {
        emailEl.style.borderColor = '#f87171';
        showToast('Please enter a valid email address.', 'error');
        return;
      }
      closeModal('signupModal');
      showToast('Account created! Welcome to BayaniHub 🎉', 'success');
    }

    // ── Share ────────────────────────────────────────────────
    let currentShareTitle = '';
    function openShare(title) {
      currentShareTitle = title;
      document.getElementById('shareArticleTitle').textContent = title;
      openModal('shareModal');
    }
    function shareVia(platform) {
      const url = encodeURIComponent(window.location.href);
      const text = encodeURIComponent('Check this out: ' + currentShareTitle + ' — BayaniHub Cebu');
      if (platform === 'facebook') {
        window.open('https://www.facebook.com/sharer/sharer.php?u=' + url, '_blank', 'width=600,height=400');
      } else if (platform === 'twitter') {
        window.open('https://twitter.com/intent/tweet?text=' + text + '&url=' + url, '_blank', 'width=600,height=400');
      } else if (platform === 'copy') {
        navigator.clipboard.writeText(window.location.href).then(() => {
          closeModal('shareModal');
          showToast('Link copied to clipboard!', 'success');
        }).catch(() => {
          closeModal('shareModal');
          showToast('Link copied!', 'success');
        });
        return;
      }
      closeModal('shareModal');
      showToast('Opening share window…', 'info');
    }

    // ── View All News ────────────────────────────────────────
    let newsExpanded = false;
    function toggleAllNews() {
      newsExpanded = !newsExpanded;
      const extras = document.querySelectorAll('.news-extra');
      const label = document.getElementById('viewAllLabel');
      const icon = document.getElementById('viewAllIcon');
      extras.forEach(card => {
        card.classList.toggle('visible', newsExpanded);
        // Re-trigger reveal animation
        if (newsExpanded) {
          card.classList.remove('is-visible');
          setTimeout(() => observer.observe(card), 50);
        }
      });
      label.textContent = newsExpanded
        ? (currentLang === 'ceb' ? 'Ipakita Diyutay' : 'Show Less')
        : (currentLang === 'ceb' ? 'Tan-awa Tanan nga Balita' : 'View All News');
      icon.textContent = newsExpanded ? 'expand_less' : 'arrow_right_alt';
    }

    // ── Step detail info ─────────────────────────────────────
    const stepInfo = {
      1: { en: 'Open the BayaniHub app, tap "Report Issue", snap a photo of the problem, choose a category (Roads, Flooding, Waste, etc.), and hit Submit. Your report is geotagged automatically.', ceb: 'Ablihan ang BayaniHub app, i-tap ang "I-report ang Isyu", kumuha og litrato sa problema, pilia ang kategorya, ug i-submit. Ang inyong report awtomatiko nga geotagged.' },
      2: { en: 'Your report goes to the Barangay dashboard. You\'ll get push notifications at every status change: Received → Under Review → In Progress → Done.', ceb: 'Ang inyong report moadto sa Barangay dashboard. Makadawat ka og push notifications sa matag pagbabago sa status: Nadawat → Gireview → Gibuhat → Nahuman.' },
      3: { en: 'Once fixed, barangay officials upload a "resolved" photo. You\'ll be notified instantly and can rate the response. Your feedback shapes future service.', ceb: 'Sa dihang nahuman na, nag-upload ang mga opisyal og "resolved" nga litrato. Dayon ikaw abisohon ug makagrado sa tubag. Ang inyong feedback makatabang sa umaabot nga serbisyo.' }
    };
    function showStepDetail(step) {
      const info = stepInfo[step][currentLang] || stepInfo[step]['en'];
      showToast(info, 'info');
    }

    // ── Download app ─────────────────────────────────────────
    function handleDownload() {
      showToast('App coming soon to iOS & Android! 📱', 'info');
    }

    // ── Toast ────────────────────────────────────────────────
    let toastTimer;
    function showToast(msg, type = 'success') {
      const toast = document.getElementById('toast');
      const icon = document.getElementById('toastIcon');
      const msgEl = document.getElementById('toastMsg');
      const icons = { success: 'check_circle', error: 'error', info: 'info' };
      const colors = { success: '#4ade80', error: '#f87171', info: '#60a5fa' };
      icon.textContent = icons[type] || 'info';
      icon.style.color = colors[type] || '#60a5fa';
      msgEl.textContent = msg;
      toast.classList.add('show');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => toast.classList.remove('show'), 4000);
    }

    // ── UI Helpers ──────────
    function goBackToStep1() {
      document.getElementById('signupStep2').classList.add('hidden');
      document.getElementById('signupStep1').classList.remove('hidden');
      showToast('Maaari mo nang i-edit ang iyong details.', 'info');
    }

    // 1. Switch between Login and Signup modals
    function switchModal(closeId, openId) {
    closeModal(closeId);
    setTimeout(() => openModal(openId), 300);
    }

    // 2. Handle Login (Connecting to app.py)
    async function handleLogin(e) {
      e.preventDefault();
      
      const email = document.getElementById('loginEmail').value;
      const password = document.getElementById('loginPassword').value;

      if (!email || !password) {
        showToast('Please enter both email and password.', 'error');
        return;
      }

      showToast('Logging in...', 'info');

      try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            closeModal('loginModal');
            showToast('Welcome back! Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = data.redirect_url; 
            }, 1000);
        } else {
            showToast(data.error || 'Invalid credentials.', 'error');
        }
      } catch (error) {
          console.error('Error:', error);
          showToast('Server error. Is Python running?', 'error');
      }
    }

    // 3. Trigger OTP (Fixed ID reference)
    async function triggerOTP() {
      const name = document.getElementById('regName').value;
      const email = document.getElementById('regEmail').value;
      const password = document.getElementById('regPass').value; // Now matches id="regPass"
      const phone = document.getElementById('phoneNumber').value;

      if(!name || !email || !password || !phone) {
          showToast('Please fill in all fields.', 'error');
          return;
      }

      showToast('Sending OTP to your email...', 'info');

      const response = await fetch('/api/send-otp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, password, phone })
      });

      if (response.ok) {
          document.getElementById('signupStep1').classList.add('hidden');
          document.getElementById('signupStep2').classList.remove('hidden');
          showToast('OTP sent successfully!', 'success');
      } else {
          const errorData = await response.json();
          showToast(errorData.error || 'Failed to send OTP.', 'error');
      }
    }

    // 4. Handle Final Sign Up Verification
    async function handleSignupSubmit(e) {
      e.preventDefault();
      const phone = document.getElementById('phoneNumber').value;
      const code = document.getElementById('otpCodeInput').value;

      const response = await fetch('/api/verify-otp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ phone, code })
      });

      const data = await response.json();
      if (response.ok) {
          showToast('Account created! 🎉', 'success');
          setTimeout(() => {
              window.location.href = data.redirect_url;
          }, 1500);
      } else {
          showToast(data.error || 'Verification failed.', 'error');
        }
      }
  </script>#   B a y a n i h a n H u b _ H A C K U S C  
 