import os
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "blog.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deployment")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    # Optional initial admin account. Change these credentials after first login.
    admin_username = os.environ.get("BLOG_ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("BLOG_ADMIN_PASSWORD", "Admin123!")
    existing = db.execute("SELECT id FROM users WHERE username = ?", (admin_username,)).fetchone()
    if not existing:
        db.execute(
            "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)",
            (admin_username, generate_password_hash(admin_password))
        )
    db.commit()
    db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "info")
            return redirect(url_for("login"))
        user = get_db().execute(
            "SELECT is_admin FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()
        if not user or not user["is_admin"]:
            flash("Administrator permission is required.", "error")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    db = get_db()
    posts = db.execute("""
        SELECT posts.*, users.username,
               (SELECT COUNT(*) FROM comments WHERE comments.post_id = posts.id) AS comment_count
        FROM posts JOIN users ON users.id = posts.user_id
        ORDER BY posts.created_at DESC, posts.id DESC
    """).fetchall()
    return render_template("index.html", posts=posts)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if len(username) < 3 or len(username) > 30:
            flash("Username must be 3–30 characters.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
        else:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
                db.commit()
                flash("Account created. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username is already taken.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Welcome back!", "success")
            return redirect(url_for("index"))
        flash("Incorrect username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        if not title or not content:
            flash("Both title and content are required.", "error")
        elif len(title) > 120:
            flash("Title must be 120 characters or fewer.", "error")
        else:
            db = get_db()
            db.execute(
                "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
                (session["user_id"], title, content)
            )
            db.commit()
            flash("Your post has been published.", "success")
            return redirect(url_for("index"))
    return render_template("new_post.html")


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def post_detail(post_id):
    db = get_db()
    post = db.execute("""
        SELECT posts.*, users.username
        FROM posts JOIN users ON users.id = posts.user_id
        WHERE posts.id = ?
    """, (post_id,)).fetchone()
    if post is None:
        flash("Post not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        if "user_id" not in session:
            flash("Please log in to comment.", "info")
            return redirect(url_for("login"))
        content = request.form.get("content", "").strip()
        if not content:
            flash("Comment cannot be empty.", "error")
        elif len(content) > 1000:
            flash("Comment must be 1,000 characters or fewer.", "error")
        else:
            db.execute(
                "INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)",
                (post_id, session["user_id"], content)
            )
            db.commit()
            flash("Comment added.", "success")
            return redirect(url_for("post_detail", post_id=post_id))

    comments = db.execute("""
        SELECT comments.*, users.username
        FROM comments JOIN users ON users.id = comments.user_id
        WHERE comments.post_id = ?
        ORDER BY comments.created_at ASC, comments.id ASC
    """, (post_id,)).fetchall()
    return render_template("post_detail.html", post=post, comments=comments)


@app.route("/admin/post/<int:post_id>/delete", methods=["POST"])
@admin_required
def delete_post(post_id):
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    flash("Post deleted by administrator.", "success")
    return redirect(url_for("index"))


@app.context_processor
def inject_current_user():
    if "user_id" not in session:
        return {"current_user": None, "current_user_is_admin": False}
    user = get_db().execute(
        "SELECT id, username, is_admin FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    return {
        "current_user": user,
        "current_user_is_admin": bool(user and user["is_admin"])
    }


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
