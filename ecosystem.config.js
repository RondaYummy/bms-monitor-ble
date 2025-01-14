module.exports = {
  apps: [
    {
      name: '⚙️ DEPLOY: [BLE] BMS Monitor!',
      script: 'deploy.sh',
      exec_mode: 'fork',
      autorestart: true,
      max_restarts: 10,
      instances: 1,
      watch: false,
      time: true,
      shutdown_with_message: true,
      env: {
        NODE_ENV: 'production',
      },
    },
  ],
};
