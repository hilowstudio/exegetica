# 0003: The position statement and the Quiet Standards statement are separate public pages

Decided by A. James Vega, 2026-11-02.

**Decision.** `/position` shows Hi Low Studio's statement on the wise and ethical use of LLMs in Christian schooling, in the Theologian's voice. `/quiet-standards` shows the statement on the Quiet Standards Framework. They are different messages and never share a page. All Scripture quotations in the position statement are ESV, written into the file once from Crossway; the page never calls the ESV API. The statement includes Hi Low Studio's promise that Exegetica will never use AI to imitate, alter, or fabricate a student's face, voice, or words, or train a model on them.

**Why.** The position statement is theological and pastoral; the framework statement is an engineering standard. Mixing them weakens both.

**Enforced in.** `webapp/about.py` renders `docs/position-statement-christian-school-theologian.md` and `docs/quiet-standards-statement.md`; the FAQ (`webapp/templates/partials/faq.html`) and the info bubble in `webapp/templates/chat.html` link to each page separately.

**Reverse when.** By the maker's decision. If the promise about faces and voices ever stops being true (for example, if a feature generated images of students), the promise must be removed before the feature ships.
