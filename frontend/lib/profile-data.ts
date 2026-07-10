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
  ScanText,
  SlidersHorizontal,
  Workflow,
  type LucideIcon,
} from "lucide-react"

/**
 * Single source of truth for all copy on the profile homepage — including every
 * section heading, subtitle, eyebrow, and stat label. Components render from this
 * file; nothing user-visible is hard-coded in JSX.
 *
 * Derived strictly from docs/profile-draft.md — nothing here is invented. Items
 * marked [NEEDS INPUT] in the draft are omitted, not stubbed. Every proof-tile
 * number is countable from the draft (see comments on `proofTiles`).
 * When this file changes, keep backend/app/profile_agent/docs/ in sync.
 */

export const profile = {
  name: "Pradeep Sahu",
  title: "AI Engineer — Generative AI & Multi-Agent Systems",
  eyebrow: "AI Engineer · Generative AI & Multi-Agent Systems",
  valueProposition:
    "I design and ship production Generative AI systems — RAG chatbots, multi-agent workflows, document and vision intelligence — end-to-end on AWS, Azure, and Google Cloud.",
  supportingLine:
    "From prompt to production: fine-tuning, evaluation, MLOps, and the APIs and frontends around them. This site itself is a working demo.",
  email: "sahupra1357@gmail.com",
  linkedin: "https://www.linkedin.com/in/pradeep-sahu-074b92b/",
  // GitHub URL: [NEEDS INPUT] — omitted until provided.
  // Availability badge & headshot: [NEEDS INPUT] — omitted.
} as const

/** Hero CTAs (labels live here, not in JSX). */
export const heroCtas = {
  primary: "Ask my AI assistant",
  secondary: "Contact",
} as const

export interface Credential {
  icon: LucideIcon
  /** Compact label used in the hero byline row. */
  short: string
  /** Full label for accessibility / tooltip. */
  full: string
}

export const credentials: Credential[] = [
  {
    icon: GraduationCap,
    short: "MS, Data Science (Applied AI)",
    full: "MS in Data Science (Applied Artificial Intelligence) — Stevens Institute of Technology",
  },
  {
    icon: Award,
    short: "AWS ML Certified",
    full: "AWS Certified Machine Learning",
  },
  {
    icon: Award,
    short: "Azure Data Scientist",
    full: "Microsoft Certified: Azure Data Scientist Associate",
  },
  {
    icon: Award,
    short: "TensorFlow Developer",
    full: "Google TensorFlow Developer Certificate",
  },
]

export interface ProofTile {
  value: string
  label: string
}

/**
 * Stat band. Every number is countable from docs/profile-draft.md — no invented
 * metrics:
 *  - 3  = live demos (Data Extraction, Course Search, ATS Resume Matcher)
 *  - 6  = agent frameworks (LangChain, LangGraph, LlamaIndex, Google ADK, CrewAI, MCP)
 *  - 3  = clouds in the value prop (AWS, Azure, Google Cloud)
 *  - 4  = credential lines (1 MS degree + 3 certifications)
 */
export const proofTiles: ProofTile[] = [
  { value: "3", label: "Live AI demos on this site" },
  { value: "6", label: "Agent frameworks in the toolkit" },
  { value: "3", label: "Clouds shipped on" },
  { value: "4", label: "Degree & certifications" },
]

/** Section metadata — indices, nav labels, headings, and subtitles. */
export interface SectionMeta {
  id: string
  index: string
  navLabel: string
  heading: string
  subtitle: string
}

export const sections = {
  services: {
    id: "services",
    index: "01",
    navLabel: "Services",
    heading: "What can I build for you?",
    subtitle:
      "Four ways I plug into a team — from a first proof-of-concept to a system running in production.",
  },
  work: {
    id: "work",
    index: "02",
    navLabel: "Track record",
    heading: "What have I actually shipped?",
    subtitle:
      "Selected work from the field — real systems, not slideware. Presented without client names.",
  },
  demos: {
    id: "demos",
    index: "03",
    navLabel: "Live demos",
    heading: "What can you try right now?",
    subtitle:
      "Three working tools hosted on this site. Same stack I'd build yours with.",
  },
  toolbox: {
    id: "toolbox",
    index: "04",
    navLabel: "Toolbox",
    heading: "What's in the toolbox?",
    subtitle:
      "The stack behind the work, grouped by where it fits in a Generative AI system.",
  },
  chat: {
    id: "chat",
    index: "05",
    navLabel: "Ask AI",
    heading: "Ask anything about my experience",
    subtitle:
      "This assistant answers from my actual resume and project docs — try it.",
  },
} satisfies Record<string, SectionMeta>

/** Ordered list the sticky rail iterates for scrollspy + table of contents. */
export const sectionOrder: SectionMeta[] = [
  sections.services,
  sections.work,
  sections.demos,
  sections.toolbox,
  sections.chat,
]

export interface Service {
  icon: LucideIcon
  title: string
  description: string
  /** Question pre-filled into the chat when "Discuss this →" is clicked. */
  prefill: string
}

export const services: Service[] = [
  {
    icon: Sparkles,
    title: "Custom AI agents & chatbots",
    description:
      "Document-grounded assistants, multi-agent workflows, and tool-calling agents with MCP integration to your internal data and systems.",
    prefill: "Can you build a custom AI agent for my business?",
  },
  {
    icon: ScanText,
    title: "Document & image intelligence",
    description:
      "Automated extraction from documents, drawings, and photos: specs, equipment identification, structured data straight into your database.",
    prefill: "Can you automate data extraction from our documents?",
  },
  {
    icon: SlidersHorizontal,
    title: "LLM fine-tuning & optimization",
    description:
      "Fine-tune open or hosted models for your task (PEFT/LoRA/QLoRA), with GPU cost, latency, and throughput engineered in.",
    prefill: "Should I fine-tune a model or use RAG?",
  },
  {
    icon: Workflow,
    title: "Legacy systems → AI-enabled platforms",
    description:
      "Modernize internal apps into scalable FastAPI services with AI-automated workflows and measurable cycle-time reduction.",
    prefill: "Can you modernize our legacy internal tools with AI?",
  },
]

/** "Discuss this →" affordance label for the services list. */
export const serviceCtaLabel = "Discuss this"

export interface Highlight {
  /** Bold lead-in phrase. */
  lead: string
  /** Plain narrative body. */
  body: string
}

/**
 * Experience highlights from the resume, presented without employer/date
 * attribution (the resume has none — [NEEDS INPUT] to add later).
 */
export const highlights: Highlight[] = [
  {
    lead: "Multimodal internal chatbot.",
    body: "Architected a LangChain / LangGraph / LlamaIndex / Google ADK assistant with RAG and long-term memory that cut cycle time on critical process flows across departments.",
  },
  {
    lead: "Drone-vision inspection pipelines.",
    body: "Built computer-vision pipelines detecting structural corrosion, cable-integrity issues, and equipment anomalies from drone video and imagery — feeding digital-twin models for real-time maintenance alerts.",
  },
  {
    lead: "Automated tower-site certification.",
    body: "Extracted equipment make/model from close-out photos and mount specs and dimensions from analysis documents and CAD drawings, straight into downstream systems.",
  },
  {
    lead: "Geospatial siting & market modeling.",
    body: "Applied ML and geospatial optimization across coverage gaps, lease, cost, and ROI to select optimal tower locations; built a total-addressable-market model for capital allocation and carrier RFP response.",
  },
  {
    lead: "Heterogeneous CPU/GPU training platform.",
    body: "Designed CPU/GPU-partitioned architectures and ran a high-availability, multi-tenant, multi-GPU training and inference system for GIS, sensor, image, tabular, and analytics workloads.",
  },
]

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
      "RAG pipelines & vector search (Pinecone, Chroma, Milvus, OpenSearch, pgvector)",
      "Multi-agent frameworks: LangChain, LangGraph, LlamaIndex, Google ADK, CrewAI, MCP",
      "Function/tool calling, structured output & schema-constrained decoding",
      "Prompt engineering: systematic testing, context-window management, few-shot design",
      "LLM evaluation: golden datasets, regression testing, LLM-as-judge",
    ],
  },
  {
    icon: Cpu,
    title: "LLM Platforms & Models",
    items: [
      "Azure OpenAI, AWS Bedrock & SageMaker, Vertex AI, Hugging Face, Groq, Ollama, Modal",
      "OpenAI GPT, Anthropic Claude, Gemini, LLaMA, DeepSeek, Mistral, Qwen",
      "Fine-tuning: PEFT, LoRA, QLoRA, quantization, mixed precision",
      "Inference optimization, GPU sizing & capacity planning, LiteLLM / RouteLLM routing",
    ],
  },
  {
    icon: Eye,
    title: "Machine Learning & Computer Vision",
    items: [
      "PyTorch, PyTorch Lightning, TensorFlow, Keras, scikit-learn",
      "Transformers (BERT, ViT, SWIN), CNN/RNN/LSTM, XGBoost, classical ML",
      "Computer-vision pipelines: object detection, image/video analysis",
      "Time series, forecasting, optimization, geospatial (GIS) analytics",
    ],
  },
  {
    icon: Server,
    title: "Backend & Data Engineering",
    items: [
      "Python, FastAPI, Pydantic, REST APIs, Kafka",
      "PostgreSQL, Oracle, DynamoDB, Redshift, OpenSearch",
      "Apache Spark, Databricks, Airflow, Pandas/NumPy ecosystem",
      "JavaScript/TypeScript, React, Angular; SQL, Java, Rust, shell",
    ],
  },
  {
    icon: Rocket,
    title: "Cloud & MLOps",
    items: [
      "AWS (EC2, S3, ECS, VPC, ALB, SageMaker, EMR, Kinesis), Azure multi-cloud",
      "Docker, GitHub CI/CD, Harness",
      "MLflow, Weights & Biases, Comet ML, Datadog",
      "Model lifecycle: versioning, retraining, drift monitoring, artifact management",
    ],
  },
]

export interface Project {
  icon: LucideIcon
  title: string
  description: string
  builtWith: string
  href: string
}

export const projects: Project[] = [
  {
    icon: FileText,
    title: "Data Extraction",
    description:
      "Turn messy PDFs, invoices, receipts, and scanned forms into clean structured data — instantly and at scale.",
    builtWith: "FastAPI + OpenAI",
    href: "/extractor",
  },
  {
    icon: Search,
    title: "Course Search",
    description:
      "AI-assisted course search — filter by category, mode, level, price, and college rating.",
    builtWith: "Next.js + FastAPI",
    href: "/solutions/course-search",
  },
  {
    icon: ClipboardCheck,
    title: "ATS Resume Matcher",
    description:
      "Match a resume to any job description and get an ATS compatibility score with actionable feedback.",
    builtWith: "FastAPI + OpenAI",
    href: "/solutions/ats-resume-matcher",
  },
]

/** "Live demo →" affordance label for project cards. */
export const projectCtaLabel = "Live demo"
export const projectBuiltWithLabel = "Built with"

export const chatSection = {
  panelTitle: "AI Assistant",
  statusLabel: "Coming soon",
  greeting:
    "Hi! I'm Pradeep's AI assistant. Soon I'll answer your questions about his skills, projects, and services — grounded in his actual resume and project docs. The assistant is being wired up now.",
  inputPlaceholder: "Ask about my experience, projects, or services…",
  disabledNote:
    "Chat is coming soon. In the meantime, reach me directly from the section below.",
  starters: [
    "What can you build?",
    "Show me relevant projects",
    "How do we start a project?",
  ],
} as const

export const contactBand = {
  eyebrow: "Next step",
  heading: "Have a project in mind?",
  sub: "Tell me what you're building — or ask the assistant first. I read every message.",
  emailCta: "Email me",
  linkedinCta: "LinkedIn",
} as const

/** Sticky rail copy. */
export const rail = {
  tocLabel: "On this page",
  ctaLabel: "Ask my AI assistant",
} as const

export const footer = {
  tagline: "Generative AI · Multi-agent systems · MLOps",
} as const
