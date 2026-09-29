from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from datetime import date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = "gameverse_secret_key"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    conn = sqlite3.connect("gameverse.db")

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# DATABASE SETUP
# =========================================================

def create_database():

    conn = get_db()


    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL

        )
    """)


    # -----------------------------------------------------
    # PLAYER STATS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER UNIQUE,

            score INTEGER DEFAULT 0,

            xp INTEGER DEFAULT 0,

            coins INTEGER DEFAULT 0,

            level INTEGER DEFAULT 1,

            streak INTEGER DEFAULT 0,

            quizzes_played INTEGER DEFAULT 0,

            correct_answers INTEGER DEFAULT 0,

            wrong_answers INTEGER DEFAULT 0,

            total_questions INTEGER DEFAULT 0,

            last_activity TEXT,

            difficulty TEXT DEFAULT 'Easy',

            FOREIGN KEY(user_id) REFERENCES users(id)

        )
    """)


    # -----------------------------------------------------
    # ACHIEVEMENTS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS achievements (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT UNIQUE NOT NULL,

            description TEXT NOT NULL,

            icon TEXT NOT NULL,

            xp_reward INTEGER DEFAULT 0,

            coin_reward INTEGER DEFAULT 0

        )
    """)


    # -----------------------------------------------------
    # USER ACHIEVEMENTS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            achievement_id INTEGER,

            earned_date TEXT,

            UNIQUE(user_id, achievement_id),

            FOREIGN KEY(user_id) REFERENCES users(id),

            FOREIGN KEY(achievement_id) REFERENCES achievements(id)

        )
    """)


    # -----------------------------------------------------
    # DAILY CHALLENGES
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_challenges (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            challenge_date TEXT UNIQUE NOT NULL,

            question TEXT NOT NULL,

            option1 TEXT NOT NULL,

            option2 TEXT NOT NULL,

            option3 TEXT NOT NULL,

            option4 TEXT NOT NULL,

            answer INTEGER NOT NULL,

            xp_reward INTEGER DEFAULT 30,

            coin_reward INTEGER DEFAULT 10

        )
    """)


    # -----------------------------------------------------
    # DAILY COMPLETION
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_completions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            challenge_id INTEGER,

            completed_date TEXT,

            UNIQUE(user_id, challenge_id),

            FOREIGN KEY(user_id) REFERENCES users(id),

            FOREIGN KEY(challenge_id) REFERENCES daily_challenges(id)

        )
    """)


    # =====================================================
    # OLD DATABASE MIGRATION
    # =====================================================

    existing_columns = conn.execute(
        "PRAGMA table_info(player_stats)"
    ).fetchall()

    column_names = [column["name"] for column in existing_columns]


    new_columns = {

        "correct_answers":
            "INTEGER DEFAULT 0",

        "wrong_answers":
            "INTEGER DEFAULT 0",

        "total_questions":
            "INTEGER DEFAULT 0",

        "last_activity":
            "TEXT",

        "difficulty":
            "TEXT DEFAULT 'Easy'"

    }


    for column, definition in new_columns.items():

        if column not in column_names:

            conn.execute(
                f"""
                ALTER TABLE player_stats
                ADD COLUMN {column} {definition}
                """
            )


    # =====================================================
    # CREATE STATS FOR OLD USERS
    # =====================================================

    users = conn.execute(
        "SELECT id FROM users"
    ).fetchall()


    for user in users:

        existing = conn.execute(
            """
            SELECT id
            FROM player_stats
            WHERE user_id = ?
            """,
            (user["id"],)
        ).fetchone()


        if existing is None:

            conn.execute(
                """
                INSERT INTO player_stats (user_id)
                VALUES (?)
                """,
                (user["id"],)
            )


    # =====================================================
    # ACHIEVEMENTS
    # =====================================================

    achievements = [

        (
            "First Quiz",
            "Complete your first quiz.",
            "🎯",
            20,
            10
        ),

        (
            "100 XP",
            "Earn 100 XP.",
            "⚡",
            20,
            10
        ),

        (
            "500 XP",
            "Earn 500 XP.",
            "🔥",
            50,
            25
        ),

        (
            "Quiz Master",
            "Complete 5 quizzes.",
            "🏆",
            50,
            30
        ),

        (
            "Level 3",
            "Reach Level 3.",
            "⭐",
            30,
            20
        ),

        (
            "Level 5",
            "Reach maximum Level 5.",
            "👑",
            100,
            50
        ),

        (
            "Streak 3",
            "Maintain a 3 day streak.",
            "🔥",
            30,
            20
        ),

        (
            "Streak 7",
            "Maintain a 7 day streak.",
            "💎",
            100,
            50
        )

    ]


    for achievement in achievements:

        conn.execute(
            """
            INSERT OR IGNORE INTO achievements
            (
                name,
                description,
                icon,
                xp_reward,
                coin_reward
            )

            VALUES (?, ?, ?, ?, ?)
            """,
            achievement
        )


    # =====================================================
    # DAILY CHALLENGE
    # =====================================================

    today = date.today().isoformat()


    daily_questions = [

        (
            "Which algorithm is used to find a Minimum Spanning Tree?",
            "Dijkstra",
            "Kruskal",
            "BFS",
            "Binary Search",
            1
        ),

        (
            "Which data structure follows LIFO?",
            "Queue",
            "Stack",
            "Tree",
            "Graph",
            1
        ),

        (
            "What does AI stand for?",
            "Artificial Intelligence",
            "Automatic Internet",
            "Advanced Input",
            "Artificial Interface",
            0
        ),

        (
            "Which SQL clause filters groups?",
            "WHERE",
            "SELECT",
            "HAVING",
            "FROM",
            2
        ),

        (
            "Which language is commonly used for Machine Learning?",
            "HTML",
            "Python",
            "CSS",
            "SQL",
            1
        )

    ]


    day_number = date.today().toordinal()

    question_data = daily_questions[
        day_number % len(daily_questions)
    ]


    conn.execute(
        """
        INSERT OR IGNORE INTO daily_challenges
        (
            challenge_date,
            question,
            option1,
            option2,
            option3,
            option4,
            answer,
            xp_reward,
            coin_reward
        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            today,
            question_data[0],
            question_data[1],
            question_data[2],
            question_data[3],
            question_data[4],
            question_data[5],
            30,
            10
        )
    )


    conn.commit()

    conn.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        confirm_password = request.form["confirm_password"]


        if password != confirm_password:

            return "Passwords do not match!"


        conn = get_db()


        try:

            hashed_password = generate_password_hash(password)


            cursor = conn.execute(
                """
                INSERT INTO users
                (
                    username,
                    password
                )

                VALUES (?, ?)
                """,
                (
                    username,
                    hashed_password
                )
            )


            user_id = cursor.lastrowid


            conn.execute(
                """
                INSERT INTO player_stats
                (
                    user_id
                )

                VALUES (?)
                """,
                (user_id,)
            )


            conn.commit()


        except sqlite3.IntegrityError:

            conn.close()

            return "Username already exists!"


        conn.close()


        return redirect("/login")


    return render_template("register.html")


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]


        conn = get_db()


        user = conn.execute(
            """
            SELECT *

            FROM users

            WHERE username = ?
            """,
            (username,)
        ).fetchone()


        conn.close()


        if user:

            stored_password = user["password"]


            # ------------------------------------------------
            # New hashed passwords
            # ------------------------------------------------

            password_valid = False


            try:

                password_valid = check_password_hash(
                    stored_password,
                    password
                )

            except ValueError:

                password_valid = (
                    stored_password == password
                )


            if password_valid:

                session["user_id"] = user["id"]

                session["username"] = user["username"]


                return redirect("/dashboard")


        return "Invalid username or password!"


    return render_template("login.html")


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:

        return redirect("/login")


    conn = get_db()


    stats = conn.execute(
        """
        SELECT *

        FROM player_stats

        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()


    achievements = conn.execute(
        """
        SELECT
            achievements.*

        FROM achievements

        JOIN user_achievements

        ON achievements.id =
           user_achievements.achievement_id

        WHERE user_achievements.user_id = ?

        ORDER BY user_achievements.id DESC
        """,
        (session["user_id"],)
    ).fetchall()


    conn.close()


    return render_template(

        "dashboard.html",

        stats=stats,

        achievements=achievements

    )


# =========================================================
# QUIZ
# =========================================================

@app.route("/quiz")
def quiz():

    if "user_id" not in session:

        return redirect("/login")


    conn = get_db()


    stats = conn.execute(
        """
        SELECT difficulty

        FROM player_stats

        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()


    conn.close()


    difficulty = "Easy"


    if stats:

        difficulty = stats["difficulty"] or "Easy"


    return render_template(

        "quiz.html",

        difficulty=difficulty

    )


# =========================================================
# ADAPTIVE DIFFICULTY
# =========================================================

@app.route("/adaptive_difficulty")
def adaptive_difficulty():

    if "user_id" not in session:

        return jsonify({
            "success": False
        })


    conn = get_db()


    stats = conn.execute(
        """
        SELECT
            correct_answers,
            wrong_answers,
            difficulty

        FROM player_stats

        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()


    conn.close()


    if not stats:

        return jsonify({
            "success": True,
            "difficulty": "Easy"
        })


    correct = stats["correct_answers"]

    wrong = stats["wrong_answers"]

    total = correct + wrong


    if total == 0:

        difficulty = "Easy"

    else:

        accuracy = (correct / total) * 100


        if accuracy >= 80:

            difficulty = "Hard"

        elif accuracy >= 60:

            difficulty = "Medium"

        else:

            difficulty = "Easy"


    return jsonify({

        "success": True,

        "difficulty": difficulty

    })


# =========================================================
# SAVE QUIZ RESULT
# =========================================================

@app.route("/save_result", methods=["POST"])
def save_result():

    if "user_id" not in session:

        return jsonify({

            "success": False,

            "message": "Please login"

        })


    data = request.get_json() or {}


    score = int(data.get("score", 0))

    xp = int(data.get("xp", 0))

    coins = int(data.get("coins", 0))

    correct = int(data.get("correct", 0))

    wrong = int(data.get("wrong", 0))


    conn = get_db()


    stats = conn.execute(
        """
        SELECT *

        FROM player_stats

        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()


    if stats is None:

        conn.execute(
            """
            INSERT INTO player_stats
            (
                user_id
            )

            VALUES (?)
            """,
            (session["user_id"],)
        )


        conn.commit()


        stats = conn.execute(
            """
            SELECT *

            FROM player_stats

            WHERE user_id = ?
            """,
            (session["user_id"],)
        ).fetchone()


    new_score = stats["score"] + score

    new_xp = stats["xp"] + xp

    new_coins = stats["coins"] + coins


    new_correct = (
        stats["correct_answers"] + correct
    )

    new_wrong = (
        stats["wrong_answers"] + wrong
    )

    new_total = (
        stats["total_questions"]
        + correct
        + wrong
    )


    # =====================================================
    # LEVEL
    # =====================================================

    new_level = (new_xp // 100) + 1


    if new_level > 5:

        new_level = 5


    # =====================================================
    # ADAPTIVE DIFFICULTY
    # =====================================================

    if new_total == 0:

        difficulty = "Easy"

    else:

        accuracy = (
            new_correct / new_total
        ) * 100


        if accuracy >= 80:

            difficulty = "Hard"

        elif accuracy >= 60:

            difficulty = "Medium"

        else:

            difficulty = "Easy"


    # =====================================================
    # STREAK
    # =====================================================

    today = date.today()

    today_string = today.isoformat()

    last_activity = stats["last_activity"]

    new_streak = stats["streak"]


    if last_activity:

        last_date = date.fromisoformat(
            last_activity
        )

        difference = (
            today - last_date
        ).days


        if difference == 1:

            new_streak += 1

        elif difference > 1:

            new_streak = 1

    else:

        new_streak = 1


    # Same day → streak doesn't increase


    # =====================================================
    # UPDATE STATS
    # =====================================================

    conn.execute(
        """
        UPDATE player_stats

        SET

            score = ?,

            xp = ?,

            coins = ?,

            level = ?,

            streak = ?,

            quizzes_played =
                quizzes_played + 1,

            correct_answers = ?,

            wrong_answers = ?,

            total_questions = ?,

            last_activity = ?,

            difficulty = ?

        WHERE user_id = ?
        """,
        (
            new_score,

            new_xp,

            new_coins,

            new_level,

            new_streak,

            new_correct,

            new_wrong,

            new_total,

            today_string,

            difficulty,

            session["user_id"]
        )
    )


    conn.commit()


    # =====================================================
    # ACHIEVEMENT CHECKING
    # =====================================================

    check_achievements(
        conn,
        session["user_id"],
        new_xp,
        new_level,
        new_streak,
        stats["quizzes_played"] + 1
    )


    conn.commit()

    conn.close()


    return jsonify({

        "success": True,

        "score": new_score,

        "xp": new_xp,

        "coins": new_coins,

        "level": new_level,

        "streak": new_streak,

        "difficulty": difficulty

    })


# =========================================================
# ACHIEVEMENT FUNCTION
# =========================================================

def check_achievements(
    conn,
    user_id,
    xp,
    level,
    streak,
    quizzes_played
):

    earned = []


    if quizzes_played >= 1:

        earned.append("First Quiz")


    if xp >= 100:

        earned.append("100 XP")


    if xp >= 500:

        earned.append("500 XP")


    if quizzes_played >= 5:

        earned.append("Quiz Master")


    if level >= 3:

        earned.append("Level 3")


    if level >= 5:

        earned.append("Level 5")


    if streak >= 3:

        earned.append("Streak 3")


    if streak >= 7:

        earned.append("Streak 7")


    for achievement_name in earned:

        achievement = conn.execute(
            """
            SELECT *

            FROM achievements

            WHERE name = ?
            """,
            (achievement_name,)
        ).fetchone()


        if achievement is None:

            continue


        existing = conn.execute(
            """
            SELECT id

            FROM user_achievements

            WHERE user_id = ?

            AND achievement_id = ?
            """,
            (
                user_id,
                achievement["id"]
            )
        ).fetchone()


        if existing is None:

            conn.execute(
                """
                INSERT INTO user_achievements
                (
                    user_id,
                    achievement_id,
                    earned_date
                )

                VALUES (?, ?, ?)
                """,
                (
                    user_id,

                    achievement["id"],

                    date.today().isoformat()
                )
            )


            conn.execute(
                """
                UPDATE player_stats

                SET

                    xp = xp + ?,

                    coins = coins + ?

                WHERE user_id = ?
                """,
                (
                    achievement["xp_reward"],

                    achievement["coin_reward"],

                    user_id
                )
            )


# =========================================================
# DAILY CHALLENGE PAGE
# =========================================================

@app.route("/daily-challenge")
def daily_challenge():

    if "user_id" not in session:

        return redirect("/login")


    conn = get_db()


    challenge = conn.execute(
        """
        SELECT *

        FROM daily_challenges

        WHERE challenge_date = ?
        """,
        (date.today().isoformat(),)
    ).fetchone()


    completed = conn.execute(
        """
        SELECT *

        FROM daily_completions

        WHERE user_id = ?

        AND challenge_id = ?
        """,
        (
            session["user_id"],

            challenge["id"]
        )
    ).fetchone()


    conn.close()


    return render_template(

        "daily_challenge.html",

        challenge=challenge,

        completed=completed

    )


# =========================================================
# DAILY CHALLENGE RESULT
# =========================================================

@app.route(
    "/daily-challenge/submit",
    methods=["POST"]
)
def submit_daily_challenge():

    if "user_id" not in session:

        return jsonify({
            "success": False
        })


    data = request.get_json() or {}

    selected = int(
        data.get("answer", -1)
    )


    conn = get_db()


    challenge = conn.execute(
        """
        SELECT *

        FROM daily_challenges

        WHERE challenge_date = ?
        """,
        (date.today().isoformat(),)
    ).fetchone()


    if challenge is None:

        conn.close()

        return jsonify({
            "success": False,
            "message": "Challenge not found"
        })


    existing = conn.execute(
        """
        SELECT id

        FROM daily_completions

        WHERE user_id = ?

        AND challenge_id = ?
        """,
        (
            session["user_id"],

            challenge["id"]
        )
    ).fetchone()


    if existing:

        conn.close()

        return jsonify({

            "success": False,

            "message":
                "Daily challenge already completed!"

        })


    correct = (
        selected == challenge["answer"]
    )


    if correct:

        reward_xp = challenge["xp_reward"]

        reward_coins = challenge["coin_reward"]

    else:

        reward_xp = 5

        reward_coins = 0


    stats = conn.execute(
        """
        SELECT *

        FROM player_stats

        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()


    new_xp = stats["xp"] + reward_xp

    new_coins = (
        stats["coins"] + reward_coins
    )


    new_level = (new_xp // 100) + 1


    if new_level > 5:

        new_level = 5


    conn.execute(
        """
        UPDATE player_stats

        SET

            xp = ?,

            coins = ?,

            level = ?

        WHERE user_id = ?
        """,
        (
            new_xp,

            new_coins,

            new_level,

            session["user_id"]
        )
    )


    conn.execute(
        """
        INSERT INTO daily_completions
        (
            user_id,
            challenge_id,
            completed_date
        )

        VALUES (?, ?, ?)
        """,
        (
            session["user_id"],

            challenge["id"],

            date.today().isoformat()
        )
    )


    conn.commit()

    conn.close()


    return jsonify({

        "success": True,

        "correct": correct,

        "xp": reward_xp,

        "coins": reward_coins,

        "level": new_level

    })


# =========================================================
# LEADERBOARD
# =========================================================

@app.route("/leaderboard")
def leaderboard():

    if "user_id" not in session:

        return redirect("/login")


    conn = get_db()


    players = conn.execute(
        """
        SELECT

            users.username,

            player_stats.score,

            player_stats.xp,

            player_stats.coins,

            player_stats.level,

            player_stats.streak

        FROM users

        JOIN player_stats

        ON users.id =
           player_stats.user_id

        ORDER BY

            player_stats.score DESC
        """
    ).fetchall()


    conn.close()


    return render_template(

        "leaderboard.html",

        players=players

    )


# =========================================================
# PROFILE + STATISTICS
# =========================================================

@app.route("/profile")
def profile():

    if "user_id" not in session:

        return redirect("/login")


    conn = get_db()


    user = conn.execute(
        """
        SELECT username

        FROM users

        WHERE id = ?
        """,
        (session["user_id"],)
    ).fetchone()


    stats = conn.execute(
        """
        SELECT *

        FROM player_stats

        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()


    achievements = conn.execute(
        """
        SELECT

            achievements.name,

            achievements.description,

            achievements.icon,

            user_achievements.earned_date

        FROM achievements

        JOIN user_achievements

        ON achievements.id =
           user_achievements.achievement_id

        WHERE user_achievements.user_id = ?

        ORDER BY user_achievements.id DESC
        """,
        (session["user_id"],)
    ).fetchall()


    conn.close()


    accuracy = 0


    if stats["total_questions"] > 0:

        accuracy = round(

            (
                stats["correct_answers"]
                /
                stats["total_questions"]
            ) * 100,

            1

        )


    return render_template(

        "profile.html",

        user=user,

        stats=stats,

        achievements=achievements,

        accuracy=accuracy

    )


# =========================================================
# STATISTICS API
# =========================================================

@app.route("/statistics")
def statistics():

    if "user_id" not in session:

        return jsonify({
            "success": False
        })


    conn = get_db()


    stats = conn.execute(
        """
        SELECT *

        FROM player_stats

        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()


    conn.close()


    accuracy = 0


    if stats["total_questions"] > 0:

        accuracy = round(

            (
                stats["correct_answers"]
                /
                stats["total_questions"]
            ) * 100,

            1

        )


    return jsonify({

        "success": True,

        "score": stats["score"],

        "xp": stats["xp"],

        "coins": stats["coins"],

        "level": stats["level"],

        "streak": stats["streak"],

        "quizzes_played":
            stats["quizzes_played"],

        "correct_answers":
            stats["correct_answers"],

        "wrong_answers":
            stats["wrong_answers"],

        "total_questions":
            stats["total_questions"],

        "accuracy": accuracy,

        "difficulty":
            stats["difficulty"]

    })


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    create_database()

    app.run(debug=True)