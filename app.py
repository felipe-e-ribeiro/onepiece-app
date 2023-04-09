#from flask import Flask, render_template, request
from flask import Flask, render_template, request, redirect, url_for
from flask_mysqldb import MySQL

app = Flask(__name__)
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "opwq9021"
app.config["MYSQL_DB"] = "onepiece"
mysql = MySQL(app)

@app.route("/")
def index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM editions")
    editions = cur.fetchall()
    cur.close()
    return render_template("index.html", editions=editions)

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM editions WHERE volume_number = %s", [id])
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
    return render_template("edit.html", edition=edition)

if __name__ == "__main__":
    app.run(debug=True)