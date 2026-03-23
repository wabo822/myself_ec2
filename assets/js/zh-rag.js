(function () {
  const prompts = [
    "他做过哪些 RAG 相关项目？",
    "他在嵌入式视觉方向有什么经验？",
    "他现在在找什么样的 alternance？",
    "他掌握了哪些技术栈？"
  ];

  const state = {
    history: []
  };

  const $ = (selector, scope = document) => scope.querySelector(selector);

  const create = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof text === "string") node.textContent = text;
    return node;
  };

  const appendMessage = (role, message) => {
    const log = $("#zh-chat-log");
    const item = create("article", `chat-message ${role}`, "");
    item.appendChild(create("span", "chat-role", role === "assistant" ? "助手" : "你"));
    item.appendChild(create("p", "chat-content", message));
    log.appendChild(item);
    log.scrollTop = log.scrollHeight;
  };

  const renderSources = (sources) => {
    const container = $("#zh-source-list");
    container.innerHTML = "";

    if (!sources || !sources.length) {
      container.appendChild(create("p", "source-empty", "暂时还没有显示来源。"));
      return;
    }

    sources.forEach((source) => {
      const card = create("article", "source-card", "");
      card.appendChild(create("strong", "source-card-title", source.source));
      card.appendChild(create("p", "source-card-snippet", source.snippet));
      container.appendChild(card);
    });
  };

  const setLoading = (isLoading) => {
    $("#zh-chat-submit").disabled = isLoading;
    $("#zh-chat-input").disabled = isLoading;
    $("#zh-chat-clear").disabled = isLoading;
    $("#zh-chat-submit").textContent = isLoading ? "发送中..." : "发送";
  };

  const syncHealth = async () => {
    const status = $("#zh-status");

    try {
      const response = await fetch("/api/health");
      if (!response.ok) {
        throw new Error("health_failed");
      }

      const data = await response.json();
      status.textContent = data.llm_configured
        ? `中文问答可用 · ${data.chunk_count} 个知识块`
        : `知识库已加载，但 LLM 还没配置好 · ${data.chunk_count} 个知识块`;
      status.classList.add(data.llm_configured ? "is-ready" : "is-degraded");
    } catch (error) {
      status.textContent = "服务暂时不可用";
      status.classList.add("is-offline");
    }
  };

  const setupPrompts = () => {
    const container = $("#zh-prompts");
    prompts.forEach((prompt) => {
      const button = create("button", "tag", prompt);
      button.type = "button";
      button.addEventListener("click", () => {
        $("#zh-chat-input").value = prompt;
        $("#zh-chat-form").requestSubmit();
      });
      container.appendChild(button);
    });
  };

  const setupChat = () => {
    const form = $("#zh-chat-form");
    const input = $("#zh-chat-input");
    const clear = $("#zh-chat-clear");

    clear.addEventListener("click", () => {
      state.history = [];
      $("#zh-chat-log").innerHTML = "";
      renderSources([]);
      appendMessage(
        "assistant",
        "你好，你可以直接用中文问我和王稼瀚有关的问题，例如项目经历、RAG、嵌入式系统、技能或求职方向。"
      );
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const question = input.value.trim();

      if (!question) {
        return;
      }

      appendMessage("user", question);
      state.history.push({ role: "user", content: question });
      input.value = "";
      setLoading(true);

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            question,
            history: state.history.slice(-6)
          })
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "中文问答服务暂时返回了错误。");
        }

        appendMessage("assistant", data.answer);
        state.history.push({ role: "assistant", content: data.answer });
        renderSources(data.sources || []);
      } catch (error) {
        appendMessage(
          "assistant",
          typeof error.message === "string" ? error.message : "中文问答服务暂时不可用。"
        );
      } finally {
        setLoading(false);
      }
    });
  };

  appendMessage(
    "assistant",
    "你好，你可以直接用中文问我和王稼瀚有关的问题，例如项目经历、RAG、嵌入式系统、技能或求职方向。"
  );
  renderSources([]);
  setupPrompts();
  setupChat();
  syncHealth();
})();
