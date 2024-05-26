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
    cur.execute("SELECT arc, GROUP_CONCAT(volume_number ORDER BY volume_number SEPARATOR ',') as volumes FROM editions GROUP BY arc ORDER BY MIN(volume_number)")
    editions = cur.fetchall()
    cur.close()
    return render_template("index.html", owned=owned, editions=editions, css_url=url_for('static', filename='style.css'))

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT volume_number,is_owned FROM editions WHERE volume_number = %s", [id])
    edition = cur.fetchone()
    if request.method == "POST":
        #is_owned = request.form.get("is_owned", False)
        is_owned = bool(request.form.get("is_owned"))
        cur.execute("UPDATE editions SET is_owned = %s WHERE volume_number = %s", [is_owned, id])
        mysql.connection.commit()
        cur.close()
        #return "Edition updated."
        return redirect(url_for('index'))
    cur.close()
    return render_template("edit.html", edition=edition, css_url=url_for('static', filename='style.css'))

if __name__ == "__main__":
    app.run(host="0.0.0.0")
