# Deployment patch checklist

### Railway
- Main `backend/`: use its existing Railway service URL for the APK.
- `backend3/`: set `RESEARCH_BACKEND_URL` on the main backend to this service URL.
- `backend4/`: set `JUDGE_BACKEND_URL` on the main backend to this service URL.
- Configure `/health` as the Railway healthcheck. Railway healthchecks validate startup only, not continuous uptime, so use an external monitor for continuous checks.

### Render
- `backend2`: memory service. Set `MONGO_URI` for durable memory.
- `backend5`: public web fetcher.
- `backend6`: context compressor.
- `backend7`: cache/jobs service.
- Each Dockerfile now honors Render's injected `PORT`.

### Android
- `INTERNET` and `ACCESS_NETWORK_STATE` are explicitly declared.
- `/chat` request JSON is encoded as UTF-8 bytes.
