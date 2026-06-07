async function refreshResults() {
  const btn = document.getElementById('refresh-btn');
  const status = document.getElementById('refresh-status');

  btn.disabled = true;
  btn.textContent = '... FETCHING';
  status.textContent = '';
  status.style.color = '#00cc33';

  try {
    const res = await fetch('/api/refresh', { method: 'POST' });
    const data = await res.json();

    if (data.status === 'ok') {
      status.textContent = 'UPDATED! RELOADING...';
      status.style.color = '#00ff41';
      setTimeout(() => location.reload(), 1200);
      return;
    } else if (data.status === 'cached') {
      status.textContent = data.message.toUpperCase();
      status.style.color = '#008f11';
    } else {
      status.textContent = ('ERROR: ' + (data.message || 'UNKNOWN')).toUpperCase();
      status.style.color = '#ff2244';
    }
  } catch {
    status.textContent = 'CONNECTION ERROR';
    status.style.color = '#ff2244';
  }

  btn.disabled = false;
  btn.textContent = '\u{8635} REFRESH RESULTS';
  setTimeout(() => { status.textContent = ''; }, 6000);
}
