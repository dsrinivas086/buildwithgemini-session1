# Travel Concierge AI Agent

An intelligent, multi-modal **Travel Concierge** agent built with Google's **Agent Development Kit (ADK 1.1.0)** and powered by **Gemini**. The agent helps travelers discover luxury destinations, book itinerary reservations, check live exchange rates, geocode locations, search nearby points of interest, and generate custom destination photos and video previews.

![Travel Concierge Agent Demo](./demo.gif)

---

## 🌟 Features & Implemented Capabilities

This repository contains a fully functioning travel concierge agent with the following verified tools and Google Cloud services:

* **Long-Term Memory (Vertex AI Memory Bank)**:
  * Automatically extracts and persists user preferences, travel styles, and critical dietary/food allergies across conversations using `VertexAiMemoryBankService`.

* **Database Operations (Google Cloud Firestore)**:
  * `search_destinations`: Keyword and category search over curated luxury travel destinations.
  * `get_destination_details`: Lookup detailed information for specific destinations.
  * `add_destination`: Add new luxury travel recommendations to the database.
  * `book_destination_itinerary`: Confirm and record travel reservations in the `bookings` collection.

* **Multi-Modal Generation & Public Cloud Storage**:
  * `generate_destination_image`: Generates high-resolution destination photos using `gemini-3.1-flash-lite-image` and uploads them to a public Google Cloud Storage bucket.
  * `generate_destination_video`: Generates short cinematic video previews using Google's Omni model (`gemini-omni-flash-preview`) via the Interactions API and uploads them to Cloud Storage.

* **Geospatial & Mapping (Google Maps APIs)**:
  * `geocode_address`: Converts landmark names or street addresses to geographic coordinates using the Google Geocoding API.
  * `find_nearby_places`: Discovers nearby restaurants, hotels, and tourist attractions using the Google Places API (New).

* **Interactive Agent-to-User UI (A2UI)**:
  * Streams dynamic A2UI surface cards (cards, columns, rows, text, and embedded public image URLs) directly into the chat interface for a rich visual experience.

* **Code Execution Sandbox**:
  * Safely executes Python code snippets via `AgentEngineSandboxCodeExecutor` for complex calculations and data processing.

* **Live Exchange Rates & Utility Tools**:
  * `get_exchange_rate`: Fetches real-time currency conversion rates for travel budgeting.
  * `get_weather` & `get_current_time`: Simulated weather lookups and timezone checks.

---

## 🛠️ Architecture Overview

```
               +-----------------------------------+
               |    FastAPI Chat Web Frontend      |
               |      (HTML / Vanilla CSS / JS)    |
               +-----------------+-----------------+
                                 | A2A Protocol
                                 v
               +-----------------+-----------------+
               |       ADK Root Agent (Gemini)     |
               |    - A2UI Surface Callback        |
               |    - Memory Generation Callback   |
               +--------+----------------+---------+
                        |                |
         +--------------+--+          +--+----------------+
         | Google Cloud    |          | External Tools    |
         | - Memory Bank   |          | - Geocoding API   |
         | - Firestore DB  |          | - Places API New  |
         | - Cloud Storage |          | - Exchange Rates  |
         | - Gemini Models |          | - Python Sandbox  |
         +-----------------+          +-------------------+
```

---

## 🚀 Setup & Local Execution

Follow these steps to run the agent locally on your machine.

### Prerequisites
* Python 3.11 or 3.12
* `uv` or `pip` package manager
* Google Cloud Project with Vertex AI, Firestore, and Cloud Storage enabled
* Google Maps API key (with Geocoding and Places API enabled)

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone <your-repository-url>
cd simple-agent

# Install dependencies using uv or pip
uv pip install -r requirements.txt
```

### 2. Environment Configuration

Set your Google Cloud Project ID and Maps API Key:

```bash
export GOOGLE_CLOUD_PROJECT="your-gcp-project-id"
export GOOGLE_MAPS_API_KEY="<YOUR_KEY>"
```

### 3. Run the Agent Locally

Start the local agent server using the ADK CLI:

```bash
# Launch ADK Web interface on port 8080
uv run adk web . --port 8080 --reload_agents
```

### 4. Run the Web Frontend (Optional)

To start the custom FastAPI chat proxy frontend:

```bash
cd frontend

# Install frontend dependencies
pip install -r requirements.txt

# Set local proxy target variables
export AGENT_ENGINE_RESOURCE_NAME="projects/YOUR_PROJECT_ID/locations/us-east1/reasoningEngines/YOUR_ENGINE_ID"
export AGENT_DIRECTORY="app"

# Start FastAPI frontend server
python main.py
```

---

## 📁 Repository Structure

```
.
├── app/
│   ├── agent.py            # Main ADK Root Agent, tools, callbacks, and A2UI instruction
│   ├── a2ui_utils.py       # A2UI event & surface callback helpers
│   ├── fast_api_app.py     # FastAPI server wrapper
│   └── app_utils/          # Utility modules
├── frontend/
│   ├── main.py             # FastAPI proxy backend
│   └── static/
│       └── index.html      # Custom luxury travel concierge chat UI with A2UI renderer
├── agents-cli-manifest.yaml# Manifest for deployment with agents-cli
├── demo.gif                # Recorded demonstration of the agent UI
├── requirements.txt        # Project Python dependencies
└── README.md               # Project documentation
```
