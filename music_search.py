"""Small iTunes catalog client. Caches metadata only, never audio."""
import json
import time
from threading import RLock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


def apple_url(value, store=False):
    if not isinstance(value, str):
        return ""
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    allowed = (host in ("itunes.apple.com", "music.apple.com") if store else
               host.endswith(".mzstatic.com") or host.endswith(".itunes.apple.com"))
    return value if parsed.scheme == "https" and allowed and not parsed.username and parsed.port in (None, 443) else ""


class CatalogUnavailable(Exception):
    pass


class MusicSearch:
    def __init__(self):
        self.cache = {}
        self.calls = []
        self.lock = RLock()

    def search(self, term, country="US"):
        term = " ".join(term.split())
        if not 2 <= len(term) <= 100:
            raise ValueError("Enter between 2 and 100 characters to search.")
        if country not in ("US", "AE", "IN", "GB"):
            raise ValueError("Choose an available store region.")
        key = (term.casefold(), country)
        with self.lock:
            now = time.monotonic()
            self.cache = {k: v for k, v in self.cache.items() if now - v[0] < 120}
            if key in self.cache:
                return self.cache[key][1]
            self.calls = [stamp for stamp in self.calls if now - stamp < 60]
            if len(self.calls) >= 18:
                raise CatalogUnavailable("Music search is busy. Please try again in a minute.")
            self.calls.append(now)
            query = urlencode(dict(term=term, country=country, media="music", entity="song", limit=24))
            request = Request("https://itunes.apple.com/search?" + query,
                              headers={"Accept": "application/json", "User-Agent": "MelodyCafe/1.0"})
            try:
                with urlopen(request, timeout=10) as response:
                    data = json.loads(response.read(2_000_000))
                results = []
                for item in data.get("results", []):
                    if item.get("kind") != "song":
                        continue
                    store = apple_url(item.get("trackViewUrl"), store=True)
                    if not store:
                        continue
                    results.append({"id": item.get("trackId"), "title": item.get("trackName", "Untitled"),
                                    "artist": item.get("artistName", "Unknown artist"),
                                    "album": item.get("collectionName", ""),
                                    "artwork": apple_url(item.get("artworkUrl100")),
                                    "audio": apple_url(item.get("previewUrl")), "store": store})
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, AttributeError, TypeError):
                raise CatalogUnavailable("Apple's catalog is unavailable right now. Please try again shortly.") from None
            payload = {"results": results, "country": country}
            if len(self.cache) >= 64:
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = (time.monotonic(), payload)
            return payload
