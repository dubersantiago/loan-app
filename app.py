import os
import sqlite3
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash

# --- Configuración (se puede sobreescribir con variables de entorno) ---
APP_PASSWORD = os.environ.get("APP_PASSWORD", "cambia-esta-clave")
SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esta-clave-secreta")
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "prestamo.db"))

app = Flask(__name__)
app.secret_key = SECRET_KEY


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS abonos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            monto REAL NOT NULL,
            nota TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS config (
            clave TEXT PRIMARY KEY,
            valor TEXT
        )
        """
    )
    cur = conn.execute("SELECT valor FROM config WHERE clave = 'tasa'")
    if cur.fetchone() is None:
        conn.execute("INSERT INTO config (clave, valor) VALUES ('tasa', '0.10')")
    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == APP_PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        flash("Clave incorrecta")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET"])
@login_required
def index():
    conn = get_db()
    abonos = conn.execute("SELECT * FROM abonos ORDER BY fecha ASC, id ASC").fetchall()
    tasa = float(conn.execute("SELECT valor FROM config WHERE clave='tasa'").fetchone()["valor"])
    conn.close()

    total_prestado = sum(a["monto"] for a in abonos)
    interes = total_prestado * tasa
    total_pagar = total_prestado + interes

    return render_template(
        "index.html",
        abonos=abonos,
        tasa=tasa,
        total_prestado=total_prestado,
        interes=interes,
        total_pagar=total_pagar,
    )


@app.route("/add", methods=["POST"])
@login_required
def add():
    fecha = request.form.get("fecha")
    monto_raw = request.form.get("monto")
    nota = request.form.get("nota", "").strip()

    try:
        monto = float(monto_raw)
    except (TypeError, ValueError):
        flash("Monto inválido")
        return redirect(url_for("index"))

    if not fecha or monto <= 0:
        flash("Revisa la fecha y el monto")
        return redirect(url_for("index"))

    conn = get_db()
    conn.execute("INSERT INTO abonos (fecha, monto, nota) VALUES (?, ?, ?)", (fecha, monto, nota))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/delete/<int:abono_id>", methods=["POST"])
@login_required
def delete(abono_id):
    conn = get_db()
    conn.execute("DELETE FROM abonos WHERE id = ?", (abono_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.route("/tasa", methods=["POST"])
@login_required
def set_tasa():
    tasa_raw = request.form.get("tasa")
    try:
        tasa = float(tasa_raw) / 100
    except (TypeError, ValueError):
        flash("Tasa inválida")
        return redirect(url_for("index"))

    conn = get_db()
    conn.execute("UPDATE config SET valor = ? WHERE clave = 'tasa'", (str(tasa),))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
