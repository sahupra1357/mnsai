import {
  Bot,
  Cpu,
  Eye,
  Server,
  Rocket,
  GraduationCap,
  Award,
  FileText,
  Search,
  ClipboardCheck,
  Sparkles,
  Layers,
  MessageSquare,
  Database,
  ScanSearch,
  Boxes,
  Briefcase,
  FolderGit2,
  Megaphone,
  Mail,
  type LucideIcon,
} from "lucide-react"

/**
 * Single source of truth for all copy on the v3 profile homepage — every
 * heading, label, chip, eyebrow, placeholder label, and stat. Components render
 * from this file; nothing user-visible is hard-coded in JSX.
 *
 * Derived strictly from docs/profile-draft.md — nothing here is invented. Items
 * marked [NEEDS INPUT] in the draft are represented as EMPTY arrays / null so the
 * UI renders an explicit blank placeholder (dashed slot + muted label), never
 * fabricated data. Filling a slot later means adding data, not code.
 *
 * When this file changes, keep backend/app/profile_agent/docs/ in sync.
 */

/* ─────────────────────────── Hero ─────────────────────────── */

export const profile = {
  name: "Pradeep Sahu",
  /** Initials shown in the avatar ring until a headshot exists. */
  initials: "PS",
  /**
   * Static fallback headshot path. The live headshot is uploaded at
   * /settings → "Profile photo" (see lib/profile-image.ts); this is only a
   * second fallback, and null renders the initials-ring placeholder.
   */
  headshot: null as string | null,
  greeting: "Hi, I'm Pradeep Sahu,",
  /** Gradient display headline — the specialty that defines the work. */
  headlineAccent: "Generative AI & Multi-Agent Systems",
  /** Bold foreground descriptor lines, drawn from the value proposition. */
  headlineLines: [
    "AI Engineer shipping RAG, agents, and",
    "document & vision intelligence to production.",
  ],
  valueProposition:
    "I design and ship production Generative AI systems — RAG chatbots, multi-agent workflows, document and vision intelligence — end-to-end on AWS, Azure, and Google Cloud.",
  supportingLine:
    "From prompt to production: fine-tuning, evaluation, MLOps, and the APIs and frontends around them. This site itself is a working demo.",
  email: "sahupra1357@gmail.com",
  linkedin: "https://www.linkedin.com/in/pradeep-sahu-074b92b/",
  // GitHub URL: [NEEDS INPUT] — omitted until provided.
  // Availability badge: [NEEDS INPUT] — omitted.
} as const

/** Role-descriptor pills under the hero headline. All trace to the value prop. */
export const heroChips: string[] = [
  "AI Engineer",
  "RAG systems",
  "Multi-agent workflows",
  "Document & vision AI",
  "MLOps",
]

/**
 * "As featured in" slot. No approved press yet → EMPTY array renders a blank
 * dashed placeholder. Adding logos later is a data change only.
 */
export const featuredIn: { name: string }[] = []
export const featuredInLabel = "As featured in"
export const featuredInPlaceholder = "Press & mentions — coming soon"

/* ───────────────────── Section metadata ───────────────────── */

export interface SectionMeta {
  id: string
  navLabel: string
  heading: string
  subtitle: string
  icon: LucideIcon
}

export const sections = {
  work: {
    id: "work",
    navLabel: "Experience",
    heading: "Work experience",
    subtitle:
      "Systems shipped in the field — real production work, presented without client names.",
    icon: Briefcase,
  },
  projects: {
    id: "projects",
    navLabel: "Projects",
    heading: "Projects",
    subtitle:
      "Working software you can open right now — including this site and its assistant.",
    icon: FolderGit2,
  },
  sharing: {
    id: "sharing",
    navLabel: "Sharing",
    heading: "Sharing & talks",
    subtitle: "Writing and talks about building with Generative AI.",
    icon: Megaphone,
  },
  learning: {
    id: "learning",
    navLabel: "Education",
    heading: "Education & certifications",
    subtitle: "Formal training and the certifications behind the work.",
    icon: GraduationCap,
  },
  skills: {
    id: "skills",
    navLabel: "Skills",
    heading: "Skills & tooling",
    subtitle:
      "The stack behind the work, grouped by where it fits in a Generative AI system.",
    icon: Layers,
  },
  contact: {
    id: "contact",
    navLabel: "Contact",
    heading: "Have a project in mind?",
    subtitle:
      "Tell me what you're building — or ask the assistant first. I read every message.",
    icon: Mail,
  },
} satisfies Record<string, SectionMeta>

/* ───────────────── Left "On this page" rail ───────────────── */

/** Copy for the sticky left rail (xl+). */
export const rail = {
  tocLabel: "On this page",
} as const

export interface RailEntry {
  id: string
  navLabel: string
  /** Two-digit ordinal shown before the label (01, 02, …). */
  index: string
}

/**
 * Ordered entries the sticky rail iterates for scrollspy + smooth-scroll. One
 * per main content section; ids match the <section> anchors on the page. Labels
 * trace to `sections` above so the rail and headings never drift apart.
 */
export const sectionOrder: RailEntry[] = [
  { id: sections.work.id, navLabel: sections.work.navLabel, index: "01" },
  { id: sections.projects.id, navLabel: sections.projects.navLabel, index: "02" },
  { id: sections.sharing.id, navLabel: sections.sharing.navLabel, index: "03" },
  { id: sections.skills.id, navLabel: sections.skills.navLabel, index: "04" },
  { id: sections.learning.id, navLabel: sections.learning.navLabel, index: "05" },
  { id: sections.contact.id, navLabel: sections.contact.navLabel, index: "06" },
]

/* ───────────────────── Work experience ───────────────────── */

export interface ExperienceEntry {
  org: string
  location: string
  role: string
  dateRange: string
  summary: string
  bullets: string[]
}

/**
 * Employer entries. The resume carries NO employer names or dates
 * ([NEEDS INPUT]), so this array is EMPTY → the section renders one dashed
 * placeholder entry, and the real accomplishments live in `selectedWork` below,
 * unattributed.
 */
export const experienceEntries: ExperienceEntry[] = []

export const experience = {
  placeholderTitle: "Employer details coming soon",
  placeholderBody:
    "Named roles, companies, and dates are being confirmed. The work itself is below — presented without attribution.",
  selectedWorkLabel: "Selected work",
  /** Corporate-client logo strip — no approved clients → blank placeholder. */
  clientsLabel: "Corporate clients",
  clients: [] as { name: string }[],
  clientsPlaceholder: "Client logos — coming soon",
} as const

export interface Highlight {
  lead: string
  body: string
}

/** The five resume accomplishments, presented without employer/date attribution. */
export const selectedWork: Highlight[] = [
  {
    lead: "Multimodal internal chatbot",
    body: "Architected a LangChain / LangGraph / LlamaIndex / Google ADK assistant with RAG and long-term memory that cut cycle time on critical process flows across departments.",
  },
  {
    lead: "Drone-vision inspection pipelines",
    body: "Built computer-vision pipelines detecting structural corrosion, cable-integrity issues, and equipment anomalies from drone video and imagery — feeding digital-twin models for real-time maintenance alerts.",
  },
  {
    lead: "Automated tower-site certification",
    body: "Extracted equipment make/model from close-out photos and mount specs and dimensions from analysis documents and CAD drawings, straight into downstream systems.",
  },
  {
    lead: "Geospatial siting & market modeling",
    body: "Applied ML and geospatial optimization across coverage gaps, lease, cost, and ROI to select optimal tower locations; built a total-addressable-market model for capital allocation and carrier RFP response.",
  },
  {
    lead: "Heterogeneous CPU/GPU training platform",
    body: "Designed CPU/GPU-partitioned architectures and ran a high-availability, multi-tenant, multi-GPU training and inference system for GIS, sensor, image, tabular, and analytics workloads.",
  },
]

export interface FeaturedStat {
  value: string
  label: string
}

export interface FeaturedBullet {
  icon: LucideIcon
  text: string
}

/**
 * Featured-work panel. Content is the flagship shipped system (selectedWork #1);
 * the stat tiles use ONLY numbers that are countable from docs/profile-draft.md:
 *  - 6 = agent frameworks (LangChain, LangGraph, LlamaIndex, Google ADK, CrewAI, MCP)
 *  - 3 = clouds in the value prop (AWS, Azure, Google Cloud)
 *  - 3 = live demos hosted on this site
 */
export const featuredWork = {
  badge: "Flagship system",
  icon: Bot,
  title: "Multimodal internal chatbot",
  description:
    "A document-grounded assistant with RAG and long-term memory, architected end to end and adopted across departments to cut cycle time on critical process flows.",
  bullets: [
    { icon: Boxes, text: "LangChain / LangGraph / LlamaIndex / Google ADK orchestration" },
    { icon: Database, text: "RAG over internal documents with long-term memory" },
    { icon: ScanSearch, text: "Multimodal inputs — text, documents, and imagery" },
  ] as FeaturedBullet[],
  stats: [
    { value: "6", label: "Agent frameworks" },
    { value: "3", label: "Clouds shipped on" },
    { value: "3", label: "Live demos on this site" },
  ] as FeaturedStat[],
} as const

/* ───────────────────────── Projects ───────────────────────── */

export interface Project {
  icon: LucideIcon
  title: string
  status: string
  description: string
  chips: string[]
  href: string
  ctaLabel: string
}

/**
 * Wide intro panel: this site itself, described as a working project. Facts come
 * from the draft and the repo (Next.js + FastAPI, a document-grounded RAG chat
 * agent that answers only from profile docs). The CTA opens the floating chat
 * widget (there is no in-page chat section).
 */
export const platformProject = {
  icon: Sparkles,
  badge: "You're using it now",
  title: "This site & its AI assistant",
  description:
    "A live profile platform with a document-grounded chat agent that answers only from my resume and project docs — retrieval, streaming, and guardrails included.",
  bullets: [
    { icon: MessageSquare, text: "Streaming RAG assistant grounded in profile documents" },
    { icon: Server, text: "Next.js 15 frontend over a FastAPI backend" },
    { icon: Database, text: "Answers only from source docs; declines out-of-scope questions" },
  ] as FeaturedBullet[],
  chips: ["Next.js 15", "FastAPI", "OpenAI", "RAG"],
  ctaLabel: "Try the assistant",
} as const

/** Three live demos hosted on this site. */
export const projects: Project[] = [
  {
    icon: FileText,
    title: "Data Extraction",
    status: "Live demo",
    description:
      "Turn messy PDFs, invoices, receipts, and scanned forms into clean structured data — instantly and at scale.",
    chips: ["FastAPI", "OpenAI"],
    href: "/extractor",
    ctaLabel: "Open demo",
  },
  {
    icon: Search,
    title: "Course Search",
    status: "Live demo",
    description:
      "AI-assisted course search — filter by category, mode, level, price, and college rating.",
    chips: ["Next.js", "FastAPI"],
    href: "/solutions/course-search",
    ctaLabel: "Open demo",
  },
  {
    icon: ClipboardCheck,
    title: "ATS Resume Matcher",
    status: "Live demo",
    description:
      "Match a resume to any job description and get an ATS compatibility score with actionable feedback.",
    chips: ["FastAPI", "OpenAI"],
    href: "/solutions/ats-resume-matcher",
    ctaLabel: "Open demo",
  },
]

/* ───────────────────── Sharing / social proof ───────────────────── */

/**
 * Posts / talks. No approved content → EMPTY array renders two dashed
 * placeholder cards. Adding items later is a data change only.
 */
export const socialPosts: { title: string; source: string; href: string }[] = []
export const sharing = {
  placeholderCount: 2,
  placeholder: "Posts and talks — coming soon",
} as const

/* ───────────────── Education & certifications ───────────────── */

export interface EducationItem {
  /** Year is [NEEDS INPUT] → null renders a muted blank-year chip. */
  year: string | null
  institution: string
  degree: string
}

export const education: EducationItem[] = [
  {
    year: null,
    institution: "Stevens Institute of Technology",
    degree: "MS in Data Science (Applied Artificial Intelligence)",
  },
]

export interface Certification {
  /** Year is [NEEDS INPUT] → null renders a muted blank-year chip. */
  year: string | null
  title: string
  issuer: string
}

export const certifications: Certification[] = [
  {
    year: null,
    title: "AWS Certified Machine Learning",
    issuer: "Amazon Web Services",
  },
  {
    year: null,
    title: "Azure Data Scientist Associate",
    issuer: "Microsoft",
  },
  {
    year: null,
    title: "TensorFlow Developer Certificate",
    issuer: "Google",
  },
]

export const learning = {
  educationLabel: "Education",
  educationIcon: GraduationCap,
  certificationsLabel: "Certifications",
  certificationsIcon: Award,
  blankYearLabel: "Year TBC",
} as const

/* ─────────────────────────── Skills ─────────────────────────── */

export interface SkillGroup {
  icon: LucideIcon
  title: string
  items: string[]
}

export const skillGroups: SkillGroup[] = [
  {
    icon: Bot,
    title: "GenAI & Agentic Systems",
    items: [
      "RAG pipelines & vector search",
      "Pinecone",
      "Chroma",
      "Milvus",
      "OpenSearch",
      "pgvector",
      "LangChain",
      "LangGraph",
      "LlamaIndex",
      "Google ADK",
      "CrewAI",
      "MCP",
      "Function / tool calling",
      "Structured output",
      "Prompt engineering",
      "LLM evaluation (golden sets, LLM-as-judge)",
    ],
  },
  {
    icon: Cpu,
    title: "LLM Platforms & Models",
    items: [
      "Azure OpenAI",
      "AWS Bedrock & SageMaker",
      "Vertex AI",
      "Hugging Face",
      "Groq",
      "Ollama",
      "Modal",
      "OpenAI GPT",
      "Anthropic Claude",
      "Gemini",
      "LLaMA",
      "DeepSeek",
      "Mistral",
      "Qwen",
      "PEFT / LoRA / QLoRA",
      "Quantization",
      "LiteLLM / RouteLLM",
    ],
  },
  {
    icon: Eye,
    title: "Machine Learning & Computer Vision",
    items: [
      "PyTorch",
      "PyTorch Lightning",
      "TensorFlow",
      "Keras",
      "scikit-learn",
      "Transformers (BERT, ViT, SWIN)",
      "CNN / RNN / LSTM",
      "XGBoost",
      "Object detection",
      "Image / video analysis",
      "Time series & forecasting",
      "Geospatial (GIS) analytics",
    ],
  },
  {
    icon: Server,
    title: "Backend & Data Engineering",
    items: [
      "Python",
      "FastAPI",
      "Pydantic",
      "REST APIs",
      "Kafka",
      "PostgreSQL",
      "Oracle",
      "DynamoDB",
      "Redshift",
      "OpenSearch",
      "Apache Spark",
      "Databricks",
      "Airflow",
      "Pandas / NumPy",
      "TypeScript",
      "React",
      "Angular",
    ],
  },
  {
    icon: Rocket,
    title: "Cloud & MLOps",
    items: [
      "AWS (EC2, S3, ECS, SageMaker, EMR, Kinesis)",
      "Azure multi-cloud",
      "Docker",
      "GitHub CI/CD",
      "Harness",
      "MLflow",
      "Weights & Biases",
      "Comet ML",
      "Datadog",
      "Versioning & retraining",
      "Drift monitoring",
    ],
  },
]

/* ──────────────────── Floating chat widget ──────────────────── */

export interface ChatStarter {
  /** Short chip label shown in the widget. */
  label: string
  /** The full question prefilled into the input when the chip is clicked. */
  question: string
  icon: LucideIcon
}

/**
 * Copy for the floating chat widget — the ONLY chat surface on the page. There
 * is no in-page chat section. All wording is ours, derived from the draft's chat
 * section (and its contact facts); the messenger format is structure only.
 */
export const chatWidget = {
  /** Launcher button aria labels (toggles between the two states). */
  launcherOpenLabel: "Open AI assistant",
  launcherCloseLabel: "Close AI assistant",
  /** Header row. */
  name: "Pradeep's AI Assistant",
  tagline: "Ask me about my experience",
  statusLabel: "Online",
  /** Assistant greeting bubble shown when the panel opens empty. */
  greeting:
    "Hi! I'm Pradeep's AI assistant. Ask me about his skills, projects, and services — I answer from his actual resume and project docs.",
  inputPlaceholder: "Type your question…",
  sendLabel: "Send message",
  /** Small disclosure under the input. */
  disclaimer:
    "AI-generated from Pradeep's docs. For timelines or pricing, email him directly.",
  /** Starter chips — includes a Contact chip. Clicking prefills the input. */
  starters: [
    { label: "What can you build?", question: "What can you build?", icon: Sparkles },
    { label: "Relevant projects", question: "Show me relevant projects", icon: FolderGit2 },
    { label: "How do we start?", question: "How do we start a project?", icon: Rocket },
    { label: "Contact", question: "How can I get in touch with Pradeep?", icon: Mail },
  ] as ChatStarter[],
} as const

/* ────────────────────────── Contact ────────────────────────── */

export const contactBand = {
  emailCta: "Email me",
  linkedinCta: "LinkedIn",
  // GitHub CTA: [NEEDS INPUT] — omitted until a URL is provided.
} as const

/* ────────────────────────── Footer ────────────────────────── */

export const footer = {
  tagline: "Generative AI · Multi-agent systems · MLOps",
} as const
