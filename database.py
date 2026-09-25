import sqlite3


DATABASE_NAME = "ayush_skillbridge.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.row_factory = sqlite3.Row

    # Foreign key support
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# =========================================================
# ADD MISSING COLUMN HELPER
# =========================================================

def add_missing_column(connection, table_name, column_name, column_definition):
    """
    Adds a column only if it does not already exist.
    This allows us to update an existing SQLite database safely.
    """

    columns = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    existing_columns = [column["name"] for column in columns]

    if column_name not in existing_columns:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


# =========================================================
# CREATE TABLES
# =========================================================

def create_tables():

    connection = get_connection()

    # =====================================================
    # USERS TABLE
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)


    # =====================================================
    # STUDENT PROFILES TABLE
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS student_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL UNIQUE,

            full_name TEXT,
            email TEXT,
            institution TEXT,
            course TEXT,
            department TEXT,
            graduation_year TEXT,
            career_interest TEXT,
            opportunity_type TEXT,
            bio TEXT,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)


    # =====================================================
    # ASSESSMENT QUESTIONS TABLE
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS assessment_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            question TEXT NOT NULL,
            category TEXT NOT NULL,
            question_type TEXT NOT NULL DEFAULT 'self_rating',

            option_a TEXT,
            option_b TEXT,
            option_c TEXT,
            option_d TEXT,
            option_e TEXT,

            correct_answer TEXT,
            max_score INTEGER DEFAULT 5
        )
    """)


    # =====================================================
    # UPDATE OLD ASSESSMENT QUESTIONS TABLE
    # =====================================================

    add_missing_column(
        connection,
        "assessment_questions",
        "question_type",
        "TEXT NOT NULL DEFAULT 'self_rating'"
    )

    add_missing_column(
        connection,
        "assessment_questions",
        "option_a",
        "TEXT"
    )

    add_missing_column(
        connection,
        "assessment_questions",
        "option_b",
        "TEXT"
    )

    add_missing_column(
        connection,
        "assessment_questions",
        "option_c",
        "TEXT"
    )

    add_missing_column(
        connection,
        "assessment_questions",
        "option_d",
        "TEXT"
    )

    add_missing_column(
        connection,
        "assessment_questions",
        "option_e",
        "TEXT"
    )

    add_missing_column(
        connection,
        "assessment_questions",
        "correct_answer",
        "TEXT"
    )

    add_missing_column(
        connection,
        "assessment_questions",
        "max_score",
        "INTEGER DEFAULT 5"
    )


    # =====================================================
    # ASSESSMENT RESULTS TABLE
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS assessment_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            total_score REAL DEFAULT 0,
            max_score REAL DEFAULT 0,
            percentage REAL DEFAULT 0,

            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)


    # =====================================================
    # ASSESSMENT ANSWERS TABLE
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS assessment_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            result_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,

            selected_answer TEXT,
            score REAL DEFAULT 0,

            FOREIGN KEY (result_id)
                REFERENCES assessment_results(id)
                ON DELETE CASCADE,

            FOREIGN KEY (question_id)
                REFERENCES assessment_questions(id)
                ON DELETE CASCADE
        )
    """)


    # =====================================================
    # OPPORTUNITIES TABLE
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            organization TEXT NOT NULL,

            description TEXT,

            opportunity_type TEXT NOT NULL,

            domain TEXT,

            location TEXT,

            mode TEXT,

            duration TEXT,

            stipend TEXT,

            eligibility TEXT,

            required_skills TEXT,

            deadline TEXT,

            status TEXT DEFAULT 'Open',

            created_by INTEGER,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (created_by)
                REFERENCES users(id)
                ON DELETE SET NULL
        )
    """)


    # =====================================================
    # APPLICATIONS TABLE
    # =====================================================

    connection.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            opportunity_id INTEGER NOT NULL,

            student_id INTEGER NOT NULL,

            cover_note TEXT,

            resume_file TEXT,

            status TEXT DEFAULT 'Submitted',

            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (opportunity_id)
                REFERENCES opportunities(id)
                ON DELETE CASCADE,

            FOREIGN KEY (student_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            UNIQUE (opportunity_id, student_id)
        )
    """)


    # =====================================================
    # ASSESSMENT QUESTIONS DATA
    # =====================================================

    questions = [

        {
            "question": (
                "How would you rate your current understanding of "
                "AYUSH systems, concepts and their applications?"
            ),
            "category": "AYUSH Domain Knowledge",
            "question_type": "self_rating",
            "option_a": "Beginner",
            "option_b": "Basic",
            "option_c": "Intermediate",
            "option_d": "Advanced",
            "option_e": "Expert",
            "correct_answer": None,
            "max_score": 5
        },

        {
            "question": (
                "How confident are you in conducting basic research, "
                "documenting findings and presenting evidence-based information?"
            ),
            "category": "Research & Documentation",
            "question_type": "self_rating",
            "option_a": "Beginner",
            "option_b": "Basic",
            "option_c": "Intermediate",
            "option_d": "Advanced",
            "option_e": "Expert",
            "correct_answer": None,
            "max_score": 5
        },

        {
            "question": (
                "How comfortable are you with digital tools, data handling "
                "and technology used in healthcare or academic projects?"
            ),
            "category": "Digital & Healthcare Skills",
            "question_type": "self_rating",
            "option_a": "Beginner",
            "option_b": "Basic",
            "option_c": "Intermediate",
            "option_d": "Advanced",
            "option_e": "Expert",
            "correct_answer": None,
            "max_score": 5
        },

        {
            "question": (
                "How confident are you in analyzing information, "
                "interpreting data and solving unfamiliar problems?"
            ),
            "category": "Analytical Thinking",
            "question_type": "self_rating",
            "option_a": "Beginner",
            "option_b": "Basic",
            "option_c": "Intermediate",
            "option_d": "Advanced",
            "option_e": "Expert",
            "correct_answer": None,
            "max_score": 5
        },

        {
            "question": (
                "How confidently can you communicate ideas, work in teams "
                "and collaborate with academic or industry stakeholders?"
            ),
            "category": "Communication & Collaboration",
            "question_type": "self_rating",
            "option_a": "Beginner",
            "option_b": "Basic",
            "option_c": "Intermediate",
            "option_d": "Advanced",
            "option_e": "Expert",
            "correct_answer": None,
            "max_score": 5
        },

        {
            "question": (
                "If a research project has multiple possible approaches, "
                "what should you do first?"
            ),
            "category": "Aptitude & Problem Solving",
            "question_type": "objective",
            "option_a": "Choose the first approach immediately",
            "option_b": "Compare the approaches using available evidence",
            "option_c": "Ask someone else to always decide",
            "option_d": "Ignore the project requirements",
            "option_e": None,
            "correct_answer": "B",
            "max_score": 5
        }
    ]


    # =====================================================
    # INSERT ASSESSMENT QUESTIONS
    # =====================================================

    for item in questions:

        existing_question = connection.execute(
            """
            SELECT id
            FROM assessment_questions
            WHERE question = ?
            """,
            (item["question"],)
        ).fetchone()

        if existing_question is None:

            connection.execute(
                """
                INSERT INTO assessment_questions (
                    question,
                    category,
                    question_type,
                    option_a,
                    option_b,
                    option_c,
                    option_d,
                    option_e,
                    correct_answer,
                    max_score
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["question"],
                    item["category"],
                    item["question_type"],
                    item["option_a"],
                    item["option_b"],
                    item["option_c"],
                    item["option_d"],
                    item["option_e"],
                    item["correct_answer"],
                    item["max_score"]
                )
            )


    # =====================================================
    # SAMPLE AYUSH OPPORTUNITIES
    # =====================================================

    opportunities = [

        {
            "title": "AYUSH Research Internship",
            "organization": "AYUSH Research & Innovation Centre",
            "description": (
                "A project-based internship focused on AYUSH research, "
                "documentation, evidence review and healthcare research activities."
            ),
            "opportunity_type": "Internship",
            "domain": "AYUSH Research",
            "location": "Bhopal",
            "mode": "Hybrid",
            "duration": "8 Weeks",
            "stipend": "Performance Based",
            "eligibility": (
                "Students interested in AYUSH research, healthcare, "
                "data analysis or academic research."
            ),
            "required_skills": (
                "Research, Documentation, Communication, Analytical Thinking"
            ),
            "deadline": "30-09-2026",
            "status": "Open"
        },

        {
            "title": "Digital Health Project Internship",
            "organization": "Healthcare Technology Innovation Lab",
            "description": (
                "Work on digital healthcare projects involving data, "
                "technology, documentation and healthcare process improvement."
            ),
            "opportunity_type": "Internship",
            "domain": "Digital Health",
            "location": "Remote",
            "mode": "Remote",
            "duration": "6 Weeks",
            "stipend": "Certificate + Project Experience",
            "eligibility": (
                "Students with interest in digital health, technology, "
                "data or healthcare innovation."
            ),
            "required_skills": (
                "Digital Skills, Data Handling, Communication, Problem Solving"
            ),
            "deadline": "15-10-2026",
            "status": "Open"
        },

        {
            "title": "Healthcare Innovation Project",
            "organization": "Academia Industry Innovation Network",
            "description": (
                "Collaborative project opportunity focused on healthcare "
                "innovation, problem solving and academic-industry collaboration."
            ),
            "opportunity_type": "Project",
            "domain": "Healthcare Innovation",
            "location": "Nagpur",
            "mode": "Hybrid",
            "duration": "10 Weeks",
            "stipend": "Project Certificate",
            "eligibility": (
                "Students from healthcare, technology, research and "
                "interdisciplinary academic backgrounds."
            ),
            "required_skills": (
                "Innovation, Analytical Thinking, Communication, Research"
            ),
            "deadline": "25-10-2026",
            "status": "Open"
        }
    ]


    # =====================================================
    # INSERT SAMPLE OPPORTUNITIES WITHOUT DUPLICATES
    # =====================================================

    for item in opportunities:

        existing_opportunity = connection.execute(
            """
            SELECT id
            FROM opportunities
            WHERE title = ?
              AND organization = ?
            """,
            (
                item["title"],
                item["organization"]
            )
        ).fetchone()

        if existing_opportunity is None:

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
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["title"],
                    item["organization"],
                    item["description"],
                    item["opportunity_type"],
                    item["domain"],
                    item["location"],
                    item["mode"],
                    item["duration"],
                    item["stipend"],
                    item["eligibility"],
                    item["required_skills"],
                    item["deadline"],
                    item["status"]
                )
            )

    # =====================================================
    # SAMPLE PLACEMENT / JOB DATA
    # =====================================================

    placements = [

        {
            "title": "AYUSH Healthcare Graduate Trainee",
            "organization": "Healthcare Innovation Network",
            "description": (
                "Entry-level opportunity for students interested in "
                "AYUSH healthcare, research support and digital health."
            ),
            "opportunity_type": "Placement",
            "domain": "AYUSH Healthcare",
            "location": "Bhopal",
            "mode": "On-site",
            "duration": "Full Time",
            "stipend": "As per organization policy",
            "eligibility": (
                "Graduates with interest in AYUSH, healthcare technology "
                "or research."
            ),
            "required_skills": (
                "AYUSH Knowledge, Communication, Research, "
                "Analytical Thinking"
            ),
            "deadline": "31-10-2026",
            "status": "Open"
        },

        {
            "title": "Digital Health Associate",
            "organization": "Healthcare Technology Solutions",
            "description": (
                "Career opportunity focused on digital healthcare "
                "solutions, data handling and technology-enabled services."
            ),
            "opportunity_type": "Job",
            "domain": "Digital Health",
            "location": "Remote",
            "mode": "Remote",
            "duration": "Full Time",
            "stipend": "Salary Based",
            "eligibility": (
                "Students or graduates with knowledge of digital tools, "
                "healthcare and data."
            ),
            "required_skills": (
                "Digital Skills, Data Handling, Communication, "
                "Problem Solving"
            ),
            "deadline": "15-11-2026",
            "status": "Open"
        },

        {
            "title": "Healthcare Research Executive",
            "organization": "Applied Health Research Group",
            "description": (
                "Research-oriented career opportunity involving "
                "documentation, data analysis and healthcare projects."
            ),
            "opportunity_type": "Job",
            "domain": "Healthcare Research",
            "location": "Nagpur",
            "mode": "Hybrid",
            "duration": "Full Time",
            "stipend": "Salary Based",
            "eligibility": (
                "Candidates interested in healthcare research, "
                "documentation and analytical work."
            ),
            "required_skills": (
                "Research, Documentation, Data Interpretation, "
                "Analytical Thinking"
            ),
            "deadline": "30-11-2026",
            "status": "Open"
        }
    ]


    # =====================================================
    # INSERT PLACEMENTS WITHOUT DUPLICATES
    # =====================================================

    for item in placements:

        existing_placement = connection.execute(
            """
            SELECT id
            FROM opportunities
            WHERE title = ?
            AND organization = ?
            """,
            (
                item["title"],
                item["organization"]
            )
        ).fetchone()

        if existing_placement is None:

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
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["title"],
                    item["organization"],
                    item["description"],
                    item["opportunity_type"],
                    item["domain"],
                    item["location"],
                    item["mode"],
                    item["duration"],
                    item["stipend"],
                    item["eligibility"],
                    item["required_skills"],
                    item["deadline"],
                    item["status"]
                )
            )
    # =====================================================
    # SAVE CHANGES
    # =====================================================

    connection.commit()
    connection.close()


# =========================================================
# RUN DATABASE SETUP
# =========================================================

if __name__ == "__main__":

    create_tables()

    print(
        "Database, assessment, opportunity and application tables are ready!"
    )