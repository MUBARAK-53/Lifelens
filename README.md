
# LifeLens AI – Ghost in the Machine

Your memories never disappear. They wait to be remembered.

LifeLens AI is a personal AI memory assistant that helps users
store, search, retrieve, and rediscover meaningful experiences
using natural language and Gemma.

## Features

- AI-powered conversations using Gemma.
- Persistent conversation history.
- Save and manage personal memories.
- Upload photos, receipts, and other experiences.
- Search stored experiences using natural language.
- Retrieve relevant memories with source references.
- AI-powered experience analysis.

## Technology Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Gemma
- Pydantic

## Project Structure

```text
LifeLens/
├── backend/
│   └── app/
│       ├── core/
│       ├── models/
│       ├── routers/
│       ├── schemas/
│       ├── services/
│       ├── database.py
│       └── main.py
├── .gitignore
└── README.md
```

## Current Development Status

The backend currently supports:

- Chat with persistent sessions.
- Memory management.
- Experience uploads and search.
- AI-based experience analysis.
- Retrieval of relevant experiences in chat.
- References to retrieved experience records.

## Getting Started

Clone the repository:

```bash
git clone https://github.com/MUBARAK-53/Lifelens.git
cd Lifelens
```

Create and activate a Python virtual environment, install the
backend requirements, configure your environment variables,
and start the FastAPI application.

API documentation is available at:

`http://127.0.0.1:8000/docs`

## Privacy

Do not commit API keys, database credentials, personal uploads,
or local database files.

## Project

Built as part of the Hacktoberfest 2026 Week 4 challenge.
