from cs50 import SQL
from flask import Flask, jsonify, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, coingecko, usd, get_coin_info

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
    if request.method == "POST":
        oc = db.execute(
            "SELECT opportunity_costs FROM users WHERE id = ?", session["user_id"]
        )[0]["opportunity_costs"]
        if oc != 0:
            db.execute(
                "UPDATE users SET opportunity_costs = ? WHERE id = ?", 0, session["user_id"]
            )
        return redirect("/")
    else:
        coins = get_coin_info(session["user_id"])
        oc = db.execute(
            "SELECT opportunity_costs FROM users WHERE id = ?", session["user_id"]
        )[0]["opportunity_costs"]
        return render_template("index.html", coins = coins, oc=oc)


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
            "aEarned": 0
        }

        return jsonify({"ok": True, "coin": new_coin})
    else:
        list = coingecko("coins/list")
        if list == None:
            return jsonify({"status": "error", "message": "Too many API requests"}), 400

        coins = get_coin_info(session["user_id"])

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
        "SELECT coin_id, buy, amount, date FROM transactions where id = ?", tx_id
    )[0]
    if checks["buy"] == True:
        checkTotal = db.execute(
            "WITH Bought AS ( \
                SELECT COALESCE(SUM(amount), 0) AS total_bought \
                FROM transactions \
                WHERE buy = true AND coin_id = ? AND date <= ? AND user_id = ? \
            ), \
            Sold AS ( \
                SELECT COALESCE(SUM(amount), 0) AS total_sold \
                FROM transactions \
                WHERE buy = false AND coin_id = ? AND date <= ? AND user_id = ? \
            ) \
            SELECT \
                (Bought.total_bought - Sold.total_sold) AS net_amount \
            FROM Bought, Sold", 
            checks["coin_id"], checks["date"], session["user_id"], checks["coin_id"], checks["date"], session["user_id"]
        )
        
        if checkTotal[0]["net_amount"] < checks["amount"]:
            return jsonify({"status": "error", "message": "Your portfolio would be negative, if you delete this tx"}), 400

    if not tx_id:
        return jsonify({"success": False, "error": "Missing tx_id"}), 400

    try:
        db.execute("DELETE FROM transactions WHERE id = ?", tx_id)
        return jsonify({
            "success": True, 
            "buy": checks["buy"], 
            "amount": checks["amount"],
            "date": checks["date"]
        })
    except:
        return jsonify({"success": False, "error": "Tx not found"}), 404
    
@app.route('/coins/<name>', methods=["GET"])
@login_required
def coin_page(name):
    coin_info = db.execute(
        "SELECT id, genesis, coin_id FROM coins WHERE name = ? AND user_id = ?", name, session["user_id"]
    )
    txs = db.execute(
        "SELECT * from transactions WHERE user_id = ? AND coin_id = ? ORDER BY date", session["user_id"], coin_info[0]["id"]
    )
    other_txs = db.execute(
        "SELECT * from transactions WHERE user_id = ? AND coin_id != ? ORDER BY date", session["user_id"], coin_info[0]["id"]
    )
    genesis = coin_info[0]["genesis"]
    coin_id = coin_info[0]["coin_id"]
    id = coin_info[0]["id"]

    other_coins = db.execute(
        "SELECT id, name FROM coins WHERE user_id = ? AND coin_id != ?", session["user_id"], coin_id
    )

    return render_template('transactions.html', txs = txs, genesis = genesis, coin_id = coin_id, id = id, other_coins = other_coins, other_txs = other_txs)

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

    elif form_type == "swapData":
        try:
            swap_amount = int(request.form.get("amountSwap"))
        except: 
            return jsonify({"status": "error", "message": "Invalid input for amount"}), 400 
        date = request.form.get("dateInputSwap")
        coin_id = request.form.get("coin_id_swap")
        try:
            swap_id = int(request.form.get("other_coin_id"))
        except: 
            return jsonify({"status": "error", "message": "Invalid swap coin id"}), 400 
        swap_coin_id = db.execute(
            "SELECT coin_id FROM coins WHERE id = ?", swap_id
        )[0]["coin_id"]
        set_zero = False
        event = True
        set_swap = request.form.get("setSwap")
        if set_swap:
            try:
                custom_amount = float(request.form.get("receiveValue"))
            except: 
                return jsonify({"status": "error", "message": "Invalid Amount"}), 400
        
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    formatted_date = date_obj.strftime('%d-%m-%Y')
    
    if set_zero:
        hPrice = 0
    else: 
        priceObject = coingecko(f"coins/{coin_id}/history?date={formatted_date}")
        if priceObject == None:
            return jsonify({"status": "error", "message": "API Request failed"}), 400

        hPrice = float(priceObject["market_data"]["current_price"]["usd"])

    if form_type == "swapData":
        swap_price = coingecko(f"coins/{swap_coin_id}/history?date={formatted_date}")
        if swap_price == None:
            return jsonify({"status": "error", "message": "API Request failed"}), 400

        hSwapPrice = float(swap_price["market_data"]["current_price"]["usd"])
        if set_swap:
            amount = custom_amount
            opportunity_costs = swap_amount * hSwapPrice - custom_amount * hPrice
            db.execute (
                "UPDATE users SET opportunity_costs = opportunity_costs + ? WHERE id = ?", opportunity_costs, session["user_id"]    
            )
        else:
            amount = swap_amount * hSwapPrice / hPrice
    
    if amount <= 0:
       return jsonify({"status": "error", "message": "Amount has to be higher than 0"}), 400
    
    try:
        id = db.execute(
            "Select id FROM coins WHERE user_id = ? AND coin_id = ?", session["user_id"], coin_id
        )[0]["id"]
    except:
        return jsonify({"status": "error", "message": "Invalid coin-id"}), 400
    
    #checks für sells
    if form_type == "sellData":
        checkTotal = db.execute(
            "WITH Bought AS ( \
                SELECT COALESCE(SUM(amount), 0) AS total_bought \
                FROM transactions \
                WHERE buy = true AND date <= ? AND coin_id = ? \
            ), \
            Sold AS ( \
                SELECT COALESCE(SUM(amount), 0) AS total_sold \
                FROM transactions \
                WHERE buy = false AND date <= ? AND coin_id = ? \
            ) \
            SELECT \
                (Bought.total_bought - Sold.total_sold) AS net_amount \
            FROM Bought, Sold", date, swap_id, date, swap_id
        )[0]["net_amount"]
        if checkTotal < amount:
            return jsonify({"status": "error", "message": "You can't sell more coins than you own"}), 400
    
    if form_type == "swapData":
        checkTotal = db.execute(
            "WITH Bought AS ( \
                SELECT COALESCE(SUM(amount), 0) AS total_bought \
                FROM transactions \
                WHERE buy = true AND date <= ? AND coin_id = ? \
            ), \
            Sold AS ( \
                SELECT COALESCE(SUM(amount), 0) AS total_sold \
                FROM transactions \
                WHERE buy = false AND date <= ? AND coin_id = ? \
            ) \
            SELECT \
                (Bought.total_bought - Sold.total_sold) AS net_amount \
            FROM Bought, Sold", date, swap_id, date, swap_id
        )[0]["net_amount"]
        if checkTotal < swap_amount:
            return jsonify({"status": "error", "message": "You can't sell more coins than you own"}), 400
    
    new_id = db.execute(
                "INSERT INTO transactions (user_id, coin_id, buy, price, amount, date) VALUES (?, ?, ?, ?, ?, ?)", session["user_id"], id, event, hPrice, amount, date
            )
    tx = {
            "id": new_id,
            "buy": event,
            "amount": amount,
            "price": hPrice,
            "date": date,
        }

    if form_type == "swapData":
        db.execute(
                "INSERT INTO transactions (user_id, coin_id, buy, price, amount, date) VALUES (?, ?, ?, ?, ?, ?)", session["user_id"], swap_id, False, hSwapPrice, swap_amount, date
            )
        
        other_tx = {
            "id": swap_id,
            "buy": False,
            "date": date,
            "amount": swap_amount,
        }
    else:
        other_tx = None

    return jsonify({"ok": True, "tx": tx, "other_tx": other_tx}), 200

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
        return redirect("/")

    else:
        return render_template("register.html")
