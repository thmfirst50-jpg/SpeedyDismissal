import os

from cs50 import SQL
from datetime import datetime
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from flask_socketio import SocketIO, emit, join_room
import re
import time
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# configure application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

# connect to SQL database
db = SQL("sqlite:///dismissal.db")

# configure session to use filsystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@socketio.on('join_group')
def joinGroup(data):
    room = str(data['room'])
    join_room(room)
    print(f"Joined group {room}")



# ----------------------------------------------------------------------------------------------------------------------------------------------------- #
# Pages

@app.route("/")
@login_required
def index():
    user = db.execute("SELECT first_name, last_name, role, group_id FROM users WHERE id = ?", session["user_id"])
    students = db.execute("SELECT ps.pickup_id, s.id AS student_id, s.first_name || ' ' || s.last_name AS student, p.requested_at, ps.status FROM pickup_students ps JOIN students s ON s.id = ps.student_id JOIN pickups  p ON p.id = ps.pickup_id WHERE s.group_id = (SELECT group_id FROM users WHERE id = ?) ORDER BY CASE WHEN ps.status = 'PENDING' THEN 0 ELSE 1 END, p.requested_at DESC;", session["user_id"])
    return render_template("index.html", user=user, students=students)


@app.route("/logs")
def logs():
    pendingStudents = db.execute("SELECT s.id, s.first_name || ' ' || s.last_name AS student, p.requested_at, u.first_name || ' ' || u.last_name AS teacher_name FROM pickup_students ps JOIN students s ON s.id = ps.student_id JOIN pickups p ON p.id = ps.pickup_id JOIN users u ON u.group_id = s.group_id WHERE sent_at = 'None' ORDER BY requested_at DESC;")
    sentStudents = db.execute("SELECT s.id, s.first_name || ' ' || s.last_name AS student, ps.sent_at, u.first_name || ' ' || u.last_name AS teacher_name FROM pickup_students ps JOIN students s ON s.id = ps.student_id JOIN users u ON u.group_id = s.group_id WHERE sent_at != 'None' ORDER BY sent_at DESC;")
    return render_template("logs.html", pendingStudents=pendingStudents, sentStudents=sentStudents)



@app.route("/scanner")
def scanner():
    return render_template("scanner.html")


@app.route("/admin")
def admin():
    students = db.execute("SELECT * FROM students;")
    groups = db.execute("SELECT * FROM groups;")
    guardians = db.execute("SELECT * FROM guardians;")
    users = db.execute("SELECT id, username, 'Censored' AS password_hash, first_name, last_name, role, group_id FROM users;")
    tokens = db.execute("SELECT * FROM tokens;")
    guardian_students = db.execute("SELECT * FROM guardian_students")
    return render_template("admin.html", students=students, groups=groups, guardians=guardians, users=users, tokens=tokens, guardian_students=guardian_students)

# end pages
# ----------------------------------------------------------------------------------------------------------------------------------------------------- #




@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            return apology("Please enter a valid username/password")

        user = db.execute("SELECT id, password_hash FROM users WHERE username = ?", username)
        if not check_password_hash(user[0]["password_hash"], password):
            return apology("Incorrect Password")

        session["user_id"] = user[0]["id"]

        return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")




@app.route("/test_emit/<string:room>/<string:message>")
def test_emit(room, message):
    socketio.emit("update_logs", {"student": message}, room=room)
    return "Emitted"




def broadcastNewStudent(student_ids, pickup_id):
    for student_id in student_ids:
        student = db.execute("SELECT ps.pickup_id, s.id, s.first_name || ' ' || s.last_name AS student, p.requested_at, ps.status, s.group_id, u.first_name || ' ' || u.last_name as teacher_name FROM pickup_students ps JOIN students s ON s.id = ps.student_id JOIN pickups p on p.id = ps.pickup_id JOIN users u ON u.group_id = s.group_id WHERE ps.student_id = ? AND p.id = ?", student_id["id"], pickup_id)
        socketio.emit("student_added", student[0], room=str(student[0]["group_id"]))
        socketio.emit("update_logs", student[0], room="logs")
    return


@socketio.on("update_status")
def updateStatus(data):
    student_id = data["student_id"]
    group_id = data["group_id"]
    if not student_id or not group_id:
        return "Invalid data passed in."
    try:
        db.execute("UPDATE pickup_students SET status = 'SENT', sent_at = ? WHERE student_id = ?;", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), student_id)
        # send update status to teacher's dashboard
        socketio.emit("status_updated", {"student_id" : student_id, "status": "SENT"}, room=group_id)
        # send update status to logs page
        socketio.emit("update_logs",
            db.execute("SELECT s.id, s.first_name || ' ' || s.last_name AS student, ps.sent_at, ps.status, u.first_name || ' ' || u.last_name AS teacher_name FROM pickup_students ps JOIN students s ON s.id = ps.student_id JOIN users u ON u.group_id = s.group_id WHERE ps.student_id = ?", student_id)[0],
        room="logs")
    except Exception as e:
        print(str(e))
        return "Error updating status."

    

@app.route("/DELETE", methods=["POST"])
def DELETE():
    table = request.json.get("table")
    values = request.get_json()

    query = f"DELETE FROM {table} WHERE "
    for key in values:
        if key != "table":
            query += f"{key} = '{values[key]}' AND "
    query += "1 = 1"
    
    print(query)

    try:
        db.execute(query)
        return jsonify({"success": True, "message": f"Removed Record"}), 200
    except Exception as e:
        print(str(e))

    return jsonify({"success": False, "message": "Error Deleting"}), 400
    

@app.route("/INSERT", methods=["POST"])
def INSERT():

    values = request.get_json()
    params = ""

    match values['table']:
        case 'students':
            params = "(first_name, last_name, grade, group_id, active)"
        case 'groups':
            params = "(name)"
        case 'guardians':
            params = "(name, phone, email)"
        case 'users':
            params = "(username, password_hash, first_name, last_name, role, group_id)"
            values['password_hash'] = generate_password_hash(values['password_hash'])
        case 'tokens':
            params = "(token_value, guardian_id, active, created_at, revoked_at)"
        case 'guardian_students':
            params = "(guardian_id, student_id)"
    
    query = f"INSERT INTO {values['table']} {params} VALUES ("
    args = []

    for key, value in values.items():
        if key != "table":
            query += f" ?,"
            args.append(f"{value}")
    query = query[:len(query) - 1] + ")"

    print(query, "args: ", args)
    
    try:
        id = db.execute(query, *args)
        return jsonify({"success": True, "message": "Success", "id": id}), 200
    except Exception as e:
        print(str(e))

    return jsonify({"success": False, "message": "Error"}), 400


@app.route("/QUERY", methods=["POST"])
def QUERY():
    data = request.get_json()
    query = f"SELECT * FROM {data['table']} WHERE "

    params = []
    for key, value in data.items():
        if key == "table" or not value:
            continue
        query += f"{key} LIKE ? AND "
        params.append(f"%{value}%")
    query += "1 = 1"
    
    print(query)

    try:
        if not params: 
            query = f"SELECT * FROM {data['table']}"
            response = db.execute(query)
        else:
            response = db.execute(query, params)
        
        for item in response:
            if "password_hash" in item:
                item["password_hash"] = "Censored"

        return jsonify({"success": True, 'items': response}), 200
    except Exception as e:
        pass

    return jsonify({"success": False, "message": "Error Querying"}), 400


def validateInput(data):
    for item in data:
        if not item:
            return False
    return True






@app.route("/scan", methods=["GET", "POST"])
def scan():
    if request.method == "GET":
        token_value = request.args.get("token")
    else:
        token_value = request.json.get("token")

    token = db.execute("SELECT id FROM tokens WHERE token_value = ? and active = 1;", token_value)
    if not token:
        return jsonify({"success": False, "message": "No student ID provided"}), 400

    pickupExists = db.execute("SELECT id FROM pickups WHERE token_id = ?", token[0]["id"])
    if pickupExists:
        return jsonify({"success": False, "message": "Pick up request is already active."}), 400

    student_ids = db.execute(
        "SELECT s.id FROM tokens t JOIN guardian_students gs ON gs.guardian_id = t.guardian_id JOIN students s on s.id = gs.student_id WHERE t.token_value = ? AND t.active = 1 AND s.active = 1;",
        token_value
    )
    if not student_ids:
        return jsonify({"success": False, "message": "No students linked to token"}), 400

    try:
        db.execute("BEGIN")

        pickup_id = db.execute(
            "INSERT INTO pickups (token_id, requested_by) VALUES (?, ?)",
            token[0]["id"], session["user_id"]
        )

        for student_id in student_ids:
            db.execute("INSERT INTO pickup_students (pickup_id, student_id) VALUES (?, ?)", pickup_id, student_id["id"])

        db.execute("COMMIT")

        broadcastNewStudent(student_ids, pickup_id)

        return jsonify({"success": True, "message": "Scan successful"}), 200

    except Exception as e:
        db.execute("ROLLBACK")
        return jsonify({"success": False, "message": str(e)}), 500



if __name__ == "__main__":
    # socketio.run(app, host="0.0.0.0", port=443, ssl_context=("server.crt", "server.key"))
    import eventlet
    import eventlet.wsgi

    socketio.run(app, host="127.0.0.1", port=5000)
