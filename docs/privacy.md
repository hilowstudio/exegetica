# Privacy

*Exegetica, made by A. James Vega of Hi Low Studio LLC for Yorkville Christian School. Updated 6 November 2026.*

## What Exegetica is

Exegetica is a study tool for the school's Bible and Social Sciences classes. Students' chat replies are written by an open AI language model, Nemotron 3.5 Super, made by NVIDIA. Teachers' replies are written by Claude, made by Anthropic. The models work from Exegetica's own library of texts and tools, and it can still be wrong, so check what matters against the sources it cites.

Exegetica runs on a server and needs an internet connection. Nothing in it works offline.

It is free to the school's students and teachers. Its maker pays the running costs. It shows no advertising, takes no payment, and sells no data.

## Signing in

Chat needs a school Google account. Exegetica keeps the account's email address, name, Google account number, role (student or teacher), and the dates of its first and last sign-in. It does not keep the profile photo. A small cookie keeps you signed in.

## What Exegetica keeps for your account

- **Studies.** Each chat you keep, with the tool results it used, is saved to your school account so you can open it on another computer.
- **Scripture Memory.** Your verses and folders.
- **Reading Room.** Where you stopped in each book, and the cover styles you chose.
- **Teachers' library.** A teacher's shelf and notes, and the text of any book a teacher uploads, kept encrypted.

{{retention}}

## Who can read your studies

Exegetica's maker, A. James Vega, is the one person with access to the database, so he can read saved studies. As a teacher at the school, he is a mandated reporter. No other teacher or staff member can see them through Exegetica.

Exegetica keeps no profile of a student. A new study starts with no knowledge of earlier ones, and nothing you type is used to train any model.

## Who else receives information

- **DeepInfra** runs the models that write students' replies: Nemotron 3.5 Super, and GLM-5.3-Flash, made by Z.ai, when Nemotron can't be reached. It receives each student message with the study so far. Its [terms of service](https://deepinfra.com/terms) (section 7(b)) commit it to keep no message or reply beyond the time needed to answer and to train no model on them. It keeps request counts, times, and billing records, and any records the law or the prevention of abuse requires.
- **Anthropic** receives a teacher's chat messages and writes the replies, and it drafts the Prep Room's documents. A small Anthropic model, Claude Haiku, also reads a student's last three messages to decide whether to open the **Need help now?** window. Anthropic's commercial terms bar it from training its models on this data, and it keeps the data for a limited time under its own [privacy policy](https://www.anthropic.com/legal/privacy).
- **Google** handles sign-in. A teacher's library searches go to Google Books and YouTube. Exegetica serves its typefaces from its own server, so opening a page sends nothing to Google.
- **Crossway** (the ESV) and **bible.org** (the NET Bible) receive Bible references when a tool looks up a passage. They never receive your messages.
- **Fly.io** hosts the server and keeps its logs for a short time. **Neon** hosts the database. **Cloudflare** stores a teacher's uploaded file until it is processed, and serves a maths typesetting script to the Reading Room.
- **Inngest** runs background jobs for the teachers' library. Its records hold a book's title and the uploading teacher's account number.
- **Open Library** and **Apple** receive a teacher's library searches, and Open Library serves the cover images the library shows.

## Counts kept to run the service

For each reply, Exegetica records numbers only: how long it took, how many tool calls it made, how many tokens it used, its estimated cost, and how it ended. Each day it also counts how many times the **Need help now?** window opened. These records hold no account, message, or address, and they are deleted after {{metrics_days}} days. To enforce daily limits, each account has a counter for the day under a code that only the server can match, deleted after {{cap_days}} days.

## Your choices

- Delete a study with the × beside it in your list of studies.
- **Download my data** in Settings gives you everything Exegetica keeps for your account as one file.
- **Delete my account** in Settings removes your account and everything in it. Summaries a teacher's upload added to the shared library stay, with nothing that names the teacher.
- **Clear this browser** in Settings removes what Exegetica keeps in this browser: settings, a teacher's own API key, and anything saved before sign-in. Studies kept in a browser from before sign-in are dropped after 30 days.

## Questions

Questions about this page go to Mr. Vega at Yorkville Christian School. When this page changes, the date at the top changes.
