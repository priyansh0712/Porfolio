/* ============================================================
   PRIYANSH VEKARIYA — DATA ANALYST PORTFOLIO — JAVASCRIPT
   ✏️ Edit the DATA at the top to update your content easily.
   ============================================================ */

// ============================================================
// ✏️  SERVICES — The "What I Do" cards
// ============================================================
const SERVICES = [
  {
    icon: "📊",
    iconBg: "rgba(245,158,11,0.12)",
    title: "Power BI & BI Dashboards",
    desc: "Building interactive end-to-end Power BI dashboards using star-schema modeling, Power Query transformations, and advanced DAX measures to surface actionable business KPIs.",
    tags: ["Power BI", "DAX", "Power Query", "Star Schema"],
  },
  {
    icon: "🗄️",
    iconBg: "rgba(99,102,241,0.12)",
    title: "SQL & Data Analysis",
    desc: "Writing optimized SQL queries for relational databases (PostgreSQL & MySQL), performing exploratory data analysis (EDA), data cleaning, and aggregating large datasets.",
    tags: ["SQL", "PostgreSQL", "Data Cleaning", "EDA"],
  },
  {
    icon: "🐍",
    iconBg: "rgba(45,212,191,0.12)",
    title: "Python for Data",
    desc: "Using pandas, numpy, matplotlib and seaborn for statistical analysis, exploratory workflows in Jupyter Notebooks, and automating repetitive data pipelines.",
    tags: ["Python", "Pandas", "NumPy", "Matplotlib"],
  },
  {
    icon: "🌐",
    iconBg: "rgba(251,113,133,0.12)",
    title: "Full-Stack & Backend",
    desc: "Developing web applications and backend systems with Next.js, Flask, TypeScript, and PostgreSQL — including QR-based check-in modules and team management platforms.",
    tags: ["Next.js", "Flask", "TypeScript", "PostgreSQL"],
  },
];

// ============================================================
// ✏️  SKILLS — Grouped strictly by Resume & Projects
// ============================================================
const SKILLS = [
  {
    category: "Business Intelligence & Data Analytics (Core)",
    icon: "📊",
    items: [
      {
        name: "Power BI",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="12" width="4" height="9" rx="1"/><rect x="10" y="7" width="4" height="14" rx="1"/><rect x="17" y="3" width="4" height="18" rx="1"/></svg>`,
        featured: true,
      },
      {
        name: "Power Query (ETL)",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><path d="M9 12l2 2 4-4"/><path d="M4 9h16"/></svg>`,
        featured: true,
      },
      {
        name: "DAX Measures & Calculations",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19l4-14h3l4 14"/><path d="M6 14h6"/><path d="M16 8l4 8"/><path d="M20 8l-4 8"/></svg>`,
        featured: true,
      },
      {
        name: "Star Schema Data Modeling",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
        featured: true,
      },
      {
        name: "Exploratory Data Analysis (EDA)",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>`,
        featured: true,
      },
      {
        name: "Microsoft Excel (Pivot & Reporting)",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#107c41" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="12" y2="17"/><line x1="12" y1="13" x2="8" y2="17"/></svg>`,
        featured: true,
      },
    ],
  },
  {
    category: "Python & Data Science Stack",
    icon: "🐍",
    items: [
      { name: "Python",           icon: "devicon-python-plain colored",    featured: true },
      { name: "Pandas",           icon: "devicon-pandas-original colored", featured: false },
      { name: "NumPy",            icon: "devicon-numpy-original colored",  featured: false },
      {
        name: "Matplotlib",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 9l-5 5-4-4-3 3"/></svg>`,
        featured: false,
      },
      {
        name: "Seaborn",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="16" r="2"/><circle cx="12" cy="10" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="15" cy="18" r="2"/><circle cx="9" cy="8" r="2"/></svg>`,
        featured: false,
      },
      { name: "Jupyter Notebook", icon: "devicon-jupyter-plain colored",  featured: false },
    ],
  },
  {
    category: "Databases & Data Management",
    icon: "🗄️",
    items: [
      { name: "SQL",              icon: "devicon-mysql-plain colored",        featured: true },
      { name: "PostgreSQL",       icon: "devicon-postgresql-plain colored",   featured: true },
      { name: "MySQL",            icon: "devicon-mysql-plain colored",        featured: false },
      {
        name: "SQLAlchemy ORM",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>`,
        featured: false,
      },
      {
        name: "Prisma ORM",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#818cf8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 22 20 2 20 12 2"/><polygon points="12 8 18 18 6 18 12 8"/></svg>`,
        featured: false,
      },
    ],
  },
  {
    category: "Web & Full-Stack Development",
    icon: "🌐",
    items: [
      { name: "Next.js 15",       icon: "devicon-nextjs-original",            featured: false },
      { name: "TypeScript",       icon: "devicon-typescript-plain colored",   featured: false },
      { name: "Tailwind CSS",     icon: "devicon-tailwindcss-plain colored",  featured: false },
      { name: "Flask",            icon: "devicon-flask-original",             featured: false },
      { name: "Django",           icon: "devicon-django-plain colored",       featured: false },
      { name: "JavaScript",       icon: "devicon-javascript-plain colored",   featured: false },
      { name: "HTML5 / CSS3",     icon: "devicon-html5-plain colored",        featured: false },
      {
        name: "Auth.js (NextAuth)",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#a855f7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>`,
        featured: false,
      },
    ],
  },
  {
    category: "Tools, Systems & Workflow",
    icon: "🛠️",
    items: [
      { name: "Git",              icon: "devicon-git-plain colored",          featured: false },
      { name: "GitHub",           icon: "devicon-github-original",            featured: false },
      { name: "VS Code",          icon: "devicon-vscode-plain colored",       featured: false },
      {
        name: "QR Code Systems",
        svg: `<svg viewBox="0 0 24 24" fill="none" stroke="#22c55e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="3" height="3"/><rect x="18" y="18" width="3" height="3"/></svg>`,
        featured: false,
      },
    ],
  },
];

// ============================================================
// ✏️  PROJECTS — All projects
// ============================================================
const PROJECTS = [
  {
    title: "Syntra — Hackathon Management System",
    emoji: "⚡",
    gradient: "linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #0f172a 100%)",
    desc: "A collaborative full-stack hackathon management platform for organizers & participants — featuring role-based dashboards, QR-code attendance check-in, food token redemption, and team lifecycle management.",
    tech: ["Next.js 15", "TypeScript", "Prisma ORM", "Auth.js", "TailwindCSS"],
    tags: ["Team Project", "Web App", "Full-Stack", "Next.js"],
    badge: "team",
    badgeText: "👥 Team Project",
    repo: "https://github.com/Tech-Wizards-1331/syntra",
    demo: "https://syntra1331.vercel.app/",
    featured: true,
  },
  {
    title: "OLA Ride-Booking Dashboard",
    emoji: "🚖",
    gradient: "linear-gradient(135deg, #0f1a2e 0%, #1a2a4a 50%, #0a1628 100%)",
    desc: "A comprehensive data analysis & visualization project on OLA ride-booking data — exploring booking patterns, cancellation trends, revenue analytics, customer ratings, and driver performance.",
    tech: ["SQL", "Power BI", "Microsoft Excel"],
    tags: ["Data Analysis", "Dashboard", "BI"],
    badge: "data",
    badgeText: "Data Project",
    repo: "https://github.com/priyansh0712/Ola_dashbord",
    demo: null,
    featured: false,
  },
  {
    title: "RetailIQ",
    emoji: "🛒",
    gradient: "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f1117 100%)",
    desc: "A retail-focused analytics web project exploring insights and interfaces for retail data — built to surface actionable information for retail decision-making.",
    tech: ["HTML", "CSS", "JavaScript"],
    tags: ["Web App", "Retail Analytics"],
    badge: "web",
    badgeText: "Web App",
    repo: "https://github.com/priyansh0712/RetailIQ",
    demo: null,
    featured: false,
  },

  {
    title: "AttendHub",
    emoji: "📋",
    gradient: "linear-gradient(135deg, #0f172a 0%, #1a3a2a 50%, #0a1a14 100%)",
    desc: "An attendance management web application built to simplify tracking and reporting — with clean interfaces for marking, viewing, and exporting attendance records.",
    tech: ["HTML", "CSS", "JavaScript"],
    tags: ["Web App", "Productivity"],
    badge: "web",
    badgeText: "Web App",
    repo: "https://github.com/priyansh0712/AttendHub",
    demo: null,
    featured: false,
  },
  {
    title: "Django Web Application",
    emoji: "🐍",
    gradient: "linear-gradient(135deg, #0f172a 0%, #0d3030 50%, #0a1a10 100%)",
    desc: "A full-featured web application showcasing Django — models, views, templates, URL routing, authentication, and a structured MVC project setup.",
    tech: ["Django", "Python", "HTML", "CSS"],
    tags: ["Web App"],
    badge: "web",
    badgeText: "Web App",
    repo: "https://github.com/priyansh0712/Django-Project",
    demo: null,
    featured: false,
  },
  {
    title: "PhonePe Payment Analytics Dashboard",
    emoji: "💳",
    gradient: "linear-gradient(135deg, #1a0a2e 0%, #2a1060 50%, #12063a 100%)",
    desc: "An end-to-end data analysis and visualization project on PhonePe transaction data — uncovering payment trends, user behaviour patterns, transaction volumes, and regional insights through interactive dashboards.",
    tech: ["SQL", "Power BI", "Microsoft Excel", "Python"],
    tags: ["Data Analysis", "Dashboard", "BI"],
    badge: "data",
    badgeText: "Data Project",
    repo: "https://github.com/priyansh0712/RW/tree/main/PowerBi/PhonePay",
    demo: null,
    featured: false,
  },
  {
    title: "Python Journey ⭐",
    emoji: "📓",
    gradient: "linear-gradient(135deg, #1a0f2a 0%, #2a1a3a 50%, #150d24 100%)",
    desc: "A complete collection documenting a Python learning journey — from basics to advanced concepts, with hands-on Jupyter notebooks covering data manipulation, visualization, and automation.",
    tech: ["Python", "Jupyter Notebook"],
    tags: ["Python", "Data"],
    badge: "pinned",
    badgeText: "⭐ Pinned",
    repo: "https://github.com/priyansh0712/Python-journey",
    demo: null,
    featured: true,
  },
];

// ============================================================
// TYPING ANIMATION — Role strings
// ============================================================
const TYPING_STRINGS = [
  "Data Analyst | SQL • Python • Power BI",
  "Turning raw data into clear insights.",
  "Building dashboards that drive decisions.",
  "Explorer of patterns in complex datasets.",
];

let typingIndex = 0;
let charIndex = 0;
let isDeleting = false;
const typingEl = document.getElementById("typingText");

function typeEffect() {
  if (!typingEl) return;
  const current = TYPING_STRINGS[typingIndex];
  if (!isDeleting) {
    typingEl.textContent = current.substring(0, charIndex + 1);
    charIndex++;
    if (charIndex === current.length) {
      setTimeout(() => { isDeleting = true; typeEffect(); }, 2200);
      return;
    }
  } else {
    typingEl.textContent = current.substring(0, charIndex - 1);
    charIndex--;
    if (charIndex === 0) {
      isDeleting = false;
      typingIndex = (typingIndex + 1) % TYPING_STRINGS.length;
    }
  }
  setTimeout(typeEffect, isDeleting ? 38 : 65);
}

// ============================================================
// PARTICLE CANVAS
// ============================================================
function initParticles() {
  const canvas = document.getElementById("particleCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let particles = [];
  let W, H;

  function resize() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }
  resize();
  window.addEventListener("resize", resize);

  for (let i = 0; i < 90; i++) {
    particles.push({
      x: Math.random() * window.innerWidth,
      y: Math.random() * window.innerHeight,
      r: Math.random() * 1.2 + 0.3,
      vx: (Math.random() - 0.5) * 0.25,
      vy: (Math.random() - 0.5) * 0.25,
      alpha: Math.random() * 0.45 + 0.1,
    });
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const c = isDark ? "99, 102, 241" : "30, 40, 80";

    particles.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${c}, ${p.alpha})`;
      ctx.fill();
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > W) p.vx *= -1;
      if (p.y < 0 || p.y > H) p.vy *= -1;
    });

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const d = Math.sqrt(dx * dx + dy * dy);
        if (d < 90) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(${c}, ${0.05 * (1 - d / 90)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }
  draw();
}

// ============================================================
// CURSOR GLOW
// ============================================================
function initCursorGlow() {
  const glow = document.getElementById("cursorGlow");
  if (!glow || window.matchMedia("(pointer: coarse)").matches) {
    if (glow) glow.style.display = "none";
    return;
  }
  let mx = -500, my = -500, cx = -500, cy = -500;
  document.addEventListener("mousemove", (e) => { mx = e.clientX; my = e.clientY; });
  function animate() {
    cx += (mx - cx) * 0.07;
    cy += (my - cy) * 0.07;
    glow.style.left = cx + "px";
    glow.style.top = cy + "px";
    requestAnimationFrame(animate);
  }
  animate();
}

// ============================================================
// NAVBAR
// ============================================================
function initNavbar() {
  const navbar = document.getElementById("navbar");
  const navLinks = document.getElementById("navLinks");
  const hamburger = document.getElementById("hamburger");
  const allLinks = document.querySelectorAll(".nav-link");

  window.addEventListener("scroll", () => {
    navbar.classList.toggle("scrolled", window.scrollY > 50);
    document.getElementById("backToTop")?.classList.toggle("visible", window.scrollY > 400);
  }, { passive: true });

  hamburger.addEventListener("click", () => {
    hamburger.classList.toggle("open");
    navLinks.classList.toggle("open");
  });

  allLinks.forEach((link) => {
    link.addEventListener("click", () => {
      hamburger.classList.remove("open");
      navLinks.classList.remove("open");
    });
  });

  document.addEventListener("click", (e) => {
    if (!navbar.contains(e.target)) {
      hamburger.classList.remove("open");
      navLinks.classList.remove("open");
    }
  });

  // Highlight active link
  const sections = document.querySelectorAll("section[id]");
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        allLinks.forEach((l) => l.classList.toggle("active", l.getAttribute("href") === `#${id}`));
      }
    });
  }, { threshold: 0.4 });
  sections.forEach((s) => observer.observe(s));
}

// ============================================================
// SCROLL ANIMATIONS
// ============================================================
function initScrollAnimations() {
  const obs = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("animated");
          obs.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.1, rootMargin: "0px 0px -50px 0px" }
  );
  document.querySelectorAll("[data-animate]").forEach((el) => obs.observe(el));
}

// ============================================================
// COUNTER ANIMATION (hero metrics)
// ============================================================
function initCounters() {
  const counters = document.querySelectorAll("[data-count]");
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const target = parseInt(entry.target.getAttribute("data-count"));
        let count = 0;
        const step = Math.ceil(target / 30);
        const interval = setInterval(() => {
          count = Math.min(count + step, target);
          entry.target.textContent = count + "+";
          if (count >= target) clearInterval(interval);
        }, 50);
        obs.unobserve(entry.target);
      }
    });
  });
  counters.forEach((c) => obs.observe(c));
}

// ============================================================
// RENDER SERVICES
// ============================================================
function renderServices() {
  const grid = document.getElementById("servicesGrid");
  if (!grid) return;
  grid.innerHTML = SERVICES.map((s, i) => `
    <div class="service-card" data-animate="fade-up" style="transition-delay:${i * 0.08}s">
      <div class="service-icon" style="background:${s.iconBg}">${s.icon}</div>
      <h3 class="service-title">${s.title}</h3>
      <p class="service-desc">${s.desc}</p>
      <div class="service-tags">
        ${s.tags.map((t) => `<span class="service-tag">${t}</span>`).join("")}
      </div>
    </div>
  `).join("");
}

// ============================================================
// RENDER SKILLS
// ============================================================
function renderSkills() {
  const grid = document.getElementById("skillsGrid");
  if (!grid) return;
  grid.innerHTML = SKILLS.map((cat) => `
    <div class="skill-category" data-animate="fade-up">
      <div class="skill-cat-header">
        <span class="skill-cat-icon">${cat.icon}</span>
        <h3 class="skill-cat-title">${cat.category}</h3>
        <div class="skill-cat-line"></div>
      </div>
      <div class="skills-chips">
        ${cat.items.map((item) => `
          <div class="skill-chip${item.featured ? " featured" : ""}">
            ${item.svg ? item.svg : (item.icon ? `<i class="${item.icon}"></i>` : "")}
            <span>${item.name}</span>
          </div>
        `).join("")}
      </div>
    </div>
  `).join("");
}

// ============================================================
// RENDER PROJECTS
// ============================================================
function renderProjects(filter = "all") {
  const grid = document.getElementById("projectsGrid");
  if (!grid) return;

  const filtered = filter === "all"
    ? PROJECTS
    : PROJECTS.filter((p) => p.tags.some((t) => t.toLowerCase().includes(filter.toLowerCase())));

  if (!filtered.length) {
    grid.innerHTML = `<p style="grid-column:1/-1;text-align:center;color:var(--text-muted);padding:3rem;">No projects found for this filter.</p>`;
    return;
  }

  grid.innerHTML = filtered.map((p) => `
    <div class="project-card${p.featured ? " featured-card" : ""}" data-animate="fade-up">
      <div class="project-banner-wrap">
        <div class="project-banner" style="background:${p.gradient}">${p.emoji}</div>
        <span class="project-badge badge-${p.badge}">${p.badgeText}</span>
      </div>
      <div class="project-body">
        <h3 class="project-title">${p.title}</h3>
        <p class="project-desc">${p.desc}</p>
        <div class="project-tech">
          ${p.tech.map((t) => `<span class="tech-tag">${t}</span>`).join("")}
        </div>
        <div class="project-links">
          ${p.repo ? `
            <a href="${p.repo}" target="_blank" rel="noopener noreferrer" class="project-link">
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
              View Code
            </a>
          ` : ""}
          ${p.demo ? `
            <a href="${p.demo}" target="_blank" rel="noopener noreferrer" class="project-link">
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
              Live Demo
            </a>
          ` : ""}
        </div>
      </div>
    </div>
  `).join("");

  initScrollAnimations();
}

// ============================================================
// PROJECT FILTERS
// ============================================================
function initProjectFilters() {
  document.querySelectorAll(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      renderProjects(btn.dataset.filter);
    });
  });
}

// ============================================================
// CONTACT FORM
// ============================================================
function initContactForm() {
  const form = document.getElementById("contactForm");
  const success = document.getElementById("formSuccess");
  const errorMsg = document.getElementById("formError");
  const submitBtn = document.getElementById("formSubmitBtn");
  const submitText = document.getElementById("submitBtnText");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name    = document.getElementById("contactName").value.trim();
    const email   = document.getElementById("contactEmail").value.trim();
    const subject = document.getElementById("contactSubject").value.trim();
    const message = document.getElementById("contactMessage").value.trim();

    if (success) success.style.display = "none";
    if (errorMsg) errorMsg.style.display = "none";

    // Set loading state
    if (submitBtn) submitBtn.disabled = true;
    if (submitText) submitText.textContent = "Sending...";

    try {
      const response = await fetch("https://formsubmit.co/ajax/priyanshvekariya06@gmail.com", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({
          name: name,
          email: email,
          _subject: `Portfolio Message: ${subject || "General Inquiry"}`,
          message: message,
          _template: "table",
          _captcha: "false"
        })
      });

      const result = await response.json();

      if (response.ok && (result.success === "true" || result.success === true || result.message)) {
        if (success) {
          success.style.display = "block";
          setTimeout(() => { success.style.display = "none"; }, 6000);
        }
        form.reset();
      } else {
        throw new Error(result.message || "Form submission failed");
      }
    } catch (err) {
      console.warn("Direct form submit error, falling back to mailto:", err);
      if (errorMsg) {
        errorMsg.style.display = "block";
        setTimeout(() => { errorMsg.style.display = "none"; }, 6000);
      }
      const body = `Hi Priyansh,%0A%0A${encodeURIComponent(message)}%0A%0AFrom: ${encodeURIComponent(name)} (${encodeURIComponent(email)})`;
      window.location.href = `mailto:priyanshvekariya06@gmail.com?subject=${encodeURIComponent(subject)}&body=${body}`;
    } finally {
      if (submitBtn) submitBtn.disabled = false;
      if (submitText) submitText.textContent = "Send Message";
    }
  });
}

// ============================================================
// THEME TOGGLE
// ============================================================
function initThemeToggle() {
  const toggle = document.getElementById("themeToggle");
  const html = document.documentElement;
  const saved = localStorage.getItem("pv-theme") || "dark";
  html.setAttribute("data-theme", saved);

  toggle.addEventListener("click", () => {
    const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    localStorage.setItem("pv-theme", next);
  });
}

// ============================================================
// BACK TO TOP
// ============================================================
function initBackToTop() {
  document.getElementById("backToTop")?.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

// ============================================================
// FOOTER YEAR
// ============================================================
function initFooterYear() {
  const el = document.getElementById("footerYear");
  if (el) el.textContent = new Date().getFullYear();
}

// ============================================================
// CARD 3D TILT (project cards — desktop only)
// ============================================================
function initCardTilt() {
  if (window.matchMedia("(pointer: coarse)").matches) return;
  document.addEventListener("mousemove", (e) => {
    document.querySelectorAll(".project-card").forEach((card) => {
      const r = card.getBoundingClientRect();
      const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
      if (inside) {
        const dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
        const dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
        card.style.transform = `translateY(-6px) rotateX(${-dy * 3}deg) rotateY(${dx * 3}deg)`;
      } else {
        card.style.transform = "";
      }
    });
  });
}

// ============================================================
// INIT
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  initThemeToggle();
  initParticles();
  initCursorGlow();
  initNavbar();

  // Render content
  renderServices();
  renderSkills();
  renderProjects();
  initProjectFilters();

  // Animations
  initScrollAnimations();
  initCounters();
  initBackToTop();
  initContactForm();
  initFooterYear();
  initCardTilt();

  // Typing animation
  setTimeout(typeEffect, 600);

  // Hero animate-in
  const heroContent = document.querySelector("#hero [data-animate='fade-up']");
  if (heroContent) setTimeout(() => heroContent.classList.add("animated"), 150);
  const heroVisual = document.querySelector(".hero-visual");
  if (heroVisual) setTimeout(() => heroVisual.classList.add("animated"), 350);

  // ---- CV PREVIEW MODAL ----
  const cvOverlay  = document.getElementById("cvModalOverlay");
  const cvClose    = document.getElementById("cvModalClose");

  function openCvModal() {
    cvOverlay.classList.add("open");
    document.body.style.overflow = "hidden";
  }

  function closeCvModal() {
    cvOverlay.classList.remove("open");
    document.body.style.overflow = "";
  }

  // Open on Resume button click
  document.getElementById("resumeBtn")?.addEventListener("click", (e) => {
    e.preventDefault();
    openCvModal();
  });

  // Close on X button
  cvClose?.addEventListener("click", closeCvModal);

  // Close clicking outside the modal card
  cvOverlay?.addEventListener("click", (e) => {
    if (e.target === cvOverlay) closeCvModal();
  });

  // Close on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && cvOverlay?.classList.contains("open")) {
      closeCvModal();
    }
  });
});

