# Privacy

*Exegetica, made by A. James Vega of Hi Low Studio LLC for Yorkville Christian School. Updated 9 November 2026.*

## What Exegetica is

Exegetica is a study tool for the school's Bible and Social Sciences classes. Chat replies are written by an open AI language model, Nemotron 3.5 Super VL, made by NVIDIA. For teachers, the Prep Room's drafts are written by Claude, made by Anthropic. The models work from Exegetica's own library of texts and tools, and it can still be wrong, so check what matters against the sources it cites.

Exegetica runs on a server and needs an internet connection. Nothing in it works offline.

It is free to the school's students and teachers. Its maker pays the running costs. It shows no advertising, takes no payment, and sells no data.

## Signing in

Chat needs a school Google account. Exegetica keeps the account's email address, name, Google account number, role (student or teacher), and the dates of its first and last sign-in. It does not keep the profile photo. A small cookie keeps you signed in.

## What Exegetica keeps for your account

- **Studies.** Each chat you keep, with the tool results it used, is saved to your school account so you can open it on another computer.
- **Scripture Memory.** Your verses and folders.
- **Living Library.** The books you put on your shelf, the classes you say you take or teach, where you stopped in each book, and the cover styles you chose. Your classes decide which shelves open your library. They are never given to the model that answers in Chat.
- **Class shelves.** The books, videos, uploads, saved pages and Prep Room resources a teacher puts on a class's shelf, for that class's students or for its teachers alone. An upload or a page shared with a class is copied there, encrypted, so the class keeps it when the teacher deletes their own. A Prep Room resource on a class shelf is kept there as its newest saved version, encrypted, and updated with each save. Students are sent only its student copy, never an answer key or teaching notes, and an answer key goes to the class's teachers alone. The other teachers of the class see which teacher added each one. Students see no names.
- **Teachers' library.** A teacher's videos, podcasts and notes, the books, handouts and other files a teacher uploads and the web pages a teacher saves (their text kept encrypted, each filed as the kind of thing it is), the moments a teacher saves from a video or podcast, and which of the school's classes the teacher teaches. A teacher's class list is first filled in from the school's book list, and the teacher can change it.
- **Reading Room suggestions.** When a teacher suggests one of their uploaded books for the Reading Room, its title, its author, the teacher's reason, and the maker's answer. The maker reads the book's text to decide.
- **Prep Room.** A teacher's units, the sources each one draws on, and every resource made there with its earlier versions. The text of a document a teacher uploads to a unit, or of a web page a teacher adds, is the teacher's copy and is kept encrypted, for that teacher's drafts only.

{{retention}}

## Who can read your studies

Exegetica's maker, A. James Vega, is the one person with access to the database, so he can read saved studies, and a teacher's units and resources. As a teacher at the school, he is a mandated reporter. No other teacher or staff member can see them through Exegetica. A teacher's units, resources and saved moments are that teacher's alone in the app; transcripts of public videos and podcast episodes are shared, since they are published text.

Exegetica keeps no profile of a student. A new study starts with no knowledge of earlier ones, and nothing you type is used to train any model.

## Who else receives information

- **DeepInfra** runs the models that write chat replies: Nemotron 3.5 Super VL, and GLM-5.3-Flash, made by Z.ai, when Nemotron can't be reached. It receives each chat message with the study so far, and Nemotron also reads your last three messages there to decide whether to open the **Need help now?** window. Its [terms of service](https://deepinfra.com/terms) (section 7(b)) commit it to keep no message or reply beyond the time needed to answer and to train no model on them. It keeps request counts, times, and billing records, and any records the law or the prevention of abuse requires.
- **Anthropic** drafts the Prep Room's documents and the summaries in a teacher's library. With a draft it receives what the teacher's unit draws on: book text, passages, a video's transcript and saved moments, and the text of a teacher's uploads and links. It receives no chat messages. Anthropic's commercial terms bar it from training its models on this data, and it keeps the data for a limited time under its own [privacy policy](https://www.anthropic.com/legal/privacy).
- **Google** handles sign-in. A teacher's video searches go to YouTube. When a teacher asks for a transcript of a video or podcast episode, Google's Gemini receives the public video's link, or the episode's audio, and nothing about the teacher or any student. Google's terms for Exegetica's paid plan bar it from using that content to improve its products, and the uploaded audio is deleted once the transcript is written. Exegetica serves its typefaces from its own server, so opening a page sends nothing to Google.
- **Crossway** (the ESV) and **bible.org** (the NET Bible) receive Bible references when a tool looks up a passage. They never receive your messages.
- **Fly.io** hosts the server and keeps its logs for a short time. **Neon** hosts the database. **Cloudflare** stores a teacher's uploaded file until it is processed, and serves a maths typesetting script to the Reading Room.
- **Inngest** runs background jobs for the teachers' library. Its records hold a book's title and the uploading teacher's account number.
- **Open Library** and **Apple** receive a teacher's library searches, and Open Library serves the cover images the library shows.
- **Web pages, YouTube and podcast feeds.** When a teacher adds a link to a unit, or looks for a video's captions or a podcast episode's transcript, Exegetica's server fetches that page or file. The site sees only a request from Exegetica's server, with nothing that names the teacher.

## Counts kept to run the service

For each reply, Exegetica records numbers only: how long it took, how many tool calls it made, how many tokens it used, its estimated cost, and how it ended. Each day it also counts how many times the **Need help now?** window opened. These records hold no account, message, or address, and they are deleted after {{metrics_days}} days. To enforce daily limits, each account has a counter for the day under a code that only the server can match, deleted after {{cap_days}} days.

## Your choices

- Delete a study with the × beside it in your list of studies.
- **Download my data** in Settings gives you everything Exegetica keeps for your account as one file.
- **Delete my account** in Settings removes your account and everything in it. A teacher's own uploads and saved pages go with it. What a teacher put on a class shelf stays with the class, a Prep Room resource as its last saved version, a Reading Room suggestion keeps its title and reason, and the summaries a teacher's upload added to the shared library stay, each with nothing that names the teacher.
- **Clear this browser** in Settings removes what Exegetica keeps in this browser: settings, a teacher's own API key, and anything saved before sign-in. Studies kept in a browser from before sign-in are dropped after 30 days.

## Questions

Questions about this page go to Mr. Vega at Yorkville Christian School. When this page changes, the date at the top changes.
