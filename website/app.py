from flask import Flask, render_template, url_for, g
import os
import sqlite3
from telemetry import setup_telemetry

app = Flask(__name__)
#setup_telemetry(app)
app.config["DATABASE"] = os.path.join(app.root_path, "my_database.db")


def get_db():
    if "db" not in g:
        # Adicionado immutable=1 para indicar que o arquivo não sofrerá escrita externa
        db_path = f"file:{app.config['DATABASE']}?mode=ro&immutable=1"
        g.db = sqlite3.connect(
            db_path,
            uri=True,
            check_same_thread=False,
        )
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/")
def index():
    db = get_db()

    owned = db.execute(
        "SELECT volume_number, is_owned FROM editions ORDER BY id"
    ).fetchall()

    raw_editions = db.execute("""
        SELECT arc,
               GROUP_CONCAT(volume_number, ',') AS volumes,
               COUNT(volume_number) AS total,
               SUM(CASE WHEN is_owned = 1 THEN 1 ELSE 0 END) AS owned
        FROM (
            SELECT *
            FROM editions
            ORDER BY volume_number
        ) AS ordered_editions
        GROUP BY arc
        ORDER BY MIN(id)
    """).fetchall()

    # Processamento para remover "_Arc" e trocar "_" por " "
    editions = []
    for row in raw_editions:
        # Pega o nome original (ex: "East_Blue_Arc")
        original_arc = row[0] 
        
        # 1. Remove "_Arc" (se existir no final)
        # 2. Troca "_" por espaço
        clean_arc = original_arc.replace("_Arc", "").replace("_", " ")
        
        # Monta uma nova lista/tupla com o nome limpo e o restante dos dados
        editions.append((clean_arc, row[1], row[2], row[3]))

    return render_template(
        "index.html",
        owned=owned,
        editions=editions,
        css_url=url_for('static', filename='style.css')
    )


@app.route("/error/")
def error():
    return render_template(
        "error.html",
        css_url=url_for('static', filename='style.css')
    )


@app.errorhandler(500)
def error_500(e):
    return render_template('error.html'), 500


@app.errorhandler(404)
def error_404(e):
    return render_template('error.html'), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0")