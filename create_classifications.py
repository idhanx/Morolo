#!/usr/bin/env python3
"""Create MoroloPII classification hierarchy in OpenMetadata."""

import json
import os
import httpx

OM_HOST = os.getenv("OM_HOST", "http://localhost:8585")
OM_TOKEN = os.getenv("OM_TOKEN")

if not OM_TOKEN:
    raise ValueError("OM_TOKEN environment variable not set")

BASE_URL = f"{OM_HOST.rstrip('/')}/api/v1"
HEADERS = {
    "Authorization": f"Bearer {OM_TOKEN}",
    "Content-Type": "application/json",
}

def create_classification(fqn: str, display_name: str, description: str) -> dict:
    """Create a classification in OpenMetadata using dot notation for hierarchy."""
    body = {
        "name": fqn,  # Use full FQN for hierarchical names like "MoroloPII.Sensitive.IndianGovtID"
        "displayName": display_name,
        "description": description,
    }

    print(f"Creating classification: {fqn}")
    
    with httpx.Client(timeout=30) as client:
        r = client.put(
            f"{BASE_URL}/classifications",
            headers=HEADERS,
            json=body,
        )
        
        if r.status_code in (200, 201):
            result = r.json()
            fqn = result.get("fullyQualifiedName", fqn)
            print(f"✓ Created: {fqn}")
            return result
        elif r.status_code == 409:
            print(f"  (Already exists)")
            # Try to fetch it
            with httpx.Client(timeout=30) as client2:
                r2 = client2.get(
                    f"{BASE_URL}/classifications/name/{fqn}",
                    headers=HEADERS,
                )
                if r2.status_code == 200:
                    return r2.json()
            return {}
        else:
            print(f"✗ Failed [{r.status_code}]: {r.text[:200]}")
            return {}

def main():
    print("=" * 60)
    print("Creating MoroloPII Classification Hierarchy")
    print("=" * 60)
    
    # Step 1: Ensure MoroloPII parent exists (should already exist)
    print("\n1. Verifying MoroloPII root classification...")
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{BASE_URL}/classifications/name/MoroloPII", headers=HEADERS)
        if r.status_code == 200:
            print("✓ MoroloPII already exists")
        else:
            print("✗ MoroloPII not found! Create it manually in OM UI first.")
            return
    
    # Step 2: Create Sensitive (under MoroloPII)
    print("\n2. Creating Sensitive sub-classification...")
    create_classification(
        fqn="MoroloPII.Sensitive",
        display_name="Sensitive",
        description="Sensitive PII data requiring special protection",
    )
    
    # Step 3: Create IndianGovtID (under MoroloPII.Sensitive)
    print("\n3. Creating IndianGovtID sub-classification...")
    create_classification(
        fqn="MoroloPII.Sensitive.IndianGovtID",
        display_name="Indian Government ID",
        description="Indian Government identification documents (Aadhaar, PAN, Driving License)",
    )
    
    # Step 4: Create ContactInfo (under MoroloPII.Sensitive)
    print("\n4. Creating ContactInfo sub-classification...")
    create_classification(
        fqn="MoroloPII.Sensitive.ContactInfo",
        display_name="Contact Information",
        description="Contact information (email, phone)",
    )
    
    # Step 5: Create specific IndianGovtID types
    print("\n5. Creating Indian Government ID types...")
    create_classification(
        fqn="MoroloPII.Sensitive.IndianGovtID.Aadhaar",
        display_name="Aadhaar",
        description="Aadhaar (12-digit biometric ID by UIDAI)",
    )
    create_classification(
        fqn="MoroloPII.Sensitive.IndianGovtID.PAN",
        display_name="PAN",
        description="PAN (Permanent Account Number for taxation)",
    )
    create_classification(
        fqn="MoroloPII.Sensitive.IndianGovtID.DrivingLicense",
        display_name="Driving License",
        description="DL (State-issued driving license)",
    )
    
    # Step 6: Create ContactInfo types
    print("\n6. Creating Contact Information types...")
    create_classification(
        fqn="MoroloPII.Sensitive.ContactInfo.Email",
        display_name="Email",
        description="Email address",
    )
    create_classification(
        fqn="MoroloPII.Sensitive.ContactInfo.Phone",
        display_name="Phone",
        description="Phone number",
    )
    
    print("\n" + "=" * 60)
    print("Classification hierarchy creation complete!")
    print("=" * 60)
    
    # Step 7: Verify by listing all
    print("\nVerifying created hierarchy...")
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{BASE_URL}/classifications?limit=100", headers=HEADERS)
        if r.status_code == 200:
            result = r.json()
            names = [c.get("name") for c in result.get("data", [])]
            print(f"Total classifications: {len(names)}")
            print(f"MoroloPII hierarchy: {sorted([n for n in names if 'Morolo' in n or n in ['Sensitive', 'IndianGovtID', 'ContactInfo', 'Aadhaar', 'PAN', 'DrivingLicense', 'Email', 'Phone']])}")

if __name__ == "__main__":
    main()
