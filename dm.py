from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for
import threading, os, time, json, requests

app = Flask(__name__)
app.secret_key = "your_secret_key"

USER_FILE = "user.txt"
RUNNING_SCRIPTS_FOLDER = "running_scripts"
if not os.path.exists(RUNNING_SCRIPTS_FOLDER):
    os.makedirs(RUNNING_SCRIPTS_FOLDER)

def check_login(username, password):
    if not os.path.exists(USER_FILE):
        return False
    with open(USER_FILE, "r") as f:
        for line in f:
            stored_user, stored_pass = line.strip().split(":")
            if username == stored_user and password == stored_pass:
                return True
    return False

def get_running_scripts(username):
    running_scripts = []
    for file in os.listdir(RUNNING_SCRIPTS_FOLDER):
        if file.startswith(username):
            with open(os.path.join(RUNNING_SCRIPTS_FOLDER, file), "r") as f:
                script_data = json.load(f)
                running_scripts.append(script_data)
    return running_scripts

def save_running_script(username, script_data):
    script_id = script_data['id']
    script_file_path = os.path.join(RUNNING_SCRIPTS_FOLDER, f"{username}_{script_id}.json")
    with open(script_file_path, "w") as f:
        json.dump(script_data, f)

def remove_running_script(username, script_id):
    path = os.path.join(RUNNING_SCRIPTS_FOLDER, f"{username}_{script_id}.json")
    if os.path.exists(path): os.remove(path)

def send_messages(script_data):
    cookies_str = script_data["cookies"]
    messages = script_data["messages"]
    convo_id = script_data["convo_id"]
    haters_name = script_data["haters_name"]
    speed = script_data["speed"]

    cookie_dict = dict(x.strip().split("=", 1) for x in cookies_str.split("; ") if "=" in x)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    fb_dtsg = "NA"  # We'll try to bypass this

    message_index = 0
    while True:
        if not messages:
            print("No messages!")
            break

        message = f"{haters_name} {messages[message_index]}"
        data = {
            "body": message,
            "tids": f"cid.c.{convo_id}",
            "wwwupp": "C3",
            "ids[0]": convo_id,
            "action_type": "ma-type:user-generated-message",
            "ephemeral_ttl_mode": "0",
            "fb_dtsg": fb_dtsg,
            "send": "Send",
        }

        try:
            res = requests.post("https://www.facebook.com/messages/send/", headers=headers, cookies=cookie_dict, data=data)
            if res.status_code == 200:
                print(f"✅ Sent: {message}")
            else:
                print(f"❌ Failed: {res.status_code}, {res.text}")
        except Exception as e:
            print(f"❌ Error: {e}")

        message_index = (message_index + 1) % len(messages)
        time.sleep(speed)

def start_running_scripts_on_restart():
    for file in os.listdir(RUNNING_SCRIPTS_FOLDER):
        if file.endswith('.json'):
            with open(os.path.join(RUNNING_SCRIPTS_FOLDER, file), "r") as f:
                script_data = json.load(f)
                threading.Thread(target=send_messages, args=(script_data,), daemon=True).start()

@app.route('/')
def index():
    if not session.get("username"):
        return render_template_string(LOGIN_HTML)
    running_scripts = get_running_scripts(session.get("username"))
    return render_template_string(MAIN_HTML, running_scripts=running_scripts)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    if not check_login(username, password):
        return "Invalid login", 403
    session['username'] = username
    return redirect(url_for('index'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop("username", None)
    return redirect(url_for('index'))

@app.route('/start', methods=['POST'])
def start_messaging():
    if not session.get("username"):
        return jsonify({"message": "Login Required"}), 403

    username = session.get("username")
    convo_id = request.form.get('convoId')
    haters_name = request.form.get('hatersName')
    speed = int(request.form.get('speed'))
    cookies_str = request.form.get('cookies')
    messages_raw = request.form.get('messages')
    messages = [line.strip() for line in messages_raw.splitlines() if line.strip()]
    script_id = str(int(time.time()))

    script_data = {
        "id": script_id,
        "convo_id": convo_id,
        "haters_name": haters_name,
        "cookies": cookies_str,
        "messages": messages,
        "speed": speed
    }

    save_running_script(username, script_data)
    threading.Thread(target=send_messages, args=(script_data,), daemon=True).start()
    return redirect(url_for('index'))

@app.route('/stop', methods=['POST'])
def stop_script():
    if not session.get("username"):
        return jsonify({"message": "Login Required"}), 403
    script_id = request.form.get("script_id")
    remove_running_script(session.get("username"), script_id)
    return redirect(url_for('index'))

start_running_scripts_on_restart()

LOGIN_HTML = '''
<style>
body { background: black; color: lime; font-family: monospace; font-size: 22px; padding: 20px; }
input, button { background: black; color: lime; border: 1px solid lime; padding: 10px; margin: 5px; }
</style>
<h2>Login</h2>
<form action="/login" method="POST">
    Username: <input type="text" name="username" required><br>
    Password: <input type="password" name="password" required><br>
    <button type="submit">Login</button>
</form>
'''

MAIN_HTML = '''
<style>
body { background: black; color: lime; font-family: monospace; font-size: 18px; padding: 20px; }
input, textarea, button { background: black; color: lime; border: 1px solid lime; padding: 8px; margin: 5px; width: 100%; }
</style>
<h2>Welcome, {{ session['username'] }}!</h2>
<form action="/logout" method="POST"><button type="submit">Logout</button></form>
<h3>Start New Script</h3>
<form action="/start" method="POST">
    Convo ID: <input type="text" name="convoId" required><br>
    Haters Name: <input type="text" name="hatersName" required><br>
    Speed (seconds): <input type="number" name="speed" required><br>
    Cookies: <textarea name="cookies" rows="4" required></textarea><br>
    Messages (one per line): <textarea name="messages" rows="6" required></textarea><br>
    <button type="submit">Start Script</button>
</form>

<h3>Running Scripts</h3>
{% for script in running_scripts %}
    <p>Script ID: {{ script['id'] }} | Convo: {{ script['convo_id'] }}</p>
    <form action="/stop" method="POST">
        <input type="hidden" name="script_id" value="{{ script['id'] }}">
        <button type="submit">Stop</button>
    </form>
{% endfor %}
'''

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # ✅ Render-compatible port
    app.run(host="0.0.0.0", port=port)
