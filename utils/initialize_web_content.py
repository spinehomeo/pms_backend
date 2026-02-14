"""
Sample Data Initialization Script
Run this script to populate your database with initial data from the JSON structure
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

# Sample data based on the provided JSON structure
sample_data = {
    "about_doctor": {
        "title": "About Doctor",
        "experience_title": "My Story",
        "experience_description": "With over 15 years of dedicated practice in herbal medicine, I have helped thousands of patients achieve better health through natural, holistic approaches. My passion for healing began early in life when I witnessed the transformative power of natural remedies in my own family.",
        "qualifications": [
            {"qualification_text": "Bachelor of Herbal Medicine (BHM)", "order": 1},
            {"qualification_text": "Master of Traditional Medicine (MTM)", "order": 2},
            {"qualification_text": "Certified Herbal Practitioner (CHP)", "order": 3},
            {"qualification_text": "15+ Years of Clinical Experience", "order": 4}
        ],
        "specializations": [
            {"specialization_text": "Cardiovascular Health", "order": 1},
            {"specialization_text": "Digestive Disorders", "order": 2},
            {"specialization_text": "Immune System Support", "order": 3},
            {"specialization_text": "Mental Wellness & Stress Management", "order": 4},
            {"specialization_text": "Chronic Disease Management", "order": 5}
        ]
    },
    
    "hero_section": {
        "title": "Herbal Medicine Specialist",
        "subtitle": "Natural Healing & Wellness",
        "description": "Consult with an experienced herbal medicine doctor for personalized natural treatments and holistic health solutions.",
        "credentials": [
            {"label": "Years Experience", "value": "15+", "order": 1},
            {"label": "Patients Treated", "value": "5000+", "order": 2},
            {"label": "Natural Treatment", "value": "100%", "order": 3}
        ]
    },
    
    "services": {
        "title": "Services & Treatments",
        "services": [
            {
                "icon": "heart",
                "image_url": "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=500&h=300&fit=crop",
                "title": "Cardiovascular Health",
                "description": "Natural treatments for heart health and circulation using proven herbal remedies.",
                "order": 1
            },
            {
                "icon": "brain",
                "image_url": "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=500&h=300&fit=crop",
                "title": "Mental Wellness",
                "description": "Herbal remedies for stress, anxiety, and mental clarity to improve overall well-being.",
                "order": 2
            },
            {
                "icon": "shield",
                "image_url": "https://images.unsplash.com/photo-1505751172876-fa1923c5c528?w=500&h=300&fit=crop",
                "title": "Immune System Support",
                "description": "Strengthen your immune system with natural herbs and traditional remedies.",
                "order": 3
            },
            {
                "icon": "activity",
                "image_url": "https://images.unsplash.com/photo-1551884170-09fb70a3a2ed?w=500&h=300&fit=crop",
                "title": "Digestive Health",
                "description": "Comprehensive herbal solutions for digestive issues and gut health optimization.",
                "order": 4
            }
        ]
    },
    
    "testimonials": {
        "title": "Patient Success Stories",
        "testimonials": [
            {
                "name": "Ahmed Ali",
                "city": "Lahore",
                "rating": 5,
                "message": "Dr. Sahib's herbal treatment completely transformed my health. After years of struggling with digestive issues, I finally found relief through natural remedies. The personalized approach made all the difference.",
                "order": 1,
                "is_approved": True
            },
            {
                "name": "Fatima Khan",
                "city": "Karachi",
                "rating": 5,
                "message": "I was skeptical about herbal medicine, but the results speak for themselves. My energy levels have improved significantly, and I feel better than I have in years. Highly recommended!",
                "order": 2,
                "is_approved": True
            },
            {
                "name": "Muhammad Hassan",
                "city": "Islamabad",
                "rating": 5,
                "message": "Professional, knowledgeable, and truly caring. The herbal treatments have helped manage my chronic condition better than conventional medicine ever did.",
                "order": 3,
                "is_approved": True
            },
            {
                "name": "Ayesha Malik",
                "city": "Faisalabad",
                "rating": 5,
                "message": "Outstanding experience! The doctor took time to understand my concerns and created a customized treatment plan. I've seen remarkable improvements in just a few months.",
                "order": 4,
                "is_approved": True
            }
        ]
    },
    
    "contact_info": {
        "title": "Contact Information",
        "address": "123 Main Street",
        "city": "Lahore, Pakistan",
        "phone_primary": "+92 300 1234567",
        "phone_secondary": "+92 42 12345678",
        "weekdays_hours": "Monday - Friday: 9:00 AM - 6:00 PM",
        "saturday_hours": "Saturday: 9:00 AM - 2:00 PM",
        "sunday_hours": "Sunday: Closed",
        "whatsapp_number": "923001234567",
        "whatsapp_message": "Hello, I would like to book an appointment"
    }
}


def initialize_about_doctor():
    """Initialize About Doctor section"""
    print("Creating About Doctor section...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/about-doctor",
            json=sample_data["about_doctor"]
        )
        if response.status_code == 201:
            print("✓ About Doctor section created successfully")
            print(f"  ID: {response.json()['id']}")
        else:
            print(f"✗ Failed to create About Doctor section: {response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")


def initialize_hero_section():
    """Initialize Hero Section"""
    print("\nCreating Hero Section...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/hero-section",
            json=sample_data["hero_section"]
        )
        if response.status_code == 201:
            print("✓ Hero Section created successfully")
            print(f"  ID: {response.json()['id']}")
        else:
            print(f"✗ Failed to create Hero Section: {response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")


def initialize_services():
    """Initialize Services & Treatments section"""
    print("\nCreating Services & Treatments section...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/services",
            json=sample_data["services"]
        )
        if response.status_code == 201:
            print("✓ Services & Treatments section created successfully")
            print(f"  ID: {response.json()['id']}")
            print(f"  Services count: {len(response.json()['services'])}")
        else:
            print(f"✗ Failed to create Services section: {response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")


def initialize_testimonials():
    """Initialize Patient Success Stories section"""
    print("\nCreating Patient Success Stories section...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/testimonials",
            json=sample_data["testimonials"]
        )
        if response.status_code == 201:
            print("✓ Patient Success Stories section created successfully")
            print(f"  ID: {response.json()['id']}")
            print(f"  Testimonials count: {len(response.json()['testimonials'])}")
        else:
            print(f"✗ Failed to create Testimonials section: {response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")


def initialize_contact_info():
    """Initialize Contact Information"""
    print("\nCreating Contact Information...")
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/contact-info",
            json=sample_data["contact_info"]
        )
        if response.status_code == 201:
            print("✓ Contact Information created successfully")
            print(f"  ID: {response.json()['id']}")
        else:
            print(f"✗ Failed to create Contact Information: {response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")


def verify_data():
    """Verify all data was created"""
    print("\n" + "="*50)
    print("Verifying data...")
    print("="*50)
    
    try:
        # Check about doctor
        response = requests.get(f"{API_BASE_URL}/api/about-doctor")
        print(f"\nAbout Doctor sections: {len(response.json())}")
        
        # Check hero section
        response = requests.get(f"{API_BASE_URL}/api/hero-section")
        print(f"Hero Sections: {len(response.json())}")
        
        # Check services
        response = requests.get(f"{API_BASE_URL}/api/services")
        print(f"Services sections: {len(response.json())}")
        
        # Check testimonials
        response = requests.get(f"{API_BASE_URL}/api/testimonials")
        print(f"Testimonials sections: {len(response.json())}")
        
        # Check contact info
        response = requests.get(f"{API_BASE_URL}/api/contact-info")
        print(f"Contact Information records: {len(response.json())}")
        
    except Exception as e:
        print(f"✗ Error during verification: {e}")


def main():
    """Main initialization function"""
    print("="*50)
    print("Herbal Medicine Website - Data Initialization")
    print("="*50)
    print("\nMake sure your FastAPI server is running at http://localhost:8000\n")
    
    # Check if server is running
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code != 200:
            print("✗ Server is not responding properly!")
            return
    except Exception as e:
        print(f"✗ Cannot connect to server: {e}")
        print("Please start the server first with: python backend_architecture.py")
        return
    
    print("✓ Server is running\n")
    
    # Initialize all sections
    initialize_about_doctor()
    initialize_hero_section()
    initialize_services()
    initialize_testimonials()
    initialize_contact_info()
    
    # Verify data
    verify_data()
    
    print("\n" + "="*50)
    print("Initialization Complete!")
    print("="*50)
    print("\nYou can now:")
    print("1. Visit http://localhost:8000/docs to see the API documentation")
    print("2. Use the API endpoints to manage your website content")
    print("3. Build your management portal frontend")


if __name__ == "__main__":
    main()
