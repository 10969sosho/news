module.exports = {
  apps: [
    {
      name: "antihoax-backend",
      cwd: "./backend",
      script: "run_server.py",
      interpreter: "python3",
      env: {
        PORT: 8000,
        HOST: "127.0.0.1",
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: "antihoax-frontend",
      cwd: "./frontend",
      script: "node_modules/next/dist/bin/next",
      args: "start -p 3000",
      env: {
        PORT: 3000,
        NODE_ENV: "production",
        BACKEND_API_URL: "http://127.0.0.1:8000"
      }
    }
  ]
};
