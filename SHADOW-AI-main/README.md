# Shadow AI 4.0 architecture

Shadow AI is split into a lightweight Android frontend and independent backend services.

## Deployment map

### Railway
- `backend/` = Main Brain / orchestrator
- `backend3/` = Multi-source research engine
- `backend4/` = Independent answer judge / audit service

### Render
- `backend2/` = Long-term memory service (MongoDB recommended)
- `backend5/` = Web page retrieval service
- `backend6/` = Context compression service
- `backend7/` = Small cache/background-job service

### Android APK
- `frontend/` is built by GitHub Actions using Buildozer.
- `INTERNET` and `ACCESS_NETWORK_STATE` are explicitly declared in `buildozer.spec`.
- `background.jpg` is bundled.
- `intro.mp4` is optional and bundled when present.

## AI team
The main brain directly calls official provider APIs. It does not use an OpenAI-compatible proxy.

Primary models: OpenAI + Anthropic.
Optional independent critics for complex tasks: Gemini, xAI, and Mistral.

The five-model fan-out is intentionally restricted to complex/research tasks. Simple conversation uses one provider, which reduces latency, API usage, CPU and memory pressure.

## Long conversation strategy
The APK only keeps a bounded recent window. The memory backend stores the durable conversation externally. The context service can compact older context. The main backend retrieves only relevant memory instead of loading an entire conversation into RAM.

## Health monitoring
Every service exposes `/health`, so an external uptime monitor can check each deployment. Uptime monitoring does not turn a free hosting plan into unlimited compute, because physics remains annoyingly employed.

## Environment variables
See each backend's `.env.example` file. Never put provider API keys in the APK.
