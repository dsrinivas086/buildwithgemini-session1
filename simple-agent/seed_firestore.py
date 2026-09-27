import os
from google.cloud import firestore

# CRITICAL: Hardcoded project ID as string, required for Agent Platform deployment
PROJECT_ID = "qwiklabs-gcp-02-c3eb38e799e1"

def seed_database():
    print(f"Connecting to Firestore for project: {PROJECT_ID}...")
    db = firestore.Client(project=PROJECT_ID)

    destinations = [
        {
            "id": "dest-kyoto",
            "name": "Kyoto Bamboo & Temple Sanctuary",
            "city": "Kyoto",
            "country": "Japan",
            "category": "Culture & Nature",
            "description": "Serene ancient temples, traditional tea houses, and bamboo groves in Arashiyama.",
            "price_per_night": 320,
            "rating": 4.9,
            "best_season": "Spring (Cherry Blossom)"
        },
        {
            "id": "dest-santorini",
            "name": "Santorini Caldera Sunset Suite",
            "city": "Santorini",
            "country": "Greece",
            "category": "Luxury & Coast",
            "description": "Iconic whitewashed cliffside villas with private infinity pools overlooking the Aegean Sea.",
            "price_per_night": 450,
            "rating": 4.8,
            "best_season": "Summer"
        },
        {
            "id": "dest-maui",
            "name": "Maui Oceanfront Eco-Resort",
            "city": "Maui",
            "country": "USA",
            "category": "Beach & Adventure",
            "description": "Pristine beachfront access, snorkeling with sea turtles, and volcanic hiking trails.",
            "price_per_night": 380,
            "rating": 4.7,
            "best_season": "Year-round"
        },
        {
            "id": "dest-swiss-alps",
            "name": "Zermatt Matterhorn Chalet",
            "city": "Zermatt",
            "country": "Switzerland",
            "category": "Alpine & Ski",
            "description": "Luxury ski-in chalet with views of the iconic Matterhorn and cozy fireside lounge.",
            "price_per_night": 520,
            "rating": 4.95,
            "best_season": "Winter"
        }
    ]

    print("Seeding destinations collection...")
    collection_ref = db.collection("destinations")
    for dest in destinations:
        doc_ref = collection_ref.document(dest["id"])
        doc_ref.set(dest)
        print(f"  ✓ Seeded: {dest['name']} ({dest['id']})")

    print("🎉 Firestore database successfully seeded!")

if __name__ == "__main__":
    seed_database()
