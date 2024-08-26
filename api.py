from dotenv import load_dotenv
load_dotenv() 
import os
from flask import Flask, request, jsonify
import time
import agentql
from playwright.sync_api import sync_playwright
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
EMAIL= os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

IS_RENDER = True if os.getenv('RENDER') else False
STATE_PATH = '/etc/secrets/quora_login.json' if IS_RENDER else 'quora_login.json'


# Define the AgentQL queries (unchanged)
LOGIN_BUTTON_QUERY = """
{
    login_button
}
"""

QUESTION_QUERY = """
{
    question_title[] {
        question_link
    }
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

@app.route('/fetch_questions', methods=['POST'])
def fetch_questions():
    logger.info("Received request to fetch questions")
    data = request.json
    url = data.get('url')
    if not url:
        logger.error("URL is missing in the request")
        return jsonify({"error": "URL is required"}), 400

    try:
        logger.info(f"Fetching questions from URL: {url}")
        questions = load_signed_in_state_and_fetch_data(url)
        logger.info(f"Successfully fetched {len(questions)} questions")
        return jsonify({"questions": questions})
    except Exception as e:
        logger.error(f"Error fetching questions: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/post_answer', methods=['POST'])
def api_post_answer():
    logger.info("Received request to post an answer")
    data = request.json
    post_url = data.get('postURL')
    if not post_url:
        logger.error("postURL is missing in the request")
        return jsonify({"success": False, "message": "postURL is required"}), 400

    logger.info(f"Posting answer to URL: {post_url}")
    success = post_answer(post_url)
    
    if success:
        logger.info("Answer posted successfully")
        return jsonify({"success": True, "message": "Answer posted successfully"}), 200
    else:
        logger.error("Failed to post the answer")
        return jsonify({"success": False, "message": "Failed to post the answer"}), 500

def post_answer(post_url):
    logger.info(f"Attempting to post answer to {post_url}")
    try:
        with sync_playwright() as playwright, playwright.chromium.launch(headless=IS_RENDER) as browser:
            logger.info("Loading saved session state")
            context = browser.new_context(storage_state=STATE_PATH)
            page = agentql.wrap(context.new_page())

            logger.info(f"Navigating to {post_url}")
            page.goto(post_url)
            page.wait_for_load_state('domcontentloaded')

            try:
                logger.info("Attempting to accept cookies")
                page.click('button[id="onetrust-accept-btn-handler"]')
            except:
                logger.warning("Cookie acceptance button not found or already accepted")

            logger.info("Clicking answer button")
            response = page.query_elements(ANSWER_BUTTON_QUERY)
            if response.answer_button:
                response.answer_button.click()
                logger.info("Answer button clicked successfully")
            else:
                logger.error("Answer button not found")
                return False

            logger.info("Entering answer text")
            page.fill('.doc.empty', 'Automation will lose a lot of jobs')
            logger.info("Clicking post button")
            response = page.query_elements(POST_BUTTON_QUERY)
            remove_onetrust_el()
            if response.post_button:
                response.post_button.click()
                logger.info("Post button clicked successfully")
            else:
                logger.error("Post button not found")
                return False

            logger.info("Waiting for post to complete")
            time.sleep(5)

            logger.info("Closing browser")
            browser.close()

            return True
    except Exception as e:
        logger.error(f"An error occurred while posting answer: {e}", exc_info=True)
        return False

def save_signed_in_state():
    logger.info("Saving signed-in state")
    with sync_playwright() as playwright, playwright.chromium.launch(headless=IS_RENDER) as browser:
        page = agentql.wrap(browser.new_page())
        logger.info("Navigating to Quora login page")
        page.goto("https://www.quora.com/")
        page.wait_for_load_state('domcontentloaded')
        try:
            logger.info("Attempting to accept cookies")
            page.click('button[id="onetrust-accept-btn-handler"]')
        except:
            logger.warning("Cookie acceptance button not found or already accepted")

        logger.info("Filling in login credentials")
        page.fill('input[name="email"]', EMAIL)
        page.fill('input[name="password"]', PASSWORD)
        time.sleep(2)

        logger.info("Clicking login button")
        response = page.query_elements(LOGIN_BUTTON_QUERY)

        if response.login_button:
            response.login_button.click()
            logger.info("Login button clicked successfully")
        else:
            logger.error("Login button not found")

        logger.info("Waiting for login process to complete")
        time.sleep(10)
        logger.info("Saving browser state")
        browser.contexts[0].storage_state(path="quora_login.json")

def load_signed_in_state_and_fetch_data(url):
    logger.info(f"Loading signed-in state and fetching data from {url}")
    with sync_playwright() as playwright, playwright.chromium.launch(headless=IS_RENDER) as browser:
        context = browser.new_context(storage_state=STATE_PATH)
        page = agentql.wrap(context.new_page())
        logger.info(f"Navigating to {url}")
        page.goto(url)
        page.wait_for_page_ready_state()

        all_questions = []

        for i in range(3):
            logger.info(f"Fetching questions (iteration {i+1}/3)")
            question_response = page.query_data(QUESTION_QUERY)
            all_questions.extend(question_response["question_title"])
            logger.info(f"Total questions fetched: {len(all_questions)}")

            logger.info("Scrolling down to load more content")
            page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            time.sleep(5)

        logger.info(f"Finished fetching questions. Total: {len(all_questions)}")
        return all_questions

PORT = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    logger.info("Starting application")
    logger.info("Saving initial signed-in state")
    # save_signed_in_state()
    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT)


def remove_onetrust_el(page):
    # remove #onetrust-consent-sdk from document
    page.evaluate('document.querySelector("#onetrust-consent-sdk")?.remove()')