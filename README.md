# Search Engine - Distributed Web Search System

A scalable, distributed search engine implementation inspired by Google's architecture, built with Python and modern web technologies.

## 🚀 Features

- **Distributed Web Crawler** - Politeness-aware crawling with robots.txt support
- **Inverted Index System** - Fast text search with TF-IDF scoring
- **PageRank Algorithm** - Link-based authority ranking
- **RESTful Search API** - JSON API with web interface
- **Real-time Indexing** - Continuous content updates
- **Anti-Spam Detection** - Content quality filtering
- **Scalable Architecture** - Microservices with Docker support

## 🏗️ Architecture
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Crawler   │───▶│   Indexer   │───▶│   Ranking   │
└─────────────┘    └─────────────┘    └─────────────┘
│                   │                   │
▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Storage   │◀───│ Search API  │───▶│ Monitoring  │
└─────────────┘    └─────────────┘    └─────────────┘
## 📋 Prerequisites

- Python 3.8+
- Docker & Docker Compose
- Redis Server
- PostgreSQL
- Elasticsearch (optional)

## 🛠️ Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/search-engine.git
cd search-engine
