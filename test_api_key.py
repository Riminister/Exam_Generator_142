"""
Test script to verify OpenAI API key is working correctly.
Run this script to test your OpenAI API connection.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

def test_openai_api():
    """Test if OpenAI API key is valid and working."""
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in .env file")
        print("Please make sure you have:")
        print("1. Created a .env file in the project root")
        print("2. Added your API key: OPENAI_API_KEY=your_key_here")
        return False
    
    if api_key == "your_openai_api_key_here":
        print("❌ ERROR: Please replace 'your_openai_api_key_here' with your actual OpenAI API key in the .env file")
        return False
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Make a simple API call to test the connection
        print("🔄 Testing OpenAI API connection...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say 'API key is working!' if you can read this."}
            ],
            max_tokens=20
        )
        
        # Extract and display the response
        message = response.choices[0].message.content
        print(f"✅ SUCCESS! OpenAI API is working correctly.")
        print(f"📝 Response: {message}")
        print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: Failed to connect to OpenAI API")
        print(f"Error details: {str(e)}")
        print("\nPossible issues:")
        print("1. Invalid API key")
        print("2. No internet connection")
        print("3. API key has insufficient credits")
        print("4. OpenAI API service is down")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("OpenAI API Key Test")
    print("=" * 50)
    print()
    
    success = test_openai_api()
    
    print()
    print("=" * 50)
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed. Please check the errors above.")
    print("=" * 50)

