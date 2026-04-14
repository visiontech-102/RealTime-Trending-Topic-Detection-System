# Real-Time-Trending-Topic-Detection-System
This project presents the design and implementation of a real-time trending topic detection system that analyzes Twitter (X) data in both English and Somali languages. The system aims to identify, track, and visualize emerging topics as they occur, enabling timely insights into social media discussions.

## System Architecture

Based on the thesis methodology and modular pipeline design, the system comprises 7 integrated layers connecting the Twitter streaming API down to the user-facing visual dashboard:

1. **Data Source Layer (Twitter / X API)**
   - **Concept:** The primary external interface from which streaming multilingual tweets are gathered.
   - **System Mapping:** `services/twitter_stream.py` handles API connection and stream reading logic.

2. **Data Ingestion Layer**
   - **Concept:** Collects live textual data and forwards it continuously to the backend pipelines without blocking execution.
   - **System Mapping:** Handled concurrently via `services/twitter_stream.py` listeners and the automated application background loops initialized in `app/main.py`.

3. **Preprocessing Layer**
   - **Concept:** An essential pipeline segment that cleans raw tweets (e.g., stripping URLs, user mentions, emojis) to reduce statistical noise.
   - **System Mapping:** Handled just before document vectorization to optimize embeddings in `services/ai_engine.py`.

4. **Feature Representation Layer**
   - **Concept:** Transforms the cleaned tweets into structural dense numerical embeddings enabling the machine to understand semantic proximity.
   - **System Mapping:** Handled by the sophisticated transformer model (`paraphrase-multilingual-MiniLM-L12-v2`) integrated into `services/ai_engine.py`.

5. **Topic Modeling Formatter & Trend Detection Layer**
   - **Concept:** The principal AI engine employing unsupervised clustering algorithms to aggregate related vectors and calculate trending scores.
   - **System Mapping:** Driven by `BERTopic` via the core `process_batch()` loop found within `services/ai_engine.py`.

6. **Storage Layer (Database)**
   - **Concept:** Persists massive volumes of raw tweets securely, while indexing derived insights and trends for hyper-fast frontend queries.
   - **System Mapping:** Monitored by `database/connection.py` utilizing MongoDB as the unified source of truth.

7. **Presentation Layer (User Interface / Dashboard)**
   - **Concept:** Unveils analytical AI results via engaging visual summaries, charts, and data tables.
   - **System Mapping:** Exposed by APIs in `app/routes.py` and visibly rendered by the React application located throughout the `ui/` directory.

## Core Features & Views

- **Bilingual Interface**: Seamlessly toggle between English and Somali functionality across the entire application utilizing a robust React Context `(EN/SO)`.
- **Adaptive Theme Engine**: Built correctly with Dark Mode and Light Mode states, automatically adjusting all typography and data visualizations.
- **Dashboard (Live Data)**: Dynamic tracking of topics with momentum metrics, volume indicators, and responsive Date Range Filters (24h, 7d, 30d).
- **Comparison Engine**: Cross-Lingual Resonance layout comparing Global (English) topics vs. Regional (Somali) topics, visualized using interactive SVG sparklines.
- **Export Repository**: Robust File generation features supporting complete CSV data downloading and PDF Report printing.
- **User Profile & Authentications**: Secure authentication flows and a dedicated user profile page for overriding system environmental configurations.

## Folder Structure

```text
/project
├── .env.example             # Environment variable templates
├── requirements.txt         # Backend Python dependencies
├── app/
│   ├── main.py              # FastAPI application initialization & loop starter
│   └── routes.py            # API routing logic for Auth and Trends
├── database/
│   └── connection.py        # MongoDB Motor async setup
├── extra/                   # Research documentation, UI/UX designs, and thesis files
├── models/
│   └── schemas.py           # Pydantic data validation schemas
├── services/
│   ├── auth.py              # JWT and password hashing logic
│   ├── ai_engine.py         # BERTopic AI clustering service
│   └── twitter_stream.py    # Tweepy streaming service (with mocks)
└── ui/
    ├── package.json         # React project dependencies (inc. react-router-dom, lucide-react)
    ├── package-lock.json    # Exact dependency tree snapshots guaranteeing deterministic builds
    ├── vite.config.js       # Vite app bundler config
    ├── tailwind.config.js   # Precise design system for dark/light utilities
    └── src/
        ├── App.jsx          # React Router definition assigning pages and Context Providers
        ├── main.jsx         # React DOM bootstrapper wrapping Browser Router
        ├── index.css        # Tailwind and custom Vision Tech utility rules
        ├── components/      # Reusable Layouts, Date Filters, and Navigational Headers
        ├── contexts/        # Centralized State Management (Theme, Language, DateRange)
        ├── services/        # Axios API wrapper connection details
        └── pages/           # Dedicated application views (Dashboard, Comparison, Profile, Export, etc.)
```

## Setup Instructions & How to Run Separately

Since this is a full-stack application, the Backend (Python) and the Frontend (React) must be run at the same time in **two separate terminal windows**.

### Prerequisites
- Python 3.9+
- Node.js & npm (Required for the Vite build step and installing frontend packages)
- MongoDB instance (local server at `mongodb://localhost:27017` or Atlas URI)

### 1. Terminal 1: Run the Backend (API & AI Engine)

1. Open a new terminal and navigate to your project folder:
```bash
cd "d:\GRADUATE PROJECT 2026\FYP"

python -m venv venv

venv\Scripts\activate
```
2. Ensure your `.env` file is ready with your `TWITTER_BEARER_TOKEN` (if using real data).
   - **Tip:** You can set a limit on how many texts to fetch per run by adding `MAX_TWEETS_PER_RUN=1000` to your `.env` file to protect your API limits!
3. Install Python dependencies if not done yet:
```bash
pip install -r requirements.txt
```
4. Run the FastAPI development server:
```bash
uvicorn app.main:app --reload
```
> Let this terminal run in the background. It will process the live data from Twitter.

### 2. Terminal 2: Run the Frontend (UI Dashboard)

1. Open a **second, new terminal** window.
2. Navigate to the `ui/` directory from the root:
```bash
cd ui
```
3. Install the necessary NPM dependencies (React, Vite, Recharts, React Router Dom, Tailwind):
```bash
npm install
```
4. Run the React development server:
```bash
npm run dev
```
> Open the local address provided (usually `http://localhost:5173`) in your browser to view the system!

## Running Without Twitter API Keys
If you lack active Twitter API v2 Streaming tokens in your `.env` file, the backend natively bootstraps a **Mock Streaming Engine**. It perfectly simulates incoming multilingual texts allowing your Dashboard UI to come alive entirely automatically for defense presentations or staging demonstrations.
