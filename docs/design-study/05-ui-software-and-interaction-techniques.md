# 5. Interface software and interaction techniques

Serves: CMU Software Structures for User Interfaces (05-431/631), Advanced Topics in UI Software (05-830), Interaction Techniques (05-440/640), Programming Interactive Experiences (05-635), Programming Usable Interfaces (retired).

## How interface software is structured
- Interfaces are event-driven. An event loop takes input events (pointer, key, touch, timer, network) from a queue and dispatches them.
- Dispatch:
  - Pointer events go to the topmost interactor under the cursor (positional dispatch).
  - Keyboard events go to the interactor with focus (focus dispatch).
  - The DOM adds capture and bubble phases, so ancestors can intercept or handle events.
- Focus management is a design problem, not plumbing. Every interactive element needs a visible focus state, and focus must move sensibly when dialogs open and close.
- Output:
  - damage and redraw (only repaint what changed)
  - painter's algorithm (draw back to front)
  - double buffering against flicker
  - retained mode (a scene graph the toolkit redraws) vs immediate mode (the app redraws every frame)
- Layout: box models, constraint systems, flexbox and grid.
- Declarative UI (React and similar): the interface is a function of state. The framework diffs and updates the real tree. Data flows one way, state lives in a known place, and events request state changes.
- Keep the UI thread free. Long work goes to background workers. Perceived performance tools:
  - skeleton screens
  - optimistic updates (show the result, reconcile later)
  - progress feedback (timing thresholds in [03](03-interaction-design-principles.md))

## Patterns
- Model-View-Controller (Reenskaug 1979, Smalltalk) and its descendants MVP and MVVM separate data, presentation and input handling.
- Observer (publish and subscribe): views update when the model changes.
- Command pattern: each user action is an object with execute and undo. Stacks of commands give undo and redo. Selective and history-based undo build on this.
- State machines and statecharts (Harel 1987): describe interactive behaviour explicitly. Dragging, for example, has the states idle, pressed, dragging, dropped and cancelled (Escape). Explicit states prevent "impossible" combinations and missing cases.
- Composite (the view hierarchy), Strategy (swappable behaviours), dataflow and constraints.
- Constraint-based UI:
  - Garnet and Amulet (Myers, CMU): one-way constraints keep graphical properties consistent automatically.
  - Cassowary: linear constraint solving, the basis of Apple's Auto Layout.
  - ConstraintJS (Oney, CMU).

## History of UI toolkits (as taught in 05-830)
- Sketchpad (Sutherland 1963): direct manipulation, constraints, objects.
- Xerox Alto and Star, and Smalltalk: windows, icons, menus, pointer, MVC.
- Macintosh Toolbox, X Windows and Motif, Java Swing, Android, iOS UIKit then SwiftUI, the web.
- Research systems:
  - Garnet and Amulet (Myers)
  - subArctic (Hudson)
  - Context Toolkit (Dey): separates context sensing from use
  - Papier-Mâché (Klemmer): tangible input from cameras and RFID
- Lesson from the history: ideas move from research prototypes to commercial systems over 10 to 20 years.

## Judging tools and frameworks
- Myers, Hudson and Pausch (2000), "Past, present and future of user interface software tools":
  - Threshold: how hard a tool is to start using.
  - Ceiling: how much a tool can do.
  - Good tools have a low threshold and a high ceiling.
  - Tools create a "path of least resistance": designers build what the tool makes easy, so tool choices shape designs.
- Olsen (2007), "Evaluating user interface systems research": judge a tool by
  - Situations, Tasks and Users (STU), and the importance of the problem
  - whether it solves a problem not previously solvable
  - generality
  - reduced solution viscosity (flexibility, expressive leverage, expressive match)
  - whether it empowers new design participants
  - power in combination
  - scalability
- API usability (Myers and Stylos 2016, "Improving API usability", CACM): APIs are interfaces for programmers, so HCI methods apply to them (heuristic evaluation, think-aloud with programmers). Studies found factory patterns harder to use than constructors, and that naming and examples in documentation matter most.

## Interaction techniques
- Course definition: a technique starts when the user does something that makes a device respond, and it includes the device's direct feedback.

### Fitts's law
- MT = a + b log2(D/W + 1), the Shannon formulation (MacKenzie 1992). D is distance to the target, W is target width along the motion, and the log term is the index of difficulty in bits.
- Consequences:
  - make frequent targets large and close
  - screen edges and corners behave as infinitely deep targets (the macOS menu bar)
  - pie menus put every item at the same short distance
- Throughput (bits per second) compares devices. ISO 9241-9 multidirectional tapping is the standard task.
- Touch target guidance:
  - Apple 44 by 44 points
  - Material 48 by 48 dp
  - WCAG 2.2 2.5.8 sets a minimum of 24 by 24 CSS pixels at level AA, with a spacing exception (verified on W3C)
  - 2.5.5 asks for 44 by 44 at AAA

### Steering, choice and practice
- Steering law (Accot and Zhai 1997): time to move through a tunnel grows with its length divided by its width. This is why cascading menus with narrow paths are hard.
- Hick-Hyman law: reaction time = a + b log2(n + 1) for n equally likely choices. Practice and familiarity shrink the effect.
- Power law of practice: time per trial falls as a power function of the number of trials. Experts look different from novices, so measure learning curves, not a single session.

### Menus and commands
- Marking menus (Kurtenbach and Buxton 1993): novices press and wait to see a radial menu, experts flick in the remembered direction without looking. The same gesture serves both, so novices rehearse expert behaviour.
- Split menus put frequent items on top. Adaptive menus that reorder themselves hurt when predictions are wrong or the layout becomes unpredictable (Findlater and McGrenere 2004). Keep adaptation predictable and stable.
- Command palettes combine recognition (browse) with recall (type).
- Keyboard shortcuts: platform conventions (Ctrl or Cmd plus a letter), shown next to menu items so they are discoverable, mnemonic where possible.

### Text entry
- QWERTY, soft keyboards, autocorrect and prediction, gesture typing (Zhai and Kristensson, SHARK), speech input.
- Measures: words per minute and error rates (MacKenzie and Soukoreff).

### Touch and gestures
- Problems:
  - the "fat finger" and occlusion (Shift, Vogel and Baudisch 2007, shows a callout of the occluded area)
  - no hover
  - gestures have no visible signifier, so discoverability suffers
- Long-press and swipe actions are hidden by default. Provide visible alternatives.
- Haptic feedback confirms actions.

### Scrolling, paging and pointing aids
- Flick-to-scroll with inertia, rubber-band overscroll. Infinite scroll suits browsing but hurts finding, footers and sense of position. Pagination supports position and return.
- Pointing aids:
  - area cursors and the bubble cursor (Grossman and Balakrishnan 2005): the cursor grabs the nearest target
  - snapping
  - semantic pointing

### Drag and drop
- Show what can be dragged and what will accept a drop, give drop-target feedback, allow cancel.
- WCAG 2.2 2.5.7 requires a single-pointer alternative for any dragging operation (verified on W3C).

### 3D, VR, game controllers, remotes
- 3D and VR: selection by ray casting or virtual hand (Go-Go extends reach), travel techniques (teleport reduces sickness), manipulation, comfort.
- Game controllers and remotes: directional focus navigation needs clear focus states and predictable movement between targets.

### Adaptations for disability
Switch scanning, dwell clicking, eye gaze, head pointers, sticky keys and voice control. See [08](08-accessibility.md).

### Evaluating techniques
Controlled experiments measuring speed, accuracy, throughput, learning curves and subjective workload. Report errors with speed, since the two trade off.

## Programming interactive experiences (05-635)
- Topics: input and output techniques, basic accessibility, reading and reviewing code, debugging, iterative movement between ideas and prototypes.
- Code craft: separation of concerns, components with clear inputs and outputs, explicit state, small testable pieces, readable names.
- Code review is a design critique of code.

## Sources
Verified this session: W3C WCAG 2.2 new-criteria page (2.5.7, 2.5.8). From training: Myers, Hudson and Pausch 2000 (TOCHI). Olsen 2007 (UIST). Myers and Stylos 2016 (CACM). Harel 1987. MacKenzie 1992. Accot and Zhai 1997. Kurtenbach and Buxton 1993. Findlater and McGrenere 2004. Vogel and Baudisch 2007. Grossman and Balakrishnan 2005. Card, Moran and Newell 1983.
