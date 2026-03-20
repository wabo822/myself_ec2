window.siteContent = {
  person: {
    name: "Jiahan Wang",
    kicker: "Paris • Étudiant ingénieur • IA appliquée • Systèmes embarqués",
    title: "Je construis des systèmes fiables entre IA appliquée, vision embarquée et hardware connecté.",
    lead:
      "Formé entre Shanghai, Lyon et Paris, je travaille sur des sujets concrets : RAG sur corpus métier, vision embarquée sur Raspberry Pi, télémétrie ESP32 et logiciels techniques pensés pour le terrain. Je recherche une alternance de 3 ans en intelligence artificielle ou ingénierie des données à partir de septembre 2026.",
    resumeUrl: "cv_mars2026.pdf",
    email: "mailto:jiahan.wang@eleve.isep.fr",
    emailLabel: "jiahan.wang@eleve.isep.fr",
    github: "https://github.com/wabo822",
    githubLabel: "github.com/wabo822",
    linkedin: "https://www.linkedin.com/in/votre-profil/",
    linkedinLabel: "linkedin.com/in/votre-profil",
    heroActions: [
      { label: "Voir les projets", href: "#projects", variant: "primary" },
      { label: "Me contacter", href: "mailto:jiahan.wang@eleve.isep.fr", variant: "secondary" },
      { label: "Voir le CV", href: "cv_mars2026.pdf", variant: "ghost", external: true }
    ],
    heroSignals: [
      "25k documents structurés en RAG",
      "+14 pts de Hit@1 sur un moteur de recherche interne",
      "18 FPS en vision embarquée sur Raspberry Pi 5"
    ],
    panel: {
      title: "Disponible pour une alternance longue en IA / data dès septembre 2026.",
      copy:
        "Profil orienté exécution, avec un vrai goût pour les systèmes qu'on peut évaluer, déployer et améliorer rapidement.",
      items: [
        { label: "Base", value: "Paris, France" },
        { label: "Formation", value: "ISEP + INSA Lyon" },
        { label: "Focus", value: "RAG, vision, IoT, data" },
        { label: "Style", value: "Builder, rigoureux, international" }
      ]
    },
    about: [
      "Mon parcours me donne une double lecture : une base scientifique exigeante, puis une montée en puissance vers l'intelligence artificielle, la data et les systèmes embarqués. Après un passage par l'INSA Lyon, j'étudie aujourd'hui à l'ISEP avec l'envie d'évoluer dans des environnements où l'on conçoit, teste et déploie vraiment.",
      "J'aime les projets où l'intelligence logicielle rencontre les contraintes du réel : indexer des milliers de documents pour un moteur RAG utile, entraîner un modèle léger pour un robot mobile, faire remonter de la télémétrie en temps réel depuis un ESP32, ou transformer une idée technique en prototype crédible.",
      "Ce que je cherche maintenant, c'est une équipe exigeante, internationale et rapide, où je peux apprendre vite, livrer proprement et participer à la construction de produits techniques avec une vraie ambition."
    ],
    metrics: [
      {
        value: "25k",
        label: "documents traités dans un pipeline RAG d'entreprise"
      },
      {
        value: "61%",
        label: "Hit@1 atteint après re-ranking cross-encoder"
      },
      {
        value: "18 FPS",
        label: "inférence temps réel sur robot mobile embarqué"
      }
    ]
  },
  skills: [
    {
      group: "Programming",
      description: "Des outils solides pour prototyper vite et structurer proprement.",
      items: ["Python", "C++", "SQL", "Algorithmique", "Analyse de données"]
    },
    {
      group: "AI / Data / LLM",
      description: "IA appliquée, retrieval, évaluation et vision par ordinateur.",
      items: ["PyTorch", "LangChain", "FAISS", "OpenCV", "RAG", "Cross-Encoder", "YOLO"]
    },
    {
      group: "Embedded / IoT",
      description: "Du capteur au prototype temps réel, avec une logique système.",
      items: ["ESP32", "Raspberry Pi 5", "MQTT", "HTTP", "TCP/IP", "Capteurs", "Télémétrie"]
    },
    {
      group: "Tools",
      description: "Un environnement d'ingénierie pratique, orienté production et itération.",
      items: [
        "Git",
        "Docker",
        "Linux",
        "Arduino IDE",
        "SolidEdge",
        "LabelImg",
        "Excel",
        "Claude Code / Cursor / Codex"
      ]
    },
    {
      group: "Languages",
      description: "À l'aise dans des contextes multiculturels et techniques.",
      items: ["Chinois (natif)", "Français (B2-C1)", "Anglais (B2)"]
    }
  ],
  projects: [
    {
      name: "Pipeline RAG pour documentation d'entreprise",
      period: "06/2025 - 08/2025",
      summary: "Améliorer la récupération d'information sur un corpus interne volumineux et préparer un service RAG exploitable.",
      problem:
        "Le besoin était de retrouver vite les bonnes informations dans environ 25k documents, avec un niveau de fiabilité suffisant pour un usage interne.",
      role:
        "J'ai prototypé le pipeline LangChain + FAISS, évalué un reranker cross-encoder, structuré les mesures, et participé à la conception d'un PoC de service RAG local conteneurisé. J'ai aussi exploré un module vision-RAG pour tableaux et images.",
      stack: ["Python", "LangChain", "FAISS", "Cross-Encoder", "Docker", "Firecrawl"],
      outcome:
        "Passage de 47% à 61% en Hit@1, Hit@5 autour de 82%, MRR proche de 0,48 sur environ 180k passages."
    },
    {
      name: "Vision embarquée pour robot mobile",
      period: "02/2026 - 04/2026",
      summary: "Construire une détection d'objets embarquée, assez légère pour fonctionner en temps réel sur un robot.",
      problem:
        "Le projet demandait un système de perception capable d'aider la navigation d'un robot mobile, avec des contraintes réelles de latence et de puissance.",
      role:
        "J'ai préparé et annoté un jeu de données personnalisé, entraîné un modèle YOLO léger, puis intégré l'inférence avec OpenCV sur Raspberry Pi 5.",
      stack: ["Raspberry Pi 5", "OpenCV", "YOLO", "LabelImg", "Python"],
      outcome:
        "Environ 1200 images annotées, mAP@0.5:0.95 = 0,82 et inférence temps réel autour de 18 FPS."
    },
    {
      name: "Fusée à eau intelligente",
      period: "02/2025 - 06/2025",
      summary: "Instrumenter une fusée à eau avec de la télémétrie temps réel et une logique de simulation.",
      problem:
        "L'objectif était de mesurer le comportement du système en vol, puis de confronter les données capteurs à une trajectoire simulée.",
      role:
        "J'ai développé la chaîne de télémétrie via ESP32 en C++, intégré un capteur barométrique et un accéléromètre, réalisé la simulation de trajectoire en Python et la modélisation 3D sous SolidEdge.",
      stack: ["ESP32", "C++", "Python", "Capteurs", "SolidEdge"],
      outcome:
        "Un prototype complet, combinant acquisition temps réel, simulation physique et conception mécanique."
    }
  ],
  timeline: {
    education: [
      {
        title: "Institut Supérieur d'Électronique de Paris (ISEP)",
        meta: "09/2025 - 06/2029 • Paris",
        details: [
          "Cycle ingénieur avec spécialisation visée en intelligence artificielle.",
          "Cours suivis : circuits numériques, robotique, télécommunications, algorithmique, signaux et systèmes.",
          "Résultats marquants : 17,5/20 en physique et 19,4/20 en mathématiques."
        ]
      },
      {
        title: "INSA Lyon",
        meta: "08/2023 - 06/2025 • Lyon",
        details: [
          "Formation scientifique en mathématiques, physique, informatique et chimie.",
          "Cours principaux : analyse, algèbre linéaire, physique générale, thermodynamique."
        ]
      },
      {
        title: "Lycée Guangming de Shanghai",
        meta: "09/2020 - 06/2023 • Shanghai",
        details: [
          "Cours de mathématiques et de physique dispensés en français par des professeurs natifs."
        ]
      }
    ],
    experience: [
      {
        title: "Hande (Shanghai) — Stagiaire Ingénieur R&D IA",
        meta: "06/2025 - 08/2025",
        details: [
          "Prototypage d'un pipeline RAG sur environ 25k documents et 180k passages.",
          "Évaluation d'un reranker cross-encoder avec gain net sur les métriques de retrieval.",
          "Exploration vision-RAG pour tableaux et images, puis participation à un PoC de service interne dockerisé."
        ]
      },
      {
        title: "Cirroparcel (Lyon) — Stagiaire",
        meta: "07/2024 - 08/2024",
        details: [
          "Gestion opérationnelle d'un flux logistique e-commerce international.",
          "Coordination terrain avec les livreurs et suivi de la performance sous Excel.",
          "Étude de marché sur la logistique e-commerce transfrontalière."
        ]
      },
      {
        title: "Enseignant de mathématiques en ligne — Freelance",
        meta: "09/2023 - présent",
        details: [
          "Préparation aux concours d'ingénieurs pour des élèves chinois.",
          "5 élèves admis, dont 4 à l'INSA Lyon."
        ]
      }
    ]
  },
  contact: [
    {
      label: "Email",
      value: "jiahan.wang@eleve.isep.fr",
      href: "mailto:jiahan.wang@eleve.isep.fr",
      note: "Canal principal pour les échanges."
    },
    {
      label: "GitHub",
      value: "github.com/wabo822",
      href: "https://github.com/wabo822",
      note: "Code, projets et expérimentations."
    },
    {
      label: "LinkedIn",
      value: "Profil LinkedIn à ajouter",
      note: "Placeholder à remplacer avant la mise en ligne finale."
    }
  ]
};
