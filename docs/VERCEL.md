# Vercel website + free Render API

Vercel serves the React website and forwards `/api/*` requests to the FastAPI service on Render. The FastAPI API, SQLite job history and analysis files stay on Render. This keeps the Vercel function runtime out of long-running GIS jobs.

## 1. Deploy the backend

Create the Render service from the free blueprint using the instructions in [RENDER.md](RENDER.md). Keep its service name `geodyssey` so its public URL is `https://geodyssey.onrender.com`. Wait for the first deploy to become Live and confirm `https://geodyssey.onrender.com/api/health` responds with `"status":"ok"`.

If Render assigns a different public hostname, replace `geodyssey.onrender.com` in the `api` rewrite in `vercel.json` with the hostname Render gives you, commit and push that change, then import the repository into Vercel.

## 2. Deploy the website

[Import Odyssey_AI into Vercel](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FBJishnuPrasad%2FOdyssey_AI). Use the free Hobby plan for a personal, non-commercial project. Vercel builds from the repository root with the included config. No API key or Vercel environment variable is needed. After deployment, copy the generated `*.vercel.app` production URL and add it to the Live Website link at the top of README.md. The Vercel project can be connected to this GitHub repository for future deployments.

The first API request after inactivity may take about a minute while Render wakes. New results and uploads are temporary on Render's free filesystem; the bundled public snapshot is restored on restart. Vercel Hobby is limited to personal/non-commercial use. Review both providers' current quotas and do not add a payment method if you require a strict zero-payment setup.

Sources: [Vercel Hobby plan](https://vercel.com/docs/plans/hobby), [Vercel rewrites](https://vercel.com/docs/routing/rewrites), [Render free web services](https://render.com/docs/free).
