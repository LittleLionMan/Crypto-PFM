import requests
import os

from cs50 import SQL
from flask import redirect, render_template, session, jsonify
from functools import wraps

db = SQL("sqlite:///pfm.db")

api_key = os.getenv("API_KEY")
url = "https://api.coingecko.com/api/v3/"
headers = {
    "accept": "application/json",
    "x-cg-demo-api-key": api_key
}

def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def coingecko(arg):
    """Look up quote for symbol."""
    try:
        response = requests.get(url+arg, headers=headers)
        response.raise_for_status() 
        return response.json()
    except requests.RequestException as e:
        print(f"Request error: {e}")
    except (KeyError, ValueError) as e:
        print(f"Data parsing error: {e}")
    return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def get_coin_info(user_id):
    coins = db.execute (
            "SELECT id, name, coin_id, symbol, image from coins WHERE user_id = ?", user_id
        )
    ids = ",".join(coin["coin_id"] for coin in coins)
        
    prices = coingecko(f"simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true")
    if prices == None:
        return jsonify({"status": "error", "message": "Too many API Requests"}), 400
        
    for coin in coins:
        buys = db.execute (
                "SELECT price, amount FROM transactions WHERE user_id = ? AND coin_id = ? AND buy = ?", user_id, coin["id"], True
        )

        sells = db.execute (
            "SELECT price, amount FROM transactions WHERE user_id = ? AND coin_id = ? AND buy = ?", user_id, coin["id"], False
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
        if (amountBuy - amountSell) > 1:
            coin["amount"] = round(amountBuy - amountSell, 2)
        else:
            coin["amount"] = round(amountBuy - amountSell, 6) #amountBuy - amountSell
            
        if amountBuy == 0:
            coin["buy"] = amountBuy  
            coin["aSpend"] = 0
        else:
            coin["buy"] = amountBuy
            coin["aSpend"] = round(spend / amountBuy, 2)
            
        if amountSell == 0:
            coin["sell"] = amountSell  
            coin["aEarned"] = 0
        else:
            coin["sell"] = amountSell  
            coin["aEarned"] = round(earned / amountSell, 2)


        coin_id = coin["coin_id"]
        if coin_id in prices:
            coin["price"] = prices[coin_id]["usd"]
            coin["price_change"] = round(prices[coin_id]["usd_24h_change"], 2)
    
    return coins
