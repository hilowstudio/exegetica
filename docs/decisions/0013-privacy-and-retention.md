# 0013: A privacy page states only what is true, and people can take their data or delete it

Recorded 2026-11-03 from the QSF scorecard (GOV-01, HON-13, DEP-09, DAT-01/02/03/07, HON-02/03) and the harness proposal, Layer 4.

**Decision.**
- **`/privacy`** says, in plain words: what is kept per account, that the maker alone can read saved studies and is a mandated reporter, which outside services receive what, how the app is paid for, and that it needs an internet connection. It is linked from the chat hint, the FAQ, and Settings.
- **Settings has three controls:** Download my data (every per-account store as one JSON file), Delete my account (typed confirmation), and Clear this browser.
- **Delete order:** R2 upload originals first. Then, in one transaction, the account's id is scrubbed from `canonical_source` and `cover_overrides`, and the account row is deleted, which cascades.
- **The Google profile photo** is no longer stored. The migration nulls the existing ones.
- **The browser:** local studies older than 30 days are dropped, and a confirmed import clears the browser copy.

**Retention.** The periods (12 months without sign-in for a student account, 30 days for finished library jobs) live in `webapp/retention.py`. The purge is OFF until the maker sets `RETENTION_PURGE=on`. The privacy page reads the same switch, so it never claims a purge that is not running. Current teachers and admins are never purged. Operational rows (metrics 90 days, cap counters 2 days) are purged on the write path and by the five-minute `/ops/flag` ping, whatever the switch says.

**Why.** Users include minors whose messages go to a model provider. There was no privacy page and no way to leave, and one line of copy was false ("saved here, in this browser only").

**Enforced in.** `docs/privacy.md` and `about.privacy_page`, `webapp/account.py`, `webapp/retention.py`, `webapp/r2.delete_prefix_async`, `auth_callback` (no photo), `webapp/static/settings.js`, `webapp/static/index.html`. Covered by `tests/test_privacy_and_data.py`.

**Open for the maker.** Turning the purge on and confirming its periods. A contact address for the page, which names Mr. Vega at school for now. Self-hosting the fonts, which would take Google Fonts off the list.

**Reverse when.** Never remove a stated right. Change a period only together with the page, which reads it from the same constant.
