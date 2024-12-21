from flask import Flask, render_template, request, url_for, flash, redirect, session, make_response, jsonify
import requests
from config.config import SECRET_KEY
import time

BACKEND_URL = "http://127.0.0.1:8000"

app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route("/")
def index():
    if "token" not in session:
        flash(f"You need to log in first", "warning")
        return redirect(url_for("login"))
    response = requests.get(f"{BACKEND_URL}/messages/overview", json={
            "token": session["token"]
        })
    if response.status_code == 200:
        return render_template('index.html', conversations=response.json().get('conversations',[]))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if "token" in session:
            flash(f"You are already logged in, if you want to log into another account please log out first", "warning")
            return redirect(url_for("index"))
    if request.method == 'POST':
        headers ={}
        if "token" in session:
            headers["Authorization"] = f"Bearer {session["token"]}"
        payload ={
            "username": request.form['username'],
            "password": request.form['password']
        }
        api_url = f"{BACKEND_URL}/login"

        response = requests.post(api_url, json=payload, headers=headers)

        if response.status_code == 200:
            session['token'] = response.cookies['token']
            flash(f"Login successful!", "success")
            return redirect(url_for("index"))
        else:
            flash(f"Error: {response.json().get('detail', 'Login failed')}", "danger")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if "token" in session:
        flash(f"You can not create a new account while you are logged in, please log out first in order to create a new account", "warning")
        return redirect(url_for("index"))
    if request.method == 'POST':
        response = requests.post(f"{BACKEND_URL}/register", json={
            "username": request.form['username'],
            "password": request.form['password']
        })

        if response.status_code == 200:
            flash("Registration successful!", "success")
            return redirect(url_for('login'))
        else:
            flash(f"Error: {response.json().get('detail', 'Registration failed')}", "danger")
    
    return render_template('register.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if "token" in session:
        session.pop('token', None)
        flash(f"Logout successful!", "success")
        return redirect(url_for("login"))
    flash(f"You can not log out when you are not logged in", "warning")
    return redirect(url_for("login"))

@app.route('/message/<int:partner_id>', methods=['GET', 'POST'])
def messages(partner_id):
    if "token" not in session:
        flash(f"You need to be logged in to send messages", "warning")
        return redirect(url_for("login"))
    response = requests.get(f"{BACKEND_URL}/messages", json={
            "token": session["token"],
            "partner_id":partner_id
        })
    if response.status_code == 401:
        flash("You need to login first", "warning")
        if "token" in session:
            session.pop("token", None)
        return redirect(url_for('login'))
    elif response.status_code == 200:
        return render_template('chat.html', messages=response.json().get('messages',[]), partner_id=partner_id)

@app.route('/send_message', methods=['POST'])
def send_message():
    # Ensure the token is provided
    if "token" not in session:
        flash(f"You need to log in first", "warning")
        return redirect(url_for("login"))

    token = session["token"]
    receiver_id = request.json["receiver_id"]
    content = request.json["content"]

    # Forward the message to FastAPI backend
    response = requests.post(f"{BACKEND_URL}/send", json={
        "token": token,
        "receiver_id": receiver_id,
        "content": content
    })

    # Handle the response from FastAPI
    if response.status_code == 200:
        return jsonify({"message": "Message sent successfully"}), 200
    else:
        return jsonify({"detail": "Failed to send message"}), response.status_code
        
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
