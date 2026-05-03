<p align="center">
  <img src="docs/images/logo-bugbuster.png" alt="BugBuster Logo" width="280"/>
</p>

<p align="center">
  <strong>AI-powered test automation platform</strong>
</p>

<p align="center">
  Vision-based testing with natural language — no code required
</p>

---

## About BugBuster

**BugBuster** is a test automation platform powered by Vision Language Models (VLM) that sees the UI like a user and understands natural language. Write test cases in plain language, without selectors, DOM knowledge, or code.

| Stack | Extensibility |
|-------|----------------|
| VLM + Grounding + Playwright | Support for other frameworks; mobile testing roadmap |

### Key Features

- **No coding skills required** — describe test steps in natural language
- **Free-form test cases** — no rigid structure like Gherkin, no extra abstraction layers
- **No selectors or locators** — no DOM access, no maintenance when layout changes
- **Stable interaction** with dynamic UI elements through visual perception
- **Natural language steps** — use verbs like *click*, *type*, *scroll*, *hover*, *wait*

### Who It's For

| Audience | Use Case |
|----------|----------|
| **QA specialists** | Fast automation without long setup; easier test maintenance |
| **Teams without QA Automation** | Introduce automated testing without dedicated automation engineers |
| **Non-technical users** | Automate scenarios without programming knowledge |

---

## Quick Start

### Prerequisites: Git LFS

This repository uses **Git LFS** for Playwright binaries and related files. Without Git LFS, these files may be missing and related functionality will not work.

<details>
<summary><b>1. Install Git LFS (one time per machine)</b></summary>

Follow the official guide for your OS: [git-lfs.com](https://git-lfs.com)

**Windows (Chocolatey):**
```bash
choco install git-lfs
git lfs install
```

If Git LFS is already installed, enable it in this repo:
```bash
git lfs install
```

</details>

<details>
<summary><b>2. Clone the repository</b></summary>

```bash
git clone <THIS_REPOSITORY_URL>
cd bugbuster
git lfs pull
```

</details>

---

## Installation Guide

### Step 1 — Infrastructure

<details>
<summary><b>Create network and start infrastructure</b></summary>

1. Create Docker network:
```bash
docker network create bugbuster
```

2. Start MinIO, PostgreSQL, Redis, RabbitMQ, ClickHouse:
```bash
docker compose -p infrastructure -f infra/docker-compose.infrastructure.yml --env-file infra/infrastructure.env.example up -d
```

3. **Configure MinIO** — open http://localhost:9001 and create buckets:
   - `happypass`, `langfuse`, `run-cases`, `backend-files`, `backend-images`

   ![Create bucket](docs/images/minio_1.png)
   ![Final](docs/images/minio_2.png)

4. **Create databases:**
```bash
docker exec -it postgres psql -U postgres -c "CREATE DATABASE portal WITH ENCODING 'UTF8';"
docker exec -it postgres psql -U postgres -c "CREATE DATABASE langfuse WITH ENCODING 'UTF8';"
```

</details>

### Step 2 — Langfuse

<details>
<summary><b>Install and configure Langfuse</b></summary>

1. Start Langfuse:
```bash
docker compose -p langfuse -f infra/docker-compose.langfuse.yml --env-file infra/langfuse.env.example up -d
```

2. **Configure** — open http://localhost:3300:
   - Register an account
   - Create an organization (e.g., `bugbuster`)
   - Create two projects: `clicker` and `rewriter`
   - Generate API keys for both projects
   - Add keys to `services.env.example`

   ![Create organization](docs/images/langfuse_1.png)
   ![Create organization](docs/images/langfuse_2.png)
   ![Create project](docs/images/langfuse_3.png)
   ![Create API keys](docs/images/langfuse_4.png)

</details>

### Step 3 — Services

<details>
<summary><b>Build and run application services</b></summary>

1. **Configure** `infra/services.env.example`:
   - Add Langfuse API keys: `LANGFUSE_CLICKER_PUBLIC_KEY`, `LANGFUSE_CLICKER_SECRET_KEY`, `LANGFUSE_REWRITER_PUBLIC_KEY`, `LANGFUSE_REWRITER_SECRET_KEY`
   - Add `OPENROUTER_API_KEY`: `INFERENCE_API_KEY`, `SOP_REWRITER_API_KEY`

2. **Build images:**
```bash
docker compose -p services -f infra/docker-compose.services.yml --env-file infra/services.env.example build
```

3. **Run migrations (one-time):**
```bash
docker compose -p services -f infra/docker-compose.services.yml --env-file infra/services.env.example run --rm alembic upgrade head
```

4. **Start services:**
```bash
docker compose -p services -f infra/docker-compose.services.yml --env-file infra/services.env.example up -d
```

</details>

---

## Main Endpoints

After startup, the platform is available at:

| Service | URL |
|---------|-----|
| **Platform (Frontend)** | http://localhost:3000 |
| **Langfuse UI** | http://localhost:3300 |
| **Backend API (Swagger)** | http://localhost:7665/docs |
| **MinIO Console** | http://localhost:9001 |
| **Playwright Trace Viewer** | http://localhost:3209 |

> Ports are defined in `infra/services.env.example` and `docker-compose.*.yml`. Adjust addresses above if you change them.

---

## Next Steps

<details>
<summary><b>Create your first test case</b></summary>

See the user guide: [docs.bug-buster.ru](https://docs.bug-buster.ru)

</details>
