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
 * Single source of truth for all copy on the profile homepage.
 * Derived strictly from docs/profile-draft.md — nothing here is invented.
 * Items marked [NEEDS INPUT] in the draft are omitted, not stubbed.
 * When this file changes, keep backend/app/profile_agent/docs/ in sync.
 */

export const profile = {
  name: "Pradeep Sahu",
  title: "AI Engineer — Generative AI & Multi-Agent Systems",
  eyebrow: "Generative AI · Multi-Agent Systems",
  valueProposition:
    "I design and ship production Generative AI systems — RAG chatbots, multi-agent workflows, document & vision intelligence — end-to-end on AWS, Azure, and Google Cloud.",
  supportingLine:
    "From prompt to production: fine-tuning, evaluation, MLOps, and the APIs and frontends around them. This site itself is a working demo.",
  email: "sahupra1357@gmail.com",
  linkedin: "https://www.linkedin.com/in/pradeep-sahu-074b92b/",
  // GitHub URL: [NEEDS INPUT] — omitted until provided.
  // Availability badge & headshot: [NEEDS INPUT] — omitted.
} as const

export interface Credential {
  icon: LucideIcon
  label: string
}

export const credentials: Credential[] = [
  {
    icon: GraduationCap,
    label:
      "MS in Data Science (Applied Artificial Intelligence) — Stevens Institute of Technology",
  },
  { icon: Award, label: "AWS Certified Machine Learning" },
  { icon: Award, label: "Microsoft Certified: Azure Data Scientist Associate" },
  { icon: Award, label: "Google TensorFlow Developer Certificate" },
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

export interface Service {
  icon: LucideIcon
  title: string
  description: string
  /** Question pre-filled into the chat when "Discuss this project" is clicked. */
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

export interface Highlight {
  text: string
}

/**
 * Experience highlights from the resume, presented without employer/date
 * attribution (the resume has none — [NEEDS INPUT] to add later).
 */
export const highlights: Highlight[] = [
  {
    text: "Architected a multimodal internal chatbot (LangChain/LangGraph/LlamaIndex/Google ADK) with RAG + long-term memory that cut cycle time on critical process flows across departments.",
  },
  {
    text: "Built computer-vision pipelines for drone video/imagery detecting structural corrosion, cable integrity issues, and equipment anomalies — feeding digital-twin models for real-time maintenance alerts.",
  },
  {
    text: "Automated tower-site certification: extracted equipment make/model from close-out photos and mount specs/dimensions from analysis documents and CAD drawings directly into downstream systems.",
  },
  {
    text: "Applied ML + geospatial optimization (coverage gaps, lease, cost, ROI) to select optimal tower locations; built a total-addressable-market model for capital allocation and carrier RFP response.",
  },
  {
    text: "Designed heterogeneous CPU/GPU architectures and maintained a high-availability, multi-tenant, multi-GPU training & inference system for GIS, sensor, image, tabular, and analytics workloads.",
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

export const chatSection = {
  heading: "Ask anything about my experience",
  sub: "This assistant answers from my actual resume and project docs — try it.",
  starters: [
    "What can you build?",
    "Show me relevant projects",
    "How do we start a project?",
  ],
} as const

export const contactBand = {
  heading: "Have a project in mind?",
  sub: "Tell me what you're building — or ask the assistant first. I read every message.",
} as const
