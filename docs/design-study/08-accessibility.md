# 8. Accessibility and assistive technology

Serves CMU courses:
- Introduction to Accessibility and Assistive Technology (05-332/632)
- Special Topics: Accessibility, A Guide to Building Future User Interfaces
- Applied Fabrication (assistive technology focus)
- PIX (basic accessibility)
- Interaction Techniques (adaptations for disability)

## Ways of thinking about disability
- Medical model: disability as a deficit in the person to be treated.
- Social model (UPIAS 1976, Oliver): disability is created by barriers in the environment.
- Biopsychosocial model (WHO ICF 2001): body, activity and participation interact with environmental and personal factors.
- Disability justice (Sins Invalid's ten principles): intersectionality, leadership of the most affected, collective access.
- Language: some communities prefer identity-first language ("Deaf person", "autistic person"), others person-first. Ask.
- "Nothing about us without us": design with disabled people, not only for them.
- Prevalence: the course says about one in five people. WHO (2023) estimates about 1.3 billion people, about 16 percent of the world. US surveys put it higher for adults, about one in four.
- Disability is normal and often temporary or situational. Everyone moves in and out of ability over a lifetime.

## Inclusive design
- Microsoft Inclusive Design toolkit:
  - Principles: recognize exclusion, learn from diversity, solve for one and extend to many.
  - Persona spectrum: one arm (permanent), arm injury (temporary), a new parent holding a baby (situational).
- Curb-cut effect: features built for disabled people serve everyone. Captions are a common example: most caption users are not deaf.
- Ability-based design (Wobbrock et al. 2011): focus on what users can do, and make systems adapt to people rather than people to systems.
- People with disabilities as early adopters, as the course stresses. Text-to-speech, OCR (the Kurzweil Reading Machine, 1976), speech recognition, predictive text, conversational assistants and tactile displays started in accessibility and spread.
- Visible and invisible disabilities (chronic pain, fatigue, mental health, cognitive conditions), online and offline.

## Who needs what
- Blind and low vision:
  - screen readers (JAWS, NVDA, VoiceOver, TalkBack), navigated by headings, landmarks, links and form controls
  - braille displays, magnification, high contrast, large text
  - screen reader users often listen at high speech rates
  - magnifier users see a small part of the screen, so keep related things close and avoid content at far edges
- Colour vision deficiency: never rely on colour alone. Add text, shape or pattern.
- Deaf and hard of hearing:
  - captions and transcripts
  - sign language (ASL is a full language, and many Deaf people's first)
  - visual alternatives to audio alerts
  - avoid voice-only interaction
- Motor and dexterity:
  - keyboard-only use, switch access (scanning), voice control, eye gaze, head pointers, sip-and-puff
  - large targets, no precise drags, no tight time limits, forgiving inputs
- Cognitive and learning disabilities:
  - plain language, consistent navigation, clear headings
  - fewer distractions, no reliance on memory
  - error prevention and clear recovery
  - extra time
- Neurodivergent people (autism, ADHD, dyslexia):
  - predictability, control over sensory load, literal language, low clutter
  - dyslexia: larger size and spacing help some readers. "Dyslexia fonts" lack evidence of benefit.
- Older adults: combined declines in vision, hearing, dexterity and memory, and varied technology experience. The W3C WAI notes that WCAG covers most of their needs.
- Speech disabilities: Augmentative and Alternative Communication (AAC) devices, symbol- or text-based.
  - Communication rates are far below speech (often around 10 to 20 words per minute against about 150).
  - Prediction helps. Respect the user's agency and voice. Never complete or rephrase for them without consent.
- Seizures and vestibular disorders: no more than three flashes per second, and honor reduced-motion settings.

## WCAG 2.2
Verified this session on W3C's "What's New in WCAG 2.2".
- Four principles (POUR): perceivable, operable, understandable, robust. Levels A, AA, AAA. AA is the usual legal and policy target.
- New in 2.2:
  - 2.4.11 Focus Not Obscured, Minimum (AA): the focused item is not entirely hidden by sticky headers, banners or chat widgets.
  - 2.4.12 Focus Not Obscured, Enhanced (AAA).
  - 2.4.13 Focus Appearance (AAA).
  - 2.5.7 Dragging Movements (AA): a single-pointer alternative to every drag.
  - 2.5.8 Target Size, Minimum (AA): at least 24 by 24 CSS pixels, or enough spacing.
  - 3.2.6 Consistent Help (A): help mechanisms appear in the same relative place across pages.
  - 3.3.7 Redundant Entry (A): don't make people re-enter information already given in the same process.
  - 3.3.8 Accessible Authentication, Minimum (AA): no cognitive function test (remembering or transcribing) to log in, unless there's an alternative. Allow paste and password managers.
  - 3.3.9 Accessible Authentication, Enhanced (AAA).
  - 4.1.1 Parsing is obsolete and removed.
- Core criteria to know by heart:
  - 1.1.1 Text alternatives. Informative images get a description of their information, functional images (icons, linked images) get the action, decorative images get empty alt text.
  - 1.2.x Captions for audio and video, audio description for visual information.
  - 1.3.1 Info and relationships. Structure is conveyed in code: headings, lists, tables, labels, landmarks.
  - 1.3.5 Identify input purpose (autocomplete attributes).
  - 1.4.1 Colour is not the only way information is conveyed.
  - 1.4.3 Text contrast at least 4.5:1, or 3:1 for large text (18 pt, or 14 pt bold).
  - 1.4.4 Text resizes to 200 percent without loss.
  - 1.4.10 Reflow. Content works at 320 CSS pixels wide without horizontal scrolling (400 percent zoom).
  - 1.4.11 Non-text contrast of 3:1 for UI component boundaries, focus indicators and meaningful graphics.
  - 1.4.12 Text spacing. Layout survives line height 1.5, paragraph spacing 2 times, letter spacing 0.12 em and word spacing 0.16 em.
  - 1.4.13 Content on hover or focus can be dismissed, hovered and stays visible.
  - 2.1.1 Everything works by keyboard. 2.1.2 No keyboard trap.
  - 2.2.1 Time limits can be adjusted. 2.2.2 Pause, stop, hide for moving content.
  - 2.3.1 No more than three flashes in a second.
  - 2.4.1 Bypass blocks (skip links). 2.4.2 Pages have titles. 2.4.3 Focus order is logical. 2.4.4 Link purpose is clear in context. 2.4.6 Headings and labels describe their content. 2.4.7 Focus is visible.
  - 2.5.3 The visible label is part of the accessible name, so voice users can say what they see.
  - 3.1.1 Page language is set.
  - 3.3.1 Errors are identified in text. 3.3.2 Labels and instructions are given. 3.3.3 Fixes are suggested.
  - 4.1.2 Name, role and value are exposed for every control.
  - 4.1.3 Status messages are announced without moving focus, using live regions. This matters for chat apps that stream replies.
- WCAG 3 is a working draft with a different conformance model. It is not yet a standard.

## Building accessibly on the web
- Use native HTML first: button, a, label, fieldset, heading levels, lists, table, dialog. The first rule of ARIA is to avoid ARIA when a native element does the job. WebAIM's annual Million report finds pages with ARIA average more errors than pages without.
- ARIA supplies roles, states and properties. Live regions (polite, assertive) announce updates.
- The ARIA Authoring Practices Guide has keyboard and semantics patterns for:
  - dialogs: move focus in, trap it, return it on close
  - tabs: arrow keys move between tabs, Tab moves into the panel
  - menus, comboboxes, disclosures, accordions
- Focus: visible, logical order. Do not use positive tabindex. Manage focus when content changes.
- Respect user settings: prefers-reduced-motion, prefers-contrast, forced-colors (Windows high contrast), font scaling.
- WebAIM Million (home pages of the top million sites): about 95 percent have detectable WCAG failures. The most common are low-contrast text, missing alt text, missing form labels, empty links and buttons, and a missing page language.

## Testing
- Automated checkers (axe, WAVE, Lighthouse) catch only a minority of issues, often cited as 30 to 40 percent.
- Manual checks:
  - keyboard-only pass
  - screen reader pass (NVDA with Chrome or Firefox, VoiceOver with Safari, TalkBack, iOS VoiceOver)
  - zoom to 200 and 400 percent
  - text spacing bookmarklet
  - forced colours
  - reduced motion
- Test with disabled participants:
  - recruit through community organizations and pay them
  - let them use their own devices and settings
  - make the logistics themselves accessible
  - treat their expertise as expertise
- The course requires teams to build and evaluate a tool with people with disabilities.

## Assistive technology topics (from the special topics course)
- Text-to-speech: from concatenative to neural voices. Prosody and pronunciation dictionaries matter, and so do speed controls.
- Speech recognition: error rates rise for accents, dysarthric and atypical speech. Projects like Project Euphonia collect atypical speech to close the gap.
- Screen readers: browse (virtual buffer) mode against focus or forms mode. Accessible names and roles drive everything.
- Voice input (Voice Control, Dragon): people speak visible labels, which is why 2.5.3 exists.
- OCR and scene description (Seeing AI, Be My Eyes with AI): useful and fallible. Show confidence and allow human help.
- Magnification: lens and full-screen modes. Keep related controls near each other.
- Alternative input: switches with scanning, sip-and-puff, eye gaze with dwell, head tracking.
- Tactile displays: refreshable braille cells, pin arrays, tactile graphics, haptics.
- Text summarization as cognitive support: helpful, but accuracy and loss of nuance are risks.
- AAC: symbol grids, text with prediction, eye-gaze AAC. Speed and personal voice are the core challenges.

## Cognitive accessibility
W3C COGA "Making Content Usable" has eight objectives:
1. Help users understand what things are and how to use them.
2. Help users find what they need.
3. Use clear and understandable content.
4. Help users avoid mistakes and know how to correct them.
5. Help users focus.
6. Make sure processes do not rely on memory.
7. Provide help and support.
8. Support adaptation and personalization.

Plain language: common words, short sentences, active voice, one idea per sentence, headings that say what follows. US federal plain language guidelines. "Easy read" formats pair text with images.

## Law and policy (US-centred, as of training)
- ADA (1990), Section 504 of the Rehabilitation Act, and Section 508 (federal ICT, the 2017 refresh references WCAG 2.0 AA).
- The 2024 Department of Justice rule under ADA Title II requires state and local governments, including public schools, to meet WCAG 2.1 AA. Deadlines are phased in 2026 and 2027 depending on size. Private schools fall under Title III, where web obligations come mainly through case law.
- 21st Century Communications and Video Accessibility Act (CVAA).
- EU: EN 301 549 and the European Accessibility Act, applying from June 2025.

## Sources
Verified this session: W3C "What's New in WCAG 2.2". From training: Microsoft Inclusive Design toolkit (the home page fetch returned little text). Wobbrock et al. 2011 (TACCESS). WHO 2023 Global report on health equity for persons with disabilities. WebAIM Million reports. W3C COGA "Making Content Usable" (2021). WAI-ARIA Authoring Practices Guide. Lazar, Goldstein and Taylor, Ensuring Digital Accessibility through Process and Policy. Pullin, Design Meets Disability. Hamraie, Building Access.
