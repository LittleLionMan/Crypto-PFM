# Portfolio Manager Crypto
#### Video Demo:  <URL HERE>
#### Description:

My final project for cs50 is a portfolio manager for crypto currencies inspired by the problem set *Finance*. Therefore I shamelessly copied **layout.html**, **login.html** and **register.html** and only slightly bended them for my needs. For this reasons the following description will only describe the remaining files of the project to highlight the unique aspects of it.

The app utilizes html, css and js for the frontend and flask & sqlite for the backend. Another important piece is the [coingecko-api](https://docs.coingecko.com/reference/introduction), even though the free demo version has some major restrictions.

The sqlite3 db **pfm.db** contains three tables called *users*, *coins* and *transactions*. The entries are related to each other. While every added coin is related to a user, each transactions is related to an user and a coin.

#### index.html

After a succesfull login this page with route "/" is the entry point for the user. **app.py** will make it that the route will be served with the data *oc* and *coins*. *oc* represent opportunity costs. *coins* is a list of dictionaries which will be enriched with data after the user adds coins and transactions to his portfolio. The frontend is seperated in two parts:

1. *Coin Distribution* is a pie-chart created using [chart.js](https://www.chartjs.org/docs/latest/samples/other-charts/pie.html) showing the distribution of the portfolio by values and amount of each coin
2. *Portfolio Overview* is a bootstrap-table summarizing key insights about the performance of the portfolio.

The pie-chart is populated with data using the provided *coins* array in the function *myChart*. The background-colors are generated randomly with the functions *backgroundColors* and *generateColors*. *coins* also provides the relevant data for the table and its content is prepared and allocated using js.

The table also contains a button in the row *opportunity costs*. This button triggers the POST-method for "/" and results in resetting the value of *opportunity_costs* in the db for the user in question to zero. This provides further customazibility for the user.

#### coins.html

This second page available over the navigation-bar also contains two parts. 

1. A button triggering a [modal](https://getbootstrap.com/docs/5.3/components/modal/). In this modal it is possible to choose from all coins supported by coingecko and add them to your portfolio. Several checks on the front- and backend prevent faulty or malicious input. 
2. A [scrollspy](https://getbootstrap.com/docs/5.3/components/scrollspy/) with a navigation bar. **app.py** serves the same *coins* dictionary to the frontend which data populates this element by using jinja.

Adding a coin will use the POST-method on the route "/coins". This will utilize [AJAX](https://www.w3schools.com/js/js_ajax_intro.asp) (a recommendation by chatgpt) to add the data to the database on one hand and load it into the frontend on the other hand without refreshing the page preventing unnecessary load on the api. With each element in the scrollspy also comes a delete button. This removes the component from the frontend and deletes the data of the coin and all related transactions from the database utilizing a similar methodology.
AJAX is also utilized on **coins.html** and **transactions.html** to push little [Toasts](https://getbootstrap.com/docs/5.3/components/toasts/) for error handling.

#### transactions.html

The last page is not reachable via the navigation bar, but a dynamic route reached by clicking on the hyperlinks generated around the headers of individuals coins on **coins.html**. This page also contains two parts.

1. A button opening one out of three modals: Buy, Sell, Swap. This is to add transactions for the coin in question
2. A table containing all already txs saved to the database in the past and also all added to the database in this session utilizing again AJAX. Each tx is connected to a delete button. Like this the archive is always fully customazible by the user.

The Swap and Sell functionalities come with check-buttons to enforce a price to $0. The standard approach is that the app fetches a price via coingecko at the date chosen by the user. By forcing the price to zero it is possible to account for airdrops, staking rewards or fees and slippage, too. Swaps also allow to set a custom amount for the received token. The standard approach here is that the user determines on how many tokens she/he wants to trade out of. By also determining the receiving amount it is possible to account for market volatility during a day (the coingecko api allows only to search for prices at one point in time during a day in the past), bridging or trading fees. Resulting surpluses or deficits are represented in the so called *opportunity costs*. Those are shown and manageable on "/".

ToDo's:
- CSS is so far only optimized for my lyptop. Especially **coins.html** isn't mobile friendly.
- The free plan of the coingecko-api is severly rate-limited and historical prices go just back for a year. Better alternatives should be implemented
- Scaling the app for several users at the same time might make a switch to mySQL or postgreSQL necessary.
