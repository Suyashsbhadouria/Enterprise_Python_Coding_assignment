(function () {
  const body = document.body;
  const sidebar = document.getElementById("app-sidebar");
  const openButton = document.querySelector("[data-open-sidebar]");
  const closeButton = document.querySelector("[data-close-sidebar]");
  const scrim = document.querySelector(".scrim");

  function closeSidebar() {
    body.classList.remove("sidebar-open");
  }

  function openSidebar() {
    body.classList.add("sidebar-open");
  }

  if (sidebar && openButton) {
    openButton.addEventListener("click", openSidebar);
  }

  if (closeButton) {
    closeButton.addEventListener("click", closeSidebar);
  }

  if (scrim) {
    scrim.addEventListener("click", closeSidebar);
  }

  window.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      closeSidebar();
    }
  });

  const filterInput = document.querySelector("[data-filter-input]");
  if (filterInput) {
    const target = filterInput.getAttribute("data-filter-target");
    const rows = Array.from(document.querySelectorAll(`[data-filter-row='${target}']`));

    filterInput.addEventListener("input", function () {
      const query = filterInput.value.trim().toLowerCase();
      rows.forEach(function (row) {
        const text = (row.getAttribute("data-search") || row.textContent || "").toLowerCase();
        row.style.display = text.includes(query) ? "" : "none";
      });
    });
  }

  const chatbotShell = document.querySelector("[data-chatbot]");
  if (chatbotShell) {
    const toggleButton = chatbotShell.querySelector("[data-chatbot-toggle]");
    const panel = chatbotShell.querySelector("[data-chatbot-panel]");
    const closeChatButton = chatbotShell.querySelector("[data-chatbot-close]");
    const form = chatbotShell.querySelector("[data-chatbot-form]");
    const input = chatbotShell.querySelector("[data-chatbot-input]");
    const sendButton = chatbotShell.querySelector("[data-chatbot-send]");
    const messages = chatbotShell.querySelector("[data-chatbot-messages]");

    let history = [];

    function setPanelOpen(isOpen) {
      if (!panel || !toggleButton) {
        return;
      }
      panel.hidden = !isOpen;
      toggleButton.setAttribute("aria-expanded", String(isOpen));
      if (isOpen && input) {
        input.focus();
      }
    }

    function appendMessage(role, text) {
      if (!messages) {
        return;
      }

      const row = document.createElement("div");
      row.className = `chatbot-row ${role === "user" ? "user" : "bot"}`;

      const bubble = document.createElement("div");
      bubble.className = "chatbot-bubble";
      bubble.textContent = text;

      row.appendChild(bubble);
      messages.appendChild(row);
      messages.scrollTop = messages.scrollHeight;
    }

    if (toggleButton) {
      toggleButton.addEventListener("click", function () {
        setPanelOpen(panel ? panel.hidden : false);
      });
    }

    if (closeChatButton) {
      closeChatButton.addEventListener("click", function () {
        setPanelOpen(false);
      });
    }

    if (form && input && sendButton) {
      form.addEventListener("submit", async function (event) {
        event.preventDefault();
        const message = input.value.trim();
        if (!message) {
          return;
        }

        appendMessage("user", message);
        input.value = "";

        sendButton.disabled = true;
        appendMessage("bot", "Analyzing dataset...");

        const pendingRow = messages ? messages.lastElementChild : null;

        try {
          const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify({
              message,
              history: history.slice(-8)
            })
          });

          const payload = await response.json();
          const reply = payload.reply || payload.error || "Unable to generate a response right now.";

          if (pendingRow && pendingRow.parentElement) {
            pendingRow.remove();
          }

          appendMessage("bot", reply);
          history.push({ role: "user", content: message });
          history.push({ role: "assistant", content: reply });
          history = history.slice(-12);
        } catch (error) {
          if (pendingRow && pendingRow.parentElement) {
            pendingRow.remove();
          }
          appendMessage("bot", "Network issue. Please try again.");
        } finally {
          sendButton.disabled = false;
        }
      });
    }
  }
})();
