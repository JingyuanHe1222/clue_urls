
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os 
import re 
import requests
import uuid
import validators

from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from flask import Flask, session, request, jsonify, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect



driver = webdriver.Chrome()

#############################################
#################### Env ####################
#############################################

# ### env var ###
load_dotenv(dotenv_path=".env.local")

VALID_API_KEYS = [os.getenv("API_KEY")]
TABLE_NAME = os.getenv("TABLE_NAME")
DATE_TABLE_NAME = os.getenv("DATE_TABLE_NAME")
POSTGRES_URL = os.getenv("POSTGRES_URL")
if POSTGRES_URL and POSTGRES_URL.startswith("postgres://"):
    POSTGRES_URL = POSTGRES_URL.replace("postgres://", "postgresql://", 1)

# ### app ###
app = Flask(__name__)


#############################################
################# Datastore #################
#############################################
app.secret_key = VALID_API_KEYS
app.config["SQLALCHEMY_DATABASE_URI"] = POSTGRES_URL
# init SQLAlchemy 
db = SQLAlchemy(app)

# data model 
class URLs(db.Model):
    __tablename__ = TABLE_NAME
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(80), nullable=False)
    worker_id = db.Column(db.String(80), nullable=False)  # Add this line
    url = db.Column(db.String(2083), nullable=False)
    date = db.Column(db.String(80), nullable=False) 
    day_time = db.Column(db.String(80), nullable=False) 
    timestamp = db.Column(db.String(80), nullable=False) 

class DATEs(db.Model):
    __tablename__ = DATE_TABLE_NAME
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(80), nullable=False)
    worker_id = db.Column(db.String(80), nullable=False)  # Add this line
    date = db.Column(db.String(80), nullable=False) 

       
# create model 
with app.app_context():
    inspector = inspect(db.engine)
    if not inspector.has_table("urls"):
        db.create_all()
    if not inspector.has_table("dates"):
        db.create_all()


#############################################
############### UI Interface ################
#############################################

# landing page 
@app.route('/')
def index():
    return render_template('landing.html')

# landing page for user consent  
@app.route('/consent')
def landing_consent():
    return render_template('landing_consent.html')

# landing page for API authentication 
@app.route('/auth')
def landing_auth():
    # This function renders the HTML template dynamically
    return render_template('landing_auth.html')

# url submission page 
@app.route('/submission')
def submission_page():
    if not session.get('authenticated'):
        return redirect(url_for('index'))  # Redirect to API key page if not authenticated
    return render_template('submission_2.html')


#############################################
############### Utility Functions ###########
#############################################


options = Options()
options.add_argument("--no-sandbox")  # Fix permission issues in WSL
options.add_argument("--headless")
options.set_capability("goog:loggingPrefs", {"performance": "ALL"})  # Enable network logs

chrome_path = "/usr/bin/chromium-browser"
chromedriver_path = "/usr/bin/chromedriver" 

service = Service(chromedriver_path)
driver = webdriver.Chrome(service=service, options=options)

driver.set_page_load_timeout(10)
driver.set_script_timeout(5) 

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

def clear_driver_logs():
    try:
        driver.get_log("performance")  # Read logs once to clear them
    except:
        pass 
    


#############################################
############### Input Validations ###########
#############################################



def is_generated_page(url, response_text): 

    # criteria 1: query or search operator 
    def contains_query_optr(url): 
        parsed_url = urlparse(url)
        if "search" in parsed_url.path or "query" in parsed_url.query:  
            return True
    
    def url_keywords(url): 
        # Define search-related keywords
        search_patterns = [r"[?&]q=", r"[?&]query=",r"[?&]keyword=",r"/search",r"/sr\?"]
        for pattern in search_patterns: 
            matched = re.search(pattern, url, re.IGNORECASE)
            if matched: 
                return matched
        return None

    # criteria 2: link structure 
    def is_mostly_links(soup):
        # links outnumber paragraphs significantly, assume it's a generated page
        links = soup.find_all("a")
        paragraphs = soup.find_all("p")
        text_length = len(soup.get_text(strip=True).replace("\n", ""))
        return len(links) > 5 * len(paragraphs) and text_length < 50
    
    soup = BeautifulSoup(response_text, "html.parser")
    return contains_query_optr(url) or url_keywords(url) or is_mostly_links(soup)


def url_validator(url): 

    clear_driver_logs()
    driver.get(url)

    # get likely static content 
    response = requests.get(url, timeout=10, headers=headers, allow_redirects=False)

    if response.status_code < 200 or response.status_code >= 300: 
        return False, "Invalid submission: URL submitted is not accessiable. Please make sure this is a public URL."
    if is_generated_page(url, response.text): 
        return False, "Invalid submission: URL submitted is generated page / online files, etc. Please refer to the Submission Must-Know FAQ. "
    return True, ""


# def is_url_accessible(url):
#     try:
#         url_session = requests.Session()
#         # User-Agent header to mimic a browser
#         headers = {
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
#         }
#         # request with headers and session
#         url_session.cookies.clear()
#         response = url_session.get(url, headers=headers, timeout=10, allow_redirects=False)

#         # retry 5 times with  
#         for _ in range(3):
#             time.sleep(_*2) # max wait 6s
#             url_session.cookies.clear()
#             response = url_session.get(url, headers=headers, timeout=10, allow_redirects=False)
#             if 200 <= response.status_code < 300: 
#                 return True 
    
#     except requests.RequestException as e:
#         return False
    
# def is_generated_page(url):

#     # criteria 1: query or search operator 
#     def contains_query_optr(url): 
#         parsed_url = urlparse(url)
#         if len(parse_qs(parsed_url.query)) > 2: 
#             return True
#         if "search" in parsed_url.path or "query" in parsed_url.query:  
#             return True
    
#     # criteria 2: link structure 
#     def is_mostly_links(soup):
#         # links outnumber paragraphs significantly, assume it's a generated page
#         links = soup.find_all("a")
#         paragraphs = soup.find_all("p")
#         text_length = len(soup.get_text(strip=True))
#         return len(links) > 5 * len(paragraphs) and text_length < 50

#     # c1: url link inpsection 
#     if contains_query_optr(url):  
#         return True 
    
#     # c2-c3: bs4 related processing 
#     try:
#         response = requests.get(url, timeout=10)
#         soup = BeautifulSoup(response.text, "html.parser")
#     except requests.RequestException:
#         return True
#     if is_mostly_links(soup): 
#         return True 
#     return False

def validate_date(date_str): 
    try:
        # Parse the date using the specified format
        date = datetime.strptime(date_str, "%m/%d/%Y")
        # Check if the date is within 1 year from the current time
        now = datetime.now() 
        past_year = now - timedelta(days=365)
        if past_year <= date <= now:
            return date, True 
        else:
            return "Invalid date. Date submitted is either too old (older than 1 year) or is invalid (future time)", False
    except ValueError:
        return "Invalid date. Please format date input as MM/DD/YYYY", False
    
def validate_timestamp(timestamp_str): 
    try:
        # Parse the timestamp using the specified format
        timestamp = datetime.strptime(timestamp_str, "%H:%M %m/%d/%Y")
        return timestamp, True 
    except ValueError:
        return "Invalid timestamp format. Use hh:mm. (24 hours format)", False

#############################################
############# Backend Methods ###############
#############################################

# API key forward
@app.route('/get-api-key', methods=['GET'])
def get_api_key():
    api_key = os.getenv("API_KEY")
    return jsonify({"api_key": api_key})


# Get number of entry per submission 
@app.route('/get-num-entry', methods=['GET'])
def get_num_entry():
    num_entry = os.getenv("NUM_ENTRY")
    return jsonify({"num_entry": num_entry})


# authenticate to reach submission forum 
@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.json
    api_key = data.get("api_key")
    worker_id = data.get("worker_id", "").strip()

    if not worker_id:
        return jsonify({"error": "Worker ID is required!"}), 400

    response = make_response(jsonify({"message": "Worker ID saved!"}))
    response.set_cookie("worker_id", worker_id, max_age=60*60*24*365, httponly=True, samesite="Lax")  # 1-year cookie

    if api_key in VALID_API_KEYS:
        session['authenticated'] = True  
        response = make_response(jsonify({"message": "Authentication successful!"}))
        response.set_cookie("worker_id", worker_id, max_age=60*60*24*365, httponly=True, samesite="Lax")  # 1-year cookie
        return response, 200
    else:
        return jsonify({"error": "Invalid API key!"}), 401


# check user submissions 
@app.route('/submission_count', methods=['GET'])
def get_submission_count():
    user_id = request.cookies.get("user_id")
    submission_count = int(request.cookies.get("submission_count", 0))
    return jsonify({"user_id": user_id, "submission_count": submission_count})


# check if the submission date is valid 
@app.route('/validate_date', methods=['POST'])
def validate_date_entry(): 

    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized access!"}), 403

    data = request.json
    date_str = data.get("date", "").strip()
    date, valid_date = validate_date(date_str)
    if not valid_date: 
        return jsonify({"error": date}), 400
    
    # check if the date is submitted by this user already 
    worker_id = request.cookies.get("worker_id")
    user_id = request.cookies.get("user_id")
    existing_submission = DATEs.query.filter_by(user_id=user_id, worker_id=worker_id, date=date_str).first()
    if existing_submission:
        return jsonify({"error": "Invalid submission: you have already submitted the browsing history for this date."}), 400

    response = make_response(jsonify({
        "date": date_str,
    }))
    return response


# check if an url-time entry is valid   
@app.route('/validate', methods=['POST'])
def validate_entry():

    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized access!"}), 403

    data = request.json
    url = data.get("url", "").strip()
    time_str = data.get("timestamp", "").strip()
    date_str = data.get("date", "").strip()
    timestamp_str = f"{time_str} {date_str}"

    # check if user input is valid as a submission record 
    if not url or not timestamp_str:
        return jsonify({"error": "Both URL and timestamp are required."}), 400
    timestamp, valid_time = validate_timestamp(timestamp_str)
    if not valid_time:
        # for invalid timestamp, str returned is error cause 
        return jsonify({"error": timestamp}), 400
    if not validators.url(url): 
        return jsonify({"error": "Please input a valid URL."}), 400
        
    # check if url accessible 
    validate_url, msg = url_validator(url)
    if not validate_url: 
        return jsonify({"error": msg}), 400

    unix_time = str(int(timestamp.timestamp()))

    worker_id = request.cookies.get("worker_id")
    # uid - persistent 
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())

    # if duplicate -> count as invalid
    existing_urls = URLs.query.filter_by(user_id=user_id, worker_id=worker_id, url=url, day_time=time_str).first()
    if existing_urls:
        return jsonify({"error": "Invalid submission: you have already submitted this URL at the exact same time of another day."}), 400

    response = make_response(jsonify({
        "url": url,
        "user_id": user_id, 
        "worker_id": worker_id, 
        "day_time": time_str, 
        "date": date_str, 
        "timestamp": unix_time, 
    }))
    return response
    

# submit a date for a submission entry: ensure no repeated dates
@app.route('/submit_date', methods=['POST'])
def submit_date():

    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized access!"}), 403

    data = request.json
    user_id = data.get("user_id", {})
    worker_id = data.get("worker_id", {})
    date = data.get("date", {})

    if not user_id or not worker_id or not date: 
        return jsonify({"error": "Submission date input is corrupted!"}), 403
    
    # save 
    new_record = DATEs(user_id=user_id, worker_id=worker_id, date=date)
    db.session.add(new_record)
    db.session.commit()
    response = make_response(jsonify({
        "message": "DATEs workload saved successfully!",
        "user_id": user_id,
        "worker_id": worker_id,
        "date": date, 
    }))
    return response 


# handle text submission
@app.route('/submit', methods=['POST'])
def submit_text():

    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized access!"}), 403

    data = request.json
    submission = data.get("submissions", {})

    # save each entry 
    for pair in submission: 

        user_id, worker_id = submission[pair]["user_id"], submission[pair]["worker_id"]
        url, unix_time = submission[pair]["url"], submission[pair]["timestamp"]
        date, day_time = submission[pair]["date"], submission[pair]["day_time"]

        if not user_id or not worker_id or not url or not unix_time or not day_time: 
            return jsonify({"error": "Submission corrupted!"}), 403

        # save 
        new_record = URLs(user_id=user_id, worker_id=worker_id, url=url, timestamp=unix_time, date=date, day_time=day_time)
        db.session.add(new_record)
        db.session.commit()

    # update number of valid submission (no matter in domain or not)
    submission_count = int(request.cookies.get("submission_count", 0)) + 1

    response = make_response(jsonify({
        "message": "URL saved successfully!",
        "user_id": user_id,
        "worker_id": worker_id,
        "submission_count": submission_count
    }))
    
    response.set_cookie("user_id", user_id, max_age=60*60*24*365, httponly=True, samesite="Lax")  # 1-year cookie
    response.set_cookie("submission_count", str(submission_count), max_age=60*60*24*365, httponly=True, samesite="Lax")

    return response


if __name__ == '__main__':
    app.run(debug=True)
