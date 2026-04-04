# 🚀 Deployment Guide: ClaimCopilot

To deploy this project, we recommend a **Split Deployment Strategy**. This ensures the Python backend has enough memory for the AI models and the React frontend remains lightning-fast.

---

## 1. 🐍 Backend Deployment (**Render.com**)

Vercel is great for frontend but has tight limits on Python memory and execution time. **Render** is better for this backend because it supports persistent disks (for your vector store and records) and longer timeouts for AI processing.

### Steps for [Render](https://render.com):
1.  **New Web Service**: Connect your GitHub repository.
2.  **Root Directory**: `backend`
3.  **Environment**: `Python 3`
4.  **Build Command**: `pip install -r requirements.txt`
5.  **Start Command**: `gunicorn main:app --timeout 600 --bind 0.0.0.0:$PORT`
    *   *(Note: You'll need to add `gunicorn` to your requirements.txt)*
6.  **Advanced → Environment Variables**:
    *   `OPENROUTER_API_KEY`: Your key
    *   `PYTHON_VERSION`: `3.10.0` (or higher)
7.  **Disk (Important)**:
    *   Add a **Persistent Disk** mounted at `/backend/data`.
    *   Update `config.py` in your dashboard if you want to store results persistently.

---

## 2. ⚛️ Frontend Deployment (**Vercel**)

Vercel is the perfect choice for the React/Vite frontend.

### Steps for [Vercel](https://vercel.com):
1.  **New Project**: Select your GitHub repository.
2.  **Root Directory**: `frontend`
3.  **Framework Preset**: `Vite` (Vercel should auto-detect this).
4.  **Build Command**: `npm run build`
5.  **Output Directory**: `dist`
6.  **Environment Variables**:
    *   `VITE_API_URL`: The URL of your Render backend (e.g., `https://your-backend.onrender.com`).

### Configuration File (`vercel.json`)
Create this file in the `frontend/` directory to handle React routing:

```json
{
  "rewrite": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

---

## 3. 🛠️ Preparing for Deployment

I have already updated your code to use environment variables for the API URLs. Before you push, please run these commands:

### Update requirements.txt
Add `gunicorn` to the backend dependencies for production hosting:

```bash
cd backend
echo "gunicorn" >> requirements.txt
```

### Update CORS (Optional)
Once you have your Vercel URL, update `backend/main.py` to only allow that origin for better security:

```python
CORS(app, resources={r"/*": {"origins": ["https://your-frontend.vercel.app"]}})
```

---

## 4. 🏁 Checkpoint
1.  Deploy the **Backend** first to get its URL.
2.  Deploy the **Frontend** with that URL provided as `VITE_API_URL`.
3.  Enjoy your deployed Insurance Claim Assistant!
