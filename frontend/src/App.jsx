import { useEffect, useState } from "react";

import { chinesePaths, siteContent, zhPageContent } from "./siteContent.js";
import "./styles.css";

function updateMeta(name, content) {
  const tag = document.querySelector(`meta[name="${name}"]`);
  if (tag) {
    tag.setAttribute("content", content);
  }
}

function usePageMetadata(meta) {
  useEffect(() => {
    document.title = meta.title;
    document.documentElement.lang = meta.lang;
    updateMeta("description", meta.description);
    updateMeta("robots", meta.robots);
    updateMeta("theme-color", "#0b0f17");
  }, [meta.description, meta.lang, meta.robots, meta.title]);
}

function useRevealObserver(pageKey) {
  useEffect(() => {
    const items = document.querySelectorAll(".reveal");
    if (!items.length) {
      return undefined;
    }

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
    return () => observer.disconnect();
  }, [pageKey]);
}

function useRagChat(config) {
  const [messages, setMessages] = useState([{ role: "assistant", content: config.welcome }]);
  const [history, setHistory] = useState([]);
  const [sources, setSources] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState(config.status.loading);
  const [statusClass, setStatusClass] = useState("");

  useEffect(() => {
    let ignore = false;

    const syncHealth = async () => {
      try {
        const response = await fetch("/api/health");
        if (!response.ok) {
          throw new Error("health_failed");
        }

        const data = await response.json();
        if (ignore) {
          return;
        }

        if (data.llm_configured) {
          setStatusText(`${config.status.ready} • ${data.chunk_count} ${config.chunkLabel}`);
          setStatusClass("is-ready");
          return;
        }

        setStatusText(`${config.status.degraded} • ${data.chunk_count} ${config.chunkLabel}`);
        setStatusClass("is-degraded");
      } catch (error) {
        if (ignore) {
          return;
        }
        setStatusText(config.status.offline);
        setStatusClass("is-offline");
      }
    };

    syncHealth();
    return () => {
      ignore = true;
    };
  }, [config.status]);

  const clearChat = () => {
    setMessages([{ role: "assistant", content: config.welcome }]);
    setHistory([]);
    setSources([]);
    setInput("");
  };

  const askQuestion = async (rawQuestion) => {
    const question = rawQuestion.trim();
    if (!question || loading) {
      return;
    }

    const nextHistory = [...history, { role: "user", content: question }];
    setMessages((current) => [...current, { role: "user", content: question }]);
    setHistory(nextHistory);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          question,
          history: nextHistory.slice(-6)
        })
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || config.fallbackError);
      }

      setMessages((current) => [...current, { role: "assistant", content: data.answer }]);
      setHistory([...nextHistory, { role: "assistant", content: data.answer }]);
      setSources(data.sources || []);
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: typeof error.message === "string" ? error.message : config.fallbackError
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await askQuestion(input);
  };

  return {
    messages,
    sources,
    input,
    setInput,
    loading,
    statusText,
    statusClass,
    clearChat,
    askQuestion,
    handleSubmit
  };
}

function renderLinkProps(item) {
  if (!item.href) {
    return {};
  }

  if (item.external) {
    return {
      href: item.href,
      target: "_blank",
      rel: "noreferrer"
    };
  }

  if (item.href.startsWith("mailto:") || item.href.startsWith("#") || item.href.startsWith("/")) {
    return { href: item.href };
  }

  return {
    href: item.href,
    target: "_blank",
    rel: "noreferrer"
  };
}

function ChatMessages({ messages, assistantLabel, userLabel }) {
  return (
    <div className="chat-log" aria-live="polite">
      {messages.map((message, index) => (
        <article className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
          <span className="chat-role">{message.role === "assistant" ? assistantLabel : userLabel}</span>
          <p className="chat-content">{message.content}</p>
        </article>
      ))}
    </div>
  );
}

function SourceList({ sources, emptyLabel }) {
  return (
    <div className="source-list">
      {!sources.length ? (
        <p className="source-empty">{emptyLabel}</p>
      ) : (
        sources.map((source, index) => (
          <article className="source-card" key={`${source.source}-${index}`}>
            <strong className="source-card-title">{source.source}</strong>
            <p className="source-card-snippet">{source.snippet}</p>
          </article>
        ))
      )}
    </div>
  );
}

function PortfolioPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const assistant = useRagChat(siteContent.assistant);

  usePageMetadata(siteContent.meta);
  useRevealObserver("portfolio");

  return (
    <>
      <a className="skip-link" href="#main">
        Aller au contenu
      </a>

      <div className="site-shell">
        <header className="site-header">
          <a className="brand" href="#top" aria-label="Retour en haut de page">
            <span className="brand-mark">JW</span>
            <span className="brand-copy">
              <strong>{siteContent.person.name}</strong>
              <small>AI &amp; Embedded Systems Builder</small>
            </span>
          </a>

          <button
            className="menu-toggle"
            type="button"
            aria-expanded={String(menuOpen)}
            aria-controls="site-nav"
            onClick={() => setMenuOpen((current) => !current)}
          >
            Menu
          </button>

          <nav
            className={`site-nav${menuOpen ? " is-open" : ""}`}
            id="site-nav"
            aria-label="Navigation principale"
          >
            {siteContent.navigation.map((item) => (
              <a href={item.href} key={item.href} onClick={() => setMenuOpen(false)}>
                {item.label}
              </a>
            ))}
          </nav>
        </header>

        <main id="main">
          <section className="hero section" id="top">
            <div className="hero-copy reveal">
              <p className="eyebrow">{siteContent.person.kicker}</p>
              <h1>{siteContent.person.title}</h1>
              <p className="hero-lead">{siteContent.person.lead}</p>

              <div className="hero-cta" id="hero-actions">
                {siteContent.person.heroActions.map((action) => (
                  <a className={`btn btn-${action.variant}`} key={action.label} {...renderLinkProps(action)}>
                    {action.label}
                  </a>
                ))}
              </div>

              <ul className="signal-list" aria-label="Faits saillants">
                {siteContent.person.heroSignals.map((signal) => (
                  <li className="signal-pill" key={signal}>
                    {signal}
                  </li>
                ))}
              </ul>
            </div>

            <aside className="hero-panel reveal" aria-label="Portrait, statut et focus">
              <div className="hero-panel-head">
                <div className="hero-portrait-frame">
                  <img
                    className="hero-portrait"
                    src={siteContent.person.portraitSrc}
                    alt="Portrait de Jiahan Wang"
                  />
                </div>

                <div className="hero-panel-copy">
                  <div className="panel-label">Statut / Focus</div>
                  <h2>{siteContent.person.panel.title}</h2>
                  <p className="panel-copy">{siteContent.person.panel.copy}</p>
                </div>
              </div>

              <div className="panel-grid" id="panel-items">
                {siteContent.person.panel.items.map((item) => (
                  <div className="panel-item" key={item.label}>
                    <span className="panel-item-label">{item.label}</span>
                    <strong className="panel-item-value">{item.value}</strong>
                  </div>
                ))}
              </div>
            </aside>
          </section>

          <section className="section" id="assistant">
            <div className="section-heading reveal">
              <p className="section-kicker">Assistant AI</p>
              <h2>Un point d&apos;entrée RAG pour poser des questions directement sur mon profil.</h2>
            </div>

            <div className="assistant-layout">
              <aside className="assistant-info card reveal">
                <p className={`assistant-status ${assistant.statusClass}`}>{assistant.statusText}</p>
                <h3>{siteContent.assistant.title}</h3>
                <p className="assistant-description">{siteContent.assistant.description}</p>
                <div className="tag-list" id="assistant-prompts">
                  {siteContent.assistant.prompts.map((prompt) => (
                    <button
                      className="tag prompt-tag"
                      type="button"
                      key={prompt}
                      onClick={() => assistant.askQuestion(prompt)}
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </aside>

              <div className="assistant-chat card reveal">
                <div className="chat-topbar">
                  <div>
                    <p className="chat-label">{siteContent.assistant.chatLabel}</p>
                    <strong className="chat-title">{siteContent.assistant.chatTitle}</strong>
                  </div>
                  <button className="chat-clear" id="chat-clear" type="button" onClick={assistant.clearChat}>
                    {siteContent.assistant.clearLabel}
                  </button>
                </div>

                <ChatMessages messages={assistant.messages} assistantLabel="AI" userLabel="Vous" />

                <div className="source-panel">
                  <p className="source-title">Sources RAG</p>
                  <SourceList
                    sources={assistant.sources}
                    emptyLabel={siteContent.assistant.emptySources}
                  />
                </div>

                <form className="chat-form" onSubmit={assistant.handleSubmit}>
                  <label className="chat-label sr-only" htmlFor="chat-input">
                    Votre question
                  </label>
                  <textarea
                    id="chat-input"
                    name="question"
                    rows="4"
                    maxLength="800"
                    placeholder={siteContent.assistant.placeholder}
                    required
                    value={assistant.input}
                    onChange={(event) => assistant.setInput(event.target.value)}
                    disabled={assistant.loading}
                  />
                  <div className="chat-actions">
                    <p className="chat-hint">{siteContent.assistant.hint}</p>
                    <button className="btn btn-primary" type="submit" disabled={assistant.loading}>
                      {assistant.loading
                        ? siteContent.assistant.sendingLabel
                        : siteContent.assistant.submitLabel}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </section>

          <section className="section" id="about">
            <div className="section-heading reveal">
              <p className="section-kicker">À propos</p>
              <h2>Un profil d&apos;ingénieur en construction, avec une logique produit très concrète.</h2>
            </div>

            <div className="about-layout">
              <div className="about-copy card reveal" id="about-copy">
                {siteContent.person.about.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>

              <div className="metrics-grid" id="metrics-grid">
                {siteContent.person.metrics.map((metric) => (
                  <article className="metric-card reveal" key={metric.label}>
                    <strong className="metric-value">{metric.value}</strong>
                    <p className="metric-label">{metric.label}</p>
                  </article>
                ))}
              </div>
            </div>
          </section>

          <section className="section" id="skills">
            <div className="section-heading reveal">
              <p className="section-kicker">Compétences</p>
              <h2>Des bases solides en logiciel, IA appliquée et systèmes embarqués.</h2>
            </div>

            <div className="skills-grid" id="skills-grid">
              {siteContent.skills.map((skill) => (
                <article className="skill-card card reveal" key={skill.group}>
                  <p className="skill-group">{skill.group}</p>
                  <h3 className="skill-title">{skill.description}</h3>
                  <div className="tag-list">
                    {skill.items.map((item) => (
                      <span className="tag" key={item}>
                        {item}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="section" id="projects">
            <div className="section-heading reveal">
              <p className="section-kicker">Projets</p>
              <h2>Des projets construits pour être utiles, mesurables et testables.</h2>
            </div>

            <div className="projects-grid" id="projects-grid">
              {siteContent.projects.map((project) => (
                <article className="project-card card reveal" key={project.name}>
                  <p className="project-period">{project.period}</p>
                  <h3 className="project-title">{project.name}</h3>
                  <p className="project-summary">{project.summary}</p>

                  {[
                    { label: "Probleme", value: project.problem },
                    { label: "Contribution", value: project.role },
                    { label: "Impact", value: project.outcome }
                  ].map((detail) => (
                    <div className="project-row" key={detail.label}>
                      <span className="project-row-label">{detail.label}</span>
                      <p className="project-row-value">{detail.value}</p>
                    </div>
                  ))}

                  <div className="tag-list">
                    {project.stack.map((item) => (
                      <span className="tag" key={item}>
                        {item}
                      </span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="section" id="journey">
            <div className="section-heading reveal">
              <p className="section-kicker">Formation &amp; Expérience</p>
              <h2>Un parcours international entre Shanghai, Lyon et Paris.</h2>
            </div>

            <div className="journey-grid">
              <div className="journey-column">
                <div className="column-title reveal">
                  <span className="column-index">01</span>
                  <h3>Formation</h3>
                </div>
                <div className="timeline-list">
                  {siteContent.timeline.education.map((entry) => (
                    <article className="timeline-card card reveal" key={entry.title}>
                      <h3 className="timeline-title">{entry.title}</h3>
                      <p className="timeline-meta">{entry.meta}</p>
                      <ul className="timeline-points">
                        {entry.details.map((detail) => (
                          <li key={detail}>{detail}</li>
                        ))}
                      </ul>
                    </article>
                  ))}
                </div>
              </div>

              <div className="journey-column">
                <div className="column-title reveal">
                  <span className="column-index">02</span>
                  <h3>Expérience</h3>
                </div>
                <div className="timeline-list">
                  {siteContent.timeline.experience.map((entry) => (
                    <article className="timeline-card card reveal" key={entry.title}>
                      <h3 className="timeline-title">{entry.title}</h3>
                      <p className="timeline-meta">{entry.meta}</p>
                      <ul className="timeline-points">
                        {entry.details.map((detail) => (
                          <li key={detail}>{detail}</li>
                        ))}
                      </ul>
                    </article>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="section" id="contact">
            <div className="contact-panel reveal">
              <div className="contact-copy">
                <p className="section-kicker">Contact</p>
                <h2>Ouvert aux projets sérieux, aux échanges techniques et à une alternance IA / data.</h2>
                <p>
                  Si votre équipe construit des produits techniques utiles, avec de vraies contraintes
                  d&apos;exécution, je suis toujours partant pour en discuter.
                </p>
              </div>

              <div className="contact-grid" id="contact-grid">
                {siteContent.contact.map((item) => {
                  const Tag = item.href ? "a" : "div";
                  return (
                    <Tag className="contact-card" key={item.label} {...renderLinkProps(item)}>
                      <span className="contact-label">{item.label}</span>
                      <strong className="contact-value">{item.value}</strong>
                      <p className="contact-note">{item.note}</p>
                    </Tag>
                  );
                })}
              </div>
            </div>
          </section>
        </main>

        <footer className="site-footer">
          <p>
            {new Date().getFullYear()} Jiahan Wang. Portfolio personnel avec assistant RAG, pensé
            pour GitHub et un déploiement simple sur EC2.
          </p>
        </footer>
      </div>
    </>
  );
}

function ChinesePage() {
  const assistant = useRagChat(zhPageContent.assistant);

  usePageMetadata(zhPageContent.meta);
  useRevealObserver("zh");

  return (
    <div className="zh-shell">
      <header className="card zh-topbar">
        <div className="zh-topbar-copy">
          <p className="section-kicker">{zhPageContent.topbarKicker}</p>
          <strong>{zhPageContent.topbarTitle}</strong>
        </div>
        <a className="zh-back-link" href="/">
          {zhPageContent.backLabel}
        </a>
      </header>

      <main>
        <section className="zh-intro">
          <div className="card zh-intro-card reveal">
            <p className="section-kicker">{zhPageContent.introKicker}</p>
            <h1>{zhPageContent.introTitle}</h1>
            <p>{zhPageContent.introCopy}</p>
            <div className="zh-intro-points">
              {zhPageContent.introTags.map((tag) => (
                <span className="tag" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
          </div>

          <aside className="card zh-assistant-card reveal">
            <p className="section-kicker">{zhPageContent.usageKicker}</p>
            <h2>{zhPageContent.usageTitle}</h2>
            <p>{zhPageContent.usageCopy}</p>
          </aside>
        </section>

        <section className="zh-layout">
          <aside className="card zh-side reveal">
            <p className={`zh-status ${assistant.statusClass}`}>{assistant.statusText}</p>
            <div>
              <p className="section-kicker">{zhPageContent.sideKicker}</p>
              <h3>{zhPageContent.sideTitle}</h3>
            </div>
            <ul>
              {zhPageContent.sideQuestions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ul>
            <div className="zh-prompt-grid">
              {zhPageContent.assistant.prompts.map((prompt) => (
                <button className="tag" type="button" key={prompt} onClick={() => assistant.askQuestion(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
          </aside>

          <div className="card zh-chat reveal">
            <div className="chat-topbar">
              <div>
                <p className="chat-label">{zhPageContent.assistant.chatLabel}</p>
                <strong className="chat-title">{zhPageContent.assistant.chatTitle}</strong>
              </div>
              <button className="chat-clear" type="button" onClick={assistant.clearChat}>
                {zhPageContent.assistant.clearLabel}
              </button>
            </div>

            <ChatMessages messages={assistant.messages} assistantLabel="助手" userLabel="你" />

            <div className="source-panel">
              <p className="source-title">{zhPageContent.assistant.sourceTitle}</p>
              <p className="zh-source-note">{zhPageContent.assistant.sourceNote}</p>
              <SourceList
                sources={assistant.sources}
                emptyLabel={zhPageContent.assistant.emptySources}
              />
            </div>

            <form className="chat-form" onSubmit={assistant.handleSubmit}>
              <label className="chat-label sr-only" htmlFor="zh-chat-input">
                你的问题
              </label>
              <textarea
                id="zh-chat-input"
                name="question"
                rows="4"
                maxLength="800"
                placeholder={zhPageContent.assistant.placeholder}
                required
                value={assistant.input}
                onChange={(event) => assistant.setInput(event.target.value)}
                disabled={assistant.loading}
              />
              <div className="chat-actions">
                <p className="chat-hint">{zhPageContent.assistant.hint}</p>
                <button className="btn btn-primary" type="submit" disabled={assistant.loading}>
                  {assistant.loading
                    ? zhPageContent.assistant.sendingLabel
                    : zhPageContent.assistant.submitLabel}
                </button>
              </div>
            </form>
          </div>
        </section>
      </main>
    </div>
  );
}

export default function App() {
  const pathname = window.location.pathname;
  const isChinesePage = chinesePaths.has(pathname);

  if (isChinesePage) {
    return <ChinesePage />;
  }

  return <PortfolioPage />;
}
