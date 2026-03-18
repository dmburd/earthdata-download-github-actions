import os
import sys

def main():
    # Get the comment text from environment variables
    payload = os.environ.get('INPUT_PAYLOAD', '')
    
    if not payload.strip():
        print("Error: No input data provided.")
        sys.exit(1)

    # Your processing logic here. 
    # As an example, we will just count the number of characters and convert the text to UPPERCASE
    char_count = len(payload)
    processed_text = payload.upper()

    # Everything the script outputs via print will be intercepted by GitHub Actions 
    # and sent to the user in a response comment
    print(f"Data received: {char_count} characters.")
    print(f"Processed content:\n{processed_text}")

if __name__ == "__main__":
    main()
