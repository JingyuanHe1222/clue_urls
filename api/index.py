
from datetime import datetime
from dotenv import load_dotenv
import os 
import uuid
import requests
import validators

from flask import Flask, session, request, jsonify, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect


# ### env var ###
load_dotenv(dotenv_path=".env.local")

VALID_API_KEYS = [os.getenv("API_KEY")]
TABLE_NAME = os.getenv("TABLE_NAME")
POSTGRES_URL = os.getenv("POSTGRES_URL")
if POSTGRES_URL and POSTGRES_URL.startswith("postgres://"):
    POSTGRES_URL = POSTGRES_URL.replace("postgres://", "postgresql://", 1)

print(f"POSTGRES_URL: {POSTGRES_URL}")


# ### app ###
app = Flask(__name__)

print("app created...")


# ### datastore ### 
app.secret_key = VALID_API_KEYS
app.config["SQLALCHEMY_DATABASE_URI"] = POSTGRES_URL
# init SQLAlchemy 
db = SQLAlchemy(app)

# data model 
class URLs(db.Model):
    __tablename__ = 'recsys_urls_clueweb_filtered'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(80), nullable=False)
    worker_id = db.Column(db.String(80), nullable=False)  # Add this line
    url = db.Column(db.String(2083), nullable=False)
    timestamp = db.Column(db.String(80), nullable=False) 
                          

# create model 
with app.app_context():
    inspector = inspect(db.engine)
    if not inspector.has_table("urls"):
        db.create_all()

print("table created...")

# ### UI Interface ### 

# landing page 
@app.route('/')
def index():
    return render_template('landing_2.html')

# authenticate to reach submission forum 
@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.json
    api_key = data.get("api_key")

    if api_key in VALID_API_KEYS:
        session['authenticated'] = True  
        return jsonify({"message": "Authentication successful!"}), 200
    else:
        return jsonify({"error": "Invalid API key!"}), 401

# url submission page 
@app.route('/submission')
def submission_page():
    if not session.get('authenticated'):
        return redirect(url_for('index'))  # Redirect to API key page if not authenticated
    return render_template('submission_2.html')


# check user submissions 
@app.route('/submission_count', methods=['GET'])
def get_submission_count():
    user_id = request.cookies.get("user_id")
    submission_count = int(request.cookies.get("submission_count", 0))
    return jsonify({"user_id": user_id, "submission_count": submission_count})


# Handle text submission
@app.route('/submit', methods=['POST'])
def submit_text():

    if not session.get('authenticated'):
        return jsonify({"error": "Unauthorized access!"}), 403

    data = request.json
    url = data.get("url", "").strip()
    timestamp_str = data.get("timestamp", "").strip()
    worker_id = data.get("worker_id", "").strip()

    # check if user input is valid as a submission record 
    if not url or not timestamp_str or not worker_id:
        return jsonify({"error": "URL, timestamp, and worker ID are required."}), 400
    try:
        timestamp = datetime.strptime(timestamp_str, "%H:%M %m/%d/%Y")
    except ValueError:
        return jsonify({"error": "Invalid timestamp format. Use hh:mm MM/DD/YYYY. (24 hours format)"}), 400
    if not validators.url(url): 
        return jsonify({"error": "Please input a valid URL."}), 400

    def is_url_accessible(url):
        try:
            url_session = requests.Session()
            # User-Agent header to mimic a browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
            }
            # request with headers and session
            url_session.cookies.clear()
            response = url_session.get(url, headers=headers, timeout=10, allow_redirects=False)

            breakpoint()
            # output code in log 
            print("response.status_code: ", response.status_code)

            if response.status_code in [401, 403]:  
                return False
            return response.status_code == 200
        
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return False
        
    if not is_url_accessible(url): 
        return jsonify({"error": f"Invalid submission: URL submitted is not accessiable. Please make sure this is a public URL."}), 400


    unix_time = str(int(timestamp.timestamp()))

    # uid - persistent 
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())

    # if duplicate -> count as invalid
    existing_urls = URLs.query.filter_by(user_id=user_id, url=url, timestamp=unix_time).first()
    if existing_urls:
        return jsonify({"error": "Invalid submission: you have already submitted this URL at the exact same timestamp."}), 400

    # save 
    new_record = URLs(user_id=user_id, worker_id=worker_id, url=url, timestamp=unix_time)
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
    response.set_cookie("worker_id", worker_id, max_age=60*60*24*365, httponly=True, samesite="Lax")  # 1-year cookie
    response.set_cookie("submission_count", str(submission_count), max_age=60*60*24*365, httponly=True, samesite="Lax")

    return response


if __name__ == '__main__':
    app.run(debug=True)
