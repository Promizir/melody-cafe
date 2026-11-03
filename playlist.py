"""Melody Cafe assessment: a custom, non-circular doubly linked list.

Rename RollNo_Name to your own roll number and name before submission.
"""


class Song:
    def __init__(self, title, duration):
        if len(title) > 30:
            raise ValueError("A song title must contain at most 30 characters.")
        self.title = title
        self.duration = duration  # Duration in seconds.
        self.prev = None
        self.next = None


class Playlist:
    def __init__(self):
        self.head = None
        self.tail = None

    def addSong(self, title, duration):
        new_song = Song(title, duration)
        if self.head is None:
            self.head = new_song
            self.tail = new_song
        else:
            new_song.prev = self.tail
            self.tail.next = new_song
            self.tail = new_song
        return new_song

    def insertAfter(self, key, title, duration):
        current = self.head
        while current is not None and current.title != key:
            current = current.next

        if current is None:
            print(f"Song not found: {key}")
            return False

        new_song = Song(title, duration)
        following = current.next
        new_song.prev = current
        new_song.next = following

        if following is None:
            self.tail = new_song
        else:
            following.prev = new_song
        current.next = new_song
        return True

    def removeSong(self, title):
        current = self.head
        while current is not None and current.title != title:
            current = current.next

        if current is None:
            print(f"Song not found: {title}")
            return False

        previous = current.prev
        following = current.next

        if previous is None:
            self.head = following
        else:
            previous.next = following

        if following is None:
            self.tail = previous
        else:
            following.prev = previous

        current.prev = None
        current.next = None
        return True

    def displayForward(self):
        print("Forward: ", end="")
        if self.head is None:
            print("Playlist is empty.")
            return

        current = self.head
        while current is not None:
            print(current.title, end="")
            current = current.next
            if current is not None:
                print(" -> ", end="")
        print()

    def displayBackward(self):
        print("Backward: ", end="")
        if self.tail is None:
            print("Playlist is empty.")
            return

        current = self.tail
        while current is not None:
            print(current.title, end="")
            current = current.prev
            if current is not None:
                print(" -> ", end="")
        print()

    def playNext(self, current):
        """current must be a node in this playlist, or None to start playback."""
        if self.head is None:
            return None
        if current is None or current.next is None:
            return self.head
        return current.next


def main():
    playlist = Playlist()

    print("Step 1: Add Sunrise (210), Desert Rain (185), Marina Lights (240).")
    playlist.addSong("Sunrise", 210)
    playlist.addSong("Desert Rain", 185)
    marina_lights = playlist.addSong("Marina Lights", 240)

    print("Step 2: Insert Skyline (200) after Sunrise.")
    playlist.insertAfter("Sunrise", "Skyline", 200)

    print("Step 3: Insert Night Drive (195) after Marina Lights.")
    playlist.insertAfter("Marina Lights", "Night Drive", 195)

    print("Step 4: Display forward and backward.")
    playlist.displayForward()
    playlist.displayBackward()

    print("Step 5: Remove Sunrise, Desert Rain, Night Drive, then Unknown.")
    playlist.removeSong("Sunrise")
    playlist.removeSong("Desert Rain")
    playlist.removeSong("Night Drive")
    playlist.removeSong("Unknown")

    print("Step 6: Display forward and backward again.")
    playlist.displayForward()
    playlist.displayBackward()

    print("Step 7: Play the next song after Marina Lights.")
    next_song = playlist.playNext(marina_lights)
    if next_song is None:
        print("Playlist is empty.")
    else:
        print(f"Next song: {next_song.title}")


if __name__ == "__main__":
    main()
