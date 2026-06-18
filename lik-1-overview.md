# Leveraging Institutional Knowledge (LIK) — Overview

*A plain-language introduction. For real-world mappings see [lik-2-examples.md](lik-2-examples.md); for the technical design, [lik-3-architecture-concise.md](lik-3-architecture-concise.md); for the build plan, [lik-4-strategy.md](lik-4-strategy.md).*

## The problem

A company's knowledge is scattered across many systems — Google Drive, Confluence, Jira, GitHub, Slack, Gmail, Salesforce, Workday, and more. To answer one question, every AI agent, every app, and every person has to search all of those systems, over and over. That is slow, expensive, inconsistent from one tool to the next, and prone to missing the answer that is most trusted or most current.

## The idea

Leave the knowledge where it already lives. On top of it, add a lightweight layer that makes finding things fast — **without** copying everything into one place and **without** creating a second, competing "source of truth." The layer is *computed*: it is derived from the original systems and can be rebuilt from them at any time.

## Guiding Principles

Every design choice in the later docs traces back to these.

- **Very low maintenance** — minimize the code and extra data we have to keep running. Most of the layer is recomputed from the sources, so it can be rebuilt or discarded rather than carefully tended.
- **Loosely coupled** — keep the pieces independent so any one — a store, a source, a tool — can be swapped without rewriting the rest, and no single vendor becomes hard to leave.
- **Intuitive (easy to understand and adopt)** — lean on standards (e.g., MCP) and common patterns rather than bespoke mechanisms, so people and tools pick it up quickly.
- **Flexible** — adaptable to a wide range of questions, data, and tools: many small, specialized skills instead of one rigid system.
- **One source of truth** — durable knowledge always stays in its original system. The layer holds only computed copies, pointers, and signals — never a competing master record.
- **Secure by default** — least privilege, deny when unsure, and access always enforced by the *original system*, never by the layer's own metadata. A wrong entry can misdirect a lookup but can never unlock a door.
- **Build on existing sign-in** — most systems are already reached through Google single sign-on, so access reuses that existing login and its group permissions instead of standing up a new identity or permission system to maintain. (Sources that don't already use Google groups for permissions need a one-time mapping — see the architecture for details.)
- **Earn each step** — buy before building, and add each capability only once the previous one's limits prove it's needed; spend follows evidence, not ambition.

## The concepts and terminology

1. **Data Sources (DSs)** — the systems where knowledge is actually created, corrected, and governed (Drive, Confluence, Jira, GitHub, Slack, Gmail, Salesforce, Workday, …). These stay the **source of truth**: every lasting change is written here, and each system keeps controlling who may see what.

2. **Discovery Layer (DL)** — a layer of *prepared material derived from the Data Sources*: summaries, indexes, pointers, and freshness/trust signals. It exists so tools don't have to re-search everything from scratch. It is recomputable from the sources and is never a second source of truth. Its outputs come in a few flavors — readable summaries, machine retrieval signals, and confirmation signals (below).

3. **Catalog** — the Discovery Layer's "yellow pages": one well-known place that maps a *topic* to *where its prepared material lives*. A tool does **one lookup**, then follows the pointer — instead of searching every system. Move a piece of material and you change one line in the catalog, not the tools that use it.

4. **DL-creation skills** — the automated *producers*. Each reads the Data Sources, writes the Discovery Layer's prepared material, and keeps the catalog current; each runs on its own service identity, on a schedule or on demand. **There are many, not one** — a given skill is customized to the kind of source data it handles (its type, location, and owning team/project/program), so it can process and validate that source the way that team or program needs and produce a specific kind of output in a specific place.

5. **Query skills** — the *guides*. Given a question, a skill steers an AI agent to the right prepared material or the right source. They can only help an agent *find* answers faster — never widen access, because every search runs under the asking person's own permissions. **There are many, not one** — each covers a topic or question type. A skill built for a known topic can go **straight to the relevant prepared material**, skipping the catalog lookup entirely; the catalog is the fallback for questions no skill already knows where to answer.

6. **Confirmation signals** — people vouching that an answer was right (or flagging it wrong). This is the one part of the Discovery Layer that comes from *people*, not something that can be re-derived from the sources — so it is kept and backed up deliberately.

Two relationships tie these together:

- The **DL-creation skill** takes **DS records** and creates **DL data**.
- The **Query skill** queries **DL data** and **DS records** to answer a person's question.

## Progressive disclosure: answering in cheap steps

The catalog and the Discovery Layer let an agent find an answer in increasingly specific steps, instead of loading everything at once. Each step costs more than the one before, and most questions are answered before reaching the bottom.

1. **Catalog** *(the entry point)* — one lookup to learn *what exists and where* (the high-level roadmap).
2. **Discovery Layer** *(narrowing down)* — follow the pointer to prepared material already distilled from the sources (a summary, index, or signal).
3. **Data Sources** *(the original records)* — open the full records only when the question demands them.
4. **On-demand discovery** *(following links)* — from inside a record, follow links to related records to expand understanding as needed.

## Analogy: an office building

| LIK concept | Office building | Why it fits |
| --- | --- | --- |
| DS records | The individual offices, where the real work and records are kept | The source of truth; each office controls who it lets in (its own permissions). |
| DL data | Handouts and digests *about* what the offices do — posted at reception, on floor screens, in a kiosk | Derived so you don't have to visit every office; scattered across spots; can be regenerated from the offices anytime. |
| Confirmation signals | Visitor feedback cards — "Suite 4B actually solved my problem" | People vouching an answer was good; kept on the card, not inside the office. |
| Catalog | The lobby directory — topic → where its prepared material is posted | The one board everyone checks first; points to *where the handout lives*, not what's inside the offices. Move a handout and you change one directory line, not the offices. |
| DL-creation skills | Information officers, each assigned to certain offices — they tour those offices, write the handouts, and keep the directory current | Produce the derived material; each specializes in the offices (sources) it knows. |
| Query skills | Concierges, each an expert on certain topics — given your question, one points you to the right handout or office | Steer you; can only send you where you're already allowed in — the offices' own locks still decide. |

A few nuances:
- The lobby directory indexes *where prepared materials live*, never the offices' contents — so a wrong directory line can misdirect you, but it can't unlock a door.
- An office can post its own "certified" plaque (trust native to the source), separate from visitor feedback cards (DL confirmation signals); the concierge weighs both.
- There isn't one concierge or one information officer but **several, each specialized**. A concierge who already knows your topic can walk you straight to the right handout without checking the lobby directory first; the directory is there for questions no concierge has memorized.

### Other analogies

**A restaurant**
- DS: The **kitchens** cook the real food. 
- DL: A **meal-prep service** turns that into ready-to-eat boxes and a tasting menu.
- Catalog: A **directory at the pickup counter** — "boxed salads: case 3; tasting menu: shelf B" — tells you where each *prepped* item sits; it points at the boxes, not the recipes.
- Confirmation signals: **Diner reviews** say which dishes were actually good.

**Maps / GPS**
- DS: The **physical streets and buildings** are the ground truth.
- DL: A **map** is a derived, simplified rendering kept in sync with reality.
- Catalog: An **atlas's index** — "this region is on sheet 42"; it tells you which derived map sheet to open, not what's on the ground.
- Confirmation signals: **User reports** — "this road is closed," "great coffee here".

## Where to go next

- **[lik-2-examples.md](lik-2-examples.md)** — how these concepts map to systems Nava already runs (Project Indexes, OPIS).
- **[lik-3-architecture-concise.md](lik-3-architecture-concise.md)** — the technical design: components, schema, access control, write model.
- **[lik-4-strategy.md](lik-4-strategy.md)** — the build plan: buy first, then build progressively where a bought tool falls short.
