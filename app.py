from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# =========================================================
# APPLICATION SETTINGS
# =========================================================

app.secret_key = "change-this-to-a-random-secret-key"

DATABASE_NAME = "ayush_skillbridge.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# =========================================================
# ROLE CHECKS
# =========================================================

def student_required():
    return (
        "user_id" in session
        and session.get("role") == "student"
    )


def academician_required():
    return (
        "user_id" in session
        and session.get("role") == "academician"
    )


def industry_required():
    return (
        "user_id" in session
        and session.get("role") == "industry"
    )


def institution_required():
    return (
        "user_id" in session
        and session.get("role") == "institution"
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "").strip().lower()

        if not email or not password or not role:
            return "Please fill all login fields."

        connection = get_connection()

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            AND role = ?
            """,
            (email, role)
        ).fetchone()

        connection.close()

        if user is None:
            return "Invalid email or role."

        if not check_password_hash(user["password"], password):
            return "Invalid password."

        session["user_id"] = user["id"]
        session["name"] = user["name"]
        session["role"] = user["role"]

        if role == "student":
            return redirect(url_for("student_dashboard"))

        elif role == "academician":
            return redirect(url_for("academician_dashboard"))

        elif role == "industry":
            return redirect(url_for("industry_dashboard"))

        elif role == "institution":
            return redirect(url_for("institution_dashboard"))

        return "Invalid role selected."

    return render_template("login.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "").strip().lower()

        if (
            not name
            or not email
            or not password
            or not confirm_password
            or not role
        ):
            return "Please fill all required fields."

        if password != confirm_password:
            return "Passwords do not match."

        allowed_roles = [
            "student",
            "academician",
            "industry",
            "institution"
        ]

        if role not in allowed_roles:
            return "Invalid role selected."

        password_hash = generate_password_hash(password)

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO users (
                    name,
                    email,
                    password,
                    role
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    password_hash,
                    role
                )
            )

            connection.commit()
            connection.close()

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            connection.close()

            return """
            <h2>Email already registered.</h2>
            <p>Please use a different email address.</p>
            <a href="/register">Back to Registration</a>
            """

    return render_template("register.html")


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/student/dashboard")
def student_dashboard():

    if not student_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_connection()

    latest_result = connection.execute(
        """
        SELECT *
        FROM assessment_results
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()

    category_rows = []

    if latest_result:

        category_rows = connection.execute(
            """
            SELECT
                q.category AS category,
                SUM(a.score) AS score,
                SUM(q.max_score) AS max_score
            FROM assessment_answers a
            JOIN assessment_questions q
                ON a.question_id = q.id
            WHERE a.result_id = ?
            GROUP BY q.category
            ORDER BY MIN(q.id)
            """,
            (latest_result["id"],)
        ).fetchall()

    opportunity_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM opportunities
        WHERE status = 'Open'
        AND opportunity_type IN ('Internship', 'Project')
        """
    ).fetchone()[0]

    application_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM applications
        WHERE student_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    connection.close()

    overall_percentage = 0
    strong_count = 0
    gap_count = 0

    skill_categories = []

    if latest_result:

        overall_percentage = float(
            latest_result["percentage"] or 0
        )

        for row in category_rows:

            score = float(row["score"] or 0)
            max_score = float(row["max_score"] or 0)

            if max_score > 0:
                percentage = (score / max_score) * 100
            else:
                percentage = 0

            percentage = round(percentage, 2)

            skill_categories.append(
                {
                    "category": row["category"],
                    "score": score,
                    "max_score": max_score,
                    "percentage": percentage
                }
            )

            if percentage >= 75:
                strong_count += 1

            elif percentage < 60:
                gap_count += 1

    return render_template(
        "student_dashboard.html",
        name=session.get("name"),
        overall_percentage=round(overall_percentage, 2),
        skill_gap_count=gap_count,
        matched_opportunities=opportunity_count,
        application_count=application_count,
        strong_count=strong_count,
        skill_categories=skill_categories
    )


# =========================================================
# STUDENT PROFILE
# =========================================================

@app.route("/student/profile", methods=["GET", "POST"])
def student_profile():

    if not student_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_connection()

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        institution = request.form.get("institution", "").strip()
        course = request.form.get("course", "").strip()
        department = request.form.get("department", "").strip()
        graduation_year = request.form.get("graduation_year", "").strip()
        career_interest = request.form.get("career_interest", "").strip()
        opportunity_type = request.form.get("opportunity_type", "").strip()
        bio = request.form.get("bio", "").strip()

        if not full_name or not email:

            connection.close()

            return "Full name and email are required."

        existing_profile = connection.execute(
            """
            SELECT id
            FROM student_profiles
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        if existing_profile:

            connection.execute(
                """
                UPDATE student_profiles
                SET
                    full_name = ?,
                    email = ?,
                    institution = ?,
                    course = ?,
                    department = ?,
                    graduation_year = ?,
                    career_interest = ?,
                    opportunity_type = ?,
                    bio = ?
                WHERE user_id = ?
                """,
                (
                    full_name,
                    email,
                    institution,
                    course,
                    department,
                    graduation_year,
                    career_interest,
                    opportunity_type,
                    bio,
                    user_id
                )
            )

        else:

            connection.execute(
                """
                INSERT INTO student_profiles (
                    user_id,
                    full_name,
                    email,
                    institution,
                    course,
                    department,
                    graduation_year,
                    career_interest,
                    opportunity_type,
                    bio
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    full_name,
                    email,
                    institution,
                    course,
                    department,
                    graduation_year,
                    career_interest,
                    opportunity_type,
                    bio
                )
            )

        connection.execute(
            """
            UPDATE users
            SET name = ?
            WHERE id = ?
            """,
            (full_name, user_id)
        )

        connection.commit()
        connection.close()

        session["name"] = full_name

        return redirect(url_for("student_profile"))

    profile = connection.execute(
        """
        SELECT *
        FROM student_profiles
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    connection.close()

    return render_template(
        "student_profile.html",
        name=session.get("name"),
        profile=profile
    )


# =========================================================
# STUDENT SKILL ASSESSMENT
# =========================================================

@app.route("/student/assessment", methods=["GET", "POST"])
def student_assessment():

    if not student_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_connection()

    if request.method == "GET":

        questions = connection.execute(
            """
            SELECT *
            FROM assessment_questions
            ORDER BY id
            """
        ).fetchall()

        connection.close()

        return render_template(
            "skill_assessment.html",
            name=session.get("name"),
            questions=questions
        )

    questions = connection.execute(
        """
        SELECT *
        FROM assessment_questions
        ORDER BY id
        """
    ).fetchall()

    if not questions:

        connection.close()

        return "No assessment questions are available."

    total_score = 0
    max_score = 0
    answers_to_save = []

    for question in questions:

        question_id = question["id"]

        selected_answer = request.form.get(
            f"q{question_id}",
            ""
        ).strip()

        if not selected_answer:

            connection.close()

            return f"Please answer Question {question_id}."

        question_max_score = float(
            question["max_score"] or 5
        )

        max_score += question_max_score

        score = 0

        if question["question_type"] == "self_rating":

            try:
                rating = int(selected_answer)
            except ValueError:
                rating = 0

            if 1 <= rating <= 5:
                score = rating

        elif question["question_type"] == "objective":

            correct_answer = (
                question["correct_answer"] or ""
            ).strip().upper()

            option_number_to_letter = {
                "1": "A",
                "2": "B",
                "3": "C",
                "4": "D",
                "5": "E"
            }

            selected_letter = (
                option_number_to_letter.get(
                    selected_answer,
                    ""
                )
            )

            if selected_letter == correct_answer:
                score = question_max_score

        total_score += score

        answers_to_save.append(
            (
                question_id,
                selected_answer,
                score
            )
        )

    if max_score > 0:
        percentage = (
            total_score / max_score
        ) * 100
    else:
        percentage = 0

    percentage = round(percentage, 2)

    result_cursor = connection.execute(
        """
        INSERT INTO assessment_results (
            user_id,
            total_score,
            max_score,
            percentage
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            total_score,
            max_score,
            percentage
        )
    )

    result_id = result_cursor.lastrowid

    for question_id, selected_answer, score in answers_to_save:

        connection.execute(
            """
            INSERT INTO assessment_answers (
                result_id,
                question_id,
                selected_answer,
                score
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                result_id,
                question_id,
                selected_answer,
                score
            )
        )

    connection.commit()

    category_results = connection.execute(
        """
        SELECT
            q.category AS category,
            SUM(a.score) AS score,
            SUM(q.max_score) AS max_score
        FROM assessment_answers a
        JOIN assessment_questions q
            ON a.question_id = q.id
        WHERE a.result_id = ?
        GROUP BY q.category
        ORDER BY MIN(q.id)
        """,
        (result_id,)
    ).fetchall()

    connection.close()

    session["latest_assessment_result_id"] = result_id

    return render_template(
        "assessment_result.html",
        name=session.get("name"),
        total_score=round(total_score, 2),
        max_score=round(max_score, 2),
        percentage=percentage,
        category_results=category_results
    )


# =========================================================
# STUDENT SKILL GAP
# =========================================================

@app.route("/student/skill-gap")
def student_skill_gap():

    if not student_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_connection()

    latest_result = connection.execute(
        """
        SELECT *
        FROM assessment_results
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()

    if latest_result is None:

        connection.close()

        return render_template(
            "skill_gap.html",
            name=session.get("name"),
            overall_percentage=0,
            strong_count=0,
            gap_count=0,
            categories=[],
            gaps=[],
            recommendations=[]
        )

    result_id = latest_result["id"]

    category_rows = connection.execute(
        """
        SELECT
            q.category AS category,
            SUM(a.score) AS score,
            SUM(q.max_score) AS max_score
        FROM assessment_answers a
        JOIN assessment_questions q
            ON a.question_id = q.id
        WHERE a.result_id = ?
        GROUP BY q.category
        ORDER BY MIN(q.id)
        """,
        (result_id,)
    ).fetchall()

    connection.close()

    categories = []
    strong_count = 0
    gap_count = 0

    recommendation_map = {

        "AYUSH Domain Knowledge": {
            "title": "AYUSH Domain Learning",
            "description": (
                "Strengthen your understanding of AYUSH systems, "
                "concepts, applications and domain fundamentals."
            ),
            "tag": "Domain Development"
        },

        "Research & Documentation": {
            "title": "Research Methodology",
            "description": (
                "Build stronger skills in research planning, "
                "documentation, evidence review and reporting."
            ),
            "tag": "Research Skill"
        },

        "Digital & Healthcare Skills": {
            "title": "Digital Health Fundamentals",
            "description": (
                "Improve your familiarity with digital tools, "
                "healthcare technology and data handling."
            ),
            "tag": "Digital Skill"
        },

        "Analytical Thinking": {
            "title": "Data Interpretation & Analytical Thinking",
            "description": (
                "Practice structured analysis, data interpretation "
                "and problem-solving techniques."
            ),
            "tag": "Analytical Skill"
        },

        "Communication & Collaboration": {
            "title": "Communication & Team Collaboration",
            "description": (
                "Develop presentation, communication and teamwork "
                "skills for academic and industry collaboration."
            ),
            "tag": "Soft Skill"
        },

        "Aptitude & Problem Solving": {
            "title": "Problem Solving & Aptitude Practice",
            "description": (
                "Improve logical reasoning, decision-making and "
                "structured problem-solving abilities."
            ),
            "tag": "Aptitude"
        }
    }

    for row in category_rows:

        score = float(row["score"] or 0)
        max_score = float(row["max_score"] or 0)

        if max_score > 0:
            percentage = (score / max_score) * 100
        else:
            percentage = 0

        percentage = round(percentage, 2)

        categories.append(
            {
                "category": row["category"],
                "score": score,
                "max_score": max_score,
                "percentage": percentage
            }
        )

        if percentage >= 75:
            strong_count += 1

        elif percentage < 60:
            gap_count += 1

    gaps = []

    for item in categories:

        if item["percentage"] < 60:

            gaps.append(
                {
                    "category": item["category"],
                    "percentage": item["percentage"]
                }
            )

    recommendations = []

    for gap in gaps:

        category = gap["category"]

        if category in recommendation_map:

            recommendations.append(
                recommendation_map[category]
            )

    return render_template(
        "skill_gap.html",
        name=session.get("name"),
        overall_percentage=float(
            latest_result["percentage"] or 0
        ),
        strong_count=strong_count,
        gap_count=gap_count,
        categories=categories,
        gaps=gaps,
        recommendations=recommendations
    )


# =========================================================
# STUDENT LEARNING
# =========================================================

@app.route("/student/learning")
def student_learning():

    if not student_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_connection()

    latest_result = connection.execute(
        """
        SELECT *
        FROM assessment_results
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()

    if latest_result is None:

        connection.close()

        return render_template(
            "learning.html",
            name=session.get("name"),
            overall_percentage=0,
            gap_count=0,
            recommendations=[],
            gaps=[]
        )

    result_id = latest_result["id"]

    category_rows = connection.execute(
        """
        SELECT
            q.category AS category,
            SUM(a.score) AS score,
            SUM(q.max_score) AS max_score
        FROM assessment_answers a
        JOIN assessment_questions q
            ON a.question_id = q.id
        WHERE a.result_id = ?
        GROUP BY q.category
        ORDER BY MIN(q.id)
        """,
        (result_id,)
    ).fetchall()

    connection.close()

    recommendation_map = {

        "AYUSH Domain Knowledge": {
            "title": "AYUSH Domain Learning",
            "description": (
                "Strengthen your understanding of AYUSH systems, "
                "traditional healthcare concepts and applications."
            ),
            "tag": "Domain Development"
        },

        "Research & Documentation": {
            "title": "Research Methodology",
            "description": (
                "Improve research planning, literature review, "
                "documentation and evidence-based reporting."
            ),
            "tag": "Research Skill"
        },

        "Digital & Healthcare Skills": {
            "title": "Digital Health Fundamentals",
            "description": (
                "Build knowledge of digital healthcare tools, "
                "health data handling and technology."
            ),
            "tag": "Digital Skill"
        },

        "Analytical Thinking": {
            "title": "Data Interpretation & Analytical Thinking",
            "description": (
                "Practice structured thinking, data interpretation "
                "and analytical problem-solving."
            ),
            "tag": "Analytical Skill"
        },

        "Communication & Collaboration": {
            "title": "Communication & Team Collaboration",
            "description": (
                "Develop communication, presentation, teamwork "
                "and collaboration skills."
            ),
            "tag": "Soft Skill"
        },

        "Aptitude & Problem Solving": {
            "title": "Problem Solving & Aptitude Practice",
            "description": (
                "Improve logical reasoning, decision-making "
                "and structured problem-solving."
            ),
            "tag": "Aptitude"
        }
    }

    gaps = []

    for row in category_rows:

        score = float(row["score"] or 0)
        max_score = float(row["max_score"] or 0)

        if max_score > 0:
            percentage = (score / max_score) * 100
        else:
            percentage = 0

        percentage = round(percentage, 2)

        if percentage < 60:

            gaps.append(
                {
                    "category": row["category"],
                    "percentage": percentage
                }
            )

    recommendations = []

    for gap in gaps:

        category = gap["category"]

        if category in recommendation_map:

            recommendations.append(
                recommendation_map[category]
            )

    return render_template(
        "learning.html",
        name=session.get("name"),
        overall_percentage=float(
            latest_result["percentage"] or 0
        ),
        gap_count=len(gaps),
        recommendations=recommendations,
        gaps=gaps
    )
# =========================================================
# SMART SKILL MATCHING
# =========================================================

@app.route("/student/smart-matching")
def smart_matching():

    if not student_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_connection()

    # Student profile
    profile = connection.execute("""
        SELECT *
        FROM student_profiles
        WHERE user_id = ?
    """, (user_id,)).fetchone()

    # Latest assessment
    latest_result = connection.execute("""
        SELECT *
        FROM assessment_results
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,)).fetchone()

    # Open opportunities
    opportunities = connection.execute("""
        SELECT *
        FROM opportunities
        WHERE status = 'Open'
        AND opportunity_type IN ('Internship', 'Project')
        ORDER BY id DESC
    """).fetchall()

    # Student strong skills
    student_skills = set()

    if latest_result:

        skill_rows = connection.execute("""
            SELECT
                q.category AS category,
                SUM(a.score) AS score,
                SUM(q.max_score) AS max_score
            FROM assessment_answers a
            JOIN assessment_questions q
                ON a.question_id = q.id
            WHERE a.result_id = ?
            GROUP BY q.category
        """, (latest_result["id"],)).fetchall()

        for row in skill_rows:

            score = float(row["score"] or 0)
            max_score = float(row["max_score"] or 0)

            if max_score > 0:
                percentage = (score / max_score) * 100
            else:
                percentage = 0

            if percentage >= 60:
                student_skills.add(
                    row["category"].strip().lower()
                )

    matches = []

    career_interest = ""

    if profile:
        career_interest = (
            profile["career_interest"] or ""
        ).strip().lower()

    overall_percentage = 0

    if latest_result:
        overall_percentage = float(
            latest_result["percentage"] or 0
        )

    for opportunity in opportunities:

        required_skills_text = (
            opportunity["required_skills"] or ""
        ).lower()

        domain_text = (
            opportunity["domain"] or ""
        ).lower()

        opportunity_text = (
            required_skills_text
            + " "
            + domain_text
        )

        matched_skills = []

        for skill in student_skills:

            if skill in opportunity_text:

                matched_skills.append(skill)

        # Career interest match
        career_match = False

        if career_interest:

            if career_interest in opportunity_text:
                career_match = True

        skill_score = 0

        if student_skills:

            skill_score = (
                len(matched_skills)
                / len(student_skills)
            ) * 100

        career_score = 20 if career_match else 0

        match_percentage = min(
            100,
            round(
                (skill_score * 0.8) + career_score,
                2
            )
        )

        # Show opportunities even when no exact skill text matches,
        # but give them a lower score.
        if match_percentage == 0:

            if career_interest and career_interest in domain_text:
                match_percentage = 50
            else:
                match_percentage = 25

        matches.append({
            "id": opportunity["id"],
            "title": opportunity["title"],
            "organization": opportunity["organization"],
            "description": opportunity["description"],
            "opportunity_type": opportunity["opportunity_type"],
            "domain": opportunity["domain"],
            "mode": opportunity["mode"],
            "match_percentage": match_percentage,
            "matched_skills": matched_skills
        })

    matches.sort(
        key=lambda x: x["match_percentage"],
        reverse=True
    )

    connection.close()

    return render_template(
        "smart_matching.html",
        name=session.get("name"),
        career_interest=(
            profile["career_interest"]
            if profile else ""
        ),
        overall_percentage=round(
            overall_percentage,
            2
        ),
        matches=matches
    )

# =========================================================
# STUDENT OPPORTUNITIES
# =========================================================

@app.route("/student/opportunities")
def student_opportunities():

    if not student_required():
        return redirect(url_for("login"))

    connection = get_connection()

    opportunities = connection.execute(
        """
        SELECT *
        FROM opportunities
        WHERE status = 'Open'
        AND opportunity_type IN ('Internship', 'Project')
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "opportunities.html",
        name=session.get("name"),
        opportunities=opportunities
    )


# =========================================================
# OPPORTUNITY DETAILS
# =========================================================

@app.route("/student/opportunity/<int:opportunity_id>")
def student_opportunity_details(opportunity_id):

    if not student_required():
        return redirect(url_for("login"))

    connection = get_connection()

    opportunity = connection.execute(
        """
        SELECT *
        FROM opportunities
        WHERE id = ?
        """,
        (opportunity_id,)
    ).fetchone()

    connection.close()

    if opportunity is None:

        return """
        <h2>Opportunity Not Found</h2>
        <a href="/student/opportunities">
            Back to Opportunities
        </a>
        """

    return render_template(
        "opportunity_details.html",
        name=session.get("name"),
        opportunity=opportunity
    )


# =========================================================
# APPLY FOR OPPORTUNITY
# =========================================================

@app.route(
    "/student/opportunity/<int:opportunity_id>/apply",
    methods=["GET", "POST"]
)
def apply_opportunity(opportunity_id):

    if not student_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_connection()

    opportunity = connection.execute(
        """
        SELECT *
        FROM opportunities
        WHERE id = ?
        AND status = 'Open'
        """,
        (opportunity_id,)
    ).fetchone()

    if opportunity is None:

        connection.close()

        return """
        <h2>Opportunity Not Available</h2>
        <a href="/student/opportunities">
            Back to Opportunities
        </a>
        """

    existing_application = connection.execute(
        """
        SELECT *
        FROM applications
        WHERE opportunity_id = ?
        AND student_id = ?
        """,
        (
            opportunity_id,
            user_id
        )
    ).fetchone()

    if existing_application:

        connection.close()

        return """
        <h2>Already Applied</h2>
        <p>You have already applied for this opportunity.</p>
        <a href="/student/applications">
            View My Applications
        </a>
        """

    if request.method == "GET":

        connection.close()

        return render_template(
            "apply.html",
            name=session.get("name"),
            opportunity=opportunity
        )

    cover_note = request.form.get(
        "cover_note",
        ""
    ).strip()

    resume_file = request.form.get(
        "resume_file",
        ""
    ).strip()

    if not cover_note:

        connection.close()

        return "Please enter your application note."

    try:

        connection.execute(
            """
            INSERT INTO applications (
                opportunity_id,
                student_id,
                cover_note,
                resume_file,
                status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                opportunity_id,
                user_id,
                cover_note,
                resume_file,
                "Submitted"
            )
        )

        connection.commit()
        connection.close()

    except sqlite3.IntegrityError:

        connection.close()

        return """
        <h2>Application Already Exists</h2>
        <a href="/student/applications">
            View My Applications
        </a>
        """

    return redirect(
        url_for("student_applications")
    )


# =========================================================
# MY APPLICATIONS
# =========================================================

@app.route("/student/applications")
def student_applications():

    if not student_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_connection()

    applications = connection.execute(
        """
        SELECT
            a.id,
            a.cover_note,
            a.resume_file,
            a.status,
            a.applied_at,
            o.title,
            o.organization,
            o.opportunity_type,
            o.domain,
            o.location,
            o.mode,
            o.duration
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE a.student_id = ?
        ORDER BY a.id DESC
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    return render_template(
        "applications.html",
        name=session.get("name"),
        applications=applications
    )


# =========================================================
# STUDENT PLACEMENTS
# =========================================================

@app.route("/student/placements")
def student_placements():

    if not student_required():
        return redirect(url_for("login"))

    connection = get_connection()

    placements = connection.execute(
        """
        SELECT *
        FROM opportunities
        WHERE status = 'Open'
        AND opportunity_type IN ('Placement', 'Job')
        ORDER BY id DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "placements.html",
        name=session.get("name"),
        placements=placements
    )


# =========================================================
# PLACEMENT DETAILS
# =========================================================

@app.route("/student/placement/<int:opportunity_id>")
def student_placement_details(opportunity_id):

    if not student_required():
        return redirect(url_for("login"))

    connection = get_connection()

    placement = connection.execute(
        """
        SELECT *
        FROM opportunities
        WHERE id = ?
        AND opportunity_type IN ('Placement', 'Job')
        """,
        (opportunity_id,)
    ).fetchone()

    connection.close()

    if placement is None:

        return """
        <h2>Placement Not Found</h2>
        <a href="/student/placements">
            Back to Placements
        </a>
        """

    return render_template(
        "placement_details.html",
        name=session.get("name"),
        placement=placement
    )


# =========================================================
# STUDENT PORTFOLIO
# =========================================================

@app.route("/student/portfolio")
def student_portfolio():

    if not student_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_connection()

    profile = connection.execute(
        """
        SELECT *
        FROM student_profiles
        WHERE user_id = ?
        """,
        (user_id,)
    ).fetchone()

    latest_result = connection.execute(
        """
        SELECT *
        FROM assessment_results
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    ).fetchone()

    application_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM applications
        WHERE student_id = ?
        """,
        (user_id,)
    ).fetchone()[0]

    connection.close()

    return render_template(
        "portfolio.html",
        name=session.get("name"),
        profile=profile,
        latest_result=latest_result,
        application_count=application_count
    )


# =========================================================
# STUDENT NOTIFICATIONS
# =========================================================

@app.route("/student/notifications")
def notifications():

    if not student_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]

    connection = get_connection()

    applications = connection.execute(
        """
        SELECT
            a.*,
            o.title
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE a.student_id = ?
        ORDER BY a.applied_at DESC
        """,
        (user_id,)
    ).fetchall()

    opportunities = connection.execute(
        """
        SELECT *
        FROM opportunities
        WHERE status = 'Open'
        ORDER BY created_at DESC
        LIMIT 5
        """
    ).fetchall()

    connection.close()

    return render_template(
        "notifications.html",
        name=session.get("name"),
        applications=applications,
        opportunities=opportunities
    )


# =========================================================
# ACADEMICIAN DASHBOARD
# =========================================================

@app.route("/academician/dashboard")
def academician_dashboard():

    if not academician_required():
        return redirect(url_for("login"))

    return render_template(
        "academician_dashboard.html",
        name=session.get("name")
    )


# =========================================================
# ACADEMICIAN FACULTY OPPORTUNITIES
# =========================================================

@app.route("/academician/faculty-opportunities")
def academician_faculty_opportunities():

    if not academician_required():
        return redirect(url_for("login"))

    return render_template(
        "academician_faculty_opportunities.html",
        name=session.get("name")
    )


# =========================================================
# ACADEMICIAN INDUSTRIAL TRAINING
# =========================================================

@app.route("/academician/industrial-training")
def academician_industrial_training():

    if not academician_required():
        return redirect(url_for("login"))

    return render_template(
        "academician_industrial_training.html",
        name=session.get("name")
    )


# =========================================================
# ACADEMICIAN RESEARCH PROJECTS
# =========================================================

@app.route("/academician/research-projects")
def academician_research_projects():

    if not academician_required():
        return redirect(url_for("login"))

    return render_template(
        "academician_research_projects.html",
        name=session.get("name")
    )


# =========================================================
# ACADEMICIAN FDP & WORKSHOPS
# =========================================================

@app.route("/academician/fdp-workshops")
def academician_fdp_workshops():

    if not academician_required():
        return redirect(url_for("login"))

    return render_template(
        "academician_fdp_workshops.html",
        name=session.get("name")
    )


# =========================================================
# ACADEMICIAN CONSULTANCY
# =========================================================

@app.route("/academician/consultancy")
def academician_consultancy():

    if not academician_required():
        return redirect(url_for("login"))

    return render_template(
        "academician_consultancy.html",
        name=session.get("name")
    )


# =========================================================
# ACADEMICIAN COLLABORATION
# =========================================================

@app.route("/academician/collaboration")
def academician_collaboration():

    if not academician_required():
        return redirect(url_for("login"))

    return render_template(
        "academician_collaboration.html",
        name=session.get("name")
    )


# =========================================================
# INDUSTRY DASHBOARD
# =========================================================

@app.route("/industry/dashboard")
def industry_dashboard():

    if not industry_required():
        return redirect(url_for("login"))

    connection = get_connection()

    opportunity_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM opportunities
        WHERE created_by = ?
        AND status = 'Open'
        """,
        (session["user_id"],)
    ).fetchone()[0]

    application_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.created_by = ?
        """,
        (session["user_id"],)
    ).fetchone()[0]

    connection.close()

    return render_template(
        "industry_dashboard.html",
        name=session.get("name"),
        opportunity_count=opportunity_count,
        application_count=application_count
    )


# =========================================================
# INDUSTRY POST OPPORTUNITY
# =========================================================

@app.route(
    "/industry/post-opportunity",
    methods=["GET", "POST"]
)
def industry_post_opportunity():

    if not industry_required():
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        opportunity_type = request.form.get(
            "opportunity_type",
            ""
        ).strip()

        domain = request.form.get(
            "domain",
            ""
        ).strip()

        location = request.form.get(
            "location",
            ""
        ).strip()

        mode = request.form.get(
            "mode",
            ""
        ).strip()

        duration = request.form.get(
            "duration",
            ""
        ).strip()

        stipend = request.form.get(
            "stipend",
            ""
        ).strip()

        eligibility = request.form.get(
            "eligibility",
            ""
        ).strip()

        required_skills = request.form.get(
            "required_skills",
            ""
        ).strip()

        deadline = request.form.get(
            "deadline",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        if (
            not title
            or not opportunity_type
            or not domain
            or not description
        ):
            return "Please fill all required fields."

        connection = get_connection()

        connection.execute(
            """
            INSERT INTO opportunities (
                title,
                organization,
                description,
                opportunity_type,
                domain,
                location,
                mode,
                duration,
                stipend,
                eligibility,
                required_skills,
                deadline,
                status,
                created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                session.get("name"),
                description,
                opportunity_type,
                domain,
                location,
                mode,
                duration,
                stipend,
                eligibility,
                required_skills,
                deadline,
                "Open",
                session["user_id"]
            )
        )

        connection.commit()
        connection.close()

        return redirect(
            url_for("industry_dashboard")
        )

    return render_template(
        "industry_post_opportunity.html",
        name=session.get("name")
    )


# =========================================================
# INDUSTRY STUDENT APPLICATIONS
# =========================================================

@app.route("/industry/applications")
def industry_applications():

    if not industry_required():
        return redirect(url_for("login"))

    industry_id = session["user_id"]

    connection = get_connection()

    applications = connection.execute(
        """
        SELECT
            a.id,
            a.cover_note,
            a.resume_file,
            a.status,
            a.applied_at,

            o.title,
            o.opportunity_type,
            o.domain,

            u.name AS student_name,
            u.email AS student_email

        FROM applications a

        JOIN opportunities o
            ON a.opportunity_id = o.id

        JOIN users u
            ON a.student_id = u.id

        WHERE o.created_by = ?

        ORDER BY a.id DESC
        """,
        (industry_id,)
    ).fetchall()

    connection.close()

    return render_template(
        "industry_applications.html",
        name=session.get("name"),
        applications=applications
    )


# =========================================================
# INDUSTRY UPDATE APPLICATION STATUS
# =========================================================

@app.route(
    "/industry/application/<int:application_id>/<status>",
    methods=["POST"]
)
def industry_update_application_status(
    application_id,
    status
):

    if not industry_required():
        return redirect(url_for("login"))

    allowed_statuses = [
        "Approved",
        "Rejected"
    ]

    if status not in allowed_statuses:
        return "Invalid application status."

    industry_id = session["user_id"]

    connection = get_connection()

    application = connection.execute(
        """
        SELECT
            a.id
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE a.id = ?
        AND o.created_by = ?
        """,
        (
            application_id,
            industry_id
        )
    ).fetchone()

    if application is None:

        connection.close()

        return "Application not found."

    connection.execute(
        """
        UPDATE applications
        SET status = ?
        WHERE id = ?
        """,
        (
            status,
            application_id
        )
    )

    connection.commit()
    connection.close()

    return redirect(
        url_for("industry_applications")
    )


# =========================================================
# INDUSTRY FIND TALENT
# =========================================================

@app.route("/industry/talent")
def industry_talent():

    if not industry_required():
        return redirect(url_for("login"))

    search = request.args.get(
        "search",
        ""
    ).strip().lower()

    connection = get_connection()

    students = connection.execute(
        """
        SELECT
            u.id,
            u.name,
            u.email,

            sp.institution,
            sp.course,
            sp.career_interest,

            ar.percentage

        FROM users u

        LEFT JOIN student_profiles sp
            ON u.id = sp.user_id

        LEFT JOIN assessment_results ar
            ON ar.id = (
                SELECT id
                FROM assessment_results
                WHERE user_id = u.id
                ORDER BY id DESC
                LIMIT 1
            )

        WHERE u.role = 'student'

        ORDER BY u.name
        """
    ).fetchall()

    final_students = []

    for student in students:

        skills_rows = connection.execute(
            """
            SELECT
                q.category,
                SUM(a.score) AS score,
                SUM(q.max_score) AS max_score
            FROM assessment_answers a

            JOIN assessment_questions q
                ON a.question_id = q.id

            WHERE a.result_id = (
                SELECT id
                FROM assessment_results
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
            )

            GROUP BY q.category
            """,
            (student["id"],)
        ).fetchall()

        skills = []

        for skill_row in skills_rows:

            score = float(
                skill_row["score"] or 0
            )

            max_score = float(
                skill_row["max_score"] or 0
            )

            if max_score > 0:
                percentage = (
                    score / max_score
                ) * 100
            else:
                percentage = 0

            if percentage >= 75:

                skills.append(
                    skill_row["category"]
                )

        student_data = {
            "id": student["id"],
            "name": student["name"],
            "email": student["email"],
            "institution": student["institution"],
            "course": student["course"],
            "career_interest": student["career_interest"],
            "percentage": round(
                float(student["percentage"] or 0),
                2
            ),
            "skills": skills
        }

        if search:

            searchable_text = " ".join(
                [
                    str(student_data["name"] or ""),
                    str(student_data["email"] or ""),
                    str(student_data["institution"] or ""),
                    str(student_data["course"] or ""),
                    str(student_data["career_interest"] or ""),
                    " ".join(skills)
                ]
            ).lower()

            if search not in searchable_text:
                continue

        final_students.append(
            student_data
        )

    connection.close()

    return render_template(
        "industry_talent.html",
        name=session.get("name"),
        students=final_students,
        search=search
    )


# =========================================================
# INDUSTRY COLLABORATION
# =========================================================

@app.route("/industry/collaboration")
def industry_collaboration():

    if not industry_required():
        return redirect(url_for("login"))

    return render_template(
        "industry_collaboration.html",
        name=session.get("name")
    )



# =========================================================
# INDUSTRY ANALYTICS
# =========================================================

@app.route("/industry/analytics")
def industry_analytics():

    if not industry_required():
        return redirect(url_for("login"))

    industry_id = session["user_id"]

    connection = get_connection()

    opportunity_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM opportunities
        WHERE created_by = ?
        AND status = 'Open'
        """,
        (industry_id,)
    ).fetchone()[0]

    application_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.created_by = ?
        """,
        (industry_id,)
    ).fetchone()[0]

    approved_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.created_by = ?
        AND a.status = 'Approved'
        """,
        (industry_id,)
    ).fetchone()[0]

    rejected_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.created_by = ?
        AND a.status = 'Rejected'
        """,
        (industry_id,)
    ).fetchone()[0]

    submitted_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.created_by = ?
        AND a.status = 'Submitted'
        """,
        (industry_id,)
    ).fetchone()[0]

    connection.close()

    total = (
        approved_count
        + rejected_count
        + submitted_count
    )

    if total > 0:
        submitted_percentage = round(
            (submitted_count / total) * 100,
            2
        )
        approved_percentage = round(
            (approved_count / total) * 100,
            2
        )
        rejected_percentage = round(
            (rejected_count / total) * 100,
            2
        )
    else:
        submitted_percentage = 0
        approved_percentage = 0
        rejected_percentage = 0

    return render_template(
        "industry_analytics.html",
        name=session.get("name"),
        opportunity_count=opportunity_count,
        application_count=application_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        submitted_count=submitted_count,
        submitted_percentage=submitted_percentage,
        approved_percentage=approved_percentage,
        rejected_percentage=rejected_percentage
    )


# =========================================================
# INSTITUTION DASHBOARD
# =========================================================

@app.route("/institution/dashboard")
def institution_dashboard():

    if not institution_required():
        return redirect(url_for("login"))

    connection = get_connection()

    student_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE role = 'student'
        """
    ).fetchone()[0]

    academician_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM users
        WHERE role = 'academician'
        """
    ).fetchone()[0]

    opportunity_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM opportunities
        WHERE status = 'Open'
        """
    ).fetchone()[0]

    application_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM applications
        """
    ).fetchone()[0]

    connection.close()

    return render_template(
        "institution_dashboard.html",
        name=session.get("name"),
        student_count=student_count,
        academician_count=academician_count,
        opportunity_count=opportunity_count,
        application_count=application_count
    )


# =========================================================
# INSTITUTION STUDENTS
# =========================================================

@app.route("/institution/students")
def institution_students():

    if not institution_required():
        return redirect(url_for("login"))

    connection = get_connection()

    students = connection.execute("""
        SELECT
            u.name,
            u.email,
            sp.course,
            sp.institution,
            sp.career_interest,
            sp.skills
        FROM users u
        LEFT JOIN student_profiles sp
            ON u.id = sp.user_id
        WHERE u.role = 'student'
        ORDER BY u.name
    """).fetchall()

    connection.close()

    return render_template(
        "institution_students.html",
        students=students,
        name=session.get("name")
    )


# =========================================================
# INSTITUTION ACADEMICIANS
# =========================================================

@app.route("/institution/academicians")
def institution_academicians():

    if not institution_required():
        return redirect(url_for("login"))

    connection = get_connection()

    academicians = connection.execute("""
        SELECT
            id,
            name,
            email,
            role
        FROM users
        WHERE role = 'academician'
        ORDER BY name
    """).fetchall()

    connection.close()

    return render_template(
        "institution_academicians.html",
        academicians=academicians,
        name=session.get("name")
    )


# =========================================================
# INSTITUTION OPPORTUNITIES
# =========================================================

@app.route("/institution/opportunities")
def institution_opportunities():

    if not institution_required():
        return redirect(url_for("login"))

    connection = get_connection()

    opportunities = connection.execute("""
        SELECT
            id,
            title,
            organization,
            description,
            opportunity_type,
            domain,
            location,
            mode,
            duration,
            stipend,
            eligibility,
            required_skills,
            deadline,
            status
        FROM opportunities
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "institution_opportunities.html",
        opportunities=opportunities,
        name=session.get("name")
    )
# =========================================================
# INSTITUTION SKILL ANALYTICS
# =========================================================

@app.route("/institution/skill-analytics")
def institution_skill_analytics():

    if not institution_required():
        return redirect(url_for("login"))

    connection = get_connection()

    assessed_students = connection.execute("""
        SELECT COUNT(DISTINCT user_id)
        FROM assessment_results
    """).fetchone()[0]

    rows = connection.execute("""
        SELECT
            q.category AS category,
            SUM(a.score) AS total_score,
            SUM(q.max_score) AS total_max_score
        FROM assessment_answers a
        JOIN assessment_questions q
            ON a.question_id = q.id
        GROUP BY q.category
        ORDER BY MIN(q.id)
    """).fetchall()

    connection.close()

    skill_analytics = []
    strong_skills = 0
    gap_skills = 0

    for row in rows:

        total_score = float(row["total_score"] or 0)
        total_max_score = float(row["total_max_score"] or 0)

        if total_max_score > 0:
            percentage = (
                total_score / total_max_score
            ) * 100
        else:
            percentage = 0

        percentage = round(percentage, 2)

        skill_analytics.append({
            "category": row["category"],
            "percentage": percentage
        })

        if percentage >= 75:
            strong_skills += 1

        elif percentage < 60:
            gap_skills += 1

    return render_template(
        "institution_skill_analytics.html",
        name=session.get("name"),
        assessed_students=assessed_students,
        strong_skills=strong_skills,
        gap_skills=gap_skills,
        skill_analytics=skill_analytics
    )
# =========================================================
# INSTITUTION PLACEMENT ANALYTICS
# =========================================================

@app.route("/institution/placement-analytics")
def institution_placement_analytics():

    if not institution_required():
        return redirect(url_for("login"))

    connection = get_connection()

    total_applications = connection.execute("""
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.opportunity_type IN ('Placement', 'Job')
    """).fetchone()[0]

    approved_applications = connection.execute("""
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.opportunity_type IN ('Placement', 'Job')
        AND a.status = 'Approved'
    """).fetchone()[0]

    rejected_applications = connection.execute("""
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.opportunity_type IN ('Placement', 'Job')
        AND a.status = 'Rejected'
    """).fetchone()[0]

    pending_applications = connection.execute("""
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.opportunity_type IN ('Placement', 'Job')
        AND a.status = 'Submitted'
    """).fetchone()[0]

    placement_applications = connection.execute("""
        SELECT
            u.name AS student_name,
            o.title,
            o.organization,
            o.opportunity_type,
            a.status,
            a.applied_at
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        JOIN users u
            ON a.student_id = u.id
        WHERE o.opportunity_type IN ('Placement', 'Job')
        ORDER BY a.id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "institution_placement_analytics.html",
        name=session.get("name"),
        total_applications=total_applications,
        approved_applications=approved_applications,
        rejected_applications=rejected_applications,
        pending_applications=pending_applications,
        placement_applications=placement_applications
    )
# =========================================================
# INSTITUTION REPORTS
# =========================================================

@app.route("/institution/reports")
def institution_reports():

    if not institution_required():
        return redirect(url_for("login"))

    connection = get_connection()

    student_count = connection.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'student'
    """).fetchone()[0]

    academician_count = connection.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'academician'
    """).fetchone()[0]

    opportunity_count = connection.execute("""
        SELECT COUNT(*)
        FROM opportunities
        WHERE status = 'Open'
    """).fetchone()[0]

    application_count = connection.execute("""
        SELECT COUNT(*)
        FROM applications
    """).fetchone()[0]

    assessed_students = connection.execute("""
        SELECT COUNT(DISTINCT user_id)
        FROM assessment_results
    """).fetchone()[0]

    rows = connection.execute("""
        SELECT
            q.category,
            SUM(a.score) AS total_score,
            SUM(q.max_score) AS total_max_score
        FROM assessment_answers a
        JOIN assessment_questions q
            ON a.question_id = q.id
        GROUP BY q.category
    """).fetchall()

    strong_skills = 0
    gap_skills = 0

    for row in rows:

        total_score = float(row["total_score"] or 0)
        total_max_score = float(row["total_max_score"] or 0)

        if total_max_score > 0:
            percentage = (
                total_score / total_max_score
            ) * 100
        else:
            percentage = 0

        if percentage >= 75:
            strong_skills += 1

        elif percentage < 60:
            gap_skills += 1

    total_applications = connection.execute("""
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.opportunity_type IN ('Placement', 'Job')
    """).fetchone()[0]

    approved_applications = connection.execute("""
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.opportunity_type IN ('Placement', 'Job')
        AND a.status = 'Approved'
    """).fetchone()[0]

    pending_applications = connection.execute("""
        SELECT COUNT(*)
        FROM applications a
        JOIN opportunities o
            ON a.opportunity_id = o.id
        WHERE o.opportunity_type IN ('Placement', 'Job')
        AND a.status = 'Submitted'
    """).fetchone()[0]

    connection.close()

    return render_template(
        "institution_reports.html",
        name=session.get("name"),
        student_count=student_count,
        academician_count=academician_count,
        opportunity_count=opportunity_count,
        application_count=application_count,
        assessed_students=assessed_students,
        strong_skills=strong_skills,
        gap_skills=gap_skills,
        total_applications=total_applications,
        approved_applications=approved_applications,
        pending_applications=pending_applications
    )
# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)