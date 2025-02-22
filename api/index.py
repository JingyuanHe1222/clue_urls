
from datetime import datetime
import pickle

from urllib.parse import urlparse

from flask import Flask, request, jsonify, render_template, make_response
import sqlite3
import uuid


app = Flask(__name__)

# init the database
def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id TEXT, 
            url TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def load_domains(file_path): 
    with open(file_path, "rb") as f:
        domains = pickle.load(f)
    return domains 


init_db()
domains = load_domains('domains/domains_8.pickle')
# {'www.cmu.edu', 'www.airbnb.com', 'gradescope.com', 'bing.com', 'google.com', 'about.meta.com', 'yahoot.com', 'wandb.ai'}

# interface homepage
@app.route('/')
def index():
    return render_template('index.html')

# check user submissions 
@app.route('/submission_count', methods=['GET'])
def get_submission_count():
    user_id = request.cookies.get("user_id")
    submission_count = int(request.cookies.get("submission_count", 0))
    return jsonify({"user_id": user_id, "submission_count": submission_count})


# Handle text submission
@app.route('/submit', methods=['POST'])
def submit_text():
    data = request.json
    url = data.get("url", "").strip()
    timestamp_str = data.get("timestamp", "").strip()

    # check if user input is valid as a submission record 
    if not url or not timestamp_str:
        return jsonify({"error": "Both URL and timestamp are required."}), 400
    try:
        timestamp = datetime.strptime(timestamp_str, "%H:%M %m/%d/%Y")
    except ValueError:
        return jsonify({"error": "Invalid timestamp format. Use hh:mm MM/DD/YYYY. (24 hours format)"}), 400

    unix_time = int(timestamp.timestamp()) 

    # uid - persistent 
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())

    # store if url domain in ClueWeb
    url_domain = urlparse(url).netloc
    if url_domain in domains:

        # connect  to database
        conn = sqlite3.connect("data.db")
        c = conn.cursor()

        # check if there's a duplicated submission 
        c.execute("SELECT COUNT(*) FROM submissions WHERE user_id = ? AND url = ? AND timestamp = ?", 
                    (user_id, url, unix_time))
        duplicate_count = c.fetchone()[0]
        # if duplicate -> count as invalid
        if duplicate_count > 0:
            conn.close()
            return jsonify({"error": "Invalid submission: you have already submitted this URL at the exact same timestamp."}), 400

        # save 
        c.execute("INSERT INTO submissions (user_id, url, timestamp) VALUES (?, ?, ?)", (user_id, url, unix_time))
        conn.commit()
        conn.close()

    # update number of valid submission (no matter in domain or not)
    submission_count = int(request.cookies.get("submission_count", 0)) + 1
    
    response = make_response(jsonify({"message": f"URL saved successfully!", "user_id": user_id, "submission_count": submission_count}))
    response.set_cookie("user_id", user_id, max_age=60*60*24*365, httponly=True, samesite="Lax")  # 1-year cookie
    response.set_cookie("submission_count", str(submission_count), max_age=60*60*24*365, httponly=True, samesite="Lax")

    return response

if __name__ == '__main__':
    app.run(debug=True)
