from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database setup
def init_db():
    conn = sqlite3.connect("dashboard.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        location TEXT NOT NULL,
        date TEXT NOT NULL
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS attendees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        event_id INTEGER,
        FOREIGN KEY(event_id) REFERENCES events(id)
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        deadline TEXT NOT NULL,
        status TEXT CHECK(status IN ('Pending', 'Completed')) DEFAULT 'Pending',
        attendee_id INTEGER,
        FOREIGN KEY(attendee_id) REFERENCES attendees(id)
    )""")
    conn.commit()
    conn.close()

# Signup route
@app.route("/", methods=['GET', 'POST'])
def signup():
    msg = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username and password:
            conn = sqlite3.connect("dashboard.db")
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                conn.close()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                msg = "Username already exists!"
        else:
            msg = "Please fill out all fields."
    return render_template("Signup.html", msg=msg)

# Login route
@app.route("/login", methods=['GET', 'POST'])
def login():
    msg = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect("dashboard.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        account = c.fetchone()
        conn.close()
        if account:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('home_page'))
        else:
            msg = "Invalid username or password!"
    return render_template("Login.html", msg=msg)

# Home route
@app.route("/home")
def home_page():
    if 'logged_in' in session:
        return render_template("Home.html")
    else:
        return redirect(url_for('login'))

# Events route
@app.route("/events", methods=['GET', 'POST'])
def events_page():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("dashboard.db")
    c = conn.cursor()

    if request.method == "POST":
        event_id = request.form.get("event_id")
        name = request.form["name"]
        description = request.form["description"]
        location = request.form["location"]
        date = request.form["date"]

        if event_id and event_id.strip():
            c.execute(
                "UPDATE events SET name=?, description=?, location=?, date=? WHERE id=?",
                (name, description, location, date, event_id),
            )
        else:
            c.execute(
                "INSERT INTO events (name, description, location, date) VALUES (?, ?, ?, ?)",
                (name, description, location, date),
            )
        conn.commit()

    c.execute("SELECT * FROM events")
    events = [
        dict(id=row[0], name=row[1], description=row[2], location=row[3], date=row[4])
        for row in c.fetchall()
    ]
    conn.close()

    return render_template("Events.html", events=events)

# Route for editing an event
@app.route("/edit_event/<int:event_id>", methods=['GET', 'POST'])
def edit_event(event_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("dashboard.db")
    c = conn.cursor()

    # Get the event details
    c.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = c.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        location = request.form['location']
        date = request.form['date']

        c.execute(
            "UPDATE events SET name=?, description=?, location=?, date=? WHERE id=?",
            (name, description, location, date, event_id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for('events_page'))

    conn.close()

    return render_template("EditEvent.html", event=event)

# Delete event route
@app.route("/delete_event/<int:event_id>")
def delete_event(event_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("dashboard.db")
    c = conn.cursor()
    c.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('events_page'))

# Attendees route
@app.route("/attendees", methods=['GET', 'POST'])
def attendees_page():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("dashboard.db")
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        event_id = request.form['event_id']
        c.execute("INSERT INTO attendees (name, event_id) VALUES (?, ?)", (name, event_id))
        conn.commit()

    c.execute("SELECT a.id, a.name, e.name FROM attendees a LEFT JOIN events e ON a.event_id = e.id")
    attendees = [{'id': row[0], 'name': row[1], 'event_name': row[2]} for row in c.fetchall()]

    c.execute("SELECT id, name FROM events")
    events = [{'id': row[0], 'name': row[1]} for row in c.fetchall()]
    conn.close()
    return render_template("Attendees.html", attendees=attendees, events=events)

# Delete attendee route
@app.route("/delete_attendee/<int:attendee_id>")
def delete_attendee(attendee_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("dashboard.db")
    c = conn.cursor()
    c.execute("DELETE FROM attendees WHERE id=?", (attendee_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('attendees_page'))

# Tasks route
@app.route("/tasks", methods=['GET', 'POST'])
def tasks_page():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("dashboard.db")
    c = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        deadline = request.form['deadline']
        status = request.form['status']
        attendee_id = request.form['attendee_id']
        c.execute("INSERT INTO tasks (name, deadline, status, attendee_id) VALUES (?, ?, ?, ?)",
                  (name, deadline, status, attendee_id))
        conn.commit()

    c.execute("SELECT t.id, t.name, t.deadline, t.status, a.name FROM tasks t LEFT JOIN attendees a ON t.attendee_id = a.id")
    tasks = [{'id': row[0], 'name': row[1], 'deadline': row[2], 'status': row[3], 'attendee_name': row[4]} for row in c.fetchall()]

    c.execute("SELECT id, name FROM attendees")
    attendees = [{'id': row[0], 'name': row[1]} for row in c.fetchall()]
    conn.close()

    return render_template("Tasks.html", tasks=tasks, attendees=attendees)

# Update task status route
@app.route("/update_task_status/<int:task_id>/<string:status>")
def update_task_status(task_id, status):
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect("dashboard.db")
    c = conn.cursor()
    c.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    conn.commit()
    conn.close()
    return redirect(url_for('tasks_page'))


# Logout route
@app.route("/logout")
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)