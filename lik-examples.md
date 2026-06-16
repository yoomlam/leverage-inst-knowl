Following are examples of how LIK concepts map to current Nava solutions.

- *DL-creation skill* takes *DS records* and creates *DL data*
- *Query skill* queries *DL data* and *DS records* to answer user questions/requests

### Analogy (intuition): an office building

Picture a large office building.

| LIK concept | Office building | Why it fits |
| --- | --- | --- |
| DS records | The individual offices, where the real work and records are kept | The source of truth; each office controls who it lets in (its own permissions). |
| DL data | Handouts and digests *about* what the offices do — posted at reception, on floor screens, in a kiosk | Derived so you don't have to visit every office; scattered across spots; can be regenerated from the offices anytime. |
| Confirmation signals | Visitor feedback cards — "Suite 4B actually solved my problem" | People vouching an answer was good; kept on the card, not inside the office. |
| Catalog | The lobby directory — topic → where its prepared material is posted | The one board everyone checks first; points to *where the handout lives*, not what's inside the offices. Move a handout and you change one directory line, not the offices. |
| DL-creation skill | The information officer who tours the offices, writes the handouts, and keeps the directory current | Produces the derived material. |
| Query skill | The concierge who, given your question, points you to the right handout or office | Steers you; can only send you where you're already allowed in — the offices' own locks still decide. |

Two nuances from the strategy:
- The lobby directory indexes *where prepared materials live*, never the offices' contents — so a wrong directory line can misdirect you, but it can't unlock a door.
- An office can post its own "certified" plaque (trust native to the DS), separate from visitor feedback cards (DL confirmation signals); the concierge weighs both.

---

## Current Nava solutions

| LIK concept | Project Indexes | OPIS PR assistant |
| --- | --- | --- |
| DS records | Confluence pages and uploaded artifacts from Slack | GitHub PRs |
| DL-creation skill | Knowledge Graph Bot via Slack | AWS Lambda |
| (DL data) Human-readable artifacts | Confluence spaces (Project Index) | Retrieved chunks (must query vector DB) |
| (DL data) Machine retrieval signals | Confluence page labels, tags, metadata | Semantic embeddings and metadata in vector DB |
| DL Confirmation signals | manual validation? | (TODO) engineers like, dislike, and comment on GitHub PRs |
| DL Catalog | Project Index Directory | Query vector DB |
| Query skill | Knowledge Graph Bot (via Slack) or Confluence Rovo | (TODO) chatbot UI and MCP service |

---

### [Project Indexes](https://navasage.atlassian.net/wiki/x/A4BGoQ)
* DS records: Confluence pages and uploaded artifacts from Slack
* DL-creation skill: Knowledge Graph Bot via Slack
* DL data
    * Human-readable artifacts: Confluence spaces (Project Index)
    * Machine retrieval signals: Confluence page labels, tags, metadata (e.g., each Confluence space's [Update History's ](https://navasage.atlassian.net/wiki/spaces/PIVAAIS/pages/3078684730/Update+History))
* DL Confirmation signals: manual validation?
* DL Catalog: [Project Index Directory](https://navasage.atlassian.net/wiki/spaces/KGWS/pages/2705752067/Project+Index+Directory)
* Query skill: Knowledge Graph Bot (via Slack) or Confluence Rovo

#### (Yoom's preliminary testing on top of Project Indexes)
* DS records: (provided by Project Indexes)
* DL-creation skill: (provided by Project Indexes)
* DL data: (provided by Project Indexes)
* DL Confirmation signals: TODO
* DL Catalog: adds (Confluence) Catalog entries via `discovery-catalog-sync`
* Query skill: `dl-project-index-query`


---

### OPIS (RAG-based) PR assistant
* DS records: GitHub PRs
* DL-creation skill: AWS Lambda
* DL data
    * Human-readable artifacts: retrieved chunks (must query vector DB)
    * Machine retrieval signals: semantic embeddings and metadata in vector DB
* DL Confirmation signals: (TODO) engineers to like, dislike, and comment on GitHub PRs
* DL Catalog: query vector DB
* Query skill: (TODO) chatbot UI and MCP service

### [In-progress] OPIS (RAG-based) Generalized
* DS records: GitHub, Confluence, Jira, and Slack
* DL-creation skill: AWS Lambda
* DL data
    * Human-readable artifacts: retrieved chunks (must query vector DB)
    * Machine retrieval signals: semantic embeddings and metadata in vector DB
* DL Confirmation signals: ?
* DL Catalog: via querying vector DB
* Query skill: (TODO) chatbot UI and MCP service

### (Using RAG-based solution as a DS)
* DS records: solution's vector DB
* DL-creation skill: solution's ingestion into vector DB
* DL data
    * Human-readable artifacts: index/summary of content in vector DB
    * Machine retrieval signals: semantic embeddings and metadata in vector DB
* DL Confirmation signals: add entry
* DL Catalog: add Catalog entries of summarized DL data
* Query skill: via MCP



---

Template -- Solution X
* DS records: 
* DL-creation skill: 
* DL data
    * Human-readable artifacts: 
    * Machine retrieval signals: 
* DL Confirmation signals:
* DL Catalog: 
* Query skill:

