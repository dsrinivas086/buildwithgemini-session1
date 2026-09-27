# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import datetime
import json
import os
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo
from typing import Optional, List, Dict, Any

from google import genai
from google.cloud import storage
from google.cloud import firestore
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog

try:
    from app.a2ui_utils import a2ui_callback
except ImportError:
    from a2ui_utils import a2ui_callback

# Load local environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# CRITICAL: Hardcoded project ID & GCS bucket strings.
# Do NOT use google.auth.default() or GOOGLE_CLOUD_PROJECT env vars on Agent Platform!
PROJECT_ID = "qwiklabs-gcp-02-c3eb38e799e1"
BUCKET_NAME = "travel-concierge-media-qwiklabs-gcp-02-c3eb38e799e1"
MEMORY_BANK_ID = "3343841359462137856"

# Initialize Firestore client with hardcoded project ID string
db = firestore.Client(project=PROJECT_ID)


def _get_agent_engine_resource_name() -> Optional[str]:
    """Helper to read remote_agent_runtime_id from deployment_metadata.json if available."""
    metadata_path = os.path.join(os.path.dirname(__file__), "..", "deployment_metadata.json")
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                data = json.load(f)
                return data.get("remote_agent_runtime_id")
        except Exception:
            pass
    return None


# Initialize AgentEngineSandboxCodeExecutor with resource name from deployment_metadata.json if present
agent_engine_resource_name = _get_agent_engine_resource_name()
code_executor = (
    AgentEngineSandboxCodeExecutor(agent_engine_resource_name=agent_engine_resource_name)
    if agent_engine_resource_name
    else AgentEngineSandboxCodeExecutor()
)


async def generate_memories_callback(callback_context: CallbackContext):
    """Callback to send completed session turns to Vertex AI Memory Bank for long-term fact and allergy extraction."""
    try:
        await callback_context.add_session_to_memory()
    except Exception:
        pass
    return None


def memory_service_builder():
    """Build VertexAiMemoryBankService instance pointing to our deployed Memory Bank for future deployments."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location="us-east1",
        agent_engine_id=MEMORY_BANK_ID,
    )


def generate_destination_image(
    prompt: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Generate a high-quality luxury destination image using Gemini 3.1 Flash Lite Image, save it as an ADK artifact, and upload to public GCS.

    Args:
        prompt: Detailed description of the luxury destination image to generate (e.g., 'A serene sunset view of a luxury villa over the cliffs of Santorini').
        tool_context: ADK ToolContext provided automatically by the agent runtime.

    Returns:
        A dictionary containing the status, prompt, public GCS image URL, and artifact filename.
    """
    try:
        # Generate image using gemini-3.1-flash-lite-image in the global location
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            )
        )

        img_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    img_bytes = part.inline_data.data
                    if part.inline_data.mime_type:
                        mime_type = part.inline_data.mime_type
                    break

        if not img_bytes:
            return {"error": "No image data was generated by the model."}

        # 1. Save with tool_context.save_artifact for Playground Artifacts panel
        filename = f"destination_{uuid.uuid4().hex[:8]}.jpg"
        artifact_part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename, artifact_part)

        # 2. Upload image bytes directly to public Cloud Storage bucket (no local file path)
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob_name = f"generated/{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(img_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

        return {
            "status": "success",
            "prompt": prompt,
            "artifact_filename": filename,
            "public_url": public_url
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload image: {str(e)}"}


def generate_destination_video(
    prompt: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Generate a short video preview for a luxury travel destination using Google Omni model (gemini-omni-flash-preview) in the global region, save it as an ADK artifact, and upload to public GCS.

    Args:
        prompt: Detailed description of the destination video to generate (e.g., 'A 5-second cinematic video of an overwater bungalow in Bora Bora').
        tool_context: ADK ToolContext provided automatically by the agent runtime.

    Returns:
        A dictionary containing status, prompt, public GCS video URL, and artifact filename.
    """
    try:
        # Generate video using gemini-omni-flash-preview in global location via Interactions API
        client = genai.Client(vertexai=True, project=PROJECT_ID, location="global")
        res = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt
        )

        video_bytes = None
        mime_type = "video/mp4"
        if hasattr(res, "output_video") and res.output_video:
            if hasattr(res.output_video, "mime_type") and res.output_video.mime_type:
                mime_type = res.output_video.mime_type
            data_val = getattr(res.output_video, "data", None)
            if isinstance(data_val, bytes):
                video_bytes = data_val
            elif isinstance(data_val, str):
                video_bytes = base64.b64decode(data_val)
        elif hasattr(res, "steps") and res.steps:
            for s in res.steps:
                if hasattr(s, "content"):
                    for c in s.content:
                        if getattr(c, "type", None) == "video" or getattr(c, "mime_type", "").startswith("video/"):
                            if getattr(c, "mime_type", None):
                                mime_type = c.mime_type
                            data_val = getattr(c, "data", None)
                            if isinstance(data_val, str):
                                video_bytes = base64.b64decode(data_val)
                            elif isinstance(data_val, bytes):
                                video_bytes = data_val
                            break

        if not video_bytes:
            return {"error": "No video data was generated by gemini-omni-flash-preview."}

        # 1. Save with tool_context.save_artifact for Playground Artifacts panel
        filename = f"destination_video_{uuid.uuid4().hex[:8]}.mp4"
        artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
        tool_context.save_artifact(filename, artifact_part)

        # 2. Upload video bytes directly to public Cloud Storage bucket (no local file writing)
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob_name = f"generated/{filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"

        return {
            "status": "success",
            "prompt": prompt,
            "artifact_filename": filename,
            "public_url": public_url
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload video: {str(e)}"}


def geocode_address(address: str) -> Dict[str, Any]:
    """Turn a street address or location name into geographic coordinates using Google Geocoding API.

    Args:
        address: Street address, landmark, or location name (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        A dictionary containing formatted address, latitude, longitude, and location details.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"
    
    req = urllib.request.Request(url, headers={"User-Agent": "TravelConciergeAgent/1.0"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "OK" and data.get("results"):
                first_result = data["results"][0]
                loc = first_result["geometry"]["location"]
                return {
                    "status": "success",
                    "formatted_address": first_result.get("formatted_address"),
                    "location": {
                        "latitude": loc.get("lat"),
                        "longitude": loc.get("lng")
                    }
                }
            return {"error": f"Geocoding failed with status: {data.get('status')}"}
    except Exception as e:
        return {"error": f"Failed to call Geocoding API: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "restaurant",
    radius_meters: float = 1000.0
) -> Dict[str, Any]:
    """Find nearby points of interest (restaurants, hotels, tourist attractions) using Google Places API (New).

    Args:
        latitude: Geographic latitude coordinate.
        longitude: Geographic longitude coordinate.
        place_type: Type of place to search for (e.g. 'restaurant', 'hotel', 'tourist_attraction', 'cafe').
        radius_meters: Search radius in meters (default: 1000.0).

    Returns:
        A list of nearby places with name, address, location coordinates, and rating.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key:
        return {"error": "GOOGLE_MAPS_API_KEY environment variable is not set."}

    url = "https://places.googleapis.com/v1/places:searchNearby"
    body = json.dumps({
        "includedTypes": [place_type.lower().strip()],
        "maxResultCount": 5,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "radius": radius_meters
            }
        }
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating"
    }

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            places_raw = data.get("places", [])
            results = []
            for p in places_raw:
                display_name = p.get("displayName", {}).get("text", "Unknown")
                results.append({
                    "name": display_name,
                    "address": p.get("formattedAddress"),
                    "location": p.get("location"),
                    "rating": p.get("rating")
                })
            return {
                "status": "success",
                "place_type": place_type,
                "count": len(results),
                "places": results
            }
    except Exception as e:
        return {"error": f"Failed to call Places API (New): {str(e)}"}


def get_exchange_rate(base_currency: str = "USD", target_currency: str = "EUR") -> Dict[str, Any]:
    """Fetch live currency exchange rates for travel budgeting using the ExchangeRate public API.

    Args:
        base_currency: 3-letter currency code for the base amount (e.g. 'USD', 'EUR').
        target_currency: 3-letter target currency code (e.g. 'JPY', 'GBP', 'EUR').

    Returns:
        A dictionary containing the exchange rate, base currency, target currency, and update time.
    """
    base = base_currency.upper().strip()
    target = target_currency.upper().strip()
    
    api_key = os.environ.get("EXCHANGE_RATE_API_KEY", "").strip()
    if api_key:
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}"
    else:
        url = f"https://open.er-api.com/v6/latest/{base}"

    req = urllib.request.Request(url, headers={"User-Agent": "TravelConciergeAgent/1.0"})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            rates = data.get("rates", {})
            if target in rates:
                return {
                    "base_currency": base,
                    "target_currency": target,
                    "exchange_rate": rates[target],
                    "last_updated": data.get("time_last_update_utc")
                }
            return {"error": f"Currency symbol '{target}' not found."}
    except Exception as e:
        return {"error": f"Failed to fetch live exchange rate: {str(e)}"}


def search_destinations(query: str = "", category: str = "") -> List[Dict[str, Any]]:
    """Search for luxury travel destinations in the Firestore database.

    Args:
        query: Optional search keyword to match against destination name, city, country, or description.
        category: Optional category filter (e.g., 'Culture & Nature', 'Luxury & Coast', 'Beach & Adventure', 'Alpine & Ski').

    Returns:
        A list of matching destination dictionary objects.
    """
    collection_ref = db.collection("destinations")
    docs = collection_ref.stream()
    
    results = []
    query_lower = query.lower().strip()
    category_lower = category.lower().strip()
    
    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        
        # Category filter
        if category_lower and category_lower not in data.get("category", "").lower():
            continue
            
        # Keyword query filter
        if query_lower:
            text_corpus = f"{data.get('name', '')} {data.get('city', '')} {data.get('country', '')} {data.get('description', '')}".lower()
            if query_lower not in text_corpus:
                continue
                
        results.append(data)
        
    return results


def get_destination_details(destination_id: str) -> Dict[str, Any]:
    """Retrieve detailed information for a specific travel destination by ID.

    Args:
        destination_id: The document ID of the destination (e.g. 'dest-kyoto', 'dest-santorini').

    Returns:
        The destination details dictionary or error dictionary if not found.
    """
    doc_ref = db.collection("destinations").document(destination_id)
    doc = doc_ref.get()
    
    if not doc.exists:
        return {"error": f"Destination with ID '{destination_id}' not found."}
        
    data = doc.to_dict()
    data["id"] = doc.id
    return data


def add_destination(
    name: str,
    city: str,
    country: str,
    category: str,
    description: str,
    price_per_night: int,
    rating: float = 4.5,
    best_season: str = "Year-round"
) -> Dict[str, Any]:
    """Add a new travel destination recommendation to the Firestore database.

    Args:
        name: Name of the destination (e.g., 'Amalfi Coast Villa').
        city: City or region.
        country: Country name.
        category: Category (e.g., 'Luxury & Coast', 'Culture & Nature').
        description: A compelling description of the location.
        price_per_night: Nightly rate in USD.
        rating: Rating out of 5.0 (default: 4.5).
        best_season: Ideal season to visit (default: 'Year-round').

    Returns:
        A dictionary confirming the newly created destination object.
    """
    doc_id = f"dest-{uuid.uuid4().hex[:8]}"
    new_dest = {
        "id": doc_id,
        "name": name,
        "city": city,
        "country": country,
        "category": category,
        "description": description,
        "price_per_night": price_per_night,
        "rating": rating,
        "best_season": best_season
    }
    
    db.collection("destinations").document(doc_id).set(new_dest)
    return {"status": "success", "message": f"Successfully created destination '{name}'", "destination": new_dest}


def book_destination_itinerary(
    destination_id: str,
    traveler_name: str,
    check_in_date: str,
    check_out_date: str,
    guests: int = 1
) -> Dict[str, Any]:
    """Create a luxury travel reservation for a destination in Firestore.

    Args:
        destination_id: Document ID of the destination (e.g. 'dest-kyoto').
        traveler_name: Full name of the primary traveler.
        check_in_date: Check-in date (YYYY-MM-DD).
        check_out_date: Check-out date (YYYY-MM-DD).
        guests: Number of guests traveling (default: 1).

    Returns:
        A dictionary containing the booking confirmation details.
    """
    booking_id = f"bk-{uuid.uuid4().hex[:8].upper()}"
    booking_record = {
        "booking_id": booking_id,
        "destination_id": destination_id,
        "traveler_name": traveler_name,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "guests": guests,
        "status": "CONFIRMED",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    db.collection("bookings").document(booking_id).set(booking_record)
    return {
        "status": "success",
        "message": f"Reservation successfully confirmed for {traveler_name}!",
        "booking": booking_record
    }


def get_weather(query: str) -> str:
    """Simulates a web search for weather information.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        query: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


# Build A2UI System Instruction (A2UI v0.8 + Basic Catalog)
schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

a2ui_instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are an expert Luxury Travel Concierge AI. You help users explore, search, and manage "
        "curated travel destinations and reservations in Firestore, check live currency exchange rates, "
        "geocode street addresses to coordinates, search nearby places using Google Maps, generate "
        "stunning destination photos, safely execute Python code in a sandbox for calculations, "
        "and remember user preferences and facts across sessions."
    ),
    workflow_description=(
        "Analyze the user's travel request, query destinations or places when needed, and return structured UI when appropriate. "
        "CRITICAL FOR MEMORY & ALLERGIES: Always pay special attention to any dietary restrictions or food/environmental allergies mentioned by the user."
    ),
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=a2ui_instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        search_destinations,
        get_destination_details,
        add_destination,
        book_destination_itinerary,
        get_exchange_rate,
        geocode_address,
        find_nearby_places,
        generate_destination_image,
        generate_destination_video,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
