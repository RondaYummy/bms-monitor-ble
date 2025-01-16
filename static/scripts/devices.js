function formatDuration(seconds) {
  const units = [
    { label: 'year', seconds: 31536000 }, // 365 днів
    { label: 'month', seconds: 2592000 }, // 30 днів
    { label: 'day', seconds: 86400 }, // 24 години
    { label: 'hour', seconds: 3600 }, // 60 хвилин
    { label: 'minute', seconds: 60 }, // 60 секунд
    { label: 'second', seconds: 1 },
  ];

  const result = [];

  for (const unit of units) {
    const value = Math.floor(seconds / unit.seconds);
    if (value > 0) {
      result.push(`${value} ${unit.label}${value > 1 ? 's' : ''}`);
      seconds %= unit.seconds; // Залишок секунд
    }
  }

  return result.join(', ');
}

async function fetchDeviceInfo() {
  try {
    const response = await fetch('/api/device-info');
    if (!response.ok) {
      throw new Error('Failed to fetch device info');
    }
    const data = await response.json();
    console.log('Device Info:', data);

    const devicesList = document.getElementById('devices-list');
    if (devicesList) {
      devicesList.innerHTML = '';

      const output = Object.values(data);
      output.forEach((device) => {
        const li = document.createElement('li');

        li.innerHTML = `
          <div class="column">
            <div class="row justify-between mb-10">
              <div class="column">
                <div id="dev-name" class="mb-10">${device.device_name}</div>
                <div id="dev-vi">${device.vendor_id}</div>
              </div>
              <div class="column">
                <div id="dev-hv" class="mb-10">Hardware v. <span class="unique">${device.hardware_version}</span></div>
                <div id="dev-sv">Software v. <span class="unique">${device.software_version}</span></div>
              </div>
            </div>
            <div id="dev-ut" class="text-center">Uptime: ${formatDuration(device.device_uptime)}.</div>
          </div>
          
        `;

        devicesList.appendChild(li);
      });
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
