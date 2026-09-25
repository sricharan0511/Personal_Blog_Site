from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "personal_blog_secret"

DATABASE = "blog.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author_id INTEGER NOT NULL,
            published INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_db()

    posts = conn.execute("""
        SELECT posts.*, users.username
        FROM posts
        JOIN users ON posts.author_id = users.id
        WHERE posts.published = 1
        ORDER BY posts.created_at DESC
    """).fetchall()

    conn.close()

    return render_template("index.html", posts=posts)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:
            flash("Please fill all fields.")
            return redirect(url_for("register"))

        conn = get_db()

        try:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, generate_password_hash(password))
            )

            conn.commit()
            conn.close()

            flash("Registration successful. Please login.")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            conn.close()
            flash("Username already exists.")
            return redirect(url_for("register"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    posts = conn.execute("""
        SELECT *
        FROM posts
        WHERE author_id = ?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("dashboard.html", posts=posts)


@app.route("/create", methods=["GET", "POST"])
def create_post():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()

        if not title or not content:
            flash("Title and content are required.")
            return redirect(url_for("create_post"))

        conn = get_db()

        conn.execute("""
            INSERT INTO posts (title, content, author_id, published)
            VALUES (?, ?, ?, 0)
        """, (title, content, session["user_id"]))

        conn.commit()
        conn.close()

        flash("Post saved as draft.")
        return redirect(url_for("dashboard"))

    return render_template("create_post.html")


@app.route("/edit/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    post = conn.execute("""
        SELECT *
        FROM posts
        WHERE id = ? AND author_id = ?
    """, (post_id, session["user_id"])).fetchone()

    if not post:
        conn.close()
        flash("Post not found.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        title = request.form["title"].strip()
        content = request.form["content"].strip()

        if not title or not content:
            conn.close()
            flash("Title and content are required.")
            return redirect(url_for("edit_post", post_id=post_id))

        conn.execute("""
            UPDATE posts
            SET title = ?, content = ?
            WHERE id = ? AND author_id = ?
        """, (title, content, post_id, session["user_id"]))

        conn.commit()
        conn.close()

        flash("Post updated successfully.")
        return redirect(url_for("dashboard"))

    conn.close()

    return render_template("edit_post.html", post=post)


@app.route("/publish/<int:post_id>")
def publish_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute("""
        UPDATE posts
        SET published = 1
        WHERE id = ? AND author_id = ?
    """, (post_id, session["user_id"]))

    conn.commit()
    conn.close()

    flash("Post published successfully.")
    return redirect(url_for("dashboard"))


@app.route("/unpublish/<int:post_id>")
def unpublish_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute("""
        UPDATE posts
        SET published = 0
        WHERE id = ? AND author_id = ?
    """, (post_id, session["user_id"]))

    conn.commit()
    conn.close()

    flash("Post moved back to draft.")
    return redirect(url_for("dashboard"))


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute("""
        DELETE FROM posts
        WHERE id = ? AND author_id = ?
    """, (post_id, session["user_id"]))

    conn.commit()
    conn.close()

    flash("Post deleted.")
    return redirect(url_for("dashboard"))


@app.route("/post/<int:post_id>")
def view_post(post_id):
    conn = get_db()

    post = conn.execute("""
        SELECT posts.*, users.username
        FROM posts
        JOIN users ON posts.author_id = users.id
        WHERE posts.id = ? AND posts.published = 1
    """, (post_id,)).fetchone()

    conn.close()

    if not post:
        flash("Post not found.")
        return redirect(url_for("index"))

    return render_template("post.html", post=post)


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
