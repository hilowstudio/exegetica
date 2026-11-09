# 19. Interface and web design from the graphic-design side

Serves RISD courses:
- Workshop: UI/UX Design, From Mind to Screen (GRAPH 2117)
- Design for Interaction (3327)
- Web Design (3271)
- Web as Medium 1 (3237)
- Type + Code
- Computational Poetics

Pairs with the CMU interaction design principles in [03](03-interaction-design-principles.md) and evaluation in [02](02-evaluation-and-measurement.md).

## What the RISD courses cover
- UI/UX workshop (Figma):
  - analyse the intuitiveness and patterns of existing apps
  - critically reassess what they do and explore other ways to use them
  - turn concepts into wireframes, a visual language and navigation systems
  - redesign around existing frustrations or a new purpose
  - build prototypes that challenge standard expectations, ending in high-fidelity interactive prototypes
- Design for Interaction:
  - asks how to turn a flat screen into something that's a joy to use
  - covers apps, websites, operating systems, video games, appliances and exhibitions
  - aims for legible, meaningful interactions, with mockups, prototypes, user research and testing
  - covers how designers and developers collaborate
- Web Design:
  - UX fundamentals starting from user needs, behaviour and habits
  - principles and laws of UX, trends and patterns, interface guidelines
  - responsive interfaces, research methods, and a design system
- Web as Medium: HTML, CSS and JavaScript, the culture and history of networks, the internet as a space for social exchange and independent expression, and a "poetic understanding" of the web as a medium for critical research and action.

## Platform guidelines and conventions
- Apple Human Interface Guidelines:
  - Older editions named clarity, deference and depth as themes.
  - Apple revised the guidelines with its 2025 design language. Check the current principles before citing them.
  - Platform conventions: navigation bars, tab bars (3 to 5 top-level destinations), sheets, the system back gesture, Dynamic Type.
- Material Design 3 (Google):
  - design tokens
  - dynamic colour from a source colour
  - components with defined states
  - elevation
  - motion with emphasized easing
- Microsoft Fluent covers the same ground for Windows.
- Jakob's law applies: people bring expectations from other products, so use conventions unless a departure clearly pays.
- Navigation patterns:
  - tab bars for a few peer destinations
  - stacks for drilling down
  - drawers hide destinations: NN/g found hidden navigation lowers discoverability and use on desktop and mobile
  - search for large content sets
  - segmented controls for views of the same content
  - modal sheets for focused subtasks

## From concept to screen
- Analyse existing products (the RISD workshop starts here): their patterns, conventions, frustrations and workarounds.
- Content first: design with real content. Placeholder text hides the real lengths, hierarchies and edge cases.
- Mobile first (Wroblewski 2011): the small screen forces priorities, and larger layouts add to them.
- User flows and wireframes settle structure and priority before visual design.
- Then:
  - a visual language (type scale, colour tokens, spacing scale on a 4- or 8-point base, icon grid)
  - components and their states
  - motion
- Every component needs its states: default, hover, focus, active or pressed, selected, disabled, loading, empty, error, success. Screens need their states too: first use or empty, partial, full, error, offline.

## Visual design for interfaces
- Hierarchy guides the eye to the primary action. Give each screen one primary action.
- Signifiers have to stay visible. Flat design weakened clickability cues, and NN/g's eye-tracking found flat elements without clear signifiers drew less attention and caused hesitation. Keep buttons looking like buttons and links like links.
- Density fits the posture. Sovereign tools can be dense, transient ones should be sparse and large. See Cooper in [03](03-interaction-design-principles.md).
- Aesthetic-usability effect (Kurosu and Kashimura 1995, Tractinsky 2000): attractive interfaces are perceived as easier to use. Beauty buys patience, and it can hide problems in testing.
- Motion: show where things came from and went, confirm actions, guide attention. Keep it short and purposeful, and honour reduced motion. Durations and easing are in [20](20-print-motion-history-critique.md).

## Design systems
- Atomic Design (Frost 2016): atoms, molecules, organisms, templates, pages.
- Tokens: primitive values (blue-600), then semantic roles (accent, surface, text-muted), then component tokens.
- Documentation: what each component is for and when not to use it, its states, accessibility notes, content guidance.
- Figma practice:
  - components and variants
  - auto layout, which mirrors CSS flexbox
  - variables for tokens and modes (light and dark)
  - interactive components for prototypes
- Designer and developer collaboration:
  - Designers should understand states, edge cases, data variability, text expansion in translation (often 30 percent or more), responsive behaviour and performance.
  - Developers should understand intent and hierarchy.
  - Shared tokens and component names keep design and code aligned.

## Responsive web design
- Ethan Marcotte (2010): fluid grids, flexible images, media queries.
- Today:
  - breakpoints chosen by content
  - container queries so components respond to their own space
  - intrinsic layout with CSS Grid and flexbox (Jen Simmons)
  - fluid type and spacing with clamp()
  - responsive images (srcset, sizes, picture)
- Progressive enhancement: semantic HTML that works first, then CSS, then JavaScript. It improves resilience and accessibility.
- Performance is design. Google's Core Web Vitals targets: Largest Contentful Paint within 2.5 s, Interaction to Next Paint within 200 ms, Cumulative Layout Shift below 0.1. Reserve space for images and fonts to avoid layout shift.
- Web typography: see [13](13-typography.md).

## The web as a medium (Web as Medium, Computational Poetics)
- HTML is material: structure, links and view-source culture. Early web pages were made by hand and personal.
- Net art:
  - JODI
  - Olia Lialina's "My Boyfriend Came Back from the War" (1996)
  - Vuk Ćosić
- Hypertext literature (Michael Joyce's afternoon, a story, 1987) and Twine games.
- Brutalist and indie-web movements reacted against template sameness.
- The web as a public space for social exchange and independent expression. The courses explicitly allow outcomes that aren't strictly practical in exchange for poetic and critical understanding.
- Interactive typography and text as interface: see Type + Code in [13](13-typography.md).

## Games, appliances and physical-digital hybrids (Design for Interaction)
- Game interface elements (Fagerholt and Lorentzon 2009):
  - diegetic: inside the game world, seen by the characters
  - non-diegetic: overlay HUD
  - spatial: in the 3D space, not seen by characters
  - meta: on the screen plane but part of the fiction, such as blood spatter
- "Juice" is generous feedback. Onboarding happens through play.
- Appliances: physical controls need natural mapping and visible state (Norman). Hybrid systems coordinate screen and object.

## Sources
From training: Apple Human Interface Guidelines (earlier editions). Material Design 3 documentation. Wroblewski, Mobile First. Marcotte, Responsive Web Design. Frost, Atomic Design. NN/g articles on flat design and hidden navigation. Kurosu and Kashimura 1995. Tractinsky 2000. web.dev Core Web Vitals. Fagerholt and Lorentzon 2009. Verified this session: lawsofux.com list, RISD course descriptions.
