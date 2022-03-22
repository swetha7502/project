from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3 as sql
import json
from flask_sqlalchemy import SQLAlchemy
import datetime
import logging

app = Flask(__name__)
app.secret_key = "ac"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user1.db'
app.config['SESSION_TYPE'] = "filesystem"
db = SQLAlchemy(app)


class Activity(db.Model):
    __tablename__ = 'activity_db'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    activity = db.Column(db.String)
    description = db.Column(db.String)
    tracker_type = db.Column(db.String)
    date = datetime.datetime.now()
    mselect = db.Column(db.String(150), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_db.id'))
    activity_data = db.relationship('TrackerData', backref="tracker")

class Users(db.Model):
    __tablename__ = 'user_db'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    trackers = db.relationship('Activity', backref="user")

class TrackerData(db.Model):
    __tablename__ = 'tracker_db'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tracker_id = db.Column(db.Integer, db.ForeignKey('activity_db.id'))
    date = db.Column(db.String, nullable=False)
    tracker_value = db.Column(db.Integer, nullable=True)
    description = db.Column(db.String, nullable=False)

@app.route("/")
def reroute():
    return redirect('home')

@app.route('/home', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def index():
    msg = None
    if request.method == 'POST':
        name = request.form['username']
        password = request.form['password']
        user_exists = Users.query.all()
        success = False
        for user in user_exists:
            if user.username == name and user.password == password:
                display_name = user.name
                success = True

        if success:
            session["name"] = name
            session["display_name"] = display_name
            session["password"] = password
            return redirect(url_for('user', username=name))
        else:
            msg = "Credentials incorrect or user doesn't exist."

    return render_template('login.html', msg=msg)

@app.route('/user/<username>', methods=["GET", "POST"])
def user(username):
    log_user = session.get('name')
    dname = session.get('display_name')
    log_user_obj = db.session.query(Users).filter(
        Users.username == log_user).first()
    log_user_id = log_user_obj.id
    log_user_activity = db.session.query(Activity).filter(
        Activity.user_id == log_user_id).all()
    for last_date in log_user_activity:
        last_date.date = db.session.query(TrackerData.date).filter(
            TrackerData.tracker_id == last_date.id).order_by(TrackerData.date.desc()).first()
        if last_date.date ==  None:
            last_date.date = ["No Data"]
    return render_template("user.html", tdata=log_user_activity, name=username, dname=dname)

@app.route('/user/<username>/<activity>')
def view_tracker(username, activity):
    log_user = session.get('name')
    session["activity"] = activity
    user_obj = db.session.query(Users).filter(
        Users.username == log_user).first()
    user_trackers = db.session.query(Activity).filter(
        Activity.user_id == user_obj.id).all()
    for tracker in user_trackers:
        if tracker.activity == activity:
            curr_tracker = tracker
    curr_tracker_logs = db.session.query(TrackerData).filter(
        TrackerData.tracker_id == curr_tracker.id).all()
    log_values_raw = []
    log_value_time = []
    for logs in curr_tracker_logs:
        log_values_raw.append(logs.tracker_value)
        log_value_time.append(logs.date)

    return render_template('activity.html', tracker=curr_tracker_logs, name=log_user, activity=activity)


@app.route('/user/<username>/log/<activity>', methods=['GET', 'POST'])
def add_log(username, activity):
    if request.method == 'GET':
        flag = False
        log_user = session.get('name')
        user_obj = db.session.query(Users).filter(
            Users.username == username).first()
        user_trackers = db.session.query(Activity).filter(
            Activity.user_id == user_obj.id).all()
        for tracker in user_trackers:
            if tracker.activity == activity:
                curr_tracker = tracker
        if curr_tracker.mselect != None:
            flag = True

        vals = curr_tracker.mselect
        datenow = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        split_strip_values = []
        if vals != None:
            split_values = vals.split(',')
            for val in split_values:
                split_strip_values.append(val.strip())

        return render_template('add_log.html', values=split_strip_values, flag=flag, name=log_user, activity=activity, datetime=datenow)

    if request.method == "POST":
        log_user = session.get('name')
        user_obj = db.session.query(Users).filter(
            Users.username == log_user).first()
        user_trackers = db.session.query(Activity).filter(
            Activity.user_id == user_obj.id).all()
        for tracker in user_trackers:
            if tracker.activity == activity:
                curr_tracker = tracker

        value = request.form['value']
        description = request.form['description']
        dstring = request.form['date']
        tdata = TrackerData(tracker_id=curr_tracker.id, date=dstring,
                            tracker_value=value, description=description)
        db.session.add(tdata)
        db.session.commit()
        return redirect('/user/{username}'.format(username=session.get('name')))


@app.route('/user/<username>/<int:tid>/<int:lid>/delete')
def del_log(username, tid, lid):
    curr_log = db.session.query(TrackerData).filter(
        TrackerData.id == lid).first()
    curr_tracker = db.session.query(
        Activity).filter(Activity.id == tid).first()
    db.session.delete(curr_log)
    db.session.commit()
    return redirect('/user/{username}/{activity}'.format(username=username, activity=curr_tracker.activity))


@app.route('/user/<username>/<int:tid>/<int:lid>/edit', methods=['GET', 'POST'])
def edit_log(username, tid, lid):
    if request.method == 'GET':
        flag = False
        cur_activity = session.get('activity')
        curr_log = db.session.query(TrackerData).filter(
            TrackerData.id == lid).first()
        curr_tracker = db.session.query(
            Activity).filter(Activity.id == tid).first()

        if curr_tracker.mselect != None:
            flag = True

        vals = curr_tracker.mselect
        split_strip_values = []
        if vals != None:
            split_values = vals.split(',')
            for val in split_values:
                split_strip_values.append(val.strip())

        return render_template('edit_log.html', log=curr_log, values=split_strip_values, flag=flag, username=username, activity=cur_activity)
    if request.method == 'POST':
        date = request.form['date']
        value = request.form['value']
        description = request.form['description']
        curr_log = db.session.query(TrackerData).filter(
            TrackerData.id == lid).first()
        curr_tracker = db.session.query(
            Activity).filter(Activity.id == tid).first()
        curr_log.tracker_value = value
        curr_log.description = description
        curr_log.date = date
        db.session.commit()
        return redirect('/user/{username}/{activity}'.format(username=username, activity=curr_tracker.activity))


@app.route('/user/<username>/<int:tid>/delete')
def del_tracker(username, tid):
    curr_tracker = db.session.query(
        Activity).filter(Activity.id == tid).first()
    db.session.delete(curr_tracker)
    db.session.commit()
    return redirect('/user/{username}'.format(username=username))


@app.route('/user/<username>/<int:tid>/edit', methods=['GET', 'POST'])
def edit_tracker(username, tid):
    if(request.method == 'GET'):
        username = session.get('name')
        curr_tracker = db.session.query(
            Activity).filter(Activity.id == tid).first()
        print(curr_tracker.mselect)
        return render_template('edit_tracker.html', tracker=curr_tracker, name=username)

    if request.method == 'POST':
        curr_tracker = db.session.query(
            Activity).filter(Activity.id == tid).first()
        name = request.form['activity']
        desc = request.form['description']
        curr_tracker.activity = name
        curr_tracker.description = desc
        db.session.commit()
        return redirect('/user/{username}'.format(username=username))


@app.route('/add_tracker', methods=['GET', 'POST'])
def add_tracker():
    msg = None
    log_user = session.get('name')
    if request.method == "POST":
        activity = request.form['activity']
        description = request.form['description']
        tracker_type = request.form['tracker_type']
        display_name = session.get('display_name')
        log_user_obj = db.session.query(Users).filter(
            Users.username == log_user).first()
        log_user_id = log_user_obj.id
        success = False
        activity_exists = db.session.query(Activity).filter(
            Activity.activity == activity).all()

        for db_activity in activity_exists:
            if db_activity.activity == activity:
                success = True

        if success:
            msg = "Activity already exists !"
            return render_template('add_tracker.html', msg=msg)

        if tracker_type == 'integer':
            tracker = Activity(activity=activity, description=description,
                               tracker_type="integer", user_id=log_user_id)
            db.session.add(tracker)
            db.session.commit()

        if tracker_type == 'multiselect':
            multi_select_values = request.form['settings']
            tracker = Activity(activity=activity, description=description,
                               tracker_type="multiselect", mselect=multi_select_values, user_id=log_user_id)
            db.session.add(tracker)
            db.session.commit()

        return redirect(url_for('user', username=log_user))

    return render_template('add_tracker.html', username=log_user)


@app.route('/tracker', methods=['GET', 'POST'])
def tracker():
    if request.method == "POST":
        activity = request.form['activity']
        description = request.form['description']
        tracker_type = request.form.getlist('type')[0]
        log_user = session.get('name')
        log_user_obj = db.session.query(Users).filter(
            Users.username == log_user).first()
        log_user_id = log_user_obj.id
        if tracker_type == '1':
            tracker = Activity(tname=activity, tdesc=description,
                               ttype="integer", user_id=log_user_id)
            db.session.add(tracker)
            db.session.commit()

        if tracker_type == '2':
            multi_select_values = request.form['settings']
            tracker = Activity(tname=activity, tdesc=description, ttype="multiselect",
                               multi_select=multi_select_values, user_id=log_user_id)
            db.session.add(tracker)
            db.session.commit()

        return redirect(url_for('tracker', username=log_user))

    return render_template('tracker.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    msg = None
    if request.method == 'POST':
        username = request.form["uname"]
        name = request.form["name"]
        password = request.form["password"]

        success = False
        user_exists = Users.query.all()
        for user in user_exists:
            if username == user.username:
                success = True

        if success:
            msg = "Sorry, this username already exists !"
            return render_template('signup.html', msg=msg)
        else:
            user = Users(username=username, name=name, password=password)
            db.session.add(user)
            db.session.commit()
        return redirect('login')

    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)
