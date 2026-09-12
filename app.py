import os
import re
import shutil
import time
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import dao
from models import User

def slugify(text):
    cleanText = text.lower().strip()
    cleanText = re.sub(r'[\s&]+', '-', cleanText)
    cleanText = re.sub(r'[^a-z0-9_-]', '', cleanText)
    return cleanText.strip('-') or 'masterclass'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'erdem-cooking-school-secret-key-2026'

loginManager = LoginManager()
loginManager.init_app(app)
loginManager.login_view = 'login'
loginManager.login_message = "Please log in to access this page."
loginManager.login_message_category = "warning"

@loginManager.user_loader
def loadUser(userId):
    dbUser = dao.getUserById(userId)
    if dbUser:
        return User(
            id=dbUser['id'],
            firstName=dbUser['first_name'],
            lastName=dbUser['last_name'],
            email=dbUser['email'],
            password=dbUser['password'],
            role=dbUser['role']
        )
    return None

@app.context_processor
def injectGlobalContext():
    simDay, simTime = dao.getSimulatedTime()
    return {
        'simulatedDay': simDay,
        'simulatedTime': simTime,
        'daysOfWeek': dao.DAYS_OF_WEEK
    }


@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/classes')
def classesCatalog():
    cuisine = request.args.get('cuisine', '').strip()
    difficulty = request.args.get('difficulty', '').strip()
    dietary = request.args.get('dietary', '').strip()
    query = request.args.get('q', '').strip()

    classes = dao.getAllClasses(
        filterCuisine=cuisine if cuisine else None,
        filterDifficulty=difficulty if difficulty else None,
        filterDietary=dietary if dietary else None,
        searchQuery=query if query else None
    )

    return render_template(
        'classes.html',
        classes=classes,
        selectedCuisine=cuisine,
        selectedDifficulty=difficulty,
        selectedDietary=dietary,
        searchQuery=query
    )


@app.route('/classes/<int:classId>')
def classDetail(classId):
    cookingClass = dao.getClassById(classId)
    if not cookingClass:
        flash("Cooking class not found.", "danger")
        return redirect(url_for('index'))

    sessions = dao.getSessionsByClassId(classId)
    ratings = dao.getClassRatings(classId)
    ingredientsList = [line.strip() for line in cookingClass['ingredients'].split('\n') if line.strip()]

    userEnrolledSessionIds = set()
    userWaitingSessionIds = set()
    if current_user.is_authenticated and current_user.isStudent():
        studentEnrollments = dao.getStudentEnrollments(current_user.id)
        userEnrolledSessionIds = {e['session_id'] for e in studentEnrollments}
        studentWaiting = dao.getStudentWaitingLists(current_user.id)
        userWaitingSessionIds = {w['session_id'] for w in studentWaiting}

    sessionCards = []
    for s in sessions:
        sDict = dict(s)
        sDict['isPast'] = dao.isSessionPast(s['day_of_week'], s['start_time'])
        sDict['isUserEnrolled'] = s['id'] in userEnrolledSessionIds
        sDict['isUserWaiting'] = s['id'] in userWaitingSessionIds
        sessionCards.append(sDict)

    return render_template(
        'class_detail.html',
        cookingClass=cookingClass,
        ingredients=ingredientsList,
        sessions=sessionCards,
        ratings=ratings
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.isManager():
            return redirect(url_for('managerProfile'))
        return redirect(url_for('studentProfile'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template('login.html', email=email)

        dbUser = dao.getUserByEmail(email)
        if not dbUser or not check_password_hash(dbUser['password'], password):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template('login.html', email=email)

        user = User(
            id=dbUser['id'],
            firstName=dbUser['first_name'],
            lastName=dbUser['last_name'],
            email=dbUser['email'],
            password=dbUser['password'],
            role=dbUser['role']
        )
        login_user(user)
        flash(f"Welcome back, {user.firstName}!", "success")

        nextPage = request.args.get('next')
        if nextPage:
            return redirect(nextPage)
        if user.isManager():
            return redirect(url_for('managerProfile'))
        return redirect(url_for('studentProfile'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        firstName = request.form.get('firstName', '').strip()
        lastName = request.form.get('lastName', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirmPassword = request.form.get('confirmPassword', '')
        role = 'student'

        errors = []
        if not firstName or len(firstName) < 2:
            errors.append("First name must be at least 2 characters.")
        if not lastName or len(lastName) < 2:
            errors.append("Last name must be at least 2 characters.")
        if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors.append("A valid email address is required.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        if password != confirmPassword:
            errors.append("Passwords do not match.")

        if dao.getUserByEmail(email):
            errors.append("An account with this email address already exists.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                'login.html',
                activeTab='register',
                firstName=firstName,
                lastName=lastName,
                email=email,
                role=role
            )

        passwordHash = generate_password_hash(password)
        newUserId = dao.createUser(firstName, lastName, email, passwordHash, role)

        user = User(
            id=newUserId,
            firstName=firstName,
            lastName=lastName,
            email=email,
            password=passwordHash,
            role=role
        )
        login_user(user)
        flash("Registration successful! Welcome to Erdem Cooking School.", "success")

        if role == 'manager':
            return redirect(url_for('managerProfile'))
        return redirect(url_for('studentProfile'))

    return render_template('login.html', activeTab='register')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('index'))


@app.route('/profile/student')
@login_required
def studentProfile():
    if not current_user.isStudent():
        flash("This page is reserved for students.", "warning")
        return redirect(url_for('managerProfile'))

    enrollments = dao.getStudentEnrollments(current_user.id)
    waitingLists = dao.getStudentWaitingLists(current_user.id)

    upcomingEnrollments = [e for e in enrollments if not e['is_past']]
    pastEnrollments = [e for e in enrollments if e['is_past']]

    return render_template(
        'profile_student.html',
        upcomingEnrollments=upcomingEnrollments,
        pastEnrollments=pastEnrollments,
        waitingLists=waitingLists,
        totalEnrollments=len(enrollments)
    )

@app.route('/sessions/<int:sessionId>/enroll', methods=['POST'])
@login_required
def enrollSession(sessionId):
    if not current_user.isStudent():
        flash("Only students can enroll in cooking sessions.", "danger")
        return redirect(url_for('index'))

    success, message = dao.enrollStudent(current_user.id, sessionId)
    if success:
        flash(message, "success")
        return redirect(url_for('studentProfile'))
    else:
        flash(message, "danger")
        ref = request.referrer or url_for('index')
        return redirect(ref)

@app.route('/sessions/<int:sessionId>/cancel', methods=['POST'])
@login_required
def cancelSession(sessionId):
    if not current_user.isStudent():
        flash("Unauthorized action.", "danger")
        return redirect(url_for('index'))

    success, message = dao.cancelEnrollment(current_user.id, sessionId)
    if success:
        flash(message, "info")
    else:
        flash(message, "danger")

    return redirect(url_for('studentProfile'))

@app.route('/sessions/<int:sessionId>/rate', methods=['POST'])
@login_required
def submitRating(sessionId):
    if not current_user.isStudent():
        flash("Only enrolled students can rate sessions.", "danger")
        return redirect(url_for('index'))

    try:
        score = int(request.form.get('score', 0))
    except ValueError:
        score = 0
    comment = request.form.get('comment', '').strip()

    success, message = dao.addRating(current_user.id, sessionId, score, comment)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(url_for('studentProfile'))

@app.route('/sessions/<int:sessionId>/waiting-list/join', methods=['POST'])
@login_required
def joinWaiting(sessionId):
    if not current_user.isStudent():
        flash("Only students can join waiting lists.", "danger")
        return redirect(url_for('index'))

    success, message = dao.joinWaitingList(current_user.id, sessionId)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    ref = request.referrer or url_for('studentProfile')
    return redirect(ref)

@app.route('/sessions/<int:sessionId>/waiting-list/leave', methods=['POST'])
@login_required
def leaveWaiting(sessionId):
    if not current_user.isStudent():
        flash("Unauthorized action.", "danger")
        return redirect(url_for('index'))

    success, message = dao.leaveWaitingList(current_user.id, sessionId)
    if success:
        flash(message, "info")
    else:
        flash(message, "danger")

    return redirect(url_for('studentProfile'))


@app.route('/profile/manager')
@login_required
def managerProfile():
    if not current_user.isManager():
        flash("This page is reserved for cooking school managers.", "warning")
        return redirect(url_for('studentProfile'))

    classes = dao.getClassesByManager(current_user.id)

    managedData = []
    for c in classes:
        sessions = dao.getSessionsByClassId(c['id'])
        sessionList = []
        for s in sessions:
            sDict = dict(s)
            sDict['students'] = dao.getEnrolledStudents(s['id'])
            sDict['waitingStudents'] = dao.getSessionWaitingList(s['id'])
            sDict['isPast'] = dao.isSessionPast(s['day_of_week'], s['start_time'])
            sessionList.append(sDict)
        managedData.append({
            'class': c,
            'sessions': sessionList
        })

    stats = dao.getManagerStatistics(current_user.id)

    return render_template(
        'profile_manager.html',
        managedData=managedData,
        stats=stats
    )

@app.route('/classes/create', methods=['GET', 'POST'])
@login_required
def createClass():
    if not current_user.isManager():
        flash("Only cooking school managers can create classes.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        cuisine = request.form.get('cuisine', '').strip()
        difficulty = request.form.get('difficulty', '').strip()
        durationStr = request.form.get('duration', '').strip()
        dietary = request.form.get('dietary_category', '').strip()
        chef = request.form.get('chef', '').strip()
        ingredients = request.form.get('ingredients', '').strip()
        description = request.form.get('description', '').strip()
        photo1 = request.form.get('photo1', '').strip()
        photo2 = request.form.get('photo2', '').strip()
        photo3 = request.form.get('photo3', '').strip()

        errors = []
        if not title:
            errors.append("Class title is required.")
        if not cuisine:
            errors.append("Cuisine is required.")
        if difficulty not in ('Beginner', 'Intermediate', 'Advanced'):
            errors.append("Please select a valid difficulty level.")
        try:
            duration = int(durationStr)
            if duration <= 0:
                errors.append("Duration must be a positive number of minutes.")
        except ValueError:
            errors.append("Duration must be a valid integer.")
            duration = 120

        if dietary not in ('Standard', 'Vegetarian', 'Vegan', 'Gluten-free'):
            errors.append("Please select a valid dietary category.")
        if not chef:
            errors.append("Chef name is required.")

        ingrLines = [line.strip() for line in ingredients.replace(',', '\n').split('\n') if line.strip()]
        if len(ingrLines) < 4:
            errors.append("Please list at least 4 main ingredients (separated by newlines or commas).")

        photoFiles = [
            request.files.get('photo1'),
            request.files.get('photo2'),
            request.files.get('photo3')
        ]
        savedFilenames = []
        classSlug = slugify(title)
        uploadFolder = os.path.join(app.root_path, 'static', 'images', classSlug)
        os.makedirs(uploadFolder, exist_ok=True)

        for idx, pf in enumerate(photoFiles, start=1):
            if pf and pf.filename:
                cleanName = secure_filename(pf.filename)
                uniqueName = f"{idx}_{cleanName}"
                savePath = os.path.join(uploadFolder, uniqueName)
                pf.save(savePath)
                savedFilenames.append(f"{classSlug}/{uniqueName}")
            else:
                errors.append(f"Photo {idx} file is required.")

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template('create_class.html', formData=request.form)

        classId = dao.createClass(
            managerId=current_user.id,
            title=title,
            cuisine=cuisine,
            difficulty=difficulty,
            duration=duration,
            dietaryCategory=dietary,
            chef=chef,
            ingredients=ingredients,
            description=description,
            photo1=savedFilenames[0],
            photo2=savedFilenames[1],
            photo3=savedFilenames[2]
        )

        flash(f"Cooking class '{title}' created successfully! Now you can schedule sessions for it.", "success")
        return redirect(url_for('createSession', classId=classId))

    return render_template('create_class.html', formData={})

@app.route('/classes/<int:classId>/delete', methods=['POST'])
@login_required
def deleteClass(classId):
    if not current_user.isManager():
        flash("Unauthorized action.", "danger")
        return redirect(url_for('index'))

    c = dao.getClassById(classId)
    if not c:
        flash("Masterclass not found.", "danger")
        return redirect(url_for('managerProfile'))

    success, message = dao.deleteClass(classId, current_user.id)
    if success:
        if c['photo1'] and '/' in c['photo1']:
            folderName = c['photo1'].split('/')[0]
            folderPath = os.path.join(app.root_path, 'static', 'images', folderName)
            if os.path.exists(folderPath):
                shutil.rmtree(folderPath, ignore_errors=True)
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(url_for('managerProfile'))

@app.route('/classes/<int:classId>/sessions/create', methods=['GET', 'POST'])
@login_required
def createSession(classId):
    if not current_user.isManager():
        flash("Only cooking school managers can schedule sessions.", "danger")
        return redirect(url_for('index'))

    c = dao.getClassById(classId)
    if not c:
        flash("Class not found.", "danger")
        return redirect(url_for('managerProfile'))

    if c['manager_id'] != current_user.id:
        flash("You can only add sessions to cooking classes you created.", "danger")
        return redirect(url_for('managerProfile'))

    existingSessions = dao.getSessionsByClassId(classId)
    defaultSessionName = f"{c['title']} {len(existingSessions) + 1}"

    if request.method == 'POST':
        dayOfWeek = request.form.get('day_of_week', '').strip()
        startTime = request.form.get('start_time', '').strip()
        kitchen = request.form.get('kitchen', '').strip()
        capacityStr = request.form.get('capacity', '').strip()

        errors = []
        if dayOfWeek not in dao.DAYS_OF_WEEK:
            errors.append("Please select a valid day of the week (Monday - Sunday).")
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", startTime):
            errors.append("Please enter a valid starting time in HH:MM format (e.g. 10:00, 18:30).")
        if not kitchen:
            errors.append("Session name is required.")
        try:
            capacity = int(capacityStr)
            if capacity <= 0:
                errors.append("Capacity must be at least 1 student.")
        except ValueError:
            errors.append("Capacity must be a positive integer.")
            capacity = 4

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template('create_session.html', cookingClass=c, formData=request.form, defaultSessionName=defaultSessionName)

        dao.createSession(
            classId=classId,
            dayOfWeek=dayOfWeek,
            startTime=startTime,
            kitchen=kitchen,
            capacity=capacity
        )
        flash(f"New session scheduled on {dayOfWeek} at {startTime} ({kitchen})!", "success")
        return redirect(url_for('managerProfile'))

    return render_template('create_session.html', cookingClass=c, formData={}, defaultSessionName=defaultSessionName)

@app.route('/sessions/<int:sessionId>/edit', methods=['GET', 'POST'])
@login_required
def editSession(sessionId):
    if not current_user.isManager():
        flash("Unauthorized action.", "danger")
        return redirect(url_for('index'))

    sessionData = dao.getSessionById(sessionId)
    if not sessionData:
        flash("Session not found.", "danger")
        return redirect(url_for('managerProfile'))

    if sessionData['manager_id'] != current_user.id:
        flash("You can only edit sessions for cooking classes you supervise.", "danger")
        return redirect(url_for('managerProfile'))

    c = dao.getClassById(sessionData['class_id'])

    if request.method == 'POST':
        dayOfWeek = request.form.get('day_of_week', '').strip()
        startTime = request.form.get('start_time', '').strip()
        kitchen = request.form.get('kitchen', '').strip()
        capacityStr = request.form.get('capacity', '').strip()

        errors = []
        if dayOfWeek not in dao.DAYS_OF_WEEK:
            errors.append("Please select a valid day of the week (Monday - Sunday).")
        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", startTime):
            errors.append("Please enter a valid starting time in HH:MM format (e.g. 10:00, 18:30).")
        if not kitchen:
            errors.append("Session name is required.")
        try:
            capacity = int(capacityStr)
            if capacity <= 0:
                errors.append("Capacity must be at least 1 student.")
        except ValueError:
            errors.append("Capacity must be a positive integer.")
            capacity = sessionData['capacity']

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template('create_session.html', cookingClass=c, sessionData=sessionData, formData=request.form)

        success, message = dao.updateSession(
            sessionId=sessionId,
            managerId=current_user.id,
            dayOfWeek=dayOfWeek,
            startTime=startTime,
            kitchen=kitchen,
            capacity=capacity
        )

        if success:
            flash(message, "success")
            return redirect(url_for('managerProfile'))
        else:
            flash(message, "danger")
            return render_template('create_session.html', cookingClass=c, sessionData=sessionData, formData=request.form)

    initialFormData = {
        'day_of_week': sessionData['day_of_week'],
        'start_time': sessionData['start_time'],
        'kitchen': sessionData['kitchen'],
        'capacity': sessionData['capacity']
    }
    return render_template('create_session.html', cookingClass=c, sessionData=sessionData, formData=initialFormData)

@app.route('/sessions/<int:sessionId>/delete', methods=['POST'])
@login_required
def deleteSession(sessionId):
    if not current_user.isManager():
        flash("Unauthorized action.", "danger")
        return redirect(url_for('index'))

    success, message = dao.deleteSession(sessionId, current_user.id)
    if success:
        flash(message, "success")
    else:
        flash(message, "danger")

    return redirect(url_for('managerProfile'))


@app.route('/set-simulated-time', methods=['POST'])
def setClock():
    newDay = request.form.get('simulated_day', '').strip()
    newTime = request.form.get('simulated_time', '').strip()

    if newDay in dao.DAYS_OF_WEEK and re.match(r"^([01]\d|2[0-3]):[0-5]\d$", newTime):
        dao.setSimulatedTime(newDay, newTime)
        flash(f"Simulated clock set to {newDay} at {newTime}.", "info")
    else:
        flash("Invalid simulated day or time format.", "danger")

    return redirect(request.referrer or url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)