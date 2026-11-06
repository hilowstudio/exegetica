# 0010: No AI-written worship, in chat or in the Prep Room

Decided by A. James Vega, 2026-11-02 ("no for now").

**Decision.** Exegetica writes no prayers, devotions, worship, or exhortations for anyone to pray or follow. In chat, it points a student to Scripture's own prayers (the Psalms, the Lord's Prayer) and to their pastor, parents, or teachers. In the Generator, the Devotional / Lectio Divina Guide format is withheld, and where any other format calls for a prayer or devotion, the document carries a placeholder ("[Prayer: led by the teacher]") for a person to lead. Scripture's own prayers may be quoted and cited as Scripture.

**Why.** The position statement: "AI Must Never Lead Worship." A generated closing prayer or devotion is AI orchestrating a devotion to God.

**Enforced in.** `BIBLE_STUDENT` in `webapp/app.py` (chat); `GENERATOR_FLOOR` and `WITHHELD_FORMATS` in `webapp/generator.py`. Covered by `tests/test_generator_conduct.py`. The placeholder rule is prompt text, so a model can still break it.

**Reverse when.** By the maker's decision ("for now"). Restoring the devotional format means removing it from `WITHHELD_FORMATS` and deciding what the Generator may write in its prayer steps.
