# 0031: Podcast episodes, a player for students, and saving many things at once

Decided by A. James Vega, 2026-11-12 (the audio through Exegetica, episodes and moments on class shelves, resources copied into a unit), from his requests of 2026-11-11: search podcasts for episodes as well as shows, save an episode as its own item, build a player students can use so podcasts can go on class shelves, and send many shelved things to a class shelf or a unit at once. It extends 0029, which held podcasts back from class shelves until students had a player.

**Decision.**
- **Episodes are found and kept on their own.** The Podcast search has Shows and Episodes. An episode comes from the same Apple directory the show search uses, with its show, date, length, description and audio. Saving one puts that episode on the teacher's shelf as its own item, apart from its show. A teacher can still save a whole show. An episode works wherever a show's episode works today: a unit, a saved moment, a transcript (0028).
- **Podcasts go on class shelves.** A teacher may place a podcast episode, or a moment in one, on a class shelf. A whole show stays off class shelves: a class gets the episode the teacher chose, never a feed of whatever the show publishes next.
- **Students listen inside Exegetica.** A podcast on a class shelf opens in a player page: the episode's title, show and description, the audio, and the transcript when a teacher has had one made. A moment starts at its second and says where it ends. The player plays only what is on the student's own class shelves.
- **The audio comes through Exegetica.** Many episodes play through a host's tracking address (an analytics redirect such as Podtrac) before the file. So a student's browser never fetches the audio from the host: Exegetica's server fetches it and passes it on, and the host and any tracker see Exegetica's server, never the student's device. The student's browser contacts no one but Exegetica (Group E, rule E6).
- **A listening place stays on the device.** Where a student stopped is kept in that browser only, the way a page remembers a setting. Nothing about a student's listening reaches the server, beyond the request for the audio itself.
- **Saving many things at once.** On a teacher's own shelf and on any class shelf they teach, Select puts a check circle on every item. The teacher picks any mix of books, uploads, saved pages, videos, podcasts and Prep Room resources, then one Save to sends them to a class shelf or a unit. The items stay where they were (a copy goes, as with one item today). A Prep Room resource sent to a unit is copied into it, newest version first, as Make a copy does, and the original stays in its own unit. One message says what went where, with Undo for the whole batch. Answer keys and teacher editions still go to a class shelf's teachers-only section. Anything a destination can't take is named in the message and left where it was.

Added the same day, at his request: **removing many things at once.**
- In Select, Remove sits beside Save to. It takes everything chosen off the shelf it stands on:
  - an item on a class shelf comes off that class shelf
  - a teacher's own Reading Room books, videos, podcasts and copies come off their shelves
  - a Prep Room resource comes off the shelf and stays in its unit
- An upload or link lives only on its teacher's shelf, so Remove deletes it, and the message says so.
- A book or upload another teacher put on a class shelf goes back to that teacher's shelf, as taking one off does.
- The school's own books for a class stay, and the message names them.
- Everything goes at once, with one Undo for the batch. Exegetica's server hears of it only after the Undo has had its moment, so an Undo never has to rebuild anything. Leaving the page sends what was waiting.

**Why.** Teachers find good teaching in single episodes far more often than in whole shows, and a class needs the episode, not the show. The 0029 hold was about students having somewhere to listen. A player inside the app gives them that without sending them to podcast apps or to hosts that track who plays what. Saving one item at a time made filling a new class shelf or unit slow.

**What it touches.**
- **0029.** The hold on podcasts lifts for episodes and moments. Students still don't search for podcasts (0029's student rules stand).
- **0013.** The privacy page names the audio relay: Exegetica fetches podcast audio on a student's behalf, so the podcast's host receives the request from Exegetica's server. It says a listening place stays in the student's browser.
- **0028.** A transcript made for a teacher's episode can be shown to the class the episode is placed for.
- **0002.** Nothing about what a student listened to is kept on the server or given to a model.

**Enforced in.** Built and deployed 2026-11-12 (release v154). Remove, added the same day, was deployed in release v155.
- **Episodes.** `library.search_episodes` (`/api/library/podcasts?kind=episodes`), and the Shows and Episodes switch in `templates/library.html` and `static/js/library.js`. `library_store._dedup_key` keys an episode as its feed and guid, and `episode_meta` keeps its audio address on the server alone.
- **Moments, transcripts and units.** `excerpts._item`, `episode_transcript` (one transcript serves every shelf item holding the feed), `moments`, `episode_list`, `fetch_transcript` and `save_excerpt`. The Gemini job falls back to the kept audio. `transcript_for_draft` and `prep_draft._library_item` give a unit a single episode's transcript.
- **Class shelves.** `shelves.place`, `_episode_for` (an episode, never a whole show), `_key_of`, `_public_ref` (no audio address to a browser) and `class_shelves`. The tile is in `static/js/shelves.js` (`podTile`).
- **The player.** `webapp/listen.py`:
  - the relay, which reaches only public addresses and is checked at every redirect
  - `/listen/<id>` and `/api/listen/<id>/audio`, for the class's students and teachers alone
  - `/api/library/item/<id>/audio`, for a teacher's own episode
  
  The page is `templates/listen.html`. The player, `static/js/listen.js` and `static/css/listen.css`, keeps the listening place in the browser.
- **Select and Save to.** `static/js/select.js`, with the tiles' `data-sel` in `shelves.js` and `library.js`, the menu's bands in `passage.js` (`smallMenu`), and `prep.copy_resource` (copying into another unit).
- **Remove.** `static/js/select.js` holds the batch for its Undo and sends it after. Each tile's `rm` in `shelves.js` and `library.js` names where it comes off, and both files keep removed tiles hidden until the server has them (`shelf:gone`). The server's take-off is `shelves.take_off`.
- **Privacy.** `docs/privacy.md`.
- **Tests.** `tests/test_podcast_episodes.py`. The SQL is checked by `scripts/check_prep_sql.py`.

**Reverse when.** By the maker's decision. Letting a whole show onto a class shelf, or letting students search for podcasts, needs its own record.
