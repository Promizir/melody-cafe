# Deploy Melody Cafe to Render

Deploy **this melody_dashboard folder as the repository root**. No changes to the original assessment file are needed. The copied `playlist.py` is included.

The app is a shared classroom demo: everyone with its public link can view and edit the same playlist. Audio attachments remain in each visitor's browser and are not uploaded. There is no account system.

## Render web service settings

| Setting | Value |
| --- | --- |
| Runtime | Python |
| Build command | `python -m unittest -v test_dashboard` |
| Start command | `python server.py` |
| Health check path | `/healthz` |

If the repository instead contains the whole Test_DSA project, set the service's Root Directory to `melody_dashboard` before deploying.

No third-party Python dependencies are required. The service automatically reads Render's `PORT`, binds to `0.0.0.0`, and accepts its `RENDER_EXTERNAL_HOSTNAME` with HTTPS browser origins. Local launch still binds to `127.0.0.1`.

## Storage choices

**Free demo:** no disk or extra variables. Playlist changes are temporary and reset on service restarts, redeployments, and idle shutdowns. The UI labels this explicitly. The local laptop copy still saves its own songs normally.

**Persistent playlist:** use a paid web service with a persistent disk mounted at `/var/data`. Set `MELODY_DATA_DIR=/var/data` and `MELODY_PERSISTENT_STORAGE=true`. Set the latter only when the persistent disk is actually attached. The app creates `songs.jsonl` in that directory and keeps it across restarts. Use one service instance because the playlist lives in process memory and on that single disk.

Use the current plan prices in Render's dashboard before choosing a paid service.

## Source publication

Push this folder to your chosen GitHub repository. The `.gitignore` excludes local playlist data, environment files, logs, and Python caches. Publish code and assets only. Render must have access to that repository before it can deploy.

## Verification

Wait for the specific deploy to become Live, then check `/healthz`, load the homepage, and verify `/api/state`. Test add/insert/remove/playback in the browser. A created service or queued deploy alone does not mean the website is ready.

References: [Render web services](https://render.com/docs/web-services), [free service limits](https://render.com/docs/free), [persistent disks](https://render.com/docs/disks).
