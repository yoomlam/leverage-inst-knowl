// Minimal SSE chat client. Sends a message, streams normalized events from the server,
// and renders assistant text, tool activity, and connection-error nudges.
(function () {
  const transcript = document.getElementById("transcript");
  const composer = document.getElementById("composer");
  const input = document.getElementById("message");
  const conversationId = transcript.dataset.conversationId;
  const agentId = transcript.dataset.agentId;

  function bubble(cls, text) {
    const el = document.createElement("div");
    el.className = "card " + cls;
    el.textContent = text;
    transcript.appendChild(el);
    return el;
  }

  // Render accumulated markdown to sanitized HTML; fall back to plain text if the CDN
  // libs didn't load (offline / blocked).
  function renderMarkdown(el, raw) {
    if (window.marked && window.DOMPurify) {
      el.innerHTML = window.DOMPurify.sanitize(window.marked.parse(raw));
    } else {
      el.textContent = raw;
    }
  }

  // Maps a tool_use id to its rendered bubble so a later tool_result can nest under its call.
  const toolCalls = {};

  function collapsible(summaryText, body) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = summaryText;
    const pre = document.createElement("pre");
    pre.textContent = body;
    details.appendChild(summary);
    details.appendChild(pre);
    return details;
  }

  function toolBubble(event) {
    const b = bubble("tool", "⚙ using " + (event.server ? event.server + " · " : "") + event.name);
    // Show the tool-call arguments in a collapsible block so the transcript stays scannable
    // but the detail is one click away. Omitted when there are no arguments.
    if (event.input && Object.keys(event.input).length) {
      b.appendChild(collapsible("arguments", JSON.stringify(event.input, null, 2)));
    }
    if (event.id) toolCalls[event.id] = b;
  }

  // A tool's returned output. Nest it under the matching call bubble when we have it;
  // otherwise (result seen before its call, or id missing) render it standalone.
  function toolResultBubble(event) {
    const label = (event.is_error ? "error" : "result");
    const call = event.tool_use_id && toolCalls[event.tool_use_id];
    if (call) {
      call.appendChild(collapsible(label, event.content || "(empty)"));
    } else {
      bubble("tool" + (event.is_error ? " error" : ""), "⚙ " + label)
        .appendChild(collapsible(label, event.content || "(empty)"));
    }
  }

  function errorBubble(event) {
    const b = bubble("error", "Connection issue" + (event.mcp_server_name ? " with " + event.mcp_server_name : "") + ". Reconnect that source and retry.");
    const link = document.createElement("a");
    link.href = "/connections?agent_id=" + encodeURIComponent(agentId);
    link.textContent = " Fix connections";
    b.appendChild(link);
  }

  // Replay prior events into the transcript before the composer is used. Each history
  // event is its own bubble (consecutive assistant messages aren't merged — the merge
  // in the live stream is only to accumulate a single reply's text deltas).
  function loadHistory() {
    return fetch("/chat/" + conversationId + "/history")
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (events) {
        if (!Array.isArray(events)) return;
        events.forEach(function (event) {
          if (event.type === "user") {
            bubble("user", "You: " + event.text);
          } else if (event.type === "text") {
            const el = bubble("assistant", "");
            renderMarkdown(el, event.text);
          } else if (event.type === "tool_use") {
            toolBubble(event);
          } else if (event.type === "tool_result") {
            toolResultBubble(event);
          } else if (event.type === "error") {
            errorBubble(event);
          }
        });
      })
      .catch(function () { /* history is best-effort; a blank transcript is fine */ });
  }

  composer.addEventListener("submit", function (e) {
    e.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    bubble("user", "You: " + message);
    input.value = "";

    let assistant = null;
    const url = "/chat/" + conversationId + "/stream?message=" + encodeURIComponent(message);
    const source = new EventSource(url);

    source.onmessage = function (ev) {
      const event = JSON.parse(ev.data);
      if (event.type === "text") {
        if (!assistant) { assistant = bubble("assistant", ""); assistant._raw = ""; }
        assistant._raw += event.text;
        renderMarkdown(assistant, assistant._raw);
      } else if (event.type === "tool_use") {
        toolBubble(event);
      } else if (event.type === "tool_result") {
        toolResultBubble(event);
      } else if (event.type === "error") {
        errorBubble(event);
      } else if (event.type === "done") {
        source.close();
      }
    };

    source.onerror = function () {
      source.close();
    };
  });

  loadHistory();
})();
