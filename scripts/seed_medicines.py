#!/usr/bin/env python
"""
Seed script to populate the medicine table with sample data.
Run with: uv run python scripts/seed_medicines.py
"""
import sys
from sqlmodel import Session, select

# Add parent directory to path
sys.path.insert(0, str(__file__).rsplit('\\', 2)[0])

from core.db import engine
from models.medicines_model import Medicine


def seed_medicines():
    """Populate medicine table with sample homeopathic remedies."""
    
    medicines_data = [
        {
            "name": "Aconite",
            "description": "Monkshood remedy - acute fevers, anxiety, panic attacks"
        },
        {
            "name": "Arnica",
            "description": "Mountain daisy - bruises, trauma, shock"
        },
        {
            "name": "Belladonna",
            "description": "Deadly nightshade - sudden onset fevers, inflammation"
        },
        {
            "name": "Bryonia",
            "description": "Wild hops - dry cough, joint pain, worse with motion"
        },
        {
            "name": "Calcarea Carbonica",
            "description": "Oyster shell - chilly, sweaty, bone health"
        },
        {
            "name": "Chamomilla",
            "description": "German chamomile - irritability, teething, complaints"
        },
        {
            "name": "Sulphur",
            "description": "Brimstone - chronic conditions, skin issues, heat intolerance"
        },
        {
            "name": "Lycopodium",
            "description": "Club moss - digestive issues, lack of confidence, flatulence"
        },
        {
            "name": "Nat Mur",
            "description": "Sodium chloride - grief, depression, headaches"
        },
        {
            "name": "Pulsatilla",
            "description": "Windflower - changeable symptoms, weepy, thirstless"
        },
        {
            "name": "Sepia",
            "description": "Cuttlefish - women's complaints, exhaustion, indifference"
        },
        {
            "name": "Phosphorus",
            "description": "Mineral - sensitive, bleeding disorders, burning pains"
        },
        {
            "name": "Silica",
            "description": "Flint - slow healing, chilly, weakness"
        },
        {
            "name": "Thuja",
            "description": "Arbor vitae - warts, vaccine reactions, suspicious"
        },
        {
            "name": "Nux Vomica",
            "description": "Poison nut - over-work, digestive complaints, irritability"
        },
    ]
    
    with Session(engine) as session:
        # Check if medicines already exist
        existing = session.exec(select(Medicine)).first()
        if existing:
            print("✓ Medicines already exist in database. Skipping seed.")
            return
        
        # Create new medicines
        medicines = [Medicine(**data) for data in medicines_data]
        
        for medicine in medicines:
            session.add(medicine)
        
        session.commit()
        
        # Verify
        count = session.exec(select(Medicine)).all()
        print(f"✓ Successfully seeded {len(count)} medicines:")
        for med in count:
            print(f"  - ID {med.id}: {med.name}")


if __name__ == "__main__":
    try:
        seed_medicines()
        print("\n✓ Seed script completed successfully!")
    except Exception as e:
        print(f"✗ Error seeding medicines: {e}")
        sys.exit(1)
