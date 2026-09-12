import sqlite3
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'school.db')

DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
DAY_TO_INDEX = {day: idx for idx, day in enumerate(DAYS_OF_WEEK)}

def getDatabaseConnection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def getSimulatedTime():
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM simulation WHERE key = 'simulated_day';")
    day_row = cursor.fetchone()
    cursor.execute("SELECT value FROM simulation WHERE key = 'simulated_time';")
    time_row = cursor.fetchone()
    conn.close()

    sim_day = day_row['value'] if day_row else 'Wednesday'
    sim_time = time_row['value'] if time_row else '14:00'
    return sim_day, sim_time

def setSimulatedTime(day_of_week, time_str):
    if day_of_week not in DAYS_OF_WEEK:
        raise ValueError(f"Invalid day: {day_of_week}")
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO simulation (key, value) VALUES ('simulated_day', ?);", (day_of_week,))
    cursor.execute("INSERT OR REPLACE INTO simulation (key, value) VALUES ('simulated_time', ?);", (time_str,))
    conn.commit()
    conn.close()

def timeToWeeklyMinutes(day_str, time_str):
    day_idx = DAY_TO_INDEX.get(day_str, 0)
    parts = time_str.split(':')
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    return (day_idx * 24 * 60) + (hours * 60) + minutes

def isSessionPast(day_of_week, start_time):
    sim_day, sim_time = getSimulatedTime()
    session_mins = timeToWeeklyMinutes(day_of_week, start_time)
    current_mins = timeToWeeklyMinutes(sim_day, sim_time)
    return session_mins <= current_mins

def canCancelEnrollment(day_of_week, start_time):
    sim_day, sim_time = getSimulatedTime()
    session_mins = timeToWeeklyMinutes(day_of_week, start_time)
    current_mins = timeToWeeklyMinutes(sim_day, sim_time)
    diff_minutes = session_mins - current_mins
    return diff_minutes >= (12 * 60)

def getUserById(userId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?;", (userId,))
    user = cursor.fetchone()
    conn.close()
    return user

def getUserByEmail(email):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?);", (email.strip(),))
    user = cursor.fetchone()
    conn.close()
    return user

def createUser(firstName, lastName, email, passwordHash, role):
    if role not in ('manager', 'student'):
        raise ValueError("Role must be 'manager' or 'student'")
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (first_name, last_name, email, password, role)
        VALUES (?, ?, ?, ?, ?);
    """, (firstName.strip(), lastName.strip(), email.strip().lower(), passwordHash, role))
    newId = cursor.lastrowid
    conn.commit()
    conn.close()
    return newId

def getAllClasses(filterCuisine=None, filterDifficulty=None, filterDietary=None, searchQuery=None):
    conn = getDatabaseConnection()
    cursor = conn.cursor()

    query = """
        SELECT c.*, u.first_name || ' ' || u.last_name AS manager_name,
               ROUND(AVG(r.score), 1) AS avg_rating,
               COUNT(DISTINCT r.id) AS total_ratings,
               COUNT(DISTINCT s.id) AS total_sessions
        FROM classes c
        JOIN users u ON c.manager_id = u.id
        LEFT JOIN sessions s ON c.id = s.class_id
        LEFT JOIN ratings r ON s.id = r.session_id
        WHERE 1=1
    """
    params = []

    if filterCuisine:
        query += " AND LOWER(c.cuisine) = LOWER(?)"
        params.append(filterCuisine)
    if filterDifficulty:
        query += " AND LOWER(c.difficulty) = LOWER(?)"
        params.append(filterDifficulty)
    if filterDietary:
        query += " AND LOWER(c.dietary_category) = LOWER(?)"
        params.append(filterDietary)
    if searchQuery:
        query += " AND (LOWER(c.title) LIKE ? OR LOWER(c.chef) LIKE ? OR LOWER(c.description) LIKE ? OR LOWER(c.ingredients) LIKE ?)"
        term = f"%{searchQuery.lower()}%"
        params.extend([term, term, term, term])

    query += " GROUP BY c.id ORDER BY c.title ASC;"

    cursor.execute(query, params)
    classes = cursor.fetchall()
    conn.close()
    return classes

def getClassById(classId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, u.first_name || ' ' || u.last_name AS manager_name, u.email AS manager_email,
               ROUND(AVG(r.score), 1) AS avg_rating,
               COUNT(DISTINCT r.id) AS total_ratings
        FROM classes c
        JOIN users u ON c.manager_id = u.id
        LEFT JOIN sessions s ON c.id = s.class_id
        LEFT JOIN ratings r ON s.id = r.session_id
        WHERE c.id = ?
        GROUP BY c.id;
    """, (classId,))
    c = cursor.fetchone()
    conn.close()
    return c

def getClassesByManager(managerId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*,
               ROUND(AVG(r.score), 1) AS avg_rating,
               COUNT(DISTINCT r.id) AS total_ratings,
               COUNT(DISTINCT s.id) AS total_sessions
        FROM classes c
        LEFT JOIN sessions s ON c.id = s.class_id
        LEFT JOIN ratings r ON s.id = r.session_id
        WHERE c.manager_id = ?
        GROUP BY c.id
        ORDER BY c.title ASC;
    """, (managerId,))
    classes = cursor.fetchall()
    conn.close()
    return classes

def createClass(managerId, title, cuisine, difficulty, duration, dietaryCategory, chef, ingredients, description, photo1, photo2, photo3):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO classes (
            manager_id, title, cuisine, difficulty, duration,
            dietary_category, chef, ingredients, description,
            photo1, photo2, photo3
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (managerId, title.strip(), cuisine.strip(), difficulty.strip(), int(duration),
          dietaryCategory.strip(), chef.strip(), ingredients.strip(), description.strip(),
          photo1.strip(), photo2.strip(), photo3.strip()))
    classId = cursor.lastrowid
    conn.commit()
    conn.close()
    return classId

def deleteClass(classId, managerId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM classes WHERE id = ?;", (classId,))
    targetClass = cursor.fetchone()
    if not targetClass:
        conn.close()
        return False, "Masterclass not found."
    if targetClass['manager_id'] != managerId:
        conn.close()
        return False, "You do not have permission to delete this masterclass."

    cursor.execute("""
        SELECT COUNT(e.id) AS enrolled_count
        FROM sessions s
        JOIN enrollments e ON s.id = e.session_id
        WHERE s.class_id = ?;
    """, (classId,))
    enrolledCount = cursor.fetchone()['enrolled_count']
    if enrolledCount > 0:
        conn.close()
        return False, "Cannot delete a masterclass that has active enrolled students in its sessions."

    cursor.execute("DELETE FROM classes WHERE id = ?;", (classId,))
    conn.commit()
    conn.close()
    return True, "Masterclass deleted successfully."

def getSessionsByClassId(classId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*,
               COUNT(DISTINCT e.id) AS enrolled_count,
               (s.capacity - COUNT(DISTINCT e.id)) AS available_seats,
               COUNT(DISTINCT w.id) AS waiting_count
        FROM sessions s
        LEFT JOIN enrollments e ON s.id = e.session_id
        LEFT JOIN waiting_list w ON s.id = w.session_id
        WHERE s.class_id = ?
        GROUP BY s.id
        ORDER BY s.day_order ASC, s.start_time ASC;
    """, (classId,))
    sessions = cursor.fetchall()
    conn.close()
    return sessions

def getSessionById(sessionId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, c.title AS class_title, c.cuisine, c.difficulty, c.duration,
               c.dietary_category, c.chef, c.ingredients, c.description,
               c.photo1, c.photo2, c.photo3, c.manager_id,
               u.first_name || ' ' || u.last_name AS manager_name,
               COUNT(DISTINCT e.id) AS enrolled_count,
               (s.capacity - COUNT(DISTINCT e.id)) AS available_seats,
               COUNT(DISTINCT w.id) AS waiting_count
        FROM sessions s
        JOIN classes c ON s.class_id = c.id
        JOIN users u ON c.manager_id = u.id
        LEFT JOIN enrollments e ON s.id = e.session_id
        LEFT JOIN waiting_list w ON s.id = w.session_id
        WHERE s.id = ?
        GROUP BY s.id;
    """, (sessionId,))
    session = cursor.fetchone()
    conn.close()
    return session

def createSession(classId, dayOfWeek, startTime, kitchen, capacity):
    if dayOfWeek not in DAYS_OF_WEEK:
        raise ValueError(f"Invalid day: {dayOfWeek}")
    dayOrder = DAY_TO_INDEX[dayOfWeek] + 1

    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (class_id, day_of_week, day_order, start_time, kitchen, capacity)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (classId, dayOfWeek, dayOrder, startTime.strip(), kitchen.strip(), int(capacity)))
    sessionId = cursor.lastrowid
    conn.commit()
    conn.close()
    return sessionId

def deleteSession(sessionId, managerId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, c.manager_id, COUNT(e.id) AS enrolled_count
        FROM sessions s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN enrollments e ON s.id = e.session_id
        WHERE s.id = ?
        GROUP BY s.id;
    """, (sessionId,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        return False, "Session not found."
    if session['manager_id'] != managerId:
        conn.close()
        return False, "You do not have permission to delete this session."
    if session['enrolled_count'] > 0:
        conn.close()
        return False, "Cannot delete a session that already has enrolled students."

    cursor.execute("DELETE FROM sessions WHERE id = ?;", (sessionId,))
    conn.commit()
    conn.close()
    return True, "Session deleted successfully."

def updateSession(sessionId, managerId, dayOfWeek, startTime, kitchen, capacity):
    if dayOfWeek not in DAYS_OF_WEEK:
        return False, f"Invalid day of week: {dayOfWeek}"
    dayOrder = DAY_TO_INDEX[dayOfWeek] + 1

    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, c.manager_id, COUNT(e.id) AS enrolled_count
        FROM sessions s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN enrollments e ON s.id = e.session_id
        WHERE s.id = ?
        GROUP BY s.id;
    """, (sessionId,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        return False, "Session not found."
    if session['manager_id'] != managerId:
        conn.close()
        return False, "You do not have permission to edit this session."
    if int(capacity) < session['enrolled_count']:
        conn.close()
        return False, f"Capacity cannot be less than the current number of enrolled students ({session['enrolled_count']})."

    cursor.execute("""
        UPDATE sessions
        SET day_of_week = ?, day_order = ?, start_time = ?, kitchen = ?, capacity = ?
        WHERE id = ?;
    """, (dayOfWeek, dayOrder, startTime.strip(), kitchen.strip(), int(capacity), sessionId))

    cursor.execute("SELECT capacity FROM sessions WHERE id = ?;", (sessionId,))
    sessionRow = cursor.fetchone()
    capacityVal = sessionRow['capacity']
    cursor.execute("SELECT COUNT(*) AS count FROM enrollments WHERE session_id = ?;", (sessionId,))
    enrolledCount = cursor.fetchone()['count']
    availableSeats = capacityVal - enrolledCount

    while availableSeats > 0:
        cursor.execute("""
            SELECT student_id FROM waiting_list
            WHERE session_id = ?
            ORDER BY joined_at ASC LIMIT 1;
        """, (sessionId,))
        nextStudent = cursor.fetchone()
        if not nextStudent:
            break
        candId = nextStudent['student_id']
        cursor.execute("DELETE FROM waiting_list WHERE session_id = ? AND student_id = ?;", (sessionId, candId))
        eligible, _ = checkEnrollmentEligibility(candId, sessionId)
        if eligible:
            cursor.execute("INSERT INTO enrollments (session_id, student_id) VALUES (?, ?);", (sessionId, candId))
            availableSeats -= 1

    conn.commit()
    conn.close()
    return True, "Session updated successfully."

def getEnrolledStudents(sessionId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.first_name, u.last_name, u.email, e.enrolled_at
        FROM enrollments e
        JOIN users u ON e.student_id = u.id
        WHERE e.session_id = ?
        ORDER BY e.enrolled_at ASC;
    """, (sessionId,))
    students = cursor.fetchall()
    conn.close()
    return students

def getActiveBookingsCount(studentId, excludeSessionId=None):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.day_of_week, s.start_time
        FROM enrollments e
        JOIN sessions s ON e.session_id = s.id
        WHERE e.student_id = ?;
    """, (studentId,))
    enrollments = cursor.fetchall()

    activeEnrollmentCount = 0
    for e in enrollments:
        if excludeSessionId and e['id'] == excludeSessionId:
            continue
        if not isSessionPast(e['day_of_week'], e['start_time']):
            activeEnrollmentCount += 1

    if excludeSessionId:
        cursor.execute("SELECT COUNT(*) AS total FROM waiting_list WHERE student_id = ? AND session_id != ?;", (studentId, excludeSessionId))
    else:
        cursor.execute("SELECT COUNT(*) AS total FROM waiting_list WHERE student_id = ?;", (studentId,))
    waitingCount = cursor.fetchone()['total']
    conn.close()

    return activeEnrollmentCount + waitingCount

def checkEnrollmentEligibility(studentId, sessionId, isPromotion=False):
    conn = getDatabaseConnection()
    cursor = conn.cursor()

    cursor.execute("SELECT role FROM users WHERE id = ?;", (studentId,))
    user = cursor.fetchone()
    if not user or user['role'] != 'student':
        conn.close()
        return False, "Only registered students can enroll in class sessions."

    cursor.execute("""
        SELECT s.*, c.duration, c.title
        FROM sessions s
        JOIN classes c ON s.class_id = c.id
        WHERE s.id = ?;
    """, (sessionId,))
    targetSession = cursor.fetchone()
    if not targetSession:
        conn.close()
        return False, "Session not found."

    if isSessionPast(targetSession['day_of_week'], targetSession['start_time']):
        conn.close()
        return False, "Cannot enroll in a session that has already started or passed."

    cursor.execute("SELECT id FROM enrollments WHERE session_id = ? AND student_id = ?;", (sessionId, studentId))
    if cursor.fetchone():
        conn.close()
        return False, "You are already enrolled in this session."

    if getActiveBookingsCount(studentId, excludeSessionId=sessionId) >= 4:
        conn.close()
        return False, "Maximum limit reached: You can have at most 4 active bookings (including waiting lists)."

    if not isPromotion:
        cursor.execute("SELECT COUNT(*) AS total FROM enrollments WHERE session_id = ?;", (sessionId,))
        if cursor.fetchone()['total'] >= targetSession['capacity']:
            conn.close()
            return False, "This session is fully booked."

    targetStart = timeToWeeklyMinutes(targetSession['day_of_week'], targetSession['start_time'])
    targetEnd = targetStart + targetSession['duration']

    cursor.execute("""
        SELECT s.day_of_week, s.start_time, c.duration, c.title
        FROM enrollments e
        JOIN sessions s ON e.session_id = s.id
        JOIN classes c ON s.class_id = c.id
        WHERE e.student_id = ?;
    """, (studentId,))
    existingEnrollments = cursor.fetchall()
    conn.close()

    for ex in existingEnrollments:
        if isSessionPast(ex['day_of_week'], ex['start_time']):
            continue
        exStart = timeToWeeklyMinutes(ex['day_of_week'], ex['start_time'])
        exEnd = exStart + ex['duration']
        if max(targetStart, exStart) < min(targetEnd, exEnd):
            return False, f"Schedule conflict: Overlaps with '{ex['title']}' on {ex['day_of_week']} at {ex['start_time']}."

    return True, "Eligible"

def enrollStudent(studentId, sessionId):
    eligible, reason = checkEnrollmentEligibility(studentId, sessionId)
    if not eligible:
        return False, reason

    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO enrollments (session_id, student_id) VALUES (?, ?);", (sessionId, studentId))
    cursor.execute("DELETE FROM waiting_list WHERE session_id = ? AND student_id = ?;", (sessionId, studentId))
    conn.commit()
    conn.close()
    return True, "Successfully enrolled in the cooking class session!"

def cancelEnrollment(studentId, sessionId):
    session = getSessionById(sessionId)
    if not session:
        return False, "Session not found."

    if not canCancelEnrollment(session['day_of_week'], session['start_time']):
        return False, "Cancellations are only permitted at least 12 hours before the scheduled class session."

    conn = getDatabaseConnection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM enrollments WHERE session_id = ? AND student_id = ?;", (sessionId, studentId))
    enrollment = cursor.fetchone()
    if not enrollment:
        conn.close()
        return False, "You are not enrolled in this session."

    cursor.execute("DELETE FROM enrollments WHERE id = ?;", (enrollment['id'],))
    conn.commit()

    promotedMsg = ""
    cursor.execute("""
        SELECT student_id FROM waiting_list
        WHERE session_id = ?
        ORDER BY joined_at ASC;
    """, (sessionId,))
    waitingCandidates = cursor.fetchall()

    for candidate in waitingCandidates:
        candId = candidate['student_id']
        eligible, _ = checkEnrollmentEligibility(candId, sessionId, isPromotion=True)
        if eligible:
            cursor.execute("INSERT INTO enrollments (session_id, student_id) VALUES (?, ?);", (sessionId, candId))
            cursor.execute("DELETE FROM waiting_list WHERE session_id = ? AND student_id = ?;", (sessionId, candId))
            promotedMsg = " The first eligible student on the waiting list was automatically enrolled."
            break
        else:
            cursor.execute("DELETE FROM waiting_list WHERE session_id = ? AND student_id = ?;", (sessionId, candId))

    conn.commit()
    conn.close()
    return True, f"Enrollment cancelled successfully.{promotedMsg}"

def getStudentEnrollments(studentId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.id AS enrollment_id, e.enrolled_at,
               s.id AS session_id, s.day_of_week, s.day_order, s.start_time, s.kitchen, s.capacity,
               c.id AS class_id, c.title, c.cuisine, c.difficulty, c.duration,
               c.dietary_category, c.chef, c.photo1,
               r.score AS user_rating, r.comment AS user_comment
        FROM enrollments e
        JOIN sessions s ON e.session_id = s.id
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN ratings r ON (r.session_id = s.id AND r.student_id = e.student_id)
        WHERE e.student_id = ?
        ORDER BY s.day_order ASC, s.start_time ASC;
    """, (studentId,))
    rawRows = cursor.fetchall()
    conn.close()

    enrollments = []
    for row in rawRows:
        d = dict(row)
        d['is_past'] = isSessionPast(d['day_of_week'], d['start_time'])
        d['can_cancel'] = canCancelEnrollment(d['day_of_week'], d['start_time'])
        enrollments.append(d)
    return enrollments

def addRating(studentId, sessionId, score, comment=""):
    if score not in (1, 2, 3, 4, 5):
        return False, "Rating score must be an integer between 1 and 5."

    session = getSessionById(sessionId)
    if not session:
        return False, "Session not found."

    if not isSessionPast(session['day_of_week'], session['start_time']):
        return False, "You can only rate class sessions that have already taken place."

    conn = getDatabaseConnection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM enrollments WHERE session_id = ? AND student_id = ?;", (sessionId, studentId))
    if not cursor.fetchone():
        conn.close()
        return False, "You can only rate sessions in which you were enrolled."

    cursor.execute("SELECT id FROM ratings WHERE session_id = ? AND student_id = ?;", (sessionId, studentId))
    existingRating = cursor.fetchone()
    if existingRating:
        cursor.execute("""
            UPDATE ratings SET score = ?, comment = ?
            WHERE id = ?;
        """, (score, comment.strip() if comment else "", existingRating['id']))
        conn.commit()
        conn.close()
        return True, "Your review has been updated successfully!"

    cursor.execute("""
        INSERT INTO ratings (session_id, student_id, score, comment)
        VALUES (?, ?, ?, ?);
    """, (sessionId, studentId, score, comment.strip() if comment else ""))
    conn.commit()
    conn.close()
    return True, "Rating submitted successfully!"

def getClassRatings(classId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.score, r.comment, r.created_at,
               u.first_name, SUBSTR(u.last_name, 1, 1) || '.' AS last_initial,
               s.day_of_week, s.start_time
        FROM ratings r
        JOIN sessions s ON r.session_id = s.id
        JOIN users u ON r.student_id = u.id
        WHERE s.class_id = ?
        ORDER BY r.created_at DESC;
    """, (classId,))
    ratings = cursor.fetchall()
    conn.close()
    return ratings

def joinWaitingList(studentId, sessionId):
    session = getSessionById(sessionId)
    if not session:
        return False, "Session not found."

    if isSessionPast(session['day_of_week'], session['start_time']):
        return False, "Cannot join waiting list for a past session."

    if session['available_seats'] > 0:
        return False, "Session has available places; you can enroll directly."

    conn = getDatabaseConnection()
    cursor = conn.cursor()

    cursor.execute("SELECT role FROM users WHERE id = ?;", (studentId,))
    user = cursor.fetchone()
    if not user or user['role'] != 'student':
        conn.close()
        return False, "Only registered students can join waiting lists."

    cursor.execute("SELECT id FROM enrollments WHERE session_id = ? AND student_id = ?;", (sessionId, studentId))
    if cursor.fetchone():
        conn.close()
        return False, "You are already enrolled in this session."

    cursor.execute("SELECT id FROM waiting_list WHERE session_id = ? AND student_id = ?;", (sessionId, studentId))
    if cursor.fetchone():
        conn.close()
        return False, "You are already on the waiting list for this session."

    if getActiveBookingsCount(studentId) >= 4:
        conn.close()
        return False, "Maximum limit reached: You can have at most 4 active bookings (including waiting lists)."

    cursor.execute("INSERT INTO waiting_list (session_id, student_id) VALUES (?, ?);", (sessionId, studentId))
    conn.commit()
    conn.close()
    return True, "Added to the waiting list! If a place frees up, you will be enrolled automatically."

def leaveWaitingList(studentId, sessionId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM waiting_list WHERE session_id = ? AND student_id = ?;", (sessionId, studentId))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        return True, "Left the waiting list."
    return False, "You were not on the waiting list for this session."

def getStudentWaitingLists(studentId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT w.id AS wait_id, w.joined_at, w.session_id,
               s.day_of_week, s.start_time, s.kitchen,
               c.id AS class_id, c.title, c.cuisine, c.chef, c.duration
        FROM waiting_list w
        JOIN sessions s ON w.session_id = s.id
        JOIN classes c ON s.class_id = c.id
        WHERE w.student_id = ?
        ORDER BY w.joined_at ASC;
    """, (studentId,))
    waitingEntries = cursor.fetchall()

    results = []
    for entry in waitingEntries:
        d = dict(entry)
        cursor.execute("""
            SELECT COUNT(*) + 1 AS position
            FROM waiting_list
            WHERE session_id = ? AND joined_at < ?;
        """, (d['session_id'], d['joined_at']))
        posRow = cursor.fetchone()
        d['position'] = posRow['position'] if posRow else 1
        results.append(d)

    conn.close()
    return results

def getSessionWaitingList(sessionId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT w.id, w.joined_at, u.id AS student_id, u.first_name, u.last_name, u.email
        FROM waiting_list w
        JOIN users u ON w.student_id = u.id
        WHERE w.session_id = ?
        ORDER BY w.joined_at ASC;
    """, (sessionId,))
    waitingStudents = cursor.fetchall()
    conn.close()
    return waitingStudents

def getManagerStatistics(managerId):
    conn = getDatabaseConnection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM classes WHERE manager_id = ?;", (managerId,))
    totalClasses = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(s.id) AS total
        FROM sessions s
        JOIN classes c ON s.class_id = c.id
        WHERE c.manager_id = ?;
    """, (managerId,))
    totalSessions = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(e.id) AS total
        FROM enrollments e
        JOIN sessions s ON e.session_id = s.id
        JOIN classes c ON s.class_id = c.id
        WHERE c.manager_id = ?;
    """, (managerId,))
    totalEnrollments = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(w.id) AS total
        FROM waiting_list w
        JOIN sessions s ON w.session_id = s.id
        JOIN classes c ON s.class_id = c.id
        WHERE c.manager_id = ?;
    """, (managerId,))
    totalWaiting = cursor.fetchone()['total']

    cursor.execute("""
        SELECT c.cuisine, COUNT(e.id) AS enroll_count
        FROM classes c
        JOIN sessions s ON c.id = s.class_id
        JOIN enrollments e ON s.id = e.session_id
        WHERE c.manager_id = ?
        GROUP BY c.cuisine
        ORDER BY enroll_count DESC
        LIMIT 1;
    """, (managerId,))
    popRow = cursor.fetchone()
    mostPopularCuisine = popRow['cuisine'] if popRow else "N/A"

    cursor.execute("""
        SELECT c.title, ROUND(AVG(r.score), 1) AS avg_score, COUNT(r.id) AS review_count
        FROM classes c
        JOIN sessions s ON c.id = s.class_id
        JOIN ratings r ON s.id = r.session_id
        WHERE c.manager_id = ?
        GROUP BY c.id
        HAVING review_count > 0
        ORDER BY avg_score DESC, review_count DESC
        LIMIT 1;
    """, (managerId,))
    topRow = cursor.fetchone()
    topRatedClass = f"{topRow['title']} ({topRow['avg_score']} / 5)" if topRow else "No ratings yet"

    conn.close()

    return {
        'totalClasses': totalClasses,
        'totalSessions': totalSessions,
        'totalEnrollments': totalEnrollments,
        'totalWaiting': totalWaiting,
        'mostPopularCuisine': mostPopularCuisine,
        'topRatedClass': topRatedClass
    }