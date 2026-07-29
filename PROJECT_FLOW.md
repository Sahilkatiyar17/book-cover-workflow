# Book Cover Creator
## Project Guide

---

# Overview

The Book Cover Creator is an AI-powered workflow that helps users generate professional-looking book covers from a simple text description.

Instead of directly asking an AI to create an image, the system first gathers visual inspiration from real-world images, lets the user choose what they like, understands those images using AI, combines everything into a refined prompt, and finally generates an original book cover.

The goal of this workflow is to improve the quality of generated book covers by using reference images and human feedback before image generation.

---

# High-Level Workflow

The project follows a sequential workflow where every stage performs exactly one task.

```
User Prompt
      │
      ▼
Search Reference Images
      │
      ▼
Download Images
      │
      ▼
Rank Images
      │
      ▼
User Selects Images
      │
      ▼
Image Understanding
      │
      ▼
Prompt Summarization
      │
      ▼
Book Cover Generation
      │
      ▼
Generated Cover
```

Every stage updates a shared state object.

Instead of passing dozens of variables between functions, the project stores all intermediate information inside one shared dictionary called the **LangGraph State**.

Each node simply reads the information it needs, performs its task, writes its output back into the state, and passes it to the next node.

---

# Project Structure

```
app/
│
├── graph/
│   ├── builder.py
│   ├── nodes.py
│
├── services/
│   ├── image_search.py
│   ├── ranking.py
│   ├── image_understanding.py
│   ├── summarization.py
│   ├── generation.py
│
├── db/
│   ├── checkpointer.py
│
├── utils/
│   ├── config.py
│   ├── constants.py
│   ├── logger.py
│   ├── exception.py
│
frontend/
│
storage/
│
logs/
│
.env
```

Each folder has a specific responsibility.

---

# Folder Explanation

## app/

Contains the complete backend logic of the application.

Everything related to searching, ranking, AI models, graph execution, utilities, and configuration lives here.

---

## graph/

This is the heart of the workflow.

Instead of calling every function manually, LangGraph controls the execution order.

It decides

- what runs first
- what runs next
- when the workflow should pause
- when it should resume
- what information should be shared

### builder.py

Creates the complete workflow.

Think of this as drawing a flowchart.

Example

```
Search

↓

Ranking

↓

Pause for User

↓

Caption Images

↓

Summarize

↓

Generate
```

builder.py connects all those pieces together.

---

### nodes.py

Contains the actual nodes used by LangGraph.

Each node performs exactly one job.

Examples

- Search node
- Ranking node
- Pause node
- Summarization node
- Generation node

Each node receives

```
State

↓

Process

↓

Updated State
```

---

# services/

Every AI model or external API is isolated inside this folder.

This makes the project modular.

If one provider changes, only one file needs to be modified.

---

## image_search.py

Responsible for finding reference images.

Current providers include

- Unsplash
- Pexels
- SerpAPI (Google Images)

Each provider follows the same interface.

```
User Prompt

↓

Search Provider

↓

Image URLs

↓

Downloaded Images
```

This design allows new providers to be added without changing the rest of the application.

---

## ranking.py

After downloading images, not every result is useful.

This service uses CLIP to compare

```
User Prompt

with

Each Image
```

The similarity score determines how closely the image matches the prompt.

The images are then sorted from best to worst.

This step runs locally and does not require an external API.

---

## image_understanding.py

Once the user chooses reference images, this service asks an AI vision model to describe them.

Instead of simply saying

> "Knight"

the model produces rich descriptions like

> "A lone knight wearing weathered silver armor stands before a ruined castle beneath a crimson moon. Dramatic lighting and deep shadows create a dark fantasy atmosphere."

These descriptions become part of the final generation prompt.

---

## summarization.py

This stage combines

- Original prompt
- AI image descriptions
- User feedback

into one clean instruction.

Instead of passing many paragraphs into the generation model,

everything is condensed into one optimized prompt.

---

## generation.py

This is the final stage.

The summarized prompt is sent to an image generation model.

Current implementation supports

- Hugging Face FLUX
- Google Gemini (prepared)
- NVIDIA (under development)

Only one provider is active at a time.

---

# utils/

Contains reusable components used throughout the project.

---

## config.py

Responsible for reading environment variables.

Instead of writing

```python
os.environ["API_KEY"]
```

throughout the project,

every module simply calls

```python
get_settings()
```

Advantages

- Centralized configuration
- Automatic type validation
- Cleaner code
- Easier deployment

---

## constants.py

Contains all configurable values.

Examples

- Number of images
- Delay between API calls
- Model names
- Directory paths

Changing constants here automatically affects the entire project.

---

## logger.py

Creates a centralized logging system.

Instead of printing messages,

the project records

- Information
- Warnings
- Errors

along with timestamps.

Logs are stored inside

```
logs/
```

which makes debugging much easier.

---

## exception.py

Provides custom exceptions.

Instead of displaying only

```
KeyError
```

or

```
TypeError
```

the project reports

- File name
- Line number
- Original error

This greatly simplifies debugging.

---

# frontend/

Contains the Streamlit application.

The frontend allows users to

- Enter prompts
- View ranked images
- Select reference images
- Upload their own image
- Provide feedback
- Generate book covers

The frontend does not perform AI tasks.

It only communicates with the backend workflow.

---

# storage/

Stores temporary project data.

Examples

- Downloaded images
- Generated covers
- Workflow checkpoints

---

# logs/

Stores log files created during execution.

Every application run creates a new log.

This helps identify errors without reading terminal output.

---

# The Shared State

Instead of creating many variables,

the workflow stores everything inside one dictionary.

Example

```python
{
    "prompt": "...",
    "image_results": [...],
    "ranked_images": [...],
    "selected_images": [...],
    "image_descriptions": {...},
    "feedback": [...],
    "summarized_prompt": "...",
    "generated_image": "..."
}
```

Every node updates only the part it owns.

---

# Provider Architecture

Every external service follows the same design.

```
Provider

↓

Receive Request

↓

Call External API

↓

Return Standard Output
```

For example,

Image Search providers all return

```
{
    url,
    source,
    metadata
}
```

regardless of whether they come from

- Unsplash
- Pexels
- Google Images

This keeps the rest of the project independent of specific providers.

---

# Error Handling

Every service uses

```
try

↓

except

↓

AgentException
```

Unexpected failures are logged with

- file name
- line number
- original message

rather than causing silent crashes.

---

# Logging

The application records

- Information logs
- Warning logs
- Error logs

Example

```
Image downloaded

↓

Image ranked

↓

Prompt summarized

↓

Generation complete
```

Every log entry contains

- timestamp
- module name
- log level

making debugging much easier.

---

# Workflow Checkpointing

Long AI workflows may fail because of

- API limits
- Internet interruptions
- Application crashes

Instead of restarting everything,

the project saves progress after each stage.

If interrupted,

execution resumes from the last completed node.

This greatly improves reliability.

---

# APIs Used

| Purpose | Provider |
|----------|----------|
| Image Search | Unsplash |
| Image Search | Pexels |
| Image Search | Google Images (SerpAPI) |
| Vision Model | Groq (Qwen) |
| Summarization | Groq (Llama) |
| Image Generation | Hugging Face FLUX |
| Future Support | Google Gemini |
| Future Support | NVIDIA |

---

# Environment Variables

All API keys are stored inside

```
.env
```

No API keys are hardcoded into the project.

This improves security and simplifies deployment.

---

# Running the Project

Install dependencies

```
pip install -r requirements.txt
```

Configure

```
.env
```

with all required API keys.

Run

```
streamlit run frontend/streamlit_app.py
```

The browser interface opens automatically.

---

# Current Features

- Multi-provider image search
- CLIP-based image ranking
- AI image understanding
- User feedback integration
- Prompt summarization
- AI image generation
- Logging
- Error handling
- Workflow checkpointing
- Provider-based architecture

---

# Future Improvements

Possible future enhancements include

- Multiple image generation models running simultaneously
- Automatic prompt optimization
- Style presets
- Character consistency across multiple covers
- Fine-tuned image ranking
- Cloud deployment
- Team collaboration
- User accounts
- Generation history
- Image editing after generation

---

# Conclusion

The Book Cover Creator is designed as a modular AI workflow rather than a single AI model.

Every stage performs one responsibility, making the project easier to understand, debug, extend, and maintain.

Because every service is isolated behind providers and coordinated using LangGraph, new AI models and external services can be integrated with minimal changes to the overall architecture.