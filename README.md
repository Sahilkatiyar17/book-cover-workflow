# Book Cover Workflow

### An agentic pipeline that turns a text prompt into a print-ready book cover, with a human-in-the-loop selection step in the middle

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agent%20Orchestration-1C3C3C?style=flat)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/Groq-LLM%20%2B%20Vision-F55036?style=flat)](https://groq.com)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-FLUX.1--schnell-FFD21E?style=flat)](https://huggingface.co)
[![Streamlit](https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)

[Why this project](#why-this-project) · [Architecture](#architecture) · [Pipeline nodes](#pipeline-nodes) · [Project structure](#project-structure) · [Setup](#setup--configuration) · [Usage](#how-to-use-it) · [API keys](#apis--keys-needed) · [Tuning](#tuning-cost-vs-quality) · [Deployment](#is-this-production-ready) · [Tech stack](#tech-stack)

---

## Why this project

[#why-this-project](#why-this-project)

Most "AI book cover generator" demos are a single text-to-image call — type a prompt, get an image, hope it looks right. This project treats it as a proper design workflow instead:

1. Search the web for reference images that match the brief
2. Rank them by actual relevance using CLIP, not just keyword matching
3. Let a human pick favorites and say *why* they like them
4. Turn that selection + feedback into a rich, unified prompt
5. Generate the final cover from that refined prompt

The interesting engineering problem isn't "call an image model" — it's the middle part: pausing a running agent graph mid-execution to wait for a real person, then resuming it later with their input, without losing any state.

---

## Architecture

[#architecture](#architecture)

```
                User Prompt (+ dimension preset)
                          │
                          ▼
        1. Image Search Node
   (Unsplash + Pexels + SerpAPI → download locally)
                          │
                          ▼
        2. Ranking Node
   (Local CLIP model: cosine similarity, prompt vs. image)
                          │
                          ▼
        3. Selection Node  ◄── Human-in-the-Loop interrupt()
   (Graph pauses. User picks ≤5 images, adds feedback,
    or uploads their own reference image)
                          │
                     [ Resumed ]
                          ▼
        4. Branch Router
   (no_feedback / text_feedback / image_upload / both)
                          │
                          ▼
        5. Image Understanding Node
   (Groq Vision-Language model captions selected images)
                          │
                          ▼
        6. Summarization Node
   (Groq LLM merges prompt + captions + feedback
    into one condensed generation prompt)
                          │
                          ▼
        7. Generation Node
   (Hugging Face FLUX.1-schnell renders the final cover)
                          │
                          ▼
              Final Book Cover + Metadata
```

State flows through a single shared `GraphState` object (LangGraph), and every node reads a slice of it and returns a partial update. A SQLite-backed checkpointer persists this state at every step, so the interrupt in step 3 is a real pause — not a blocking wait — and the graph can be resumed hours later from a completely different process.

---

## Pipeline nodes

[#pipeline-nodes](#pipeline-nodes)

| # | Node | Class | Reads | Writes | What it does |
|---|------|-------|-------|--------|---------------|
| 1 | `image_search` | `ImageSearchNode` | `prompt` | `search_results` | Queries Unsplash, Pexels, and SerpAPI in parallel, downloads results locally, hash-named to avoid re-downloading duplicates |
| 2 | `ranking` | `RankingNode` | `prompt`, `search_results` | `ranked_results` | Embeds the prompt and every image with CLIP (`openai/clip-vit-base-patch32`), scores by cosine similarity, caches embeddings to disk |
| 3 | `selection` | `SelectionNode` | `ranked_results` | `selected_images`, `feedback`, `user_uploaded_image` | Interrupts the graph and hands control back to the UI until the user responds |
| 4 | *(router)* | `BranchRouter` | resumed state | routes to `understanding` | Classifies the response as no-feedback / text / image-upload / both |
| 5 | `understanding` | `ImageUnderstandingNode` | `selected_images`, `user_uploaded_image` | `image_descriptions` | Groq Vision model writes detailed style/composition captions for each selected image |
| 6 | `summarization` | `SummarizationNode` | `prompt`, `image_descriptions`, `feedback` | `summarized_prompt` | Groq LLM (Llama 3.3 70B) compresses prompt + captions + feedback into one coherent generation prompt |
| 7 | `generation` | `GenerationNode` | `summarized_prompt`, reference images | `generated_cover_path` | Sends the final prompt to FLUX.1-schnell (or Gemini/NVIDIA, if enabled) and saves the rendered cover |

Every node is a plain Python class with a `__call__(self, state: dict) -> dict` method — that's the entire contract LangGraph needs to treat it as a graph node, no framework-specific base class required.

---

## Project structure

[#project-structure](#project-structure)

```
book-cover-workflow/
├── app/
│   ├── db/
│   │   └── checkpointer.py         # SQLite checkpointer for LangGraph thread state
│   ├── graph/
│   │   ├── builder.py              # StateGraph assembly + run/resume lifecycle
│   │   ├── edges.py                # BranchRouter — conditional routing after selection
│   │   ├── nodes.py                # SelectionNode (human-in-the-loop interrupt)
│   │   └── state.py                # GraphState, ImageResult, UserFeedback type defs
│   ├── services/
│   │   ├── image_search.py         # Unsplash / Pexels / SerpAPI / Pixabay / Pinterest clients
│   │   ├── ranking.py              # CLIP embeddings + cosine-similarity ranking
│   │   ├── image_understanding.py  # Groq Vision captioning
│   │   ├── summarization.py        # Groq text summarization
│   │   └── generation.py           # HuggingFace / Gemini / NVIDIA image generation
│   └── utils/
│       ├── config.py               # Pydantic Settings — typed env vars
│       ├── constants.py            # Tunable defaults (resolutions, model names, limits)
│       ├── exception.py            # AgentException — custom error wrapper
│       ├── logger.py               # Shared logger setup
│       └── tracing.py              # LangSmith tracing hooks
├── frontend/
│   └── streamlit_app.py            # Streamlit UI
├── storage/
│   ├── raw_images/                 # Downloaded + user-uploaded reference images
│   ├── generated_covers/           # Final rendered covers
│   └── checkpoints.db              # LangGraph thread state (auto-cleared on success)
├── requirements.txt
└── setup.py
```

---

## Setup & configuration

[#setup--configuration](#setup--configuration)

```bash
git clone <your-repo-url>
cd book-cover-workflow

conda create -n book-cover python=3.11 -y
conda activate book-cover

pip install -r requirements.txt
pip install -e .
```

Create a `.env` file in the project root:

```bash
# Image search
UNSPLASH_API_KEY=your_unsplash_key
PEXELS_API_KEY=your_pexels_key
SERPAPI_API_KEY=your_serpapi_key
PIXABAY_API_KEY=your_pixabay_key        # optional, disabled by default
APIFY_API_KEY=your_apify_key            # optional, disabled by default

# Understanding + summarization
GROQ_API_KEY=your_groq_key

# Generation
HUGGINGFACE_API_KEY=your_hf_token
GEMINI_API_KEY=your_gemini_key          # optional, disabled by default
NVIDIA_API_KEY=your_nvidia_key          # optional, experimental

# Observability (optional)
LANGSMITH_API_KEY=your_langsmith_key
```

Run it:

```bash
streamlit run frontend/streamlit_app.py
```

---

## How to use it

[#how-to-use-it](#how-to-use-it)

1. **Describe the cover** — type your prompt (e.g. *"dark fantasy castle at dusk, dragon silhouette, red sky"*) and pick a print dimension preset. Click **Search images**.
2. **Pick favorites** — the graph pauses once ranked results come back. Check up to 5 images, add short notes per image (*"like the lighting on this one"*), and optionally drag in your own reference image. Click **Generate cover**.
3. **Get your cover** — the graph resumes, captions your selections, merges everything into one prompt, and renders the final cover. Expand the debug panels to see the exact prompt and captions that were used.

---

## APIs & keys needed

[#apis--keys-needed](#apis--keys-needed)

| Node | Service | Env var | Status |
|------|---------|---------|--------|
| `image_search` | Unsplash | `UNSPLASH_API_KEY` | active |
| `image_search` | Pexels | `PEXELS_API_KEY` | active |
| `image_search` | SerpAPI | `SERPAPI_API_KEY` | active — 250 searches/month free tier |
| `image_search` | Pixabay | `PIXABAY_API_KEY` | built, disabled (CDN rate-limits aggressively) |
| `image_search` | Apify (Pinterest) | `APIFY_API_KEY` | built, disabled (unofficial scraper, ToS risk) |
| `ranking` | CLIP (`openai/clip-vit-base-patch32`) | — | runs locally, no API key |
| `understanding` | Groq Vision (`qwen/qwen3.6-27b`) | `GROQ_API_KEY` | active |
| `summarization` | Groq text (`llama-3.3-70b-versatile`) | `GROQ_API_KEY` | same key as above |
| `generation` | Hugging Face (`FLUX.1-schnell`) | `HUGGINGFACE_API_KEY` | active, default generator |
| `generation` | Gemini (`gemini-2.5-flash-image`) | `GEMINI_API_KEY` | built, disabled (requires GCP billing) |
| `generation` | NVIDIA NIM (Qwen-Image-Edit) | `NVIDIA_API_KEY` | built, experimental/unverified |
| tracing | LangSmith | `LANGSMITH_API_KEY` | optional, observability only |

> **Note on SerpAPI vs. Google Custom Search:** SerpAPI was chosen over the raw Google Custom Search API because it returns clean, structured JSON without needing a separate Google Cloud Console setup — faster to wire up when working under a tight timeline.

---

## Tuning cost vs. quality

[#tuning-cost-vs-quality](#tuning-cost-vs-quality)

All of these live in `app/utils/constants.py`:

**To reduce API cost:**
- `ImageUnderstandingConfig.MAX_IMAGES_TO_DESCRIBE` (default `5`) — lower to 2–3 to cut Groq Vision calls, since it's billed per image.
- `ImageUnderstandingConfig.MAX_TOKENS` (default `1500`) — lower to 500–800 to keep captions (and downstream prompt size) shorter.

**To improve output quality:**
- `ImageSearchConfig.DEFAULT_RESULTS_PER_QUERY` (default `10`) — raise to 15–20 for a bigger candidate pool before ranking.
- `GenerationConfig` provider — swap between:
  - **HuggingFaceProvider (FLUX.1-schnell)** — active by default, fast and free, no uptime guarantee.
  - **GeminiProvider** — accepts multiple reference images directly for closer matches to your selections; requires GCP billing to be enabled.
  - **QwenEditProvider (NVIDIA NIM)** — image-to-image editing of a selected reference; experimental.

---

## Is this production-ready?

[#is-this-production-ready](#is-this-production-ready)

No — this is a solid functional prototype, not a deployable service, for four concrete reasons:

1. **CLIP loads into memory per server process.** Concurrent users on one instance will exhaust RAM fast.
2. **SQLite checkpointing doesn't scale horizontally.** Multiple server instances can't share a local `.db` file, so a paused session on one server is invisible to another.
3. **Local file storage for images.** Every search result and generated cover writes to disk — this fills up fast under real traffic.
4. **No user accounts or auth.** There's no login, no per-user history, no rate limiting per user.

The rough scaling path, if this were to go further: shared CLIP inference behind a small API → move storage to S3/GCS → move checkpointing to managed Postgres/Redis → split frontend (React/Next.js) from backend (FastAPI) → move generation to serverless GPU endpoints (Replicate/RunPod) behind a task queue once traffic justifies it.

---

## Tech stack

[#tech-stack](#tech-stack)

| Layer | Choice |
|-------|--------|
| Agent orchestration | LangGraph (with SQLite checkpointing + `interrupt()`) |
| Image search | Unsplash, Pexels, SerpAPI (Pixabay, Pinterest/Apify built but disabled) |
| Ranking | Local CLIP (`openai/clip-vit-base-patch32`) + cosine similarity |
| Vision captioning | Groq (Qwen-VL) |
| Prompt summarization | Groq (Llama 3.3 70B) |
| Image generation | Hugging Face (FLUX.1-schnell), Gemini & NVIDIA NIM as alternates |
| Frontend | Streamlit |
| Persistence | SQLite (checkpoints), local filesystem (images) |
| Tracing | LangSmith (optional) |

---

## What's next

[#whats-next](#whats-next)

- **Query decomposition** for compound prompts — split a multi-concept prompt (e.g. "castle + dragon + moody lighting") into sub-queries before search/ranking, instead of relying on each provider's own fuzzy matching to sort it out.
- **Real-person-name handling** — flag prompts referencing named public figures before they reach search/generation, given likeness and licensing considerations.
- **Migrate checkpointing and storage** to Postgres and object storage as a first step toward the multi-instance deployment path described above.

---

Built as a two-day prototype exploring human-in-the-loop agent workflows with LangGraph — not a production system.