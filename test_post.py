# test_post.py
import requests
import json

def test_post_endpoint(username, password, data):
    url = "http://localhost:5000/offices"  # Change if your server is running on a different URL
    
    # Format the data
    formatted_data = {
        "state_office_token": data["state_office_token"],
        "area_served_token": data["area_served_token"],
        "service_token": data["service_token"],
        "meta_title": data["meta_title"],
        "meta_description": data["meta_description"],
        "page_title": data["page_title"],
        "page_content": data["page_content"]
    }
    
    # Set headers
    headers = {
        "Content-Type": "application/json"
    }
    
    # Make the POST request with authentication
    response = requests.post(
        url, 
        auth=(username, password),
        json=formatted_data,
        headers=headers
    )
    
    # Print response details
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 201:
        print("Success! Office page created successfully.")
    else:
        print(f"Error: Failed to create office page. Status code: {response.status_code}")

if __name__ == "__main__":
    # Your data
    data = {
        "id": "10584da8-5de3-4441-b526-2a761dc3461a",
        "state_office_token": "tennessee/chattanooga",
        "area_served_token": "lookout-mountain",
        "service_token": "care-services",
        "meta_title": "In Home Senior Care in Lookout Mountain, TN | Comfort Keepers",
        "meta_description": "Compassionate and personalized in home senior care in Lookout Mountain, TN and surrounding areas. Our dedicated team offers quality services to help seniors maintain their independence and well-being.",
        "page_title": "Care Services",
        "page_content": "<h1>Providing Quality In Home Senior Care in Lookout Mountain, TN</h1> <h2>What Sets Comfort Keepers Apart?</h2> At Comfort Keepers in Lookout Mountain, TN, we take great pride in offering top-notch in home senior care services to our clients. We understand that choosing the right care for your loved one can be a challenging and emotional process, which is why we strive to provide compassionate and personalized care to meet the individual needs of each senior we serve. <h3>The Importance of In Home Senior Care</h3> As our loved ones age, they may require additional assistance and support to maintain their independence and quality of life. In home senior care allows seniors to age in the comfort of their own homes while receiving the care they need. This type of care not only promotes physical well-being but also provides companionship and emotional support, helping seniors maintain a sense of purpose and connection. <h3>Our In Home Senior Care Services</h3> At Comfort Keepers, our team of trained and compassionate caregivers offers a wide range of in home senior care services in Lookout Mountain, TN and the surrounding areas. From assistance with daily tasks like bathing and dressing to medication reminders and meal preparation, our caregivers are dedicated to helping seniors live comfortably and confidently in their own homes. <h3>Personalized Care Plans</h3> We understand that each senior has unique needs and preferences, which is why we create personalized care plans for each of our clients. Our team works closely with families to develop a care plan that meets their loved one's specific needs and helps them maintain their independence and well-being. Our caregivers also provide regular updates and communication with families to ensure their loved one's needs are being met. <h3>Our Commitment to Quality Care</h3> At Comfort Keepers, we are committed to providing high-quality in home senior care services in Lookout Mountain, TN. Our caregivers are carefully selected, trained, and supervised to ensure that they provide the best care possible for our clients. We also offer ongoing training and support to our caregivers to ensure they are up to date on the latest techniques and best practices for senior care. In conclusion, Comfort Keepers in Lookout Mountain, TN is dedicated to providing compassionate and personalized in home senior care services to help seniors live comfortably and confidently in their own homes. With our personalized care plans and commitment to quality care, families can rest assured that their loved one is in good hands with our team of caregivers. Contact us today to learn more about how we can assist your family with in home senior care in Lookout Mountain, TN and the surrounding areas."
    }
    
    # Your authentication credentials
    username = "ck"  # Replace with your username
    password = "LMeAdrEsCeIr"  # Replace with your password
    
    test_post_endpoint(username, password, data)
