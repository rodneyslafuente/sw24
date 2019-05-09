import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Retrieve the symbols of the user's stocks and number of shares for each
    stocks = db.execute("SELECT symbol, SUM(shares) FROM history WHERE id = :user_id GROUP BY symbol", user_id=session["user_id"])

    # Retrieve quote for each stock (quotes is a list of dictionaries, each dictionary contains a name and price for each stock)
    quotes = [{"name": lookup(stock["symbol"]).get("name"), "price": usd(lookup(stock["symbol"]).get("price"))} for stock in stocks]

    # Calculate unformatted totals (n_totals is a list of total dollar amounts for each stock)
    n_totals = [stock["SUM(shares)"] * lookup(stock["symbol"]).get("price") for stock in stocks]

    # Retrieve user's cash amount
    cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])[0]["cash"]

    # Calculate grand total
    grandtotal = usd(sum(n_totals) + cash)

    # Format totals
    totals = [usd(total) for total in n_totals]

    return render_template("index.html", stocks=stocks, totals=totals, quotes=quotes, cash=usd(cash), grandtotal=grandtotal)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Look up quote for symbol
        quote = lookup(request.form.get("symbol"))

        # Check that symbol is valid and number of shares is integer
        if quote and request.form.get("shares").isnumeric():

            # Query for cash available
            cash = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])[0]["cash"]

            # Check that there is enough cash to buy shares
            if quote["price"] * int(request.form.get("shares")) <= cash:

                # Record transaction in database
                db.execute("INSERT INTO history (id, symbol, shares, price) VALUES(:user_id, :symbol, :shares, :price)",
                           user_id=session["user_id"], symbol=quote["symbol"], shares=int(request.form.get("shares")), price=quote["price"])

                # Update user's available cash
                db.execute("UPDATE users SET cash = cash - :spent WHERE id = :user_id",
                           spent=(quote["price"] * int(request.form.get("shares"))), user_id=session["user_id"])

                # Redirect user to home page
                return redirect("/")

            # Not enough cash to buy shares
            else:
                # Apologize
                return apology("Not enough cash")

        # Input is invalid
        else:
            # Apologize
            return apology("Invalid input")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Render buy.html
        return render_template("buy.html")


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""

    available = not db.execute("SELECT id FROM users WHERE username = :username", username=request.args.get("username"))

    return jsonify(available)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # retrieve user's history
    history = db.execute("SELECT symbol, shares, price, time FROM history WHERE id = :user_id", user_id=session["user_id"])

    # format prices
    for row in history:
        row.update(price=usd(row["price"]))

    # Render history.html
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Checks that symbol is valid
        if lookup(request.form.get("symbol")):

            # Format price
            price = usd(lookup(request.form.get("symbol"))["price"])

            # Renders quoted.html template
            return render_template("quoted.html", symbol=lookup(request.form.get("symbol")), price=price)

        # Symbol is not valid
        else:

            # Renders apology
            return apology("Invalid symbol")

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Render quote.html
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username field was filled
        if not request.form.get("username"):
            return apology("Must provide username")

        # Ensure password field was filled
        if not request.form.get("password"):
            return apology("Must provide password")

        # Ensure confirm password field was field
        if not request.form.get("confirmation"):
            return apology("Must confirm password")

        # Ensure password and confirm password fields match:
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("Password and password confirmation fields must match")

        # Add user into database, hashes password
        result = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username=request.form.get(
            "username"), hash=generate_password_hash(request.form.get("password")))

        # Check that username is not taken
        if not result:
            return apology("username taken")

        # Create session
        session["user_id"] = db.execute("SELECT id FROM users WHERE username = :username",
                                        username=request.form.get("username"))[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Render register.html
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Check that number of shares is positive integer
        if request.form.get("shares").isnumeric() and int(request.form.get("shares")) > 0:

            # Look up quote for symbol
            quote = lookup(request.form.get("symbol"))

            # Query for number of shares of the stock that the user has
            shares = db.execute("SELECT SUM(shares) FROM history WHERE symbol = :symbol AND id = :user_id",
                                symbol=quote["symbol"], user_id=session["user_id"])[0]["SUM(shares)"]

            # Check that user has enough shares of the stock to sell
            if int(request.form.get("shares")) <= shares:

                # Record transaction in database
                db.execute("INSERT INTO history (id, symbol, shares, price) VALUES(:user_id, :symbol, :shares, :price)",
                           user_id=session["user_id"], symbol=quote["symbol"], shares=-int(request.form.get("shares")), price=quote["price"])

                # Update user's available cash
                db.execute("UPDATE users SET cash = cash + :spent WHERE id = :user_id",
                           spent=(quote["price"] * int(request.form.get("shares"))), user_id=session["user_id"])

                # Redirect user to home page
                return redirect("/")

            # Not enough shares
            else:
                # Apologize
                return apology("Too many shares")

       # Invalid input for share
        else:
            # Apologize
            return apology("Invalid shares")

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Query for the symbols of the user's stocks
        symbols = db.execute("SELECT symbol FROM history GROUP BY symbol HAVING id = :user_id", user_id=session["user_id"])

        # Render sell.html
        return render_template("sell.html", symbols=symbols)


@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changepassword():
    """Change user's password"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure current password field was filled
        if not request.form.get("current_password"):
            return apology("Must provide current password")

        # Ensure new password field was filled
        if not request.form.get("new_password"):
            return apology("Must provide new password")

        # Ensure confirm new password field was field
        if not request.form.get("confirm_password"):
            return apology("Must confirm new password")

        # Query database for current password
        hash = db.execute("SELECT hash FROM users WHERE id = :user_id", user_id=session["user_id"])[0]["hash"]

        # Verify current password
        if not check_password_hash(hash, request.form.get("current_password")):
            return apology("Invalid current password")

        # Ensure new password and confirm password fields match:
        if request.form.get("new_password") != request.form.get("confirm_password"):
            return apology("New password and password confirmation fields must match")

        # Ensure new password and current don't match
        if request.form.get("current_password") == request.form.get("new_password"):
            return apology("New password must be different from current password")

        # Update user's password
        db.execute("UPDATE users SET hash=:hash WHERE id = :user_id",
                   user_id=session["user_id"], hash=generate_password_hash(request.form.get("new_password")))

        # Redirect user to homepage
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:

        # Render changepassword.html
        return render_template("changepassword.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
