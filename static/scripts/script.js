console.log('SW: ', 'serviceWorker' in navigator);

if ('serviceWorker' in navigator) {
  navigator.serviceWorker
    .register('/static/scripts/service-worker.js')
    .then((registration) => {
      console.log('Service Worker registered with scope:', registration.scope);
    })
    .catch((err) => {
      console.log('Service Worker registration failed:', err);
    });

  let deferredPrompt;

  // window.addEventListener('beforeinstallprompt', (event) => {
  //   // Запобігти автоматичному показу діалогу
  //   event.preventDefault();
  //   // Зберегти подію для подальшого використання
  //   deferredPrompt = event;

  //   // Показати кнопку чи елемент для встановлення
  //   const installButton = document.getElementById('install-button');
  //   if (installButton) {
  //     installButton.style.display = 'block';
  //     installButton.addEventListener('click', () => {
  //       // Показати діалогове вікно встановлення
  //       deferredPrompt.prompt();
  //       deferredPrompt.userChoice.then((choiceResult) => {
  //         if (choiceResult.outcome === 'accepted') {
  //           console.log('User accepted the install prompt');
  //         } else {
  //           console.log('User dismissed the install prompt');
  //         }
  //         deferredPrompt = null;
  //       });
  //     });
  //   }
  // });
}

async function fetchPageTemplate(pageId) {
  try {
    const response = await fetch(`/static/pages/${pageId}.html`);
    if (!response.ok) {
      throw new Error('Page not found');
    }
    return await response.text();
  } catch (error) {
    return `
      <h2>404</h2>
      <p>Page not found.</p>
    `;
  }
}
function loadPageScript(pageId) {
  const existingScript = document.getElementById('page-script');
  if (existingScript) {
    existingScript.remove(); // Видаляємо старий JS-файл
  }

  const script = document.createElement('script');
  script.src = `/static/scripts/${pageId}.js`;
  script.id = 'page-script';
  script.async = true;
  document.body.appendChild(script);
}
async function loadPage(path) {
  const content = document.getElementById('content');
  const pageId = path === '' || path === '/' || path === '#' ? 'summary' : path.substring(1); // Якщо "/", то відкриваємо summary
  console.log('Page ID: ', pageId);
  if (content) {
    content.innerHTML = await fetchPageTemplate(pageId);
  }
  loadPageScript(pageId);
}
document.querySelectorAll('.mobile-nav a').forEach((link) => {
  link.addEventListener('click', (event) => {
    event.preventDefault();
    const path = link.getAttribute('href');
    history.pushState({}, '', path); // Оновлюємо URL
    setupActiveLink();
    loadPage(path); // Завантажуємо відповідний контент
  });
});
// Слухач подій для кнопок "Назад" і "Вперед" у браузері
window.addEventListener('popstate', () => {
  loadPage(window.location.hash); // Завантажуємо контент для поточного шляху
});

// Завантаження початкової сторінки
window.addEventListener('DOMContentLoaded', () => {
  loadPage(window.location.hash); // Завантажуємо контент для поточного шляху
});

function setupActiveLink() {
  const links = document.querySelectorAll('.mobile-nav a');
  const currentPath = window.location.hash;

  links.forEach((link) => {
    let href = link.getAttribute('href');
    const linkPath = href === '#' || href === '/' ? '' : href;
    if (linkPath === currentPath) {
      link.classList.add('active'); // Додаємо клас активного посилання
    } else {
      link.classList.remove('active'); // Прибираємо клас, якщо посилання неактивне
    }
  });
}
document.addEventListener('DOMContentLoaded', () => setupActiveLink());
