import json

from cs50 import SQL
from flask import Flask, jsonify, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, coingecko, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///pfm.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show portfolio"""
    if request.method == "POST":

        """stocks = db.execute(
            "SELECT stock, symbol, SUM(amount) FROM transactions Where user_id = ? GROUP BY stock", session["user_id"]
        )"""
        return apology("Hello")
    else:
        return render_template("index.html")


@app.route("/coins", methods=["GET", "POST"])
@login_required
def coins():
    
    if request.method == "POST":
        name = request.form.get("coinName")
        id = request.form.get("coinId")
        symbol = request.form.get("coinSymbol")

        if not name:
            return jsonify({"status": "error", "message": "Name cannot be empty"}), 400
        elif not id:
            return jsonify({"status": "error", "message": "ID cannot be empty"}), 400
        elif not symbol:
            return jsonify({"status": "error", "message": "Symbol cannot be empty"}), 400
       
        coinData = coingecko(f"coins/{id}")
        if coinData == None:
            return jsonify({"status": "error", "message": "Too many API Requests"}), 400
        
        if coinData["image"]["small"]:
            image = coinData["image"]["small"]
        else:
            image = None
        if coinData["genesis_date"]:
            genesis = coinData["genesis_date"]
        else:
            genesis = None
        if coinData["market_data"]["price_change_percentage_24h"]:
            price_change = coinData["market_data"]["price_change_percentage_24h"]
        else:
            price_change = None
        if coinData["market_data"]["current_price"]["usd"]:
            price = coinData["market_data"]["current_price"]["usd"]
        else:
            price = None
        
        try:
            db.execute(
                "INSERT INTO coins (user_id, name, coin_id, symbol, image, genesis) VALUES (?, ?, ?, ?, ?, ?)", session["user_id"], name, id, symbol, image, genesis
            )
        except: 
            return jsonify({"status": "error", "message": "Coin already added"}), 400
        
        new_coin = {
            "coin_id": id,
            "name": name,
            "symbol": symbol,
            "image": image,
            "price": round(price, 4),
            "price_change": round(price_change, 2),
            "amount": 0,
            "aSpend": 0,
        }

        return jsonify({"ok": True, "coin": new_coin})
    else:
        list = coingecko("coins/list")
        if list == None:
            return jsonify({"status": "error", "message": "Too many API requests"}), 400

        coins = db.execute (
            "SELECT id, name, coin_id, symbol, image from coins WHERE user_id = ?", session["user_id"]
        )
        ids = ",".join(coin["coin_id"] for coin in coins)
        
        prices = coingecko(f"simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true")
        if prices == None:
            return jsonify({"status": "error", "message": "Too many API Requests"}), 400
        
        for coin in coins:
            buys = db.execute (
                "SELECT price, amount FROM transactions WHERE user_id = ? AND coin_id = ? AND buy = ?", session["user_id"], coin["id"], True
            )

            sells = db.execute (
                "SELECT price, amount FROM transactions WHERE user_id = ? AND coin_id = ? AND buy = ?", session["user_id"], coin["id"], False
            )
    
            amountBuy = 0;
            amountSell = 0;
            spend = 0;
            earned = 0;
            for buy in buys:
                amountBuy = amountBuy + buy["amount"]
                spend = spend + buy["amount"] * buy["price"]
            for sell in sells:
                amountSell = amountSell + sell["amount"]
                earned = earned + sell["amount"] * sell["price"]
            coin["amount"] = amountBuy - amountSell
            
            if amountBuy == 0:
                coin["aSpend"] = 0
            else:
                coin["aSpend"] = round(spend / amountBuy, 2)
            
            if amountSell == 0:
                coin["aEarned"] = 0
            else:  
                coin["aEarned"] = round(earned / amountSell, 2)


            coin_id = coin["coin_id"]
            if coin_id in prices:
                coin["price"] = prices[coin_id]["usd"]
                coin["price_change"] = round(prices[coin_id]["usd_24h_change"], 2)

        return render_template("coins.html", list = list, coins = coins)

@app.route("/delete_coin", methods=["POST"])
def delete_coin():
    coin_id = request.form.get("coin_id")

    if not coin_id:
        return jsonify({"success": False, "error": "Missing coin_id"}), 400

    try:
        db.execute("DELETE FROM coins WHERE user_id = ? AND coin_id = ?", session["user_id"], coin_id)
        return jsonify({"success": True})
    except:
        return jsonify({"success": False, "error": "Coin not found"}), 404
    
@app.route("/delete_tx", methods=["POST"])
def delete_tx():
    tx_id = request.form.get("tx_id")
    
    checks = db.execute (
        "SELECT buy, amount, date FROM transactions where id = ?", tx_id
    )
    if checks[0]["buy"] == True:
        checkTotal = db.execute(
            "WITH Bought AS ( \
                SELECT COALESCE(SUM(amount), 0) AS total_bought \
                FROM transactions \
                WHERE buy = true \
            ), \
            Sold AS ( \
                SELECT COALESCE(SUM(amount), 0) AS total_sold \
                FROM transactions \
                WHERE buy = false \
            ) \
            SELECT \
                (Bought.total_bought - Sold.total_sold) AS net_amount \
            FROM Bought, Sold"
            )
        
        if checkTotal[0]["net_amount"] < checks[0]["amount"]:
            return jsonify({"status": "error", "message": "Your portfolio would be negative, if you delete this tx"}), 400

    if not tx_id:
        return jsonify({"success": False, "error": "Missing tx_id"}), 400

    try:
        db.execute("DELETE FROM transactions WHERE id = ?", tx_id)
        return jsonify({
            "success": True, 
            "buy": checks[0]["buy"], 
            "amount": checks[0]["amount"],
            "date": checks[0]["date"]
        })
    except:
        return jsonify({"success": False, "error": "Tx not found"}), 404
    
@app.route('/coins/<name>', methods=["GET", "POST"])
@login_required
def coin_page(name):
    coin_info = db.execute(
        "SELECT id, genesis, coin_id FROM coins WHERE name = ? AND user_id = ?", name, session["user_id"]
    )
    txs = db.execute(
        "SELECT * from transactions WHERE user_id = ? AND coin_id = ? ORDER BY date", session["user_id"], coin_info[0]["id"]
    )
    genesis = coin_info[0]["genesis"]
    coin_id = coin_info[0]["coin_id"]

    return render_template('transactions.html', txs = txs, genesis = genesis, coin_id = coin_id)

@app.route('/tx', methods=["POST"])
@login_required
def tx():
    form_type = request.form.get('form_type')
    set_zero = False
    if form_type == "buyData":
        try:
            amount = int(request.form.get("amountBuy"))
        except: 
            return jsonify({"status": "error", "message": "Invalid input for amount"}), 400 
        date = request.form.get("dateInputBuy")
        coin_id = request.form.get("coin_id_buy")
        set_zero = request.form.get("setZero")
        event = True
    elif form_type == "sellData":
        try:
            amount = int(request.form.get("amountSell"))
        except: 
            return jsonify({"status": "error", "message": "Invalid input for amount"}), 400 
        date = request.form.get("dateInputSell")
        coin_id = request.form.get("coin_id_sell")
        set_zero = request.form.get("setZeroSell")
        event = False

        checkTotal = db.execute(
            "WITH Bought AS ( \
                SELECT COALESCE(SUM(amount), 0) AS total_bought \
                FROM transactions \
                WHERE buy = true AND date <= ? \
            ), \
            Sold AS ( \
                SELECT COALESCE(SUM(amount), 0) AS total_sold \
                FROM transactions \
                WHERE buy = false \
            ) \
            SELECT \
                (Bought.total_bought - Sold.total_sold) AS net_amount \
            FROM Bought, Sold", date
        )
        if checkTotal[0]["net_amount"] < amount:
            return jsonify({"status": "error", "message": "You can't sell more coins than you own"}), 400



    date_obj = datetime.strptime(date, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d-%m-%Y')
    if amount <= 0:
       return jsonify({"status": "error", "message": "Amount has to be higher than 0"}), 400
    
    if set_zero:
        hPrice = 0
    else: 
        priceObject = coingecko(f"coins/{coin_id}/history?date={formatted_date}")
        if priceObject == None:
            return jsonify({"status": "error", "message": "API Request failed"}), 400

        hPrice = int(priceObject["market_data"]["current_price"]["usd"])
        if hPrice > 1:
            hPrice = round(hPrice, 2)
    
    try:
        id = db.execute(
            "Select id FROM coins WHERE user_id = ? AND coin_id = ?", session["user_id"], coin_id
        )
    except:
        return jsonify({"status": "error", "message": "Invalid coin-id"}), 400
    new_id = db.execute(
                "INSERT INTO transactions (user_id, coin_id, buy, price, amount, date) VALUES (?, ?, ?, ?, ?, ?)", session["user_id"], id[0]["id"], event, hPrice, amount, date
            )
    tx = {
            "id": new_id,
            "buy": event,
            "amount": amount,
            "price": hPrice,
            "date": date,
        }

    return jsonify({"ok": True, "tx": tx})


"""@app.route("/topup", methods=["GET", "POST"])
@login_required
def topup():
    if request.method == "POST":
        topup = request.form.get("amount")
        try:
            topup = int(topup)
        except ValueError:
            return apology("Invalid amount format", 400)
        if topup > 10000:
            return apology("Only top ups up to 10.000$ are supported")
        if topup < 1:
            return apology("At least 1$ is required for a top up")
        db.execute(
            "UPDATE users SET cash = cash + ? WHERE id = ?", topup, session["user_id"]
        )
        return redirect("/")
    else:
        return render_template("topup.html")"""

"""@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        amount = request.form.get("shares")
        cash = db.execute(
            "SELECT cash FROM users WHERE id = ?", session["user_id"]
        )
        cash = cash[0]["cash"]
        if not stock:
            return apology("No stock found")
        elif not amount:
            return apology("Amount is required", 400)
        try:
            amount = int(amount)
        except ValueError:
            return apology("Invalid amount format", 400)
        if amount < 0:
            return apology("A positive amount is required")

        if (cash - stock["price"] * amount) < 0:
            return apology("You don't have enough cash to purchase this many stocks")

        db.execute(
                "INSERT INTO transactions (user_id, stock, symbol, amount, price) VALUES (?, ?, ?, ?, ?)", session["user_id"], stock["name"], stock["symbol"], amount, stock["price"]
            )

        db.execute(
                "UPDATE users SET cash = cash - ? WHERE id = ?", stock["price"] * amount, session["user_id"]
            )

        return redirect("/")
    else:
        return render_template("buy.html")"""


"""@app.route("/history")
@login_required
def history():
    txs = db.execute(
        "SELECT * from transactions WHERE user_id = ?", session["user_id"]
    )
    for tx in txs:
        if tx["amount"] < 0:
            tx["amount"] = tx["amount"] * -1
            tx["order"] = "sell"
        else:
            tx["order"] = "buy"
    return render_template("history.html", txs = txs)"""


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username_error = None
        pw_error = None
        # Ensure username was submitted
        if not request.form.get("username"):
            username_error = "Provide a username"
            return render_template("login.html", username_error=username_error)

        # Ensure password was submitted
        elif not request.form.get("password"):
            pw_error = "Provide a password"
            return render_template("login.html", pw_error=pw_error)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1:
            username_error = "Invalid username"
        elif not check_password_hash(rows[0]["hash"], request.form.get("password")):
            pw_error = "Invalid password"
        
        if username_error:
            return render_template("login.html", username_error=username_error)
        elif pw_error:
            return render_template("login.html", pw_error=pw_error)
        else:
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


"""@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        stock = lookup(request.form.get("symbol"))
        if not stock:
            return apology("No stock found")

        return render_template("quoted.html", stock=stock)

    else:
        return render_template("quote.html")"""


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        cpassword = request.form.get("confirmation")
        # Ensure username was submitted
        if not username:
            return render_template("register.html", username_error="Provide a username")

        # Ensure password was submitted
        elif not password:
            return render_template("register.html", password_error="Provide a password")

        elif not cpassword:
            return render_template("register.html", confirmation_error="Provide a confirmation")    

        elif not password == cpassword:
            return render_template("register.html", confirmation_error="The confirmation of your password doesn't match your password")

        # Query database for username
        try:
            db.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password)
            )
        except:
            return render_template("register.html", username_error="username already exists")

        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", username
        )

        session["user_id"] = rows[0]["id"]
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")



"""@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    stocks = db.execute(
            "SELECT symbol, SUM(amount) FROM transactions Where user_id = ? GROUP BY symbol", session["user_id"]
        )
    if request.method == "POST":
        symbol = request.form.get("symbol")
        amount = int(request.form.get("shares"))
        check_amount = 0
        for stock in stocks:
            if stock["symbol"] == symbol:
                check_amount = stock["SUM(amount)"]

        if check_amount == 0:
            return apology("You don't have this stock in your portfolio")
        elif amount > check_amount:
            return apology("You don't have this many shares of this stock in your portfolio")
        stock = lookup(symbol)
        db.execute(
                "INSERT INTO transactions (user_id, stock, symbol, amount, price) VALUES (?, ?, ?, ?, ?)", session["user_id"], stock["name"], stock["symbol"], amount * -1, stock["price"]
            )

        db.execute(
                "UPDATE users SET cash = cash + ? WHERE id = ?", stock["price"] * amount, session["user_id"]
            )
        return redirect("/")
    else:
        return render_template("sell.html", stocks=stocks)"""
