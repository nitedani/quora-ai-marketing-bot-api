from flask import Flask, request, jsonify
import time
import agentql
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# Quora login credentials
EMAIL= os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# Quora URL for authentication
AUTH_URL = "https://www.quora.com/"

# Define the AgentQL queries to locate the buttons
LOGIN_BUTTON_QUERY = """
{
    login_button
}
"""

ANSWER_BUTTON_QUERY = """
{
    answer_button
}
"""

POST_BUTTON_QUERY = """
{
    post_button
}
"""

def save_signed_in_state():
    with sync_playwright() as playwright, playwright.chromium.launch(headless=False) as browser:
        # Create a new browser context and page
        context = browser.new_context()
        page = agentql.wrap(context.new_page())

        # Go to the Quora home page
        page.goto(AUTH_URL)
        page.wait_for_load_state('domcontentloaded')

        # Fill in the login credentials
        page.fill('input[name="email"]', EMAIL)
        page.fill('input[name="password"]', PASSWORD)
        time.sleep(2)

        # Perform the login
        response = page.query_elements(LOGIN_BUTTON_QUERY)
        if response.login_button:
            response.login_button.click()
            print("Login button clicked!")
        else:
            print("Login button not found!")

        time.sleep(5)  # Wait for the login process to complete

        # Save the signed-in state to a file
        context.storage_state(path="quora_login.json")

        # Close the browser
        browser.close()

def post_answer(post_url):
    try:
        with sync_playwright() as playwright, playwright.chromium.launch(headless=False) as browser:
            # Load the saved session state
            context = browser.new_context(storage_state="quora_login.json")
            page = agentql.wrap(context.new_page())

            # Navigate to the specific Quora question page
            page.goto(post_url)
            page.wait_for_load_state('domcontentloaded')

            # Click the answer button
            response = page.query_elements(ANSWER_BUTTON_QUERY)
            if response.answer_button:
                response.answer_button.click()
                print("Answer button clicked!")
            else:
                print("Answer button not found!")
                return False

            # Enter the answer in the text area identified by class "doc empty"
            page.fill('.doc.empty', 'Automation will lose a lot of jobs')

            # Click the post button
            response = page.query_elements(POST_BUTTON_QUERY)
            if response.post_button:
                response.post_button.click()
                print("Post button clicked!")
            else:
                print("Post button not found!")
                return False

            # Wait for the post to complete
            time.sleep(5)

            # Close the browser
            browser.close()

            return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

@app.route('/post_answer', methods=['POST'])
def api_post_answer():
    data = request.json
    post_url = data.get('postURL')
    if not post_url:
        return jsonify({"success": False, "message": "postURL is required"}), 400

    # First, save the signed-in state (if not already done)
    save_signed_in_state()

    # Then, use the saved state to post an answer
    success = post_answer(post_url)
    
    if success:
        return jsonify({"success": True, "message": "Answer posted successfully"}), 200
    else:
        return jsonify({"success": False, "message": "Failed to post the answer"}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)