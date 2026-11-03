# Melody Cafe — Local playlist dashboard

## Start on your Windows laptop

1. Double-click `Start_Melody.cmd` in this folder.
2. Keep the terminal window open.
3. Open **http://127.0.0.1:8765** in your browser.
4. Press Ctrl+C in the terminal when finished.

Requires Python 3. No pip packages, Node installation, account, or internet connection required.

From a terminal you can also run `python melody_dashboard/server.py` from the parent folder, or `python server.py` from this folder. If port 8765 is busy, use `python server.py --port 8766` and open the printed URL.

## What you can do

- Open **Discover music** in the left navigation (or top navigation on mobile) to search the iTunes Store by song, artist, or album. Choose a store region and use **Listen** to hear Apple's available audio clip. Each result links to its iTunes page. Audio streams directly from Apple and is not downloaded or stored by this application; not every song or region has audio available.
- The Discover player and playlist player pause each other when switching views. Catalog audio is separate from the custom linked-list playlist and is not added to the shared queue.
- Add a title (1–30 characters) and duration (1–86400 whole seconds).
- Choose **After a song…** to insert after an exact title; a missing title displays a message.
- Display the linked list forward or backward. Changing display direction does not change playback order.
- Click a song to select it. Play/pause, previous, next, seek, and repeat at the end.
- Remove a song using its × button, or enter a title under **Remove by title**. As in the assessment, removal and insertion use the first matching title if duplicates exist.
- Attach an audio file to the selected song to hear real music. Without a file, playback is a timer simulation. Attached audio is local to that browser tab/session and must be reattached after refresh. Track metadata duration remains what you entered; the player uses the audio file's actual duration when attached.

The first launch contains Sunrise, Desert Rain, and Marina Lights. Metadata is saved automatically to `songs.jsonl` beside the server. Empty playlists stay empty after restarting. Playback position and audio attachments are not persisted. Use one browser tab for a consistent active player.

## Files and linked-list implementation

- `playlist.py` is an unchanged copy of `../RollNo_Name_Playlist.py`. The original assessment source is untouched.
- `server.py` adapts that copied class into a local API using Python's standard library.
- `static/index.html`, `static/style.css`, `static/app.js` provide the responsive dashboard.
- `music_search.py` and `static/discover.js` implement catalog discovery through Apple's iTunes Search API. Only metadata is cached for two minutes, with a bounded cache and request limit. Audio and artwork are provided courtesy of iTunes, with Apple's official store badge beside the listening controls.
- The backend holds songs in the custom doubly linked list. Arrays in JSON responses and the browser are only for rendering; playlist mutations happen through the Python linked-list methods.
- Forward/backward API responses walk `next`/`prev`, respectively. The original console display functions are preserved in the copy; the dashboard renders the same traversal visually instead of printing it.
- `test_dashboard.py` verifies API behavior, persistence, selection changes, validation, and local access rules with a temporary data file.

## Test

From this folder: `python -m unittest -v test_dashboard`

The local launcher listens only on your laptop at `127.0.0.1`. The app also supports Render hosting; see [DEPLOY_RENDER.md](DEPLOY_RENDER.md) for cloud settings and storage behavior. The original assessment file remains unchanged.
