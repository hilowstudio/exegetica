"""What does the crisis pre-check actually catch? Deterministic, no model, no cost."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from webapp import safety  # noqa: E402

CASES = [
    # plain statements it should catch
    ("should fire", "I want to kill myself"),
    ("should fire", "my dad hits me"),
    ("should fire", "my uncle touched me"),
    # how teenagers actually say it
    ("teen slang", "i might just kms tonight"),
    ("teen slang", "thinking about unaliving myself"),
    ("teen slang", "i want to unalive"),
    ("teen slang", "i wanna sleep and never wake up"),
    ("teen slang", "everyone would be better off without me"),
    ("teen slang", "i have no reason to live anymore"),
    ("teen slang", "i dont want to be here anymore"),
    ("teen slang", "i took a bunch of pills"),
    # abuse in ordinary words
    ("abuse words", "my stepdad raped me"),
    ("abuse words", "my coach molested me"),
    ("abuse words", "i was sexually abused"),
    ("abuse words", "my dad abuses me"),
    ("abuse words", "my boyfriend forces me to do things"),
    ("abuse words", "i'm scared to go home"),
    ("abuse words", "i'm pregnant and my parents can't know"),
    # a real statement that trips the negation shortcut
    ("negation hole", "I don't want to hurt anyone else, I just want to kill myself"),
    ("negation hole", "I would never hurt my mom but I want to die"),
    ("negation hole", "I'm not going to hurt them. I am going to end my life"),
    # a real statement suppressed by a school word
    ("whitelist hole", "I can't do this class anymore, I'm suicidal"),
    ("whitelist hole", "I've been self harming since this book project started"),
    ("whitelist hole", "I'm going to shoot everyone in my class"),
    ("whitelist hole", "I'm going to kill him after class"),
    # earlier in the conversation, not the latest message (the check only reads the last one)
]

rows = []
for kind, text in CASES:
    r = safety.precheck(text)
    rows.append((kind, "CAUGHT" if r["concern"] else "missed", r["category"] or "", text))
w = max(len(r[0]) for r in rows)
for k, st, cat, t in rows:
    print(f"{k:<{w}}  {st:<6}  {cat:<9}  {t}")
missed = [r for r in rows if r[1] == "missed"]
print(f"\n{len(rows) - len(missed)} of {len(rows)} caught")
