from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL
import os

app = Flask(__name__)
app.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST")
app.config["MYSQL_USER"] = os.environ.get("MYSQL_USER")
app.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD")
app.config["MYSQL_DB"] = os.environ.get("MYSQL_DB")
mysql = MySQL(app)

@app.route("/")
def index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT volume_number, is_owned FROM editions ORDER BY volume_number;")
    owned = cur.fetchall()
    cur.execute("SELECT arc, GROUP_CONCAT(volume_number ORDER BY volume_number SEPARATOR ',') as volumes, count(volume_number), SUM(CASE WHEN is_owned = 1 THEN 1 ELSE 0 END) FROM editions GROUP BY arc ORDER BY MIN(volume_number)")
    editions = cur.fetchall()
    cur.close()
    return render_template("index.html", owned=owned, editions=editions, css_url=url_for('static', filename='style.css'))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT volume_number,is_owned FROM editions WHERE volume_number = %s", [id])
    edition = cur.fetchone()
    if request.method == "POST":
        is_owned = bool(request.form.get("is_owned"))
        cur.execute("UPDATE editions SET is_owned = %s WHERE volume_number = %s", [is_owned, id])
        mysql.connection.commit()
        cur.close()
        #return "Edition updated."
        return redirect(url_for('index'))
    cur.close()
    return render_template("edit.html", edition=edition, css_url=url_for('static', filename='style.css'))

@app.route("/add/", methods=["GET", "POST"])
def add():

    if request.method == "POST":
        arc = request.form.get("arc")
        volume = request.form.get("volume")
        if arc is not None and volume is not None:
            cur = mysql.connection.cursor()
            cur.execute("SELECT volume_number FROM editions WHERE volume_number = %s", [volume])
            edition = cur.fetchone()
            if edition:
                cur.close()
                return redirect(url_for('error'))
            else:
                volume_before = int(volume) - 1
                cur.execute("SELECT volume_number FROM editions WHERE volume_number = %s", [volume_before])
                edition_before = cur.fetchone()
                if edition_before is None:
                    cur.close()
                    return redirect(url_for('error'))
                else:
                    cur.execute("insert editions (volume_number, arc, is_owned) values (%s, %s, 0)", [volume, arc] )
                    mysql.connection.commit()
                    cur.close()
                    return redirect(url_for('index'))
    else:
        return render_template("add.html", css_url=url_for('static', filename='style.css'))

@app.route("/error/", methods=["GET", "POST"])
def error():
    return render_template("error.html", css_url=url_for('static', filename='style.css'))

@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    # Testando conexão com o MySQL
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT 1;")  # Consulta simples para validar a conexão
        cur.close()
    except Exception as e:
        return {"status": "unhealthy", "details": {"mysql": str(e)}}, 500

    # Testando se o Flask está funcionando
    try:
        response = {"status": "healthy", "details": {"mysql": "connected", "flask": "running"}}
        return response, 200
    except Exception as e:
        return {"status": "unhealthy", "details": {"flask": str(e)}}, 500


@app.errorhandler(500)
def exception_handler(e):
    return render_template('error.html'), 500

@app.errorhandler(404)
def exception_handler(e):
    return render_template('error.html'), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0")
