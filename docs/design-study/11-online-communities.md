# 11. Online communities and social computing

Serves CMU courses:
- Designing Online Communities (05-810)
- Social Web: Content, Communities, and Context (05-320/820)
- Social Data Science
- Design of Large-scale Peer Learning Systems (community side)

## The core framing
- Online communities are socio-technical systems. They succeed when their technology and rules fit how people normally behave. The course calls this "social engineering" grounded in group and organizational research.
- Kraut and Resnick, Building Successful Online Communities (2012), turns social science into "design claims". Each claim is a statement of the form "doing X tends to produce Y", backed by theory, experiments or observation.
- The book's five challenges (verified via the publisher's description):
  1. Starting a new community.
  2. Attracting and socializing newcomers.
  3. Encouraging commitment.
  4. Encouraging contribution.
  5. Regulating misbehaviour and conflict.
  The authors want designers to weigh alternatives rather than copy features from other sites.
- The specific claims below come from training on the book and its source studies. I did not re-verify them this session.

## Starting a community
- Critical mass and the chicken-and-egg problem: nobody joins an empty room. Seed it with content and founding members, piggyback on existing groups, start narrow.
- Pick a niche: compete where existing communities serve people poorly. Scope the topic so members share interests.
- Early design choices (identity, norms, moderation) set the culture, which is hard to change later.

## Newcomers
- Recruitment works best through existing members' personal ties and word of mouth. Personal invitations outperform impersonal ones.
- Selection and self-selection: give an accurate preview of what the community is and expects, so mismatched people self-select out.
- Socialization:
  - newcomers who get a response to their first post are more likely to return (Arguello et al. 2006, Burke, Kraut and Joyce 2010)
  - mentoring and welcoming spaces help: Wikipedia's Teahouse increased newcomer retention (Morgan et al. 2013)
  - sandboxes let people practise safely
- Legitimate peripheral participation (Lave and Wenger 1991): newcomers learn by doing small real tasks at the edge and move toward the core. On Wikipedia, editors move from fixing typos to the full identity of a "Wikipedian" (Bryant, Forte and Bruckman 2005).
- Protect the community from newcomers' mistakes (probation periods, limited privileges, review of first edits) without being hostile. Reverting newcomers' edits drives them away (Halfaker et al.).

## Commitment
- Three kinds (from organizational research): affective (want to stay), normative (feel obliged), continuance (costly to leave).
- Identity-based against bond-based attachment (Prentice, Miller and Lightdale 1994, Ren, Kraut and Kiesler 2007):
  - Identity-based: attachment to the group and its purpose. Build it with a clear shared goal, group names and symbols, homogeneity of purpose, and comparison with other groups.
  - Bond-based: attachment to particular members. Build it with profiles, repeated interaction, small subgroups and personal exchanges.
  - The two have different strengths. Bond-based communities tolerate off-topic chatter, identity-based ones need topical focus.
- Emotional support in health communities increases commitment (Wang, Kraut and Levine 2012).

## Contribution
- Contributions are public goods, so free riding is rational for each person. Most members lurk.
  - Participation inequality: roughly 90 percent lurk, 9 percent contribute a little, 1 percent most (Nielsen 2006).
  - Lurkers are often learning or finding what they need, not freeloading (Preece and Nonnecke).
- Social loafing (Karau and Williams 1993, the collective effort model): effort drops when individual contributions are unidentifiable or seem unneeded.
- Design moves supported by studies:
  - tell people their contribution is unique and needed (Ludford et al. 2004, Beenen et al. 2004, MovieLens)
  - specific, challenging goals, individually or for the group, raise contribution (Beenen et al. 2004)
  - make contributions visible and acknowledged, with reputation that tracks quality
  - lower the cost of contributing (small tasks, good tools)
  - targeted, personal requests rather than broadcasts (SuggestBot recommended Wikipedia articles matched to each editor's history: Cosley et al. 2007)
  - extrinsic rewards help routine tasks but can crowd out intrinsic motivation
- Coordination: on Wikipedia, more editors improved article quality only when coordinated, either by a few people concentrating the work or by explicit coordination (Kittur and Kraut 2008).

## Regulating misbehaviour and conflict
- Limit the damage: moderation that removes, hides or moves content, rate limits, and reversibility (wiki history makes vandalism cheap to undo).
- Make rules and norms visible. Posting community rules in r/science increased newcomer compliance and participation (Matias 2019).
- Legitimacy: rules are followed when members see them as fair, made with their input, and consistently applied.
- Graduated sanctions: warnings first, escalating penalties.
- Moderators drawn from the community. Appeal processes.
- Reputation and identity: persistent pseudonyms raise accountability. eBay's feedback system worked despite flaws (Resnick et al.).
- Anyone can become a troll: mood and the surrounding discussion predict trolling as much as the individual does (Cheng et al. 2017). Design the context, not only the sanctions.
- Ostrom's eight design principles for governing commons (1990) map well onto communities:
  1. Clearly defined boundaries.
  2. Rules matched to local conditions.
  3. Collective choice: those affected help make the rules.
  4. Monitoring by accountable monitors.
  5. Graduated sanctions.
  6. Accessible conflict-resolution mechanisms.
  7. Recognition of the right to self-organize.
  8. Nested enterprises for larger systems.
- Moderation taxonomy (Grimmelmann 2015):
  - verbs: exclusion, pricing, organizing, norm-setting
  - choices: manual or automatic, transparent or secret, before or after posting, centralized or distributed
- Platform governance (Gillespie, Custodians of the Internet 2018): moderation is the product.

## Social web: content, communities, context
- Social network sites (boyd and Ellison 2007): profiles, articulated connection lists, and the ability to traverse connections.
- Networked publics (boyd): persistence, visibility, spreadability, searchability. Context collapse (Marwick and boyd 2011): many audiences merge into one, so people self-censor or speak to an imagined audience.
- Social capital:
  - weak ties carry novel information (Granovetter 1973)
  - bridging against bonding capital (Putnam)
  - Facebook use related to bridging capital among students (Ellison, Steinfield and Lampe 2007)
- Wellbeing: the original "Internet paradox" study (Kraut et al. 1998) found heavy use linked to small declines. A follow-up found those effects faded and depended on how people used the Internet. Active, social use differs from passive scrolling.
- Business challenges: network effects, advertising models, moderation costs, trust and safety.

## Communities by type (named in the course)
- Open-source projects: motivations (enjoyment, learning, reputation, need), meritocratic governance, onboarding barriers for newcomers (Steinmacher).
- Wikipedia: open editing, policies such as Neutral Point of View, bots, edit wars, coordination pages.
- Health support groups: informational against emotional support, both valued and with different effects.
- Massively multiplayer games: guilds, social roles, player types (Bartle: achievers, explorers, socializers, killers).

## Social data science
- Computational social science (Lazer et al. 2009) studies social phenomena with digital traces, experiments and simulation.
- Salganik, Bit by Bit (2018), on research in the digital age:
  - Observing behaviour: big data is always on, nonreactive and big. It is also incomplete, inaccessible, nonrepresentative, drifting, algorithmically confounded, dirty and sensitive.
  - Asking questions: surveys combined with big data.
  - Running experiments: digital field experiments.
  - Mass collaboration: crowdsourcing and citizen science.
  - Ethics: the Belmont principles (respect for persons, beneficence, justice) plus respect for law and public interest.
- Methods: agent-based simulation, network analysis, text as data (NLP), digital experiments.
- Crowdsourcing quality control: gold-standard questions, redundancy and aggregation, task decomposition (Kittur et al., CrowdForge).

## Sources
Verified this session: the publisher's description of Kraut and Resnick's five design challenges. From training: Kraut and Resnick 2012. Ren, Kraut and Kiesler 2007. Burke et al. 2010. Morgan et al. 2013. Lave and Wenger 1991. Bryant et al. 2005. Halfaker et al. 2013. Karau and Williams 1993. Beenen et al. 2004. Cosley et al. 2007. Kittur and Kraut 2008. Matias 2019 (PNAS). Cheng et al. 2017. Ostrom 1990. Grimmelmann 2015. Gillespie 2018. boyd and Ellison 2007. Marwick and boyd 2011. Ellison et al. 2007. Kraut et al. 1998, 2002. Salganik 2018. Lazer et al. 2009.
