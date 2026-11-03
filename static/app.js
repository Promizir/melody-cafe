'use strict';
const $ = id => document.getElementById(id);
let state = {songs: [], current: null}, backward = false, playing = false, position = 0;
let busy = false, lastTick = performance.now(), toastTimer;
const audio = $('audio'), files = new Map();
const time = value => { const seconds = Math.max(0, Math.floor(value || 0)); return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`; };
const currentSong = () => state.songs.find(song => song.id === state.current);
function notify(message, error = false) {
  $('toast').textContent = message; $('toast').classList.toggle('error', error); $('toast').hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 4500);
}
async function request(path, options) {
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Something went wrong. Please try again.');
  return result;
}
async function refresh() {
  const old = state.current;
  state = await request('/api/state' + (backward ? '?backward=1' : ''));
  if (state.hosted) {
    document.querySelector('.local-badge').textContent = 'Shared café playlist';
    document.querySelector('.sidebar-bottom').textContent = 'MELODY CAFÉ · ONLINE';
    document.querySelector('.saved-note').textContent = state.persistent ? 'Changes saved to the shared playlist' : 'Demo playlist · resets when the server restarts';
    document.querySelector('.panel-header p').textContent = 'One shared mix. Anyone with the link can edit.';
  }
  if (old !== state.current) { position = 0; audio.pause(); audio.removeAttribute('src'); audio.load(); }
  if (!currentSong()) playing = false;
  render();
  if (old !== state.current && playing) await startAudio();
}
async function action(data, silent = false) {
  if (busy) return false;
  busy = true;
  try {
    const result = await request('/api/action', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
    await refresh();
    if (!silent) notify(result.message);
    return true;
  } catch (error) { notify(error.message, true); return false; }
  finally { busy = false; }
}
function render() {
  const container = $('songs'); container.replaceChildren(); $('song-titles').replaceChildren();
  state.songs.forEach((song, index) => {
    const row = document.createElement('div'); row.className = 'song-row'; row.classList.toggle('is-current', song.id === state.current);
    const number = document.createElement('span'); number.className = 'row-number'; number.textContent = song.id === state.current ? '♫' : String(index + 1).padStart(2, '0');
    const select = document.createElement('button'); select.className = 'song-select'; select.setAttribute('aria-label', 'Select ' + song.title);
    const art = document.createElement('span'); art.className = 'song-art'; art.textContent = '♫';
    const info = document.createElement('span'); info.className = 'song-info';
    const title = document.createElement('strong'); title.textContent = song.title;
    const detail = document.createElement('small'); detail.textContent = files.has(song.id) ? 'Audio attached · Café collection' : 'Café collection · Timer playback';
    info.append(title, detail); select.append(art, info); select.onclick = () => action({action: 'select', id: song.id}, true);
    const duration = document.createElement('span'); duration.className = 'song-duration'; duration.textContent = time(song.duration);
    const remove = document.createElement('button'); remove.className = 'remove'; remove.textContent = '×'; remove.title = 'Remove first song titled ' + song.title; remove.setAttribute('aria-label', remove.title);
    remove.onclick = async () => {
      if (await action({action: 'remove', title: song.title})) {
        // Remove stale audio URLs after the server resolves first-match deletion.
        for (const [key, url] of files) if (!state.songs.some(s => s.id === key)) { URL.revokeObjectURL(url); files.delete(key); }
      }
    };
    row.append(number, select, duration, remove); container.append(row);
    const option = document.createElement('option'); option.value = song.title; $('song-titles').append(option);
  });
  const total = state.songs.reduce((sum, song) => sum + song.duration, 0);
  $('count').textContent = state.songs.length; $('hero-count').textContent = `${state.songs.length} ${state.songs.length === 1 ? 'song' : 'songs'}`;
  $('hero-duration').textContent = `${Math.floor(total / 60)} min`; $('total-time').textContent = `${time(total)} total`;
  $('empty').hidden = state.songs.length > 0;
  $('forward').classList.toggle('active', !backward); $('backward').classList.toggle('active', backward);
  $('forward').setAttribute('aria-pressed', String(!backward)); $('backward').setAttribute('aria-pressed', String(backward));
  $('play').disabled = $('next').disabled = $('previous').disabled = !state.songs.length;
  $('attach').disabled = !currentSong();
  updatePlayer();
}
function updatePlayer() {
  const song = currentSong();
  $('now-title').textContent = song?.title || 'Pick your first song';
  $('playback-mode').textContent = !song ? 'Select a track to begin' : files.has(song.id) ? 'Local audio · ' + (playing ? 'Playing' : 'Paused') : 'Timer only · ' + (playing ? 'Playing' : 'Ready');
  $('play').textContent = playing ? 'Ⅱ' : '▶'; $('play').setAttribute('aria-label', playing ? 'Pause' : 'Play');
  const duration = song && files.has(song.id) && Number.isFinite(audio.duration) ? audio.duration : song?.duration || 0;
  $('elapsed').textContent = time(position); $('track-duration').textContent = time(duration);
  $('progress').max = duration || 1; $('progress').value = position; $('progress').disabled = !song;
}
async function startAudio() {
  const song = currentSong();
  if (!song || !files.has(song.id)) { updatePlayer(); return; }
  if (audio.getAttribute('src') !== files.get(song.id)) { audio.src = files.get(song.id); position = 0; }
  try { await audio.play(); }
  catch { playing = false; notify('This audio could not play. Attach a supported MP3, WAV, or OGG file.', true); }
  updatePlayer();
}
$('song-form').onsubmit = async event => {
  event.preventDefault();
  const data = {action: $('placement').value === 'after' ? 'insert' : 'add', title: $('title').value.trim(), duration: Number($('duration').value), key: $('key').value.trim()};
  if (await action(data)) { $('title').value = ''; $('title').focus(); }
};
$('remove-form').onsubmit = async event => { event.preventDefault(); if (await action({action: 'remove', title: $('remove-title').value.trim()})) $('remove-title').value = ''; };
$('placement').onchange = () => { $('key-field').hidden = $('placement').value !== 'after'; $('key').required = !$('key-field').hidden; };
$('jump-add').onclick = () => { $('song-form').scrollIntoView({behavior: 'smooth', block: 'center'}); $('title').focus({preventScroll: true}); };
async function setDirection(value) { backward = value; try { await refresh(); } catch (error) { notify(error.message, true); } }
$('forward').onclick = () => setDirection(false); $('backward').onclick = () => setDirection(true);
$('next').onclick = () => advance('next'); $('previous').onclick = () => advance('previous');
async function advance(direction) {
  const old = state.current;
  if (await action({action: direction}, true)) {
    if (old === state.current) { position = 0; if (audio.src) audio.currentTime = 0; if (playing) await startAudio(); updatePlayer(); }
  } else { playing = false; audio.pause(); updatePlayer(); }
}
$('play').onclick = async () => {
  if (busy) return;
  if (!state.current && !await action({action: 'next'}, true)) return;
  if (!currentSong()) return;
  playing = !playing; lastTick = performance.now();
  if (playing) await startAudio(); else audio.pause();
  updatePlayer();
};
$('progress').oninput = () => { position = Number($('progress').value); if (currentSong() && files.has(state.current) && Number.isFinite(audio.duration)) audio.currentTime = position; updatePlayer(); };
$('attach').onclick = () => $('audio-file').click();
$('audio-file').onchange = async () => {
  const file = $('audio-file').files[0], song = currentSong();
  if (!file || !song) return;
  audio.pause(); if (files.has(song.id)) URL.revokeObjectURL(files.get(song.id));
  files.set(song.id, URL.createObjectURL(file)); position = 0; audio.src = files.get(song.id); audio.load();
  $('audio-file').value = ''; render(); notify(`Attached audio to "${song.title}" for this session.`);
  if (playing) await startAudio();
};
audio.onended = () => { if (playing) advance('next'); };
audio.onloadedmetadata = updatePlayer;
audio.onerror = () => { playing = false; updatePlayer(); notify('Unable to read this audio file. Try MP3, WAV, or OGG.', true); };
setInterval(() => {
  const now = performance.now(), delta = (now - lastTick) / 1000; lastTick = now;
  if (!playing || !currentSong() || busy) return;
  if (files.has(state.current)) position = audio.currentTime;
  else { position += delta; if (position >= currentSong().duration) { position = 0; advance('next'); } }
  updatePlayer();
}, 250);
refresh().catch(error => notify('Cannot connect to the Python server. ' + error.message, true));
