/**
 * College Digital Voting System - Main Application Logic
 * Integrates with Backend REST API for Student OTP verification, voting locking, and Admin management.
 */

// Global State
let currentStudent = null;
let activePositions = [];
let electionInfo = {};
let draftVotes = {};
let pendingRegNo = '';
let otpTimerInterval = null;

document.addEventListener('DOMContentLoaded', () => {
  initLoginModule();
  initDashboardEvents();
  initAdminModule();
});

/* ==========================================================================
   1. STUDENT LOGIN & OTP FLOW
   ========================================================================== */

function initLoginModule() {
  const regNoInput = document.getElementById('regNoInput');
  const loginSubmitBtn = document.getElementById('loginSubmitBtn');
  const loginForm = document.getElementById('loginForm');
  const derivedEmailBadge = document.getElementById('derivedEmailBadge');
  const derivedEmailText = document.getElementById('derivedEmailText');

  if (!regNoInput || !loginSubmitBtn || !loginForm) return;

  // Real-time Input Validation & Auto-Uppercase conversion
  const handleInputChange = () => {
    regNoInput.value = regNoInput.value.toUpperCase();
    const regVal = regNoInput.value.trim();

    clearAuthGlobalError();

    const valResult = ValidationModule.validateRegistrationNumber(regVal);

    if (valResult.isValid) {
      const email = ValidationModule.deriveCollegeEmail(regVal);
      if (derivedEmailText) derivedEmailText.textContent = email;
      if (derivedEmailBadge) derivedEmailBadge.style.display = 'flex';
      clearFieldError('regNoErr', regNoInput);
      loginSubmitBtn.disabled = false;
    } else {
      if (derivedEmailBadge) derivedEmailBadge.style.display = 'none';
      if (regVal.length >= 2) {
        showFieldError('regNoErr', valResult.message, regNoInput);
      } else {
        clearFieldError('regNoErr', regNoInput);
      }
      loginSubmitBtn.disabled = true;
    }
  };

  regNoInput.addEventListener('input', handleInputChange);
  regNoInput.addEventListener('blur', () => {
    const regVal = regNoInput.value.trim();
    if (!regVal) {
      showFieldError('regNoErr', 'Student Registration Number is required.', regNoInput);
      loginSubmitBtn.disabled = true;
    } else {
      const valResult = ValidationModule.validateRegistrationNumber(regVal);
      if (!valResult.isValid) {
        showFieldError('regNoErr', valResult.message, regNoInput);
        loginSubmitBtn.disabled = true;
      }
    }
  });

  // Form Submit Handler -> Request OTP
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const regVal = regNoInput.value.trim().toUpperCase();

    const formatCheck = ValidationModule.validateRegistrationNumber(regVal);
    if (!formatCheck.isValid) {
      showFieldError('regNoErr', formatCheck.message, regNoInput);
      regNoInput.focus();
      return;
    }

    const btnText = document.getElementById('btnText');
    const btnSpinner = document.getElementById('btnSpinner');

    loginSubmitBtn.disabled = true;
    btnText.style.display = 'none';
    btnSpinner.style.display = 'inline-block';
    clearAuthGlobalError();

    try {
      const res = await API.student.requestOtp(regVal);
      btnText.style.display = 'inline-block';
      btnSpinner.style.display = 'none';
      loginSubmitBtn.disabled = false;

      pendingRegNo = regVal;

      document.getElementById('otpTargetEmail').textContent = res.email || `${regVal}@kanchiuniv.ac.in`;
      document.getElementById('otpCodeInput').value = '';
      document.getElementById('otpErr').textContent = '';

      const liveNotice = document.getElementById('otpLiveNotice');
      const demoNotice = document.getElementById('otpDemoNotice');
      const demoCodeDisplay = document.getElementById('demoOtpCodeDisplay');

      if (res.demoMode && res.demoOtp) {
        if (liveNotice) liveNotice.style.display = 'none';
        if (demoNotice) demoNotice.style.display = 'block';
        if (demoCodeDisplay) demoCodeDisplay.textContent = res.demoOtp;
        showToast('Demo Testing Mode active for session.', 'warning');
      } else {
        if (liveNotice) liveNotice.style.display = 'flex';
        if (demoNotice) demoNotice.style.display = 'none';
        showToast(res.message || 'A 6-digit verification code has been sent to your registered college email.', 'success');
      }

      openModal('otpModal');
      startOtpTimer(300); // 5 minutes
      setTimeout(() => document.getElementById('otpCodeInput').focus(), 150);
    } catch (err) {
      btnText.style.display = 'inline-block';
      btnSpinner.style.display = 'none';
      loginSubmitBtn.disabled = false;
      setAuthGlobalError(err.message || 'Unable to send OTP email. Please try again.');
      showToast(err.message || 'Unable to send OTP email. Please try again.', 'danger');
    }
  });
}

// OTP Timer Countdown
function startOtpTimer(seconds) {
  if (otpTimerInterval) clearInterval(otpTimerInterval);
  let remaining = seconds;
  const timerElem = document.getElementById('otpTimerText');
  const resendBtn = document.getElementById('resendOtpBtn');

  if (resendBtn) resendBtn.disabled = true;

  const updateDisplay = () => {
    const mins = Math.floor(remaining / 60).toString().padStart(2, '0');
    const secs = (remaining % 60).toString().padStart(2, '0');
    if (timerElem) timerElem.textContent = `Code expires in ${mins}:${secs}`;
    if (remaining <= 0) {
      clearInterval(otpTimerInterval);
      if (timerElem) timerElem.textContent = 'Code expired';
      if (resendBtn) resendBtn.disabled = false;
    }
    remaining--;
  };

  updateDisplay();
  otpTimerInterval = setInterval(updateDisplay, 1000);
}

// Resend / Generate Fresh OTP Action
async function resendOtp() {
  if (!pendingRegNo) return;
  try {
    const res = await API.student.requestOtp(pendingRegNo);
    startOtpTimer(300);
    const liveNotice = document.getElementById('otpLiveNotice');
    const demoNotice = document.getElementById('otpDemoNotice');
    const demoCodeDisplay = document.getElementById('demoOtpCodeDisplay');

    if (res.demoMode && res.demoOtp) {
      if (liveNotice) liveNotice.style.display = 'none';
      if (demoNotice) demoNotice.style.display = 'block';
      if (demoCodeDisplay) demoCodeDisplay.textContent = res.demoOtp;
      showToast('Demo Mode: New session verification code generated.', 'warning');
    } else {
      if (liveNotice) liveNotice.style.display = 'flex';
      if (demoNotice) demoNotice.style.display = 'none';
      showToast(res.message || 'A 6-digit verification code has been sent to your registered college email.', 'success');
    }
  } catch (err) {
    showToast(err.message || 'Unable to send OTP email. Please try again.', 'danger');
  }
}

// Handle OTP Verification Submission
async function handleOtpSubmission(event) {
  event.preventDefault();
  const otpInput = document.getElementById('otpCodeInput');
  const otpErr = document.getElementById('otpErr');
  const verifyBtn = document.getElementById('otpVerifyBtn');
  const btnText = document.getElementById('otpBtnText');
  const btnSpinner = document.getElementById('otpBtnSpinner');

  const otpVal = otpInput.value.trim();
  const formatCheck = ValidationModule.validateOtp(otpVal);

  if (!formatCheck.isValid) {
    if (otpErr) otpErr.textContent = formatCheck.message;
    otpInput.focus();
    return;
  }

  if (otpErr) otpErr.textContent = '';
  verifyBtn.disabled = true;
  btnText.style.display = 'none';
  btnSpinner.style.display = 'inline-block';

  try {
    const res = await API.student.verifyOtp(pendingRegNo, otpVal);
    verifyBtn.disabled = false;
    btnText.style.display = 'inline-block';
    btnSpinner.style.display = 'none';

    currentStudent = res.student;
    activePositions = res.positions || [];
    electionInfo = res.electionInfo || {};

    if (otpTimerInterval) clearInterval(otpTimerInterval);
    closeModal('otpModal');

    showToast(`Welcome, ${currentStudent.name}! Redirecting to Student Dashboard...`, 'success');

    // Switch View
    document.getElementById('loginView').style.display = 'none';
    document.getElementById('dashboardView').style.display = 'block';
    document.getElementById('navbarUserSession').style.display = 'flex';

    renderStudentDashboard(currentStudent);
  } catch (err) {
    verifyBtn.disabled = false;
    btnText.style.display = 'inline-block';
    btnSpinner.style.display = 'none';
    if (otpErr) otpErr.textContent = err.message || 'Invalid verification code. Please check the active code above.';
    showToast(err.message || 'Verification failed.', 'danger');
  }
}

/* Helper Functions for Form Errors */
function showFieldError(elementId, message, inputElem) {
  const errElem = document.getElementById(elementId);
  if (errElem) errElem.textContent = message;
  if (inputElem) inputElem.classList.add('is-invalid');
}

function clearFieldError(elementId, inputElem) {
  const errElem = document.getElementById(elementId);
  if (errElem) errElem.textContent = '';
  if (inputElem) inputElem.classList.remove('is-invalid');
}

function setAuthGlobalError(message) {
  const globalErr = document.getElementById('authGlobalErr');
  if (globalErr) globalErr.textContent = message;
}

function clearAuthGlobalError() {
  const globalErr = document.getElementById('authGlobalErr');
  if (globalErr) globalErr.textContent = '';
}

/* ==========================================================================
   2. STUDENT DASHBOARD & VOTING EXPERIENCE
   ========================================================================== */

function initDashboardEvents() {
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', handleStudentLogout);
  }

  const submitVoteBtn = document.getElementById('submitVoteBtn');
  if (submitVoteBtn) {
    submitVoteBtn.addEventListener('click', handleBallotSubmitClick);
  }

  const finalConfirmVoteBtn = document.getElementById('finalConfirmVoteBtn');
  if (finalConfirmVoteBtn) {
    finalConfirmVoteBtn.addEventListener('click', executeBallotConfirmation);
  }

  const viewReceiptBtn = document.getElementById('viewReceiptBtn');
  if (viewReceiptBtn) {
    viewReceiptBtn.addEventListener('click', () => {
      openModal('receiptModal');
    });
  }
}

function renderStudentDashboard(student) {
  draftVotes = {};

  // Student Profile Card Binding
  document.getElementById('dashStudentName').textContent = student.name;
  document.getElementById('dashStudentMeta').textContent = `Reg No: ${student.regNo} | Email: ${student.email} | ${student.department} (${student.year})`;

  const dashStatusPill = document.getElementById('dashStatusPill');
  const navStudentBadge = document.getElementById('navStudentBadge');

  const votedBanner = document.getElementById('votedBanner');
  const ineligibleBanner = document.getElementById('ineligibleBanner');
  const ballotSubmitBar = document.getElementById('ballotSubmitBar');
  const receiptActionBox = document.getElementById('receiptActionBox');

  votedBanner.style.display = 'none';
  ineligibleBanner.style.display = 'none';
  ballotSubmitBar.style.display = 'none';
  receiptActionBox.style.display = 'none';

  if (!student.isEligible) {
    dashStatusPill.textContent = 'Ineligible to Vote';
    dashStatusPill.className = 'status-badge-pill badge-ineligible';

    navStudentBadge.textContent = 'Ineligible';
    navStudentBadge.className = 'status-badge-pill badge-ineligible';

    ineligibleBanner.style.display = 'flex';
    document.getElementById('ineligibleReasonText').textContent = student.ineligibilityReason || 'Your voter registration is currently on administrative hold.';
    renderBallotCards(false, null);
  } else if (student.hasVoted) {
    dashStatusPill.textContent = 'Voting Completed';
    dashStatusPill.className = 'status-badge-pill badge-voted';

    navStudentBadge.textContent = 'Ballot Locked';
    navStudentBadge.className = 'status-badge-pill badge-voted';

    votedBanner.style.display = 'flex';
    receiptActionBox.style.display = 'block';

    populateReceiptData({
      studentName: student.name,
      regNo: student.regNo,
      timestamp: student.votedAt || '2026-08-12 10:45 AM',
      receiptHash: student.receiptHash || '0x7c9b2f4a1e3d8a6b5c4d3e2f1a0b9c8d7e6f5a4b'
    });

    renderBallotCards(false, student.castedVotes);
  } else {
    dashStatusPill.textContent = 'Eligible to Vote';
    dashStatusPill.className = 'status-badge-pill badge-eligible';

    navStudentBadge.textContent = 'Eligible';
    navStudentBadge.className = 'status-badge-pill badge-eligible';

    ballotSubmitBar.style.display = 'flex';
    renderBallotCards(true, null);
  }
}

function renderBallotCards(canVote, existingVotes) {
  const container = document.getElementById('positionsContainer');
  if (!container) return;

  container.innerHTML = '';

  activePositions.forEach(position => {
    const posCard = document.createElement('div');
    posCard.className = 'position-card';

    let candidatesHTML = '';

    position.candidates.forEach(cand => {
      const isSelected = existingVotes && existingVotes[position.id] === cand.id;
      const disabledClass = canVote ? '' : 'disabled';
      const selectedClass = isSelected ? 'selected' : '';

      // Generate dynamic initials
      const initials = cand.name
        .split(' ')
        .map(part => part.replace(/[^A-Za-z]/g, ''))
        .filter(part => part.length > 0)
        .map(part => part[0])
        .join('')
        .toUpperCase()
        .substring(0, 2);

      candidatesHTML += `
        <div 
          class="candidate-item-card ${disabledClass} ${selectedClass}" 
          id="candCard_${position.id}_${cand.id}"
          onclick="${canVote ? `selectCandidate('${position.id}', '${cand.id}')` : ''}"
        >
          <div class="candidate-top">
            <div class="candidate-initials-avatar">${initials}</div>
            <div class="candidate-meta">
              <h4>${cand.name}</h4>
              <p>${cand.major} • ${cand.year}</p>
            </div>
          </div>
          <div class="candidate-motto">"${cand.motto}"</div>
          <div class="candidate-manifesto">${cand.manifesto}</div>
          <div class="radio-select-wrapper">
            <span style="font-size: 0.8rem; font-weight: 600; color: var(--text-muted);">
              ${isSelected ? 'Selected Ballot' : (canVote ? 'Click card to select' : 'Voting Locked')}
            </span>
            <input 
              type="radio" 
              name="pos_${position.id}" 
              value="${cand.id}" 
              class="radio-custom-input"
              ${isSelected ? 'checked' : ''}
              ${canVote ? '' : 'disabled'}
            >
          </div>
        </div>
      `;
    });

    posCard.innerHTML = `
      <div class="position-header">
        <h3 class="position-title">${position.title}</h3>
        <p class="position-desc">${position.description}</p>
      </div>
      <div class="candidates-grid">
        ${candidatesHTML}
      </div>
    `;

    container.appendChild(posCard);
  });
}

function selectCandidate(positionId, candidateId) {
  draftVotes[positionId] = candidateId;

  const positionObj = activePositions.find(p => p.id === positionId);
  if (!positionObj) return;

  positionObj.candidates.forEach(cand => {
    const card = document.getElementById(`candCard_${positionId}_${cand.id}`);
    const radio = card ? card.querySelector('input[type="radio"]') : null;

    if (cand.id === candidateId) {
      if (card) card.classList.add('selected');
      if (radio) radio.checked = true;
    } else {
      if (card) card.classList.remove('selected');
      if (radio) radio.checked = false;
    }
  });
}

function handleBallotSubmitClick() {
  const missingPositions = [];
  activePositions.forEach(pos => {
    if (!draftVotes[pos.id]) {
      missingPositions.push(pos.title);
    }
  });

  if (missingPositions.length > 0) {
    showToast(`Please complete your selections: Missing vote for ${missingPositions.join(', ')}`, 'warning');
    return;
  }

  // Populate confirmation modal list
  const confirmList = document.getElementById('confirmSummaryList');
  confirmList.innerHTML = '';

  activePositions.forEach(pos => {
    const selectedCandId = draftVotes[pos.id];
    const candidate = pos.candidates.find(c => c.id === selectedCandId);

    const item = document.createElement('div');
    item.style.display = 'flex';
    item.style.justifyContent = 'space-between';
    item.style.padding = '0.5rem 0';
    item.style.borderBottom = '1px solid #E2E8F0';
    item.innerHTML = `
      <span style="color: var(--text-muted); font-weight: 500;">${pos.title}:</span>
      <strong style="color: var(--primary-900);">${candidate ? candidate.name : '-'}</strong>
    `;
    confirmList.appendChild(item);
  });

  openModal('voteConfirmModal');
}

async function executeBallotConfirmation() {
  closeModal('voteConfirmModal');

  try {
    const res = await API.student.castVote(currentStudent.regNo, draftVotes);
    
    // Update local student object
    currentStudent.hasVoted = true;
    currentStudent.votedAt = res.receipt.timestamp;
    currentStudent.receiptHash = res.receipt.receiptHash;
    currentStudent.castedVotes = { ...draftVotes };

    populateReceiptData(res.receipt);
    renderStudentDashboard(currentStudent);

    showToast('Your vote has been submitted and locked successfully!', 'success');
    openModal('receiptModal');
  } catch (err) {
    showToast(err.message || 'Ballot submission failed.', 'danger');
  }
}

function populateReceiptData(receipt) {
  document.getElementById('rcptStudentName').textContent = receipt.studentName;
  document.getElementById('rcptRegNo').textContent = receipt.regNo;
  document.getElementById('rcptTimestamp').textContent = receipt.timestamp;
  document.getElementById('rcptHash').textContent = receipt.receiptHash;
}

function downloadReceiptPDF() {
  window.print();
}

function handleStudentLogout() {
  currentStudent = null;
  draftVotes = {};
  pendingRegNo = '';

  document.getElementById('loginView').style.display = 'flex';
  document.getElementById('dashboardView').style.display = 'none';
  document.getElementById('navbarUserSession').style.display = 'none';

  showToast('You have been logged out securely.', 'info');
}

function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.style.display = 'flex';
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.style.display = 'none';
}

/* ==========================================================================
   3. ADMIN PORTAL MODULE
   ========================================================================== */

function initAdminModule() {
  const adminLoginForm = document.getElementById('adminLoginForm');
  if (adminLoginForm) {
    adminLoginForm.addEventListener('submit', handleAdminLogin);
  }

  const adminBackToStudentBtn = document.getElementById('adminBackToStudentBtn');
  if (adminBackToStudentBtn) {
    adminBackToStudentBtn.addEventListener('click', showStudentPortal);
  }

  const adminLogoutBtn = document.getElementById('adminLogoutBtn');
  if (adminLogoutBtn) {
    adminLogoutBtn.addEventListener('click', handleAdminLogout);
  }

  // Set up live search and filter listeners
  const searchInput = document.getElementById('adminStudentSearch');
  const eligibilityFilter = document.getElementById('adminFilterEligibility');
  const votingFilter = document.getElementById('adminFilterVoting');

  const triggerFilter = () => {
    const query = searchInput ? searchInput.value.trim() : '';
    const elig = eligibilityFilter ? eligibilityFilter.value : 'all';
    const vot = votingFilter ? votingFilter.value : 'all';
    loadAdminStudents(query, elig, vot);
  };

  if (searchInput) searchInput.addEventListener('input', triggerFilter);
  if (eligibilityFilter) eligibilityFilter.addEventListener('change', triggerFilter);
  if (votingFilter) votingFilter.addEventListener('change', triggerFilter);

  // Ineligibility reason toggle in Add Student modal
  const newStudentEligible = document.getElementById('newStudentEligible');
  const reasonGroup = document.getElementById('ineligibilityReasonGroup');
  if (newStudentEligible && reasonGroup) {
    newStudentEligible.addEventListener('change', () => {
      reasonGroup.style.display = newStudentEligible.value === 'false' ? 'block' : 'none';
    });
  }
}

function showAdminPortal(e) {
  if (e) e.preventDefault();

  document.getElementById('loginView').style.display = 'none';
  document.getElementById('dashboardView').style.display = 'none';
  document.getElementById('navbarUserSession').style.display = 'none';

  document.getElementById('adminLoginView').style.display = 'flex';
  document.getElementById('adminDashboardView').style.display = 'none';

  document.getElementById('adminIdInput').value = '';
  document.getElementById('adminPasswordInput').value = '';
  document.getElementById('adminIdErr').textContent = '';
  document.getElementById('adminPasswordErr').textContent = '';
  document.getElementById('adminAuthGlobalErr').textContent = '';

  showToast('Welcome to the Election Administration Portal.', 'info');
}

function showStudentPortal() {
  document.getElementById('adminLoginView').style.display = 'none';
  document.getElementById('adminDashboardView').style.display = 'none';
  document.getElementById('loginView').style.display = 'flex';
}

async function handleAdminLogin(e) {
  e.preventDefault();
  const adminIdInput = document.getElementById('adminIdInput');
  const adminPasswordInput = document.getElementById('adminPasswordInput');

  const idVal = adminIdInput.value.trim();
  const passVal = adminPasswordInput.value.trim();

  let hasError = false;
  if (!idVal) {
    document.getElementById('adminIdErr').textContent = 'Admin ID is required.';
    adminIdInput.classList.add('is-invalid');
    hasError = true;
  } else {
    document.getElementById('adminIdErr').textContent = '';
    adminIdInput.classList.remove('is-invalid');
  }

  if (!passVal) {
    document.getElementById('adminPasswordErr').textContent = 'Password is required.';
    adminPasswordInput.classList.add('is-invalid');
    hasError = true;
  } else {
    document.getElementById('adminPasswordErr').textContent = '';
    adminPasswordInput.classList.remove('is-invalid');
  }

  if (hasError) return;

  try {
    const res = await API.admin.login(idVal, passVal);
    document.getElementById('adminAuthGlobalErr').textContent = '';
    document.getElementById('adminLoginView').style.display = 'none';
    document.getElementById('adminDashboardView').style.display = 'block';

    showToast('Admin session authenticated successfully.', 'success');
    switchAdminTab('overview');
  } catch (err) {
    document.getElementById('adminAuthGlobalErr').textContent = err.message || 'Invalid Admin ID or Password.';
    showToast(err.message || 'Invalid Admin credentials.', 'danger');
  }
}

function handleAdminLogout() {
  document.getElementById('adminDashboardView').style.display = 'none';
  document.getElementById('adminLoginView').style.display = 'flex';
  showToast('Admin session closed successfully.', 'info');
}

function switchAdminTab(tabId) {
  const navItems = document.querySelectorAll('.admin-nav-item');
  navItems.forEach(item => item.classList.remove('active'));

  const activeBtn = document.getElementById(`btnAdminTab_${tabId}`);
  if (activeBtn) activeBtn.classList.add('active');

  const sections = document.querySelectorAll('.admin-section');
  sections.forEach(sec => sec.style.display = 'none');

  const activeSection = document.getElementById(`adminSection_${tabId}`);
  if (activeSection) activeSection.style.display = 'flex';

  if (tabId === 'overview') {
    loadAdminOverview();
  } else if (tabId === 'students') {
    document.getElementById('adminStudentSearch').value = '';
    document.getElementById('adminFilterEligibility').value = 'all';
    document.getElementById('adminFilterVoting').value = 'all';
    loadAdminStudents();
  } else if (tabId === 'candidates') {
    loadAdminCandidates();
  } else if (tabId === 'election') {
    loadAdminElection();
  } else if (tabId === 'results') {
    loadAdminResults();
  }
}

async function loadAdminOverview() {
  try {
    const res = await API.admin.getOverview();
    const stats = res.stats;

    document.getElementById('statTotalStudents').textContent = stats.totalRegistered;
    document.getElementById('statEligibleStudents').textContent = stats.eligibleVoters;
    document.getElementById('statVotesCast').textContent = stats.votesCast;
    document.getElementById('statRemainingVoters').textContent = stats.remainingVoters;

    const dbBadge = document.getElementById('adminDbModeBadge');
    if (dbBadge) {
      dbBadge.textContent = stats.databaseMode || 'System Active';
    }

    const statusHtml = stats.electionStatus === 'Open'
      ? `<span style="width: 10px; height: 10px; border-radius: 50%; background: var(--color-success); display: inline-block;"></span> Open`
      : `<span style="width: 10px; height: 10px; border-radius: 50%; background: var(--color-danger); display: inline-block;"></span> Closed`;

    document.getElementById('statElectionStatus').innerHTML = statusHtml;
  } catch (err) {
    console.error('Error loading overview:', err);
  }
}

async function loadAdminStudents(query = '', eligibility = 'all', votingStatus = 'all') {
  const tableBody = document.getElementById('adminStudentTableBody');
  if (!tableBody) return;

  try {
    const res = await API.admin.getStudents(query, eligibility, votingStatus);
    const students = res.students || [];

    tableBody.innerHTML = '';

    if (students.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="8" style="padding: 2rem; text-align: center; color: var(--text-muted);">
            No student voter records found matching the criteria.
          </td>
        </tr>
      `;
      return;
    }

    students.forEach(s => {
      const eligBadge = s.isEligible
        ? `<span class="demo-tag tag-not-voted" style="background: var(--primary-50); color: var(--primary-800); border: 1px solid var(--primary-100);">Eligible</span>`
        : `<span class="demo-tag tag-ineligible">Ineligible</span>`;

      const voteBadge = s.hasVoted
        ? `<span class="demo-tag tag-voted">Voted</span>`
        : `<span class="demo-tag tag-not-voted">Not Voted</span>`;

      const row = document.createElement('tr');
      row.style.borderBottom = '1px solid var(--border-color)';
      row.innerHTML = `
        <td style="padding: 0.85rem 1.25rem; font-weight: 700; color: var(--primary-800);">${s.regNo}</td>
        <td style="padding: 0.85rem 1.25rem; font-weight: 600;">${s.name}</td>
        <td style="padding: 0.85rem 1.25rem; color: var(--text-muted);">${s.email}</td>
        <td style="padding: 0.85rem 1.25rem;">${s.department}</td>
        <td style="padding: 0.85rem 1.25rem;">${s.year}</td>
        <td style="padding: 0.85rem 1.25rem;">${eligBadge}</td>
        <td style="padding: 0.85rem 1.25rem;">${voteBadge}</td>
        <td style="padding: 0.85rem 1.25rem; text-align: right;">
          <button class="btn-sm ${s.isEligible ? 'btn-danger-outline' : 'btn-success-outline'}" onclick="toggleStudentEligibility('${s.regNo}', ${s.isEligible})">
            ${s.isEligible ? 'Mark Hold' : 'Approve'}
          </button>
          <button class="btn-sm btn-danger-outline" style="margin-left: 0.35rem;" onclick="deleteStudentAccount('${s.regNo}')">
            Delete
          </button>
        </td>
      `;
      tableBody.appendChild(row);
    });
  } catch (err) {
    console.error('Error loading students:', err);
  }
}

async function toggleStudentEligibility(regNo, currentEligible) {
  try {
    const newStatus = !currentEligible;
    const reason = newStatus ? '' : 'Administrative hold: Department review pending.';
    await API.admin.updateStudent(regNo, { isEligible: newStatus, ineligibilityReason: reason });
    showToast(`Eligibility updated for ${regNo}`, 'success');
    loadAdminStudents();
    loadAdminOverview();
  } catch (err) {
    showToast(err.message || 'Failed to update eligibility', 'danger');
  }
}

async function deleteStudentAccount(regNo) {
  if (!confirm(`Are you sure you want to delete student ${regNo}?`)) return;
  try {
    await API.admin.deleteStudent(regNo);
    showToast(`Student ${regNo} deleted successfully.`, 'info');
    loadAdminStudents();
    loadAdminOverview();
  } catch (err) {
    showToast(err.message || 'Failed to delete student.', 'danger');
  }
}

async function handleAdminAddStudent(e) {
  e.preventDefault();
  const regNo = document.getElementById('newStudentRegNo').value.trim().toUpperCase();
  const name = document.getElementById('newStudentName').value.trim();
  const department = document.getElementById('newStudentDept').value.trim();
  const year = document.getElementById('newStudentYear').value;
  const isEligible = document.getElementById('newStudentEligible').value === 'true';
  const ineligibilityReason = document.getElementById('newStudentReason').value.trim();

  const formatCheck = ValidationModule.validateRegistrationNumber(regNo);
  if (!formatCheck.isValid) {
    showToast(formatCheck.message, 'danger');
    return;
  }

  try {
    await API.admin.addStudent({ regNo, name, department, year, isEligible, ineligibilityReason });
    closeModal('adminAddStudentModal');
    document.getElementById('adminAddStudentForm').reset();
    showToast(`Student ${name} (${regNo}) registered successfully!`, 'success');
    loadAdminStudents();
    loadAdminOverview();
  } catch (err) {
    showToast(err.message || 'Failed to enroll student.', 'danger');
  }
}

async function loadAdminCandidates() {
  const container = document.getElementById('adminCandidatesList');
  if (!container) return;

  try {
    const res = await API.admin.getCandidates();
    const positions = res.positions || [];

    container.innerHTML = '';

    positions.forEach(pos => {
      const section = document.createElement('div');
      section.style.marginBottom = '2rem';

      let cardsHtml = '';
      pos.candidates.forEach(cand => {
        const initials = cand.name
          .split(' ')
          .map(part => part.replace(/[^A-Za-z]/g, ''))
          .filter(part => part.length > 0)
          .map(part => part[0])
          .join('')
          .toUpperCase()
          .substring(0, 2);

        cardsHtml += `
          <div class="candidate-item-card disabled" style="cursor: default; opacity: 1;">
            <div class="candidate-top">
              <div class="candidate-initials-avatar">${initials}</div>
              <div class="candidate-meta" style="flex: 1;">
                <h4>${cand.name}</h4>
                <p>ID: ${cand.id} • ${cand.major} • ${cand.year}</p>
              </div>
              <button class="btn-sm btn-danger-outline" onclick="deleteCandidateProfile('${cand.id}')" title="Delete Candidate">
                🗑️
              </button>
            </div>
            <div class="candidate-motto">"${cand.motto}"</div>
            <div class="candidate-manifesto">${cand.manifesto}</div>
          </div>
        `;
      });

      section.innerHTML = `
        <div style="border-bottom: 2px solid var(--primary-100); padding-bottom: 0.5rem; margin-bottom: 1.25rem; margin-top: 1rem;">
          <h3 style="font-size: 1.1rem; font-weight: 800; color: var(--primary-900);">${pos.title}</h3>
          <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.15rem;">${pos.description}</p>
        </div>
        <div class="candidates-grid">
          ${cardsHtml}
        </div>
      `;

      container.appendChild(section);
    });
  } catch (err) {
    console.error('Error loading candidates:', err);
  }
}

async function handleAdminAddCandidate(e) {
  e.preventDefault();
  const positionId = document.getElementById('newCandPosition').value;
  const name = document.getElementById('newCandName').value.trim();
  const major = document.getElementById('newCandMajor').value.trim();
  const year = document.getElementById('newCandYear').value.trim();
  const motto = document.getElementById('newCandMotto').value.trim();
  const manifesto = document.getElementById('newCandManifesto').value.trim();

  try {
    await API.admin.addCandidate({ positionId, name, major, year, motto, manifesto });
    closeModal('adminAddCandidateModal');
    document.getElementById('adminAddCandidateForm').reset();
    showToast(`Candidate ${name} added successfully!`, 'success');
    loadAdminCandidates();
  } catch (err) {
    showToast(err.message || 'Failed to add candidate.', 'danger');
  }
}

async function deleteCandidateProfile(candidateId) {
  if (!confirm(`Are you sure you want to delete candidate ${candidateId}?`)) return;
  try {
    await API.admin.deleteCandidate(candidateId);
    showToast(`Candidate ${candidateId} deleted.`, 'info');
    loadAdminCandidates();
  } catch (err) {
    showToast(err.message || 'Failed to delete candidate.', 'danger');
  }
}

async function loadAdminElection() {
  try {
    const res = await API.admin.getElectionInfo();
    const info = res.electionInfo;

    document.getElementById('adminElectionTitle').textContent = info.title;
    document.getElementById('adminElectionSession').textContent = info.academicYear;
    document.getElementById('adminElectionStandard').textContent = info.encryptionStandard;
    document.getElementById('adminElectionEnds').textContent = new Date(info.votingEnds).toLocaleString();

    const status = info.status || 'Open';
    const badge = document.getElementById('adminElectionStatusBadge');
    if (badge) {
      badge.textContent = status;
      badge.className = `status-badge-pill ${status === 'Open' ? 'badge-eligible' : 'badge-ineligible'}`;
    }
  } catch (err) {
    console.error('Error loading election info:', err);
  }
}

async function setServerElectionState(status) {
  try {
    const res = await API.admin.setElectionStatus(status);
    showToast(res.message, 'success');
    loadAdminElection();
    loadAdminOverview();
  } catch (err) {
    showToast(err.message || 'Failed to update election status.', 'danger');
  }
}

async function loadAdminResults() {
  const container = document.getElementById('adminResultsBoardContainer');
  if (!container) return;

  try {
    const res = await API.admin.getResults();
    const results = res.results || [];

    container.innerHTML = '';

    results.forEach(pos => {
      const section = document.createElement('div');
      section.style.marginBottom = '2.5rem';

      let rowsHtml = '';
      pos.candidates.forEach(cand => {
        rowsHtml += `
          <div class="results-row">
            <div class="results-label-row">
              <span><strong>${cand.name}</strong> (${cand.major} • ${cand.year})</span>
              <span>${cand.votesCount} votes (${cand.percentage}%)</span>
            </div>
            <div class="results-bar-bg">
              <div class="results-bar-fill" style="width: ${cand.percentage}%;"></div>
            </div>
          </div>
        `;
      });

      section.innerHTML = `
        <div style="border-bottom: 2px solid var(--primary-100); padding-bottom: 0.5rem; margin-bottom: 1.25rem;">
          <h3 style="font-size: 1.1rem; font-weight: 800; color: var(--primary-900);">${pos.positionTitle}</h3>
          <span style="font-size: 0.78rem; color: var(--text-muted);">Total Ballots Counted: ${pos.totalVotes}</span>
        </div>
        <div style="background: #FFFFFF; border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1.5rem; box-shadow: var(--shadow-sm);">
          ${rowsHtml}
        </div>
      `;

      container.appendChild(section);
    });
  } catch (err) {
    console.error('Error loading results:', err);
  }
}

/* ==========================================================================
   4. TOAST NOTIFICATION UTILITY
   ========================================================================== */

function showToast(message, type = 'info') {
  const toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) return;

  const toast = document.createElement('div');
  toast.className = `toast-message toast-${type}`;

  let iconSVG = 'ℹ️';
  if (type === 'danger') iconSVG = '⚠️';
  if (type === 'success') iconSVG = '✓';
  if (type === 'warning') iconSVG = '🔔';

  toast.innerHTML = `
    <span style="font-size: 1.1rem;">${iconSVG}</span>
    <div class="toast-content">
      <div class="toast-body">${message}</div>
    </div>
  `;

  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(40px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 4500);
}
