# Free Render demonstration

[Deploy to Render](https://render.com/deploy?repo=https://github.com/BJishnuPrasad/Odyssey_AI)

Sign in to Render, open this link, and review the blueprint. It creates one **Free** Docker web service in Singapore with no disk, paid database, or worker. Keep the free instance selected. Do not add a payment method or choose an upgrade; stop if the dashboard asks for payment. If the repository is private, authorize Render to read this repository through GitHub first.

After deployment reaches Live, open the service URL shown by Render. Verify `/api/health`, the map, the bundled completed analysis, and a heritage site model. The frontend and FastAPI share one origin; no separate frontend service or API URL setting is needed. Automatic deploys are disabled to avoid unnecessary builds. Trigger a manual deploy when you want later GitHub changes published.

## Free-tier behavior

Render sleeps free services after 15 minutes without inbound traffic. Waking takes about a minute. It provides 750 free instance hours per workspace each month; other free services share the allowance. Free services have no persistent disk: SQLite, uploads and new analysis results can disappear on sleep, restart or redeploy. Export useful results immediately. All visitors share this demonstration workspace without logins.

Startup verifies SHA-256 checksums and restores bundled public environmental evidence, six soil profiles and one completed analysis. It excludes contributor records, uploaded models, credentials and the local SQLite database. Existing data is preserved if startup runs again on the same filesystem. Original local project data is unaffected.

The free instance has limited memory and CPU. Bundled results are immediately available after startup; heavy acquisition or analysis may exceed its resources. This deployment does not promise uninterrupted API availability or durable research storage. Free PostgreSQL is deliberately not used because it expires after 30 days.

Build and bandwidth quotas also apply. With no payment method, Render suspends service or builds when relevant allowances are exhausted instead of charging overages. Do not attach a payment method if a strict no-payment limit is required. Account-level existing services and billing settings must be checked separately.

Sources: [Render free services](https://render.com/docs/free), [Blueprint specification](https://render.com/docs/blueprint-spec).

## Package and local verification

`python -m scripts.package_hosted_seed` creates a new public snapshot from a completed local analysis; it refuses to overwrite an existing seed. Review any replacement snapshot before publishing.

`python -m scripts.start_hosted` checks and imports the seed, then starts one Uvicorn process using `PORT` (default 10000) and `GEODYSSEY_RUNTIME`. Set `GEODYSSEY_HOSTED_DEMO=1` to display the free-demo notice. Use a separate runtime directory when testing. The Docker build also installs the bundled OSM extracts into `Data/derived`.

The Dockerfile builds React with Node 24 and installs the pinned Python 3.12 dependencies. Local tests verify seeding, preservation of existing runs, checksum failure and the demo flag. The actual Linux container build and public service health must additionally pass on Render; Docker is not installed on the development computer.
