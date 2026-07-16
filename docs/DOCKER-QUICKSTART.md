# GenBox Docker Quick Start

1. Install Docker Desktop or Docker Engine with Compose v2.
2. Rename `.env.example` in this package to `.env`.
3. Before the first startup, use a password manager or another trusted offline
   generator to create a strong random administrator secret. Paste it directly
   after `ADMIN_KEY=` in `.env`, then save the file securely. Do not put the
   secret in a command, URL, shell history, screenshot, or ordinary log.
4. For remote access, replace `ALLOWED_ORIGINS` with your actual HTTPS or private-network URL.
5. Start GenBox:

```bash
docker compose pull
docker compose up -d
```

Open `http://localhost:8891`. This Docker package defaults to production mode.
Production startup requires
the user-supplied `ADMIN_KEY` in `.env`; a missing or blank value fails closed
and GenBox refuses to start. GenBox does not generate or deliver this key in
container logs. Keep the key in your password manager. Runtime media and
application data are written to `./storage`.

Development mode without an administrator key is limited to local source
development bound to the loopback interface. It is not the Docker default and
must not be used for remote access.

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
