module.exports = {
  apps: [
    {
      name: "antihoax-backend",
      cwd: "/home/alurelab/news.solusisurabaya.com/backend",
      script: "run_server.py",
      interpreter: "/home/alurelab/news.solusisurabaya.com/backend/venv/bin/python",
      env: {
        PORT: 8000,
        HOST: "127.0.0.1",
        PYTHONUNBUFFERED: "1"
      }
    },
    {
      name: "antihoax-frontend",
      cwd: "/home/alurelab/news.solusisurabaya.com/frontend",
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
