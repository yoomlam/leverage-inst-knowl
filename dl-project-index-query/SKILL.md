---
name: dl-project-index-query
description: >
  Answer questions about Nava's projects by searching only the curated Discovery Layer Catalog and the project pages it links to. Use whenever someone asks about past work, project capabilities, agencies Nava has worked with, technologies used, or anything that can be answered from vetted project information. Do NOT use this for HR/policy questions (use sage-bot) or general web research. Triggers on questions like "what has Nava done with X?", "find projects related to Y", "which projects involve Z agency", "what do we know about X technology at Nava", or any question that can be answered from project history.
---

# Discovery Layer Project Index Query

## Step 0 — Fetch live instructions (REQUIRED before doing anything else)

Call `getConfluencePage` with:
- cloudId: `navasage.atlassian.net`
- pageId: `3231121417`
- contentFormat: `markdown`

Read the full page content. These are the authoritative, up-to-date instructions for this skill. Execute them exactly as written, using any arguments passed to this skill as the user's query.

Do not proceed until the instructions page has been successfully fetched. If the fetch fails, tell the user: "Could not load skill instructions from Confluence (page 3231121417). Please check your Atlassian connection and try again."
