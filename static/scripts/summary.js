async function fetchDeviceInfo() {
  try {
    const response = await fetch('/api/device-info');
    if (!response.ok) {
      throw new Error('Failed to fetch device info');
    }
    const data = await response.json();
    console.log('Device Info:', data);
    // Відобразіть дані на сторінці
    const el = document.getElementById('deviceInfo');
    if (el) {
      el.innerText = JSON.stringify(data, null, 2);
    }
  } catch (error) {
    console.error('Error fetching device info:', error);
    const el = document.getElementById('deviceInfo');

    if (el) {
      el.innerText = 'Error fetching device info.';
    }
  }
}
fetchDeviceInfo();
