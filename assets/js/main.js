(function () {
  const content = window.siteContent;

  if (!content) {
    return;
  }

  const $ = (selector, scope = document) => scope.querySelector(selector);
  const create = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (typeof text === "string") node.textContent = text;
    return node;
  };
  const appState = {
    history: []
  };

  const renderHero = () => {
    $("[data-hero-kicker]").textContent = content.person.kicker;
    $("[data-hero-title]").textContent = content.person.title;
    $("[data-hero-lead]").textContent = content.person.lead;
    $("[data-panel-title]").textContent = content.person.panel.title;
    $("[data-panel-copy]").textContent = content.person.panel.copy;

    const actions = $("#hero-actions");
    content.person.heroActions.forEach((action) => {
      const link = create("a", `btn btn-${action.variant}`, action.label);
      link.href = action.href;
      if (action.external) {
        link.target = "_blank";
        link.rel = "noreferrer";
      }
      actions.appendChild(link);
    });

    const signals = $("#hero-signals");
    content.person.heroSignals.forEach((signal) => {
      const item = create("li", "signal-pill", signal);
      signals.appendChild(item);
    });

    const panel = $("#panel-items");
    content.person.panel.items.forEach((item) => {
      const cell = create("div", "panel-item");
      cell.appendChild(create("span", "panel-item-label", item.label));
      cell.appendChild(create("strong", "panel-item-value", item.value));
      panel.appendChild(cell);
    });
  };

  const renderAbout = () => {
    const about = $("#about-copy");
    content.person.about.forEach((paragraph) => {
      about.appendChild(create("p", "", paragraph));
    });

    const metrics = $("#metrics-grid");
    content.person.metrics.forEach((metric) => {
      const card = create("article", "metric-card reveal");
      card.appendChild(create("strong", "metric-value", metric.value));
      card.appendChild(create("p", "metric-label", metric.label));
      metrics.appendChild(card);
    });
  };

  const renderSkills = () => {
    const container = $("#skills-grid");
    content.skills.forEach((skill) => {
      const card = create("article", "skill-card card reveal");
      card.appendChild(create("p", "skill-group", skill.group));
      card.appendChild(create("h3", "skill-title", skill.description));

      const list = create("div", "tag-list");
      skill.items.forEach((item) => {
        list.appendChild(create("span", "tag", item));
      });

      card.appendChild(list);
      container.appendChild(card);
    });
  };

  const renderProjects = () => {
    const container = $("#projects-grid");
    content.projects.forEach((project) => {
      const card = create("article", "project-card card reveal");
      card.appendChild(create("p", "project-period", project.period));
      card.appendChild(create("h3", "project-title", project.name));
      card.appendChild(create("p", "project-summary", project.summary));

      const details = [
        { label: "Probleme", value: project.problem },
        { label: "Contribution", value: project.role },
        { label: "Impact", value: project.outcome }
      ];

      details.forEach((detail) => {
        const row = create("div", "project-row");
        row.appendChild(create("span", "project-row-label", detail.label));
        row.appendChild(create("p", "project-row-value", detail.value));
        card.appendChild(row);
      });

      const stack = create("div", "tag-list");
      project.stack.forEach((item) => {
        stack.appendChild(create("span", "tag", item));
      });
      card.appendChild(stack);

      container.appendChild(card);
    });
  };

  const renderTimeline = () => {
    const renderList = (entries, selector) => {
      const container = $(selector);
      entries.forEach((entry) => {
        const card = create("article", "timeline-card card reveal");
        card.appendChild(create("h3", "timeline-title", entry.title));
        card.appendChild(create("p", "timeline-meta", entry.meta));

        const list = create("ul", "timeline-points");
        entry.details.forEach((detail) => {
          list.appendChild(create("li", "", detail));
        });

        card.appendChild(list);
        container.appendChild(card);
      });
    };

    renderList(content.timeline.education, "#education-list");
    renderList(content.timeline.experience, "#experience-list");
  };

  const renderContact = () => {
    const container = $("#contact-grid");
    content.contact.forEach((item) => {
      const link = create(item.href ? "a" : "div", "contact-card", "");
      if (item.href) {
        link.href = item.href;
        link.target = "_blank";
        link.rel = "noreferrer";
        if (item.href.startsWith("mailto:")) {
          link.removeAttribute("target");
          link.removeAttribute("rel");
        }
      } else {
        link.setAttribute("aria-disabled", "true");
      }

      link.appendChild(create("span", "contact-label", item.label));
      link.appendChild(create("strong", "contact-value", item.value));
      link.appendChild(create("p", "contact-note", item.note));
      container.appendChild(link);
    });
  };

  const renderAssistant = () => {
    $("[data-assistant-title]").textContent = content.assistant.title;
    $("[data-assistant-description]").textContent = content.assistant.description;
    $("[data-assistant-hint]").textContent = content.assistant.hint;
    $("#assistant-status").textContent = content.assistant.status.loading;

    const prompts = $("#assistant-prompts");
    content.assistant.prompts.forEach((prompt) => {
      const button = create("button", "tag prompt-tag", prompt);
      button.type = "button";
      button.addEventListener("click", () => {
        $("#chat-input").value = prompt;
        $("#chat-form").requestSubmit();
      });
      prompts.appendChild(button);
    });

    appendMessage("assistant", content.assistant.welcome);
  };

  const appendMessage = (role, message) => {
    const log = $("#chat-log");
    const item = create("article", `chat-message ${role}`, "");
    item.appendChild(create("span", "chat-role", role === "assistant" ? "AI" : "Vous"));
    item.appendChild(create("p", "chat-content", message));
    log.appendChild(item);
    log.scrollTop = log.scrollHeight;
  };

  const setChatLoading = (isLoading) => {
    $("#chat-submit").disabled = isLoading;
    $("#chat-input").disabled = isLoading;
    $("#chat-clear").disabled = isLoading;
    $("#chat-submit").textContent = isLoading ? "Envoi..." : "Envoyer";
  };

  const renderSources = (sources) => {
    const container = $("#source-list");
    container.innerHTML = "";

    if (!sources || !sources.length) {
      container.appendChild(create("p", "source-empty", "Aucune source affichée pour le moment."));
      return;
    }

    sources.forEach((source) => {
      const card = create("article", "source-card", "");
      card.appendChild(create("strong", "source-card-title", source.source));
      card.appendChild(create("p", "source-card-snippet", source.snippet));
      container.appendChild(card);
    });
  };

  const syncAssistantHealth = async () => {
    const status = $("#assistant-status");

    try {
      const response = await fetch("/api/health");
      if (!response.ok) {
        throw new Error("health_failed");
      }

      const data = await response.json();
      status.textContent = data.llm_configured
        ? `${content.assistant.status.ready} • ${data.chunk_count} chunks`
        : `${content.assistant.status.degraded} • ${data.chunk_count} chunks`;
      status.classList.add(data.llm_configured ? "is-ready" : "is-degraded");
    } catch (error) {
      status.textContent = content.assistant.status.offline;
      status.classList.add("is-offline");
    }
  };

  const setupChat = () => {
    const form = $("#chat-form");
    const input = $("#chat-input");
    const clear = $("#chat-clear");

    clear.addEventListener("click", () => {
      appState.history = [];
      $("#chat-log").innerHTML = "";
      renderSources([]);
      appendMessage("assistant", content.assistant.welcome);
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const question = input.value.trim();

      if (!question) {
        return;
      }

      appendMessage("user", question);
      appState.history.push({ role: "user", content: question });
      input.value = "";
      setChatLoading(true);

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            question,
            history: appState.history.slice(-6)
          })
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "Le service AI a renvoyé une erreur.");
        }

        appendMessage("assistant", data.answer);
        appState.history.push({ role: "assistant", content: data.answer });
        renderSources(data.sources || []);
      } catch (error) {
        appendMessage(
          "assistant",
          typeof error.message === "string"
            ? error.message
            : "Le service RAG n'est pas encore disponible."
        );
      } finally {
        setChatLoading(false);
      }
    });
  };

  const setupReveal = () => {
    const items = document.querySelectorAll(".reveal");
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.18 }
    );

    items.forEach((item) => observer.observe(item));
  };

  const setupMenu = () => {
    const button = $(".menu-toggle");
    const nav = $("#site-nav");

    button.addEventListener("click", () => {
      const expanded = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", String(!expanded));
      nav.classList.toggle("is-open");
    });

    nav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        button.setAttribute("aria-expanded", "false");
        nav.classList.remove("is-open");
      });
    });
  };

  const setFooterYear = () => {
    $("#footer-year").textContent = new Date().getFullYear();
  };

  renderHero();
  renderAbout();
  renderSkills();
  renderProjects();
  renderAssistant();
  renderTimeline();
  renderContact();
  renderSources([]);
  setupReveal();
  setupMenu();
  setupChat();
  syncAssistantHealth();
  setFooterYear();
})();
