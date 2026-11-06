#!/usr/bin/env python3
"""
Unit 6 (Living Water, John 4:1-42) for a day the teacher is out (one 50-minute period): a slide deck the
substitute projects, with students working in their notebooks (no handouts), and the substitute's plan with answers.

  docs/john/john-pdf/student/U6-Well-Story-Activities.pdf   the Well Story Chart (landscape), Spot the twists,
                                                        Respond, memory check; the five stop cards to cut
                                                        out; the group sheet
  docs/john/john-pdf/teacher/U6-Well-Story-Activities-TEACHER.pdf
                                                        timing, placement and materials; the chart key;
                                                        what to listen for at each question and stop;
                                                        cautions

Same pipeline as print_quiz.py: embedded fonts, one stylesheet, headless Edge.

    python scripts/print_u6_activities.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from print_quiz import _FONT_CSS, smart  # noqa: E402

COURSE = "Sophomore Bible · The Gospel of John · Unit 6: Living Water (John 4:1-42)"
MEMORY = "John 4:24"
MEMORY_TEXT = "God is spirit, and those who worship him must worship in spirit and truth."

STEPS = ["Journey", "Well", "Water", "News", "Hospitality", "Joining"]
STEP_HINT = ["Someone travels", "A man meets a woman at a well", "Someone draws water", "She runs home to tell",
             "The visitor stays and eats", "The two are joined"]
STORIES = ["Isaac & Rebekah<br><small>Genesis 24 · done for you</small>", "Jacob & Rachel<br><small>Genesis 29</small>",
           "Moses & Zipporah<br><small>Exodus 2:15-21</small>",
           "Jesus & the Samaritan woman<br><small>John 4</small>"]
REFS = [["24:10", "29:1", "2:15", "4:3-4"],
        ["24:11-15", "29:2-9", "2:15-16", "4:5-7"],
        ["24:17-20", "29:10", "2:17, 19", "4:7, 10-14"],
        ["24:28", "29:12", "2:18-19", "4:28-29"],
        ["24:31-33, 54", "29:13-14", "2:20", "4:31-34, 40"],
        ["24:67", "29:21-28", "2:21", "4:39-42"]]
EXAMPLE = ["Abraham’s servant travels to Abraham’s homeland to find a wife for Isaac.",
           "He stops at a well and prays. Rebekah comes to draw water.",
           "She gives water to him and his camels.",
           "She runs home and tells her family.",
           "Her family welcomes him and gives him a meal.",
           "Rebekah marries Isaac."]
ANSWERS = [  # Jacob, Moses, Jesus
    ["Jacob travels east to his relatives’ land.", "Moses runs away to Midian.",
     "Jesus travels from Judea toward Galilee, through Samaria."],
    ["He meets Rachel at a well.", "He sits by a well; seven sisters come.",
     "At Jacob’s well, a Samaritan woman comes."],
    ["He rolls away the stone and waters her sheep.", "He protects them and waters their flock.",
     "Jesus asks her for a drink, then offers her living water."],
    ["Rachel runs to tell her father.", "They hurry home and tell their father.",
     "She leaves her jar and tells the whole town."],
    ["Laban welcomes him; he stays a month.", "Their father invites him to eat.",
     "Jesus stays two days; he says his food is doing God’s will."],
    ["He marries Rachel (and Leah).", "He marries Zipporah.",
     "No wedding: many people in the town believe in Jesus."]]

QUESTIONS = [  # (question, lines, answer for the sub)
    ("Read Genesis 24:2-4. Who does Abraham send to find a wife for Isaac?", 2,
     "His servant (the oldest servant of his house)."),
    ("Read John 4:28. What does the woman leave behind when she runs into town? Why do you think she leaves it?", 3,
     "Her water jar. She found something better than well water (Jesus and the living water he offers), and she wants to tell everyone."),
    ("Read John 4:39-42. In the old well stories, one man marries one woman. Who comes to Jesus at the end of this story?", 3,
     "Many Samaritans from her town. They believe Jesus is “the Savior of the world” (v. 42)."),
    ("Read John 3:29. What does John the Baptist call Jesus?", 2,
     "The bridegroom."),
    ("Read John 7:37-39. What is the “living water” Jesus talks about?", 2,
     "The Holy Spirit, given to everyone who believes in Jesus."),
]

STOPS = [  # (n, read through, title, prompt, answer)
    ("1", "4:7", "Expect", "In the well stories on your chart, what usually happens after a man meets a woman at a well? "
     "Look at verse 6: whose well is this?",
     "A wedding. It is Jacob’s well, and Jacob met his wife Rachel at a well."),
    ("2", "4:15", "Living water", "Jesus asks her for a drink, then offers her “living water.” Read verses 13-14 again. "
     "How is his water different from well water?",
     "Well water leaves you thirsty again. His water means you will never thirst; it becomes a spring inside that leads to eternal life."),
    ("3", "4:20", "Outsider", "Name three reasons people back then would say Jesus should not be talking to her. "
     "(Look at verses 9, 18, and 20.) Does Jesus walk away?",
     "She is a Samaritan (Jews and Samaritans avoided each other), she has had five husbands, and her people worship in a "
     "different place. No: Jesus keeps talking with her."),
    ("4", "4:26", "Who is he?", "In verse 26, Jesus tells her who he is. Who does he say he is? Why is it surprising that "
     "he told <i>her</i>? Then say John 4:24 together.",
     "The Messiah (the Christ). She is an outsider nobody expected him to choose, yet she is the first person in John he "
     "tells. God is looking for people like her (v. 23)."),
    ("5", "4:42", "Joining", "Finish this sentence together: “The old well stories ended with one man marrying one woman. "
     "This story ends with ______.” (Look at verses 39-42.)",
     "…many people in her town believing that Jesus is the Savior of the world."),
]

CSS = """
@page { size: letter; margin: 0.6in 0.7in 0.7in; }
@page land { size: letter landscape; margin: 0.45in 0.55in 0.55in; }
.land { page: land; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; color: #000; font: 10.6pt/1.36 "Source Serif 4", Georgia, serif; }
.nb { white-space: nowrap; }
.newpage { break-before: page; }
.course { font: 600 7.5pt "Inter", sans-serif; letter-spacing: .12em; text-transform: uppercase; }
h1 { font: 600 18pt/1.15 "Fraunces", Georgia, serif; margin: 3pt 0 6pt; }
h1 .kind { font: 600 9pt "Inter", sans-serif; letter-spacing: .1em; text-transform: uppercase; display: block; margin-bottom: 2pt; }
h2 { font: 700 8.6pt "Inter", sans-serif; letter-spacing: .1em; text-transform: uppercase; margin: 14pt 0 6pt;
  padding-bottom: 3pt; border-bottom: .6pt solid #000; break-after: avoid; }
h3 { font: 600 11.5pt "Fraunces", Georgia, serif; margin: 10pt 0 3pt; break-after: avoid; }
p { margin: 0 0 6pt; }
.meta { font: 9pt "Inter", sans-serif; margin: 0 0 8pt; display: flex; flex-wrap: wrap; gap: 3pt 18pt; }
.meta b { font-weight: 600; }
.fields { display: flex; flex-wrap: wrap; gap: 6pt 16pt; font: 9.5pt "Inter", sans-serif; margin: 2pt 0 8pt; }
.fields span { white-space: nowrap; }
.line { display: inline-block; border-bottom: .75pt solid #000; height: 1em; vertical-align: -1pt; margin-left: 4pt; }
.w-name { width: 2.4in; } .w-short { width: .55in; } .w-date { width: 1in; } .w-group { width: 3.2in; }
.instr { font-size: 10pt; margin: 0 0 8pt; padding: 5pt 0; border-top: .75pt solid #000; border-bottom: .75pt solid #000; }
/* the chart */
table.chart { width: 100%; border-collapse: collapse; table-layout: fixed; }
table.chart th { font: 600 8.6pt/1.25 "Inter", sans-serif; text-align: left; vertical-align: bottom; padding: 0 6pt 4pt;
  border-bottom: .9pt solid #000; }
table.chart th small { font-weight: 400; font-size: 7.8pt; }
table.chart th:first-child { width: 0.95in; }
table.chart td { border-bottom: .6pt solid #000; height: 0.72in; vertical-align: top; padding: 4pt 6pt; }
table.chart td:not(:first-child) { border-left: .5pt solid #000; }
table.chart td.step { font: 600 9pt "Inter", sans-serif; }
table.chart td.step span { display: block; font-weight: 400; font-size: 7.6pt; margin-top: 2pt; }
table.key td { height: auto; font-size: 9.2pt; padding: 4pt 6pt; }
table.plan td { font-size: 9.4pt; padding: 3pt 6pt; }
td .ref { display: block; font: 600 7.4pt "Inter", sans-serif; letter-spacing: .04em; margin-bottom: 2pt; }
td .ex { font-style: italic; font-size: 9pt; line-height: 1.3; }
td .ans { font-size: 8.9pt; line-height: 1.3; }
.script { font-style: italic; margin: 0 0 6pt 0; padding-left: 10pt; border-left: 1.5pt solid #000; }
/* questions */
.q { break-inside: avoid; margin: 0 0 10pt; }
.q .num { font: 700 9.5pt "Inter", sans-serif; margin-right: 4pt; }
.tag { font: 600 7.4pt "Inter", sans-serif; letter-spacing: .1em; text-transform: uppercase; margin-right: 5pt; }
.lines div { height: .32in; border-bottom: .6pt solid #000; }
.look { font-size: 9.3pt; margin: 2pt 0 0 14pt; padding-left: 8pt; border-left: 1.5pt solid #000; }
.look b { font: 600 7.6pt "Inter", sans-serif; letter-spacing: .08em; text-transform: uppercase; margin-right: 4pt; }
.verse { font-style: italic; }
/* stop cards: two per row, dashed cut lines */
.cards { display: grid; grid-template-columns: 1fr 1fr; gap: 0; border-top: 1pt dashed #000; border-left: 1pt dashed #000; }
.card { break-inside: avoid; min-height: 2.3in; padding: 12pt 14pt; border-right: 1pt dashed #000; border-bottom: 1pt dashed #000; }
.card .top { display: flex; justify-content: space-between; align-items: baseline; font: 600 8pt "Inter", sans-serif;
  letter-spacing: .1em; text-transform: uppercase; }
.card .word { font: 600 15pt "Fraunces", Georgia, serif; margin: 8pt 0 6pt; }
.card p { font-size: 10.4pt; }
.cut { font: 7.5pt "Inter", sans-serif; text-align: right; margin: 4pt 0 0; }
.box { border: .75pt solid #000; height: 1.3in; margin: 4pt 0 10pt; }
.box.tall { height: 2.6in; }
ul.tight { margin: 0 0 6pt; padding-left: 16pt; } ul.tight li { margin: 2pt 0; }
"""


def doc(title: str, foot: str, body: str) -> str:
    page = ('@page{@bottom-center{content:"' + foot + ' · page " counter(page) " of " counter(pages);'
            'font:7.5pt "Inter",system-ui,sans-serif;color:#000}}'
            '@page land{@bottom-center{content:"' + foot + ' · page " counter(page) " of " counter(pages);'
            'font:7.5pt "Inter",system-ui,sans-serif;color:#000}}')
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title>'
            f"<style>{_FONT_CSS}</style><style>{CSS}</style><style>{page}</style></head><body>{body}</body></html>")


def head(kind: str, title: str) -> str:
    return f'<div class="course">{smart(COURSE)}</div><h1><span class="kind">{kind}</span>{smart(title)}</h1>'


def fields(group: bool = False) -> str:
    if group:
        return ('<div class="fields"><span>Group members<i class="line w-group"></i></span>'
                '<span>Period<i class="line w-short"></i></span><span>Date<i class="line w-date"></i></span></div>')
    return ('<div class="fields"><span>Name<i class="line w-name"></i></span>'
            '<span>Period<i class="line w-short"></i></span><span>Date<i class="line w-date"></i></span></div>')


def chart(key: bool = False) -> str:
    rows = []
    for i, s in enumerate(STEPS):
        cells = [f'<td><span class="ref">Gen <span class="nb">{REFS[i][0]}</span></span><span class="ex">{smart(EXAMPLE[i])}</span></td>']
        for j, book in ((1, "Gen"), (2, "Ex"), (3, "John")):
            body = f'<span class="ans">{smart(ANSWERS[i][j - 1])}</span>' if key else ""
            cells.append(f'<td><span class="ref">{book} <span class="nb">{REFS[i][j]}</span></span>{body}</td>')
        rows.append(f'<tr><td class="step">{i + 1}. {s}<span>{STEP_HINT[i]}</span></td>{"".join(cells)}</tr>')
    return (f'<table class="chart{" key" if key else ""}"><thead><tr><th>Step</th>'
            + "".join(f"<th>{s}</th>" for s in STORIES) + f"</tr></thead><tbody>{''.join(rows)}</tbody></table>")


def lines(n: int) -> str:
    return f'<div class="lines">{"<div></div>" * n}</div>'


# ---------------------------------------------------------------- the projected deck
DECK_CSS = """
@page { size: 13.333in 7.5in; margin: 0; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font: 26pt/1.35 "Source Serif 4", Georgia, serif; color: #1e2026; }
.slide { width: 13.333in; height: 7.5in; box-sizing: border-box; padding: 0.55in 0.8in 0.5in; break-after: page;
  background: #f0e8dc; position: relative; display: flex; flex-direction: column; overflow: hidden; }
.slide.dark { background: #1e2026; color: #f0e8dc; }
.slide .kick { font: 600 13pt "Inter", sans-serif; letter-spacing: .14em; text-transform: uppercase; color: #a8434d; }
.slide.dark .kick { color: #dd8089; }
.slide h1 { font: 600 46pt/1.1 "Fraunces", Georgia, serif; margin: 6pt 0 16pt; }
.slide h1.big { font-size: 58pt; }
.slide p { margin: 0 0 12pt; }
.slide .do { margin-top: auto; padding: 12pt 18pt; border-left: 6pt solid #a8434d; background: rgba(168,67,77,.08);
  font: 600 23pt/1.3 "Inter", sans-serif; }
.slide.dark .do { border-color: #dd8089; background: rgba(221,128,137,.12); }
.slide .do b { color: #a8434d; } .slide.dark .do b { color: #dd8089; }
.steps { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: auto 1fr; gap: 6pt 22pt; align-items: baseline; }
.steps li { display: contents; }
.steps .s { font: 600 23pt "Inter", sans-serif; white-space: nowrap; }
.steps .s small { font-weight: 400; color: #6b6058; margin-left: 8pt; }
.steps .t { font-size: 25pt; }
.steps.ex .t { font-style: italic; font-size: 22pt; }
.qs { margin: 0; padding-left: 0; list-style: none; counter-reset: q; }
.qs li { counter-increment: q; margin: 0 0 9pt; padding-left: 44pt; position: relative; font-size: 24pt; }
.qs li::before { content: counter(q) "."; position: absolute; left: 0; font: 700 20pt "Inter", sans-serif; }
.verse { font-style: italic; font-size: 34pt; line-height: 1.35; margin: 20pt 0; }
.stopno { font: 700 120pt/1 "Fraunces", Georgia, serif; color: #a8434d; opacity: .9; position: absolute; right: 0.8in; top: 0.45in; }
.read { font: 600 24pt "Inter", sans-serif; margin: 0 0 18pt; }
.foot { position: absolute; left: 0.8in; bottom: 0.25in; font: 11pt "Inter", sans-serif; color: #6b6058; }
.slide.dark .foot { color: #9a958d; }
"""


def deck() -> str:
    S = []

    def slide(body: str, dark: bool = False, n: int = 0) -> None:
        S.append(f'<section class="slide{" dark" if dark else ""}">{body}'
                 f'<div class="foot">Unit 6 · The Well Story · slide {len(S) + 1}</div></section>')

    slide('<div class="kick">Sophomore Bible · Unit 6 · John 4</div><h1 class="big">The Well Story</h1>'
          '<p>Jesus meets a woman at a well, and the story doesn’t go the way anyone expected.</p>'
          '<div class="do">Get out your <b>notebook</b> and a <b>Bible</b>. At the top of a new page, write today’s date and '
          '“The Well Story.”</div>', dark=True)
    slide('<div class="kick">The pattern</div><h1>When a man meets a woman at a well…</h1>'
          '<p>…in the Old Testament, a wedding is usually coming. The writers told these stories the same way on purpose, '
          'so readers would recognize the pattern. Here are its six steps:</p><ul class="steps">'
          + "".join(f'<li><span class="s">{i + 1}. {s}</span><span class="t">{STEP_HINT[i]}</span></li>' for i, s in enumerate(STEPS))
          + '</ul>')
    slide('<div class="kick">Example · Genesis 24</div><h1>Isaac &amp; Rebekah</h1><ul class="steps ex">'
          + "".join(f'<li><span class="s">{i + 1}. {s}<small>24:{REFS[i][0].split(":")[1]}</small></span>'
                    f'<span class="t">{smart(EXAMPLE[i])}</span></li>' for i, s in enumerate(STEPS))
          + '</ul><div class="do">Just read this one. You’ll do the next three yourself.</div>')
    for j, (name, book, abbr) in enumerate((("Jacob &amp; Rachel", "Genesis 29", "Genesis"), ("Moses &amp; Zipporah", "Exodus 2", "Exodus"),
                                           ("Jesus &amp; the Samaritan woman", "John 4", "John")), start=1):
        extra = ("<p>Watch for the places where this story is <b>different</b>.</p>" if j == 3 else "")
        slide(f'<div class="kick">Your turn · {book}</div><h1>{name}</h1>{extra}<ul class="steps">'
              + "".join(f'<li><span class="s">{i + 1}. {s}</span><span class="t">{abbr} {REFS[i][j]}</span></li>'
                        for i, s in enumerate(STEPS))
              + f'</ul><div class="do">In your notebook, write <b>{name}</b> and number 1–6. Look up each verse and write '
                'a few words about what happens.</div>')
    slide('<div class="kick">Look closer</div><h1>Five questions</h1><ol class="qs">'
          + "".join(f"<li>{smart(q)}</li>" for q, _, _ in QUESTIONS)
          + '</ol><div class="do">Number 1–5 in your notebook. Answer each in a sentence or two.</div>')
    slide('<div class="kick">Just between you and God</div><h1>What are you thirsty for?</h1>'
          '<p class="verse">“If you knew the gift of God… you would have asked him, and he would have given you living water.”'
          ' <span style="font-style:normal;font-size:20pt">(John 4:10)</span></p>'
          '<p>People try to fill their thirst with attention, grades, friends, screens. None of it lasts.</p>'
          '<div class="do">On the <b>last page</b> of your notebook (it’s private): name one “well” that never satisfies you, '
          'then write one sentence to Jesus asking for what only he can give.</div>', dark=True)
    slide('<div class="kick">Groups of 3–4</div><h1>Read and Stop</h1>'
          '<p>Your group will read John 4 out loud, one section at a time. The screen will show where to stop.</p>'
          '<p>At each stop, talk about the question together before the next section. A different person reads each time.</p>'
          '<div class="do">Get into groups of 3–4 with your Bibles. Write <b>Read and Stop</b> in your notebook and number 1–5.</div>')
    for n, after, word, prompt, _ in STOPS:
        start = {"1": "4:1", "2": "4:8", "3": "4:16", "4": "4:21", "5": "4:27"}[n]
        slide(f'<div class="stopno">{n}</div><div class="kick">Stop {n} · {word}</div>'
              f'<p class="read">Read John <span class="nb">{start}</span>–<span class="nb">{after.split(":")[1]}</span> out loud</p>'
              f'<h1 style="font-size:38pt;max-width:10.4in">{prompt}</h1>'
              '<div class="do">Talk it over as a group, then each person writes a short answer next to number ' + n + '.</div>')
    slide('<div class="kick">On your own</div><h1>The headline</h1>'
          '<p>The woman left her water jar and ran into town to tell everyone about Jesus (John 4:28-29).</p>'
          '<div class="do">In your notebook, write one sentence she might have shouted, in your own words. Then finish this '
          'sentence: <b>Jesus wants people like ____ because ____.</b></div>')
    slide('<div class="kick">Memory verse · John 4:24</div><h1>Say it together</h1>'
          f'<p class="verse">“{MEMORY_TEXT}”</p><p>John 4:24</p>', dark=True)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>The Well Story</title>'
            f"<style>{_FONT_CSS}</style><style>{DECK_CSS}</style></head><body>{''.join(S)}</body></html>")


# ---------------------------------------------------------------- substitute's copy
def teacher() -> str:
    b = [head("Substitute plan · 50 minutes", "The Well Story (John 4)"),
         '<p>Thank you for covering this class. Everything happens on the projector. First the class reads '
         '<b>U6-Woman-at-the-Well-Reading.pdf</b> together; then open <b>U6-Well-Story-Slides.pdf</b> full screen and advance '
         'the slides as the plan says. Students work in their notebooks with a Bible. There are no handouts and nothing to cut. You don’t need to teach: read the slides aloud, keep time, and walk around while they '
         'work. Answers are on the next pages.</p>',
         "<h2>The plan</h2>",
         '<table class="chart key plan"><thead><tr><th style="width:0.75in">Time</th><th style="width:0.75in">Slides</th>'
         '<th>What happens</th></tr></thead><tbody>'
         '<tr><td class="step">0–3</td><td>1</td><td>Attendance. Students get out notebooks and Bibles.</td></tr>'
         '<tr><td class="step">3–13</td><td>Reading</td><td>Project the reading. Students take turns reading aloud, one '
         'numbered paragraph each (call on readers down the rows). Keep it moving.</td></tr>'
         '<tr><td class="step">13–25</td><td>2–6</td><td>Slide 2 is a quick recap of the reading. Read slide 3 (the example) '
         'aloud, then give about 4 minutes each for slides 4–6. Slide 6 (Jesus) is the important one.</td></tr>'
         '<tr><td class="step">25–31</td><td>7</td><td>Five short questions in notebooks. Early finishers go on to slide 8, '
         'the private page.</td></tr>'
         '<tr><td class="step">31–32</td><td>8–9</td><td>Show slide 8 briefly, then slide 9: students form groups of 3–4.</td></tr>'
         '<tr><td class="step">32–44</td><td>10–14</td><td>Read and Stop. One slide per stop, about 2–3 minutes each. Groups '
         'read the section aloud, talk, and write. Move on when most groups are done.</td></tr>'
         '<tr><td class="step">44–48</td><td>15</td><td>Each student writes a headline and finishes the sentence. Ask two or '
         'three students to read their headline aloud.</td></tr>'
         '<tr><td class="step">48–50</td><td>16</td><td>The whole class says John 4:24 together from the screen.</td></tr>'
         "</tbody></table>",
         '<p><b>Running short?</b> Skip slide 5 (Moses), and on slides 10–14 do Stops 1, 3, and 5. <b>Extra time?</b> Partners quiz each other on '
         'John 4:24.</p>',
         "<h2>Nothing to collect</h2><p>Students keep their notebooks. The private page (slide 8) is between the student and God, "
         "so please don’t ask anyone to share it.</p>",
         "<h2>Two things to know</h2>"
         '<p><b>The woman’s five husbands (v. 18).</b> If students start guessing why she had five husbands, you can say: '
         '“The Bible doesn’t tell us why. Let’s look at how Jesus treats her.” He keeps talking with her and tells her who he is.</p>'
         '<p><b>If a student shares something that worries you</b>, please let the office know and leave me a note.</p>']

    b.append('<section class="newpage land">' + head("Substitute copy · Answers", "Slides 4–6: the three stories") +
             "<p>Accept any answer that shows the student found the verse and understood what happens.</p>" + chart(key=True) +
             "</section>")

    b.append(f'<section class="newpage">{head("Substitute copy · Answers", "Slide 7 and the stops")}')
    b.append("<h2>Slide 7: Look closer</h2>")
    for i, (q, _, a) in enumerate(QUESTIONS, 1):
        b.append(f'<div class="q"><p><span class="num">{i}.</span>{smart(q)}</p><p class="look"><b>Answer</b>{smart(a)}</p></div>')
    b.append("<h2>Slides 10–14: Read and Stop</h2><p>These are for groups to talk about, so any thoughtful answer is fine. "
             "Here is what to listen for as you walk around.</p>")
    for n, after, word, prompt, a in STOPS:
        b.append(f'<div class="q"><p><span class="num">Stop {n}</span><span class="tag">after John <span class="nb">{after}</span> · {word}</span>'
                 f'{prompt}</p><p class="look"><b>Listen for</b>{smart(a)}</p></div>')
    b.append(f'<h2>Memory verse</h2><p class="verse">“{MEMORY_TEXT}” ({MEMORY}, ESV)</p></section>')
    return doc("Unit 6 Well Story, substitute plan", "Unit 6 · The Well Story · substitute plan", "".join(b))


# ---------------------------------------------------------------- the reading
READING_MD = ROOT / "docs/john/john-materials/U6-Woman-at-the-Well-reading.md"
READING_CSS = """
@page { size: letter; margin: 0.75in 1.05in 0.8in 0.8in; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; padding-left: 0.45in; color: #111; font: 12pt/1.5 "Source Serif 4", Georgia, serif; counter-reset: para; }
.course { font: 600 7.5pt "Inter", sans-serif; letter-spacing: .12em; text-transform: uppercase; }
h1 { font: 600 24pt/1.12 "Fraunces", Georgia, serif; margin: 4pt 0 4pt; text-wrap: balance; }
.dek { font: italic 12pt/1.4 "Source Serif 4", Georgia, serif; margin: 0 0 16pt; padding-bottom: 12pt; border-bottom: .75pt solid #000; }
h2 { font: 600 14.5pt/1.2 "Fraunces", Georgia, serif; margin: 18pt 0 6pt; break-after: avoid; }
h3 { font: 600 11.5pt "Inter", sans-serif; margin: 12pt 0 4pt; break-after: avoid; }
p { margin: 0 0 9pt; orphans: 2; widows: 2; position: relative; }
p.n::before { counter-increment: para; content: counter(para); position: absolute; left: -0.45in; width: 0.3in; text-align: right;
  font: 600 8.5pt/2.1 "Inter", sans-serif; color: #8a8178; }
ol, ul { margin: 0 0 10pt; padding-left: 22pt; } li { margin: 0 0 3pt; }
strong { font-weight: 650; }
.end { margin-top: 14pt; text-align: center; font-size: 14pt; letter-spacing: .5em; }
"""


def reading() -> str:
    from markdown_it import MarkdownIt  # noqa: PLC0415
    md = READING_MD.read_text(encoding="utf-8")
    title, body = md.split("\n", 1)
    html_body = MarkdownIt("commonmark", {"typographer": True}).enable(["replacements", "smartquotes"]).render(body)
    html_body = html_body.replace("<p>", '<p class="n">')        # numbered paragraphs, for taking turns reading aloud
    page = ('@page{@bottom-center{content:"Unit 6 · The Woman at the Well · page " counter(page) " of " counter(pages);'
            'font:7.5pt "Inter",system-ui,sans-serif;color:#000}}')
    head_html = (f'<div class="course">{smart(COURSE)}</div><h1>{smart(title.lstrip("# ").strip())}</h1>'
                 '<p class="dek">Read this together before the activities. Take turns: each reader takes the next numbered '
                 'paragraph. Keep your Bible open to John 4.</p>')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>The Woman at the Well</title>'
            f"<style>{_FONT_CSS}</style><style>{READING_CSS}</style><style>{page}</style></head>"
            f'<body>{head_html}{html_body}<div class="end">❧</div></body></html>')


async def render(jobs):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        br = await p.chromium.launch(channel="msedge", headless=True)
        pg = await br.new_page()
        for html_doc, out in jobs:
            out.parent.mkdir(parents=True, exist_ok=True)
            await pg.set_content(html_doc, wait_until="networkidle")
            await pg.evaluate("() => document.fonts.ready")
            await pg.pdf(path=str(out), prefer_css_page_size=True, print_background=True, tagged=True)
            print(f"[pdf] {out.relative_to(ROOT)}")
        await br.close()


if __name__ == "__main__":
    asyncio.run(render([(reading(), ROOT / "docs/john/john-pdf/student/U6-Woman-at-the-Well-Reading.pdf"),
                        (deck(), ROOT / "docs/john/john-pdf/student/U6-Well-Story-Slides.pdf"),
                        (teacher(), ROOT / "docs/john/john-pdf/teacher/U6-Well-Story-SUB-PLAN.pdf")]))
