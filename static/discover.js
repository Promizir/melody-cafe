(() => {
  'use strict';
  const get = id => document.getElementById(id);
  const catalogAudio = get('catalog-audio');
  let controller, selected = null, selectedButton = null, playbackVersion = 0;

  function switchView(view) {
    const discover = view === 'discover';
    get('playlist-view').hidden = discover;
    get('discover-view').hidden = !discover;
    document.querySelector('.player').hidden = discover;
    document.querySelectorAll('[data-view]').forEach(button => {
      const active = button.dataset.view === view;
      button.classList.toggle('nav-active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    if (discover) {
      // Stop both real audio and the playlist's timer before catalog playback.
      playing = false;
      audio.pause();
      updatePlayer();
      get('music-query').focus();
    } else {
      playbackVersion++;
      catalogAudio.pause();
    }
  }
  document.querySelectorAll('[data-view]').forEach(button => {
    button.addEventListener('click', () => switchView(button.dataset.view));
  });

  function updateButton() {
    if (!selectedButton) return;
    selectedButton.textContent = catalogAudio.paused ? '▶ Listen' : 'Ⅱ Pause';
    selectedButton.setAttribute('aria-label', (catalogAudio.paused ? 'Listen to ' : 'Pause ') + selected.title);
  }
  catalogAudio.addEventListener('play', updateButton);
  catalogAudio.addEventListener('pause', updateButton);
  catalogAudio.addEventListener('ended', updateButton);
  catalogAudio.addEventListener('error', () => {
    if (catalogAudio.getAttribute('src')) notify('This song cannot play right now. Try another track or open it on iTunes.', true);
    updateButton();
  });

  async function listen(song, button) {
    const version = ++playbackVersion;
    if (selected?.id === song.id && !catalogAudio.paused) {
      catalogAudio.pause();
      return;
    }
    if (selected?.id !== song.id) {
      catalogAudio.pause();
      if (selectedButton) selectedButton.textContent = '▶ Listen';
      selected = song;
      selectedButton = button;
      catalogAudio.src = song.audio;
      get('catalog-title').textContent = song.title;
      get('catalog-artist').textContent = `${song.artist} · ${song.album}`;
      get('catalog-store').href = song.store;
      get('catalog-player').hidden = false;
    }
    if (catalogAudio.ended) catalogAudio.currentTime = 0;
    try { await catalogAudio.play(); }
    catch (error) {
      if (version === playbackVersion && error.name !== 'AbortError') notify('Unable to play this song. Try another track or open it on iTunes.', true);
    }
    if (version === playbackVersion) updateButton();
  }

  function showResults(songs) {
    const results = get('search-results');
    results.replaceChildren();
    songs.forEach(song => {
      const card = document.createElement('article'); card.className = 'music-card';
      const art = document.createElement('div'); art.className = 'catalog-art'; art.textContent = '♫';
      if (song.artwork) {
        const image = document.createElement('img'); image.src = song.artwork; image.alt = ''; image.loading = 'lazy';
        image.addEventListener('error', () => image.remove()); art.append(image);
      }
      const info = document.createElement('div'); info.className = 'catalog-info';
      const title = document.createElement('h2'); title.textContent = song.title;
      const artist = document.createElement('p'); artist.textContent = song.artist;
      const album = document.createElement('small'); album.textContent = song.album;
      info.append(title, artist, album);
      const controls = document.createElement('div'); controls.className = 'catalog-controls';
      const button = document.createElement('button'); button.className = 'secondary';
      button.textContent = song.audio ? '▶ Listen' : 'Audio unavailable'; button.disabled = !song.audio;
      button.setAttribute('aria-label', song.audio ? 'Listen to ' + song.title : 'Audio unavailable for ' + song.title);
      button.addEventListener('click', () => listen(song, button));
      const store = document.createElement('a'); store.href = song.store; store.target = '_blank'; store.rel = 'noopener noreferrer';
      store.setAttribute('aria-label', 'Get ' + song.title + ' on iTunes');
      const badge = document.createElement('img'); badge.src = '/itunes-badge.svg'; badge.alt = 'Get it on iTunes'; badge.width = 110; badge.height = 37;
      store.append(badge); controls.append(button, store); card.append(art, info, controls); results.append(card);
    });
  }

  get('music-search').addEventListener('submit', async event => {
    event.preventDefault();
    const term = get('music-query').value.trim();
    if (term.length < 2) { get('search-status').textContent = 'Enter at least two characters.'; return; }
    controller?.abort();
    const activeController = new AbortController(); controller = activeController;
    const timeout = setTimeout(() => activeController.abort(), 25000);
    playbackVersion++; catalogAudio.pause(); catalogAudio.removeAttribute('src'); catalogAudio.load();
    selected = null; selectedButton = null;
    get('catalog-player').hidden = true; get('search-intro').hidden = true;
    get('search-results').replaceChildren();
    get('search-status').textContent = `Searching for “${term}”…`;
    get('search-results').setAttribute('aria-busy', 'true');
    get('search-submit').textContent = 'Searching…';
    try {
      const params = new URLSearchParams({q: term, country: get('music-country').value});
      const response = await fetch('/api/search?' + params, {signal: activeController.signal});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Search is unavailable. Please try again.');
      if (controller !== activeController) return;
      showResults(data.results);
      get('search-status').textContent = data.results.length ? `${data.results.length} songs for “${term}”` : `No songs found for “${term}”. Try another spelling, artist, or store region.`;
    } catch (error) {
      if (controller === activeController) get('search-status').textContent = error.name === 'AbortError' ? 'Search took too long. Please try again.' : error.message;
    } finally {
      clearTimeout(timeout);
      if (controller === activeController) {
        get('search-results').setAttribute('aria-busy', 'false');
        get('search-submit').textContent = 'Search music';
      }
    }
  });
})();
