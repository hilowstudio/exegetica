# 0034: Class videos play inside Exegetica, from Exegetica's own copy where the owner allows

Decided by A. James Vega, 2026-11-14, from his request that the class's videos be hosted so the course doesn't break in
later years when links are taken down. It extends 0031, which gave podcasts a player inside Exegetica.

**Decision.**
- **A video on a class shelf opens a watch page in Exegetica** (`/watch/<shelf item>`). The page has the video's title,
  who made it, the player and the teacher's note.
  - A clip starts at its second and stops at its end, with a way to keep watching.
  - The page plays only what is on the viewer's own class shelves, as the podcast player does. A student sees what is
    placed for students in their classes, and a class's teachers see everything on its shelf.
  - Casting the page to a classroom TV works as it does for any page.
- **Hosted copies.**
  - When a video's owner has given permission, or the teacher owns a copy and the owner allows it to be hosted,
    Exegetica keeps the file in its own storage (Cloudflare R2) and plays it from there.
  - The viewer's browser gets a short-lived link to the file only after the access check.
  - A hosted video is shown whole or as a teacher's clip, never edited.
  - When the owner asks for credit, the credit shows under the player.
- **Owners who don't allow hosting.** The video plays in YouTube's privacy-enhanced player (youtube-nocookie.com) on the
  same watch page, with the clip's start and end. The player loads only when someone presses play, so opening the page
  sends nothing to YouTube.
- **Loading a video.** `scripts/host_video.py` converts a file to a web MP4 (H.264 and AAC, 720p), uploads it and
  records it on the video's catalog entry.
  - A file comes from its owner, from the owner's own download page, or from the teacher's own copy.
  - Nothing is downloaded from YouTube itself, since YouTube's terms forbid it even when the owner agrees.
- **Permissions on record, 2026-11-14:**
  - Hosting granted: Jesus Film Project (LUMO), Ligonier, Daily Dose of Greek, The Gospel Coalition, bethinking.org,
    Rebecca McLaughlin, Peter J. Williams and Tyndale House (with credit), plus Life.Church (Spoken Gospel) for the
    school's use.
  - Hosting allowed for a copy the teacher owns: Drive Thru History and the Visual Bible *Gospel of John*.
  - Refused: BibleProject. Their terms forbid uploading their videos to any other server, so their videos use the
    YouTube player.

**Why.**
- Links go dead across school years, and a course built on them breaks.
- YouTube's own site puts ads, recommendations and tracking in front of students.
- A clip can stop at its end only on a player Exegetica controls.
- The teacher casts videos to the classroom TV, so the page has to play cleanly and full screen.

**What it touches.**
- **0013.** The privacy page says where class videos come from: Exegetica's storage at Cloudflare, or YouTube's player
  for a video Exegetica can't host. In the YouTube case, YouTube sees the viewer's device once someone presses play.
- **0031.** The watch page follows the listening page: the same access rule, the same clip handling, and nothing about
  what a student watched kept on the server.
- **0002.** Nothing about what a student watched is kept on the server or given to a model.

**Enforced in.**
- `webapp/watch.py`: the access rule, the page, the short-lived file link and captions.
- `templates/watch.html`, `static/js/watch.js`, `static/css/watch.css`.
- `webapp/shelves.py`: a class shelf's video tile opens the watch page.
- `scripts/host_video.py`.
- `docs/privacy.md`.
- `tests/test_watch.py`.

**Reverse when.** An owner withdraws permission. `host_video.py --remove` deletes the copy, and the tile falls back to
the owner's own player or comes off the shelf.
