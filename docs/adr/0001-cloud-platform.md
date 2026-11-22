# ADR 0001: Cloud platform for the quotes scraper

- **Status:** Accepted
- **Date:** 2026-11-22

## Context

The existing scraper runs locally with Redis Streams, Playwright and file-based
result storage. It needs to become an asynchronous cloud service with a web UI,
a REST API and a durable queue, while staying on free tiers that do not require
a credit card.

The target flow is:

```text
Vue (GitHub Pages) -> FastAPI + worker (Render) -> Supabase (Postgres + pgmq)
                                             \-> Cloudflare Browser Rendering
```

Functional requirements:

- submit an arbitrary URL and receive a job id immediately;
- process jobs asynchronously with a durable queue;
- persist job status and results;
- poll job status and fetch the result from the frontend;
- scrape both the known `quotes.toscrape.com/scroll` page and arbitrary URLs;
- keep all secrets in environment variables;
- make every operational step reproducible through `make`.

## Considered options

### Option A: Vue + FastAPI + Supabase pgmq + Cloudflare Browser Rendering (selected)

- Vue 3 static frontend hosted on GitHub Pages.
- FastAPI REST API and an asyncio worker in the same Render web service.
- Supabase Postgres for job status/results and pgmq for the queue.
- Cloudflare Browser Rendering for pages that are not the known scroll page.

### Option B: Render monolith + Supabase + Cloudflare Browser Rendering

A single service renders the UI and serves the API, without a separate static
frontend. This reduces moving parts, but couples the UI deployment to the
backend and makes the free Render sleep behaviour affect the whole product.

### Option C: Vercel frontend + Edge Functions + QStash + Neon

Vercel hosts the frontend and edge functions, QStash schedules/serialises jobs,
and Neon provides Postgres. This avoids a long-running Render service, but adds
another vendor and an HTTP-based queue that is less convenient to consume from
an asyncio worker.

## Decision

Adopt **Option A**.

It keeps a conventional frontend/backend split, uses a real Postgres-backed
queue, and requires no paid infrastructure. The worker runs inside the FastAPI
process to avoid paying for a second Render service.

## Consequences

### Positive

- Standard, well-documented stack (Vue, FastAPI, Postgres).
- Frontend and backend can be deployed independently.
- Supabase provides managed Postgres, pgmq and RLS in one place.
- No Redis, Docker or Terraform is required for the cloud deployment.
- Cloudflare offloads headless browser execution from the small Render instance.
- All free tiers work without a credit card.

### Negative

- The worker shares the FastAPI process and the 512 MB Render memory limit.
- Render free services sleep after 15 minutes of inactivity unless kept awake.
- Cloudflare Browser Rendering has a small daily browser-time quota.
- Supabase free projects pause after a period of inactivity.
- pgmq must be exposed through the `pgmq_public` schema before the backend can
  call it over the Data API.
- The backend currently uses the public `SUPABASE_ANON_KEY`, so the SQL setup
  grants the `anon` role access. Production deployments should use a
  `service_role` key and remove the anon policies.
- Polling adds latency and egress compared with webhooks or WebSockets.

## Free tier limits

Approximate limits at the time of writing. Provider limits change, so verify
them before relying on them in production.

| Service | Free tier | Used for |
| --- | --- | --- |
| GitHub Pages | 1 GB published site, 100 GB/month soft bandwidth, 10 builds/hour | Vue frontend |
| Render Free Web Service | 512 MB RAM, 0.1 CPU, 750 instance hours/month, sleeps after 15 minutes idle | FastAPI + worker |
| Supabase Free | 500 MB database, 1 GB file storage, 5 GB/month egress, 2 active projects, pauses after 7 days of inactivity | Postgres, job tables, pgmq |
| Cloudflare Browser Rendering Free | 10 minutes/day of browser time | Scraping arbitrary URLs |
| GitHub | Unlimited public repositories and standard Actions minutes | Source code, optional CI |

## What breaks at limits

- **Cloudflare 10 min/day:** arbitrary-URL jobs start failing with
  `Browser quota exceeded` (HTTP 429 from Cloudflare). The known scroll page
  still uses Playwright on Render, but that path is limited by Render RAM/CPU.
- **Render 512 MB / 0.1 CPU:** Playwright with Chromium may be slow and can be
  killed under memory pressure. Browser-heavy scraping is the first thing to
  move to a larger instance or an external browser service.
- **Render 750 instance hours/month:** one always-on service consumes roughly
  730 hours per month. A second free service or a 24/7 keepalive for several
  services exceeds the quota.
- **Render sleep after 15 minutes:** the first request after idle incurs a cold
  start, which may exceed a client's patience. The Supabase cron keepalive
  prevents sleep but keeps the service running 24/7.
- **Supabase 500 MB database:** job results are JSONB and accumulate quickly.
  Without retention/cleanup, inserts eventually fail with disk/quota errors.
- **Supabase 5 GB/month egress:** status polling and result downloads consume
  egress. At the limit, REST requests fail even though the database is healthy.
- **Supabase 7-day inactivity pause:** the scheduled keepalive must continue to
  run, otherwise the project pauses and all API calls fail.
- **GitHub Pages 100 GB/month bandwidth:** the static frontend is small, so this
  limit is unlikely to be hit before the backend or database limits.

## Migration path

1. **More browser time:** upgrade Cloudflare Browser Rendering to a paid plan,
   or self-host Playwright/Chromium on a larger worker.
2. **Always-on backend:** upgrade Render to a paid instance with more RAM/CPU
   and no sleep. If queue throughput grows, split the worker into its own
   service so API latency and scraping do not compete for the same process.
3. **More database capacity:** upgrade Supabase to Pro for a larger database,
   no inactivity pause, backups and higher egress. pgmq is a Postgres extension,
   so the schema can also be moved to another managed Postgres provider.
4. **Less polling:** replace client polling with Server-Sent Events, WebSockets
   or webhooks once the frontend or API egress becomes a bottleneck.
5. **Independent scaling:** replace pgmq with a dedicated queue (SQS, Redis
   Streams, RabbitMQ) if multiple workers, priorities or retry policies are
   needed.
6. **Vendor diversification:** move the frontend to Cloudflare Pages or Vercel
   and the backend to Fly.io/Railway without changing the API contract.
