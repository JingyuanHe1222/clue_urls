
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os 
import re
import requests
import time 
import json 
import uuid
import validators
from threading import Lock

from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

from flask import Flask, session, request, jsonify, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect



#############################################
#################### Env ####################
#############################################

# ### env var ###
load_dotenv(dotenv_path=".env.local")

VALID_API_KEYS = [os.getenv("API_KEY")]
TABLE_NAME = os.getenv("TABLE_NAME")
DATE_TABLE_NAME = os.getenv("DATE_TABLE_NAME")
ID_TABLE_NAME = os.getenv("ID_TABLE_NAME")
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
# lock to prevent access to the table at the same time
lock = Lock()

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


class IDs(db.Model):
    __tablename__ = ID_TABLE_NAME
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(80), nullable=False)
    worker_id = db.Column(db.String(80), nullable=False)  # Add this line

       
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
    return render_template('landing_consent_2.html')

# landing page for API authentication 
@app.route('/auth')
def landing_auth():
    # This function renders the HTML template dynamically
    return render_template('landing_auth.html')

# url submission pages
@app.route('/submission')
def submission_page():
    if not session.get('authenticated'):
        return redirect(url_for('index'))  # Redirect to API key page if not authenticated
    # once enter submission page, get user_id cookie 
    return render_template('submission.html')

@app.route('/edge_submission')
def edge_submission_page():
    if not session.get('authenticated'):
        return redirect(url_for('index'))  # Redirect to API key page if not authenticated
    # once enter submission page, get user_id cookie 
    return render_template('submission_edge.html')

@app.route('/chrome_submission')
def chrome_submission_page():
    if not session.get('authenticated'):
        return redirect(url_for('index'))  # Redirect to API key page if not authenticated
    # once enter submission page, get user_id cookie 
    return render_template('submission_chrome.html')

@app.route('/manual_submission')
def manual_submission_page():
    if not session.get('authenticated'):
        return redirect(url_for('index'))  # Redirect to API key page if not authenticated
    # once enter submission page, get user_id cookie 
    return render_template('submission_2.html')


# Exit study 
@app.route('/exit-page')
def exit_page():
    return render_template('exit_page.html')



#############################################
############### Utility Functions ###########
#############################################

# User-Agent header to mimic a browser
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

# Compile a regular expression pattern (case insensitive)
url_keywords = ["sso", "signin", "login"]
pattern = re.compile("|".join(url_keywords), re.IGNORECASE)

def is_url_accessible(url):
    try:
        response = requests.get(url, headers=headers, timeout=4, allow_redirects=True)
        # simple check for authentication upon redirection 
        if response.url != url: 
            if pattern.search(response.url):
                return False
            else:
                return True 
        return 200 <= response.status_code < 300
    except requests.RequestException as e:
        return False
    
def is_landing_page(url):
    parsed = urlparse(url)
    return parsed.path in ["", "/"]  # Exclude root pages
    
def is_generated_page(url):

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
        text_length = len(soup.get_text(strip=True))
        return len(links) > 5 * len(paragraphs) and text_length < 50

    # c1: url link inpsection 
    if contains_query_optr(url) or url_keywords(url):  
        return True 
    
    # c2-c3: bs4 related processing 
    try:
        response = requests.get(url, headers=headers, timeout=4, allow_redirects=False)
        soup = BeautifulSoup(response.text, "html.parser")
    except requests.RequestException:
        return True
    if is_mostly_links(soup): 
        return True 
    return False


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
    
def validate_iso_timestamp(timestamp_str, date): 
    try: 
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        # not the same date as above 
        if dt.date() != datetime.strptime(date, "%m/%d/%Y").date(): 
            return None, None, 2
        unix_time = str(int(dt.timestamp()))
        time_str = dt.strftime("%H:%M")
        return unix_time, time_str, 1
    except: 
        return None, None, 0
    

def validate_unix_timestamp(timestamp): 
    try: 
        ts = datetime.fromtimestamp(timestamp)
        time_str = ts.strftime("%H:%M")
        return timestamp, ts.date(), time_str, 1
    except: 
        return None, None, None, 0
    




#############################################
############# Backend Methods ###############
#############################################

# API key forward
@app.route('/get-api-key', methods=['GET'])
def get_api_key():
    api_key = os.getenv("API_KEY")
    session["api_key_generated"] = True
    return jsonify({"api_key": api_key})


# Check the consent and study requirement 
@app.route('/submit-consent', methods=['POST'])
def submit_consent():
    if request.form.get('age') != 'yes': 
        return jsonify({"error": "You do not meet the age requirement of this study."}), 400
    if request.form.get('loc_and_lang') != 'yes': 
        return jsonify({"error": "You do not meet the location or language requirement of this study."}), 400
    if request.form.get('policy') != 'yes':
        return jsonify({"error": "You do not meet the policy requirement of this study."}), 400
    if request.form.get('commitment') != 'yes': 
        return jsonify({"error": "You do not commit to the study URL submission requirements."}), 400
    if request.form.get('submission_policy') != 'yes': 
        return jsonify({"error": "You do not commit to the study URL submission policy requirements."}), 400
    response = make_response(jsonify({"message": "Form requirement met!"}))        
    return response, 200


# authenticate to reach submission forum 
@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.json
    api_key = data.get("api_key")
    worker_id = data.get("worker_id", "").strip()

    if not worker_id:
        return jsonify({"error": "Worker ID is required!"}), 400

    if api_key in VALID_API_KEYS:
        session['authenticated'] = True  
        response = make_response(jsonify({"message": "Authentication successful!"}))        
        # setup uuid
        exist_user = IDs.query.filter_by(worker_id=worker_id).first()
        if exist_user: 
            user_id = exist_user.user_id
            print("existing user: ", exist_user.user_id) ### 
        else: 
            user_id = str(uuid.uuid4()) 
            print("new user: ", user_id) ###
            # store to ID map also 
            uuid_map = IDs(user_id=user_id, worker_id=worker_id)
            db.session.add(uuid_map)
            db.session.commit()
        # set cookies 
        response.set_cookie("user_id", user_id, max_age=60*60*24*365, httponly=True, samesite="Lax")  # 1-year cookie
        response.set_cookie("worker_id", worker_id, max_age=60*60*24*365, httponly=True, samesite="Lax")  # 1-year cookie
        return response, 200
    else:
        return jsonify({"error": "Invalid API key!"}), 401


# Get number of entry per submission 
@app.route('/get-num-entry', methods=['GET'])
def get_num_entry():
    num_entry = os.getenv("NUM_ENTRY")
    return jsonify({"num_entry": num_entry})


# check user submissions 
@app.route('/submission_count', methods=['GET'])
def get_submission_count():
    user_id = request.cookies.get("user_id", "")
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

    with lock: 
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
    # check if user input is a valid url 
    if not validators.url(url): 
        return jsonify({"error": "Please input a valid URL."}), 400
        
    # # check if url accessible 
    # if not is_url_accessible(url): 
    #     return jsonify({"error": f"Invalid submission: URL submitted is not accessiable. Please make sure this is a public URL or all contents loaded correctly in the page."}), 400
    
    # check if url not generated 
    if is_generated_page(url): 
        return jsonify({"error": f"Invalid submission: URL submitted is generated page / online files / search results, etc. Please refer to the Submission Must-Know FAQ. "}), 400

    if is_landing_page(url): 
        return jsonify({"error": f"Invalid submission: URL submitted is a landing page (e.g. https://www.reddit.com/). Please submit a page over specific item or content."}), 400


    unix_time = str(int(timestamp.timestamp()))

    worker_id = request.cookies.get("worker_id")
    # uid - persistent 
    user_id = request.cookies.get("user_id")
    # if not user_id:
    #     user_id = str(uuid.uuid4())

    # if duplicate -> count as invalid
    with lock: 
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
    with lock: 
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
        with lock: 
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
    
    # response.set_cookie("user_id", user_id, max_age=60*60*24*365, httponly=True, samesite="Lax")  # 1-year cookie
    response.set_cookie("submission_count", str(submission_count), max_age=60*60*24*365, httponly=True, samesite="Lax")

    return response


@app.route('/validate_and_submit_edge', methods=['POST'])
def validate_and_submit_edge(): 
    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized access!"}), 403

    data = request.json
    url = data.get("urlInput", "").strip()
    date_str = data.get("dateInput", "").strip()
    
    valid_urls = []
    url_lines = url.split("\n")

    if len(url_lines) == 0: 
        return jsonify({"error": "No input. "}), 400

    for url_line in url_lines: 

        try: 
            parts = url_line.strip().split(",")
            timestamp_str = parts[0].strip()
            url = parts[1].strip()
        except IndexError: 
            return jsonify({"error": "Your input does not follow the format requirement."}), 400

        # check validity of the URL
        if not url or not validators.url(url): 
            continue 
        # heck validity of time stamp 
        if not timestamp_str:
            continue 
        unix_time, day_time, valid_time = validate_iso_timestamp(timestamp_str, date_str)
        if not valid_time: 
            continue 
        elif valid_time == 2: 
            return jsonify({"error": "Make sure the browsing history you submit has the same date as the input date on top."}), 400
            
        # if duplicate record in the submission 
        if (url, day_time, unix_time) in valid_urls: 
            continue 

        # # check if url accessible 
        # if not is_url_accessible(url): 
        #     return jsonify({"error": f"Invalid submission: URL submitted is not accessiable. Please make sure this is a public URL or all contents loaded correctly in the page."}), 400
        
        # check if url not generated 
        if is_generated_page(url): 
            continue 

        if is_landing_page(url): 
            continue 

        # add to valid url list
        valid_urls.append((url, day_time, unix_time))

    # if long enough to submit
    if len(valid_urls) < 10: 
        return jsonify({"error": f"Only {len(valid_urls)} URLs are valid. Please add more browsing records of the same day."}), 400

    # uid - persistent 
    worker_id = request.cookies.get("worker_id")
    user_id = request.cookies.get("user_id")
    
    # submit date
    new_record = DATEs(user_id=user_id, worker_id=worker_id, date=date_str)
    with lock: 
        db.session.add(new_record)
        db.session.commit()

    # submit urls 
    for url_pair in valid_urls: 
        url, day_time, unix_time = url_pair
        new_record = URLs(user_id=user_id, worker_id=worker_id, url=url, timestamp=unix_time, date=date_str, day_time=day_time)
        with lock: 
            db.session.add(new_record)
            db.session.commit()

    print(f"Successfully submitted {len(valid_urls)} urls...")

    
    # update number of valid submission (no matter in domain or not)
    submission_count = int(request.cookies.get("submission_count", 0)) + 1

    response = make_response(jsonify({
        "message": "URL saved successfully!",
        "user_id": user_id,
        "worker_id": worker_id,
        "submission_count": submission_count
    }))
    
    # response.set_cookie("user_id", user_id, max_age=60*60*24*365, httponly=True, samesite="Lax")  # 1-year cookie
    response.set_cookie("submission_count", str(submission_count), max_age=60*60*24*365, httponly=True, samesite="Lax")

    return response




@app.route('/validate_and_submit_chrome', methods=['POST'])
def validate_and_submit_chrome(): 
    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized access!"}), 403

    data = request.json
    url = data.get("urlInput", "").strip()
    
    valid_urls = defaultdict(list)

    try: 
        url = "[" + url.strip().rstrip(",") + "]"
        url_lines = json.loads(url)
    except: 
        return jsonify({"error": "Your input does not follow the format requirement."}), 400

    if len(url_lines) == 0: 
        return jsonify({"error": "No input. "}), 400

    for url_dict in url_lines: 

        try: 
            url = url_dict["url"]
            timestamp_str = url_dict["time_usec"]
            timestamp = int(timestamp_str) // 1_000_000
        except IndexError: 
            return jsonify({"error": "Your input does not follow the format requirement."}), 400

        # check validity of the URL
        if not url or not validators.url(url): 
            continue 
        # heck validity of time stamp 
        if not timestamp:
            continue 
        unix_time, date, day_time, valid_time = validate_unix_timestamp(timestamp)
        if not valid_time: 
            continue 

        # if duplicate record in the submission 
        if (url, day_time, unix_time) in valid_urls[date]: 
            continue 

        # # check if url accessible 
        # if not is_url_accessible(url): 
        #     return jsonify({"error": f"Invalid submission: URL submitted is not accessiable. Please make sure this is a public URL or all contents loaded correctly in the page."}), 400
        
        # check if url not generated 
        if is_generated_page(url): 
            continue 

        if is_landing_page(url): 
            continue 

        # add to valid url list
        valid_urls[date].append((url, day_time, unix_time))

    # uid - persistent 
    worker_id = request.cookies.get("worker_id")
    user_id = request.cookies.get("user_id")

    # for each date submitted 
    success_submissions = 0
    over_time = []
    already_submitted = []
    less_than = []
    for date in valid_urls: 

        date_str = date.strftime("%m/%d/%Y")
        # if date is not within expected time or sequences is too short: abandon 
        if not validate_date(date_str): 
            over_time.append(date_str)
            continue 
        if len(valid_urls[date]) < 10: 
            less_than.append(date_str)
            continue 
            
        # check if date has been submitted previously 
        with lock: 
            existing_submission = DATEs.query.filter_by(user_id=user_id, worker_id=worker_id, date=date_str).first()
        if existing_submission:
            already_submitted.append(date_str)
            continue 

        # submit date
        new_record = DATEs(user_id=user_id, worker_id=worker_id, date=date_str)
        with lock: 
            db.session.add(new_record)
            db.session.commit()

        # submit urls of this date 
        for url_pair in valid_urls[date]: 
            url, day_time, unix_time = url_pair

            new_record = URLs(user_id=user_id, worker_id=worker_id, url=url, timestamp=unix_time, date=date_str, day_time=day_time)
            with lock: 
                db.session.add(new_record)
                db.session.commit()
            print(f"Successfully submitted {len(valid_urls[date])} urls on date {date}...")

        success_submissions += 1

    if success_submissions < 1: 
        # structure error msg 
        error_msg = ""
        if len(over_time) > 0: 
            over_time = ",".join(over_time)
            error_msg = f"Dates of invalid timeframe: {over_time}; "
        if len(already_submitted) > 0: 
            already_submitted = ",".join(already_submitted)
            error_msg += f"Dates already submitted: {already_submitted}; "
        if len(less_than) > 0: 
            less_than = ",".join(less_than)
            error_msg += f"Dates whose valid URLs sequences less than 10: {less_than}; "

        return jsonify({"error": f"No successful submissions are made. {error_msg} "}), 400
    
    # update number of valid submission (no matter in domain or not)
    submission_count = int(request.cookies.get("submission_count", 0)) + 1

    response = make_response(jsonify({
        "message": "URL saved successfully!",
        "user_id": user_id,
        "worker_id": worker_id,
        "submission_count": submission_count
    }))
    
    # response.set_cookie("user_id", user_id, max_age=60*60*24*365, httponly=True, samesite="Lax")  # 1-year cookie
    response.set_cookie("submission_count", str(submission_count), max_age=60*60*24*365, httponly=True, samesite="Lax")

    return response



if __name__ == '__main__':
    app.run(debug=True)
