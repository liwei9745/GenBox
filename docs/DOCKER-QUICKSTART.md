# GenBox Docker Quick Start

1. Install Docker Desktop or Docker Engine with Compose v2.
2. Rename `.env.example` in this package to `.env`.
3. For remote access, replace `ALLOWED_ORIGINS` with your actual HTTPS or private-network URL.
4. Start GenBox:

```bash
docker compose pull
docker compose up -d
```

Open `http://localhost:8891`. The first startup creates an administrator key.
Read it once with `docker compose logs genbox`, then store it in a password
manager. The generated key is persisted to the mounted `.env` file. Runtime
media and application data are written to `./storage`.

Check status with:

```bash
docker compose ps
docker compose logs --tail=100 genbox
```

Update with:

```bash
docker compose pull
docker compose up -d
```
