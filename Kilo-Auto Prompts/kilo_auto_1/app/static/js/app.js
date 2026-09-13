// Kilo Marketplace — shared app logic

// Flash messages from hx-response headers
document.addEventListener('htmx:response', function (evt) {
  try {
    const headers = evt.detail.xhr.getAllResponseHeaders();
    const match = headers.match(/X-Flash:\s*(.+)/i);
    if (match) {
      const flashes = JSON.parse(decodeURIComponent(match[1]));
      flashes.forEach(function (f) {
        const div = document.createElement('div');
        div.className =
          'fixed top-4 right-4 z-[100] px-4 py-3 rounded-lg shadow-lg text-white text-sm font-medium flash';
        div.style.backgroundColor =
          f.type === 'error' ? '#dc2626' : f.type === 'warning' ? '#f59e0b' : '#16a34a';
        div.textContent = f.text;
        div.addEventListener('click', function () {
          div.remove();
        });
        document.getElementById('flash-container').appendChild(div);
        setTimeout(function () {
          div.remove();
        }, 4000);
      });
    }
  } catch (e) {}
});

// HTMX global defaults
document.addEventListener('htmx:config', function (evt) {
  evt.detail.verbs['patch'] = {
    swapStyle: 'innerHTML',
    trigger: 'click',
  };
});

// Auto-focus on input fields
document.addEventListener('htmx:load', function (evt) {
  const input = evt.target.querySelector('input[type="text"], input[type="email"], textarea');
  if (input) input.focus();
});
