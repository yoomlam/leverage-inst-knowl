

(SSA data sources)
* **Salesforce**: Generally **available**. Salesforce provides fully hosted MCP servers (such as the Data 360 and Salesforce DX servers), enabling AI agents to securely query and act upon your organization’s data and setups using natural language.  
* **Greenhouse**: Generally **available**. The Greenhouse MCP allows users to connect AI platforms directly to their hiring and applicant tracking processes. It supports actions like candidate creation and job discovery.  
  * rolling out starting June 2026. There are also community/third-party Greenhouse MCP servers.  
* **Workday**: While Workday features an active Agent System of Record (ASOR) designed for agent-to-agent and MCP communication, direct connections are typically facilitated through **third-party automation hubs and integration tools** like [Workato](https://www.workato.com/product-hub/mcp-monday-26-pre-built-mcp-servers-one-enterprise-platform/) or [CData](https://www.cdata.com/kb/tech/workday-cloud-claude-agent-sdk.rst) rather than a native Workday-hosted MCP.  
  * CData’s Workday MCP server and Workato’s Workday End User MCP server. CData says its server connects LLMs to Workday data; Unified.to explicitly notes Workday does **not** ship an official MCP server.  
* **Unanet**: Unanet relies on standard integration methods (such as Unanet Connect and **APIs**) rather than Model Context Protocol (MCP) servers.  
  * **Community MCP server**, not clearly official; the GitHub repo exists but was archived by the owner on May 12, 2026.  
* (SSA will do one-time static loads from ***Lever and Paylocity***)

Other data sources
* Google Drive — official/vendor MCP server
    * (Gmail — MCP servers available; must set up Cloud project)
* Confluence/Jira — official/vendor MCP server via Atlassian Rovo MCP
* GitHub — official/vendor MCP server
* Slack — official/vendor MCP server
