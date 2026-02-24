#!/usr/bin/env python
"""
Direct database query to check prescription data using raw SQL.
Run with: uv run python scripts/check_data_sql.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(__file__).rsplit('\\', 2)[0])

try:
    from sqlalchemy import create_engine, text
    from core.config import settings
    
    # Create engine directly
    database_url = settings.DATABASE_URL
    print(f"Connecting to: {database_url.split('@')[-1]}")  # Show DB without credentials
    
    engine = create_engine(database_url, echo=False)
    
    print("\n" + "="*80)
    print("MEDICINES DATA")
    print("="*80)
    
    with engine.connect() as conn:
        # Check potency distribution
        result = conn.execute(text("""
            SELECT potency, COUNT(*) as count, 
                   STRING_AGG(name, ', ' ORDER BY name) as medicines
            FROM medicine
            GROUP BY potency
            ORDER BY count DESC
        """))
        print("\nPotency Distribution:")
        for row in result:
            potency, count, medicines = row
            med_list = medicines[:60] + "..." if len(medicines or "") > 60 else medicines
            print(f"  '{potency}': {count} medicines")
            print(f"    → {med_list}\n")
        
        # Check prescriptions
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN duration_days IS NULL THEN 1 END) as null_duration,
                COUNT(CASE WHEN prescription_duration = 'string' THEN 1 END) as string_duration
            FROM prescription
        """))
        for row in result:
            print(f"\nPrescriptions:")
            print(f"  Total: {row[0]}")
            print(f"  With duration_days = NULL: {row[1]}")
            print(f"  With duration = 'string': {row[2]}")
        
        # Check prescription medicines
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN quantity_prescribed IS NULL THEN 1 END) as null_qty,
                COUNT(CASE WHEN frequency IS NULL THEN 1 END) as null_freq
            FROM prescription_medicine
        """))
        for row in result:
            print(f"\nPrescription Medicines:")
            print(f"  Total: {row[0]}")
            print(f"  With quantity_prescribed = NULL: {row[1]}")
            print(f"  With frequency = NULL: {row[2]}")
        
        # Check RepetitionEnum values
        result = conn.execute(text("""
            SELECT DISTINCT option_value 
            FROM enum_option 
            WHERE enum_name = 'RepetitionEnum'
            ORDER BY option_value
        """))
        freqs = result.fetchall()
        print(f"\nValid Frequencies (RepetitionEnum):")
        for row in freqs:
            print(f"  - {row[0]}")

    print("\n" + "="*80 + "\n")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
