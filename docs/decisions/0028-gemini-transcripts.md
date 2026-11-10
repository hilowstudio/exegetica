# 0028: Gemini writes transcripts for the Living Library when a teacher asks

Decided by A. James Vega, 2026-11-09 ("Gemini it is, then"), after YouTube's captions stopped reaching other sites.

**Decision.**
- A teacher's video or podcast episode gets its transcript from a free, published source first: a feed's own `<podcast:transcript>` file, or YouTube's captions on the rare video whose captions still come through. When there is none, the teacher can ask for one with **Make a transcript**.
- **Gemini 3.5 Flash-Lite** writes it (`TRANSCRIBE_MODEL` changes the model). For a video it watches the public YouTube link at low resolution. For an episode, Exegetica's server downloads the audio, uploads it to Gemini's file store for that one request, and deletes it from both places after. Gemini is told to transcribe word for word, never to summarize, and to stamp a time at least every 30 seconds.
- The transcript is **kept and shared**: every teacher who adds the same video or show gets it, so each recording is transcribed once. It is published broadcast text, which the Living Library plan allows to be stored.
- **Limits:** nothing longer than two hours (YouTube's own length, or the feed's), audio under 300 MB, one job per recording at a time, ten transcripts per teacher and $5 for everyone together per school day. A capped teacher sees one fixed line, and no model is called. A job that fails keeps a plain sentence saying why, and is never retried on its own, so a recording is never paid for twice.

**Why.** Since 2025 YouTube's caption links need a token only its own player can make, so they return an empty file for nearly every video. Podcatch's caption step fails the same way, silently. The church-world podcasts teachers use (BibleProject, The Bible Recap, Ask NT Wright Anything) publish no transcripts. Gemini is the one route that covers both, works within YouTube's rules, and is already a provider for the Living Library.

**Cost, measured 2026-11-09.** A 6.7-minute BibleProject video: 12 seconds and $0.018. A 33-minute BibleProject episode: 53 seconds and $0.068. That is about $0.15 an hour of video and $0.13 an hour of a two-voice podcast, at Google's printed paid-tier price for 3.5 Flash-Lite ($0.30 per million input tokens for every medium, $2.50 output). On the paid tier Google states it does not use the content to improve its products.

**Enforced in.** `webapp/transcripts.py` (`gemini_youtube`, `gemini_audio`, `MAX_SECONDS`, `PROMPT`); `webapp/excerpts.py` (`_start`, `run`, the job row in `library_transcribe_jobs`); `transcribe-media` in `webapp/inngest_app.py` (one run per recording, two at once, no retries), with an in-process task when Inngest isn't configured; `usage.transcribe_check` and `usage.transcribe_add`; the route label `library:transcribe` in `webapp/metrics.py`, so every run's cost shows on `/ops`. Covered by `tests/test_transcripts.py` and `scripts/check_prep_sql.py`.

**Needs before it runs in production.** `GEMINI_API_KEY` set as a Fly secret, and `YOUTUBE_API_KEY` for the length check (neither is set on Fly today).

**Reverse when.** By the maker's decision. Changing the model, the length limit or the caps needs only the constants above and this record.
