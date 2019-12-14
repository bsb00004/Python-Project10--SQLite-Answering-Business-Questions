#!/usr/bin/env python
# coding: utf-8

# ### Project 10-Answering Business Questions using SQL
# 
# In this project, we're going to answer business questions using our SQL skills like: SQL joining, using subqueries, multiple joins, set operations, aggregate functions and more. We are using diffrent tasks in every steps to go through all of the SQL skills:
# 
# - Write a SQL query to extract the relevant data
# - Create plots where necessary to visualize the data
# - Write a short paragraph, drawing conclusions and explaining the data and/or visualizations.
# 
# We are using the Chinook database, which is provided as a SQLite database file called __chinook.db__. A copy of the database schema is below - we'll need to come back to this step often to consult the schema as we write your queries.
# <img src="https://s3.amazonaws.com/dq-content/191/chinook-schema.svg" />
# 
# It's worth remembering that our database retains 'state', so if we run a query with a CREATE or DROP twice, the query will fail.  But if you have trouble, or if you manage to lock your database, we have provided a __chinook-unmodified.db__ file that you can copy over the __chinook.db__ to restore it back to its initial state (see [this blog post on how to run shell commands within a Jupyter notebook](https://www.dataquest.io/blog/jupyter-notebook-tips-tricks-shortcuts/#17executingshellcommands)).
# 
# Here are a few tips to keep in mind while working on these queries:
# 
# - Write your query in stages, and run it as you go to make sure at each stage it's producing the output you expect.
# - If something isn't behaving as you expect, break parts of the query out into their own, separate queries to make sure there's not an inner logic error.
# - Don't be afraid to write separate queries to check the underlying data, for instance you might write a query that you can use to manually check a calculation and give yourself confidence that the output you're seeing is correct.
# 
# ### Creating Helper Functions

# In[1]:


# Importing the SQLite, pandas and matplotlib modules
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
# magic command %matplotlib inline 
# to make sure any plots render in the notebook
get_ipython().magic('matplotlib inline')

db = 'chinook.db'
# Creating a run_query() function, that takes 
# a SQL query as an argument and returns 
# a pandas dataframe of that query
def run_query(q):
    with sqlite3.connect(db) as conn:
        return pd.read_sql(q, conn)

# Creating a run_command() function that takes 
# a SQL command as an argument and executes it 
# using the sqlite module.
def run_command(c):
    with sqlite3.connect(db) as conn:
        conn.isolation_level = None
        conn.execute(c)

# Creating a show_tables() function that calls 
# the run_query() function to return a list of 
# all tables and views in the database.        
def show_tables():
    q = '''
    SELECT
        name,
        type
    FROM sqlite_master
    WHERE type IN ("table","view");
    '''
    return run_query(q)

# Runing the show_tables() function.
show_tables()


# ### Selecting New Albums to Purchase
# Writing a query that returns each genre, with the number of tracks sold in the USA:
# - in absolute numbers
# - in percentages.

# In[2]:


albums_to_purchase = '''
WITH usa_tracks_sold AS
   (
    SELECT il.* FROM invoice_line il
    INNER JOIN invoice i on il.invoice_id = i.invoice_id
    INNER JOIN customer c on i.customer_id = c.customer_id
    WHERE c.country = "USA"
   )

SELECT
    g.name genre,
    count(uts.invoice_line_id) tracks_sold,
    cast(count(uts.invoice_line_id) AS FLOAT) / (
        SELECT COUNT(*) from usa_tracks_sold
    ) percentage_sold
FROM usa_tracks_sold uts
INNER JOIN track t on t.track_id = uts.track_id
INNER JOIN genre g on g.genre_id = t.genre_id
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
'''

run_query(albums_to_purchase)


# ### Creating a plot to show the above data.

# In[3]:


genre_sales_usa = run_query(albums_to_purchase)
genre_sales_usa.set_index("genre", inplace=True, drop=True)

genre_sales_usa["tracks_sold"].plot.barh(
    title="Top Selling Genres in the USA",
    xlim=(0, 625),
    colormap=plt.cm.Accent
)

plt.ylabel('')

for i, label in enumerate(list(genre_sales_usa.index)):
    score = genre_sales_usa.loc[label, "tracks_sold"]
    label = (genre_sales_usa.loc[label, "percentage_sold"] * 100
            ).astype(int).astype(str) + "%"
    plt.annotate(str(label), (score + 10, i - 0.15))

plt.show()


# Based on the sales of tracks across different genres in the USA, we should purchase the new albums by the following artists:
# 
# - Red Tone (Punk)
# - Slim Jim Bites (Blues)
# - Meteor and the Girls (Pop)
# 
# It's worth keeping in mind that combined, these three genres only make up only 17% of total sales, so we should be on the lookout for artists and albums from the 'rock' genre, which accounts for 53% of sales.
# 
# ### Analyzing Employee Sales Performance
# Writing a query that finds the total dollar amount of sales assigned to each sales support agent within the company. Add any extra attributes for that employee that you find are relevant to the analysis.

# In[4]:


employee_sales_performance = '''
WITH customer_support_rep_sales AS
    (
     SELECT
         i.customer_id,
         c.support_rep_id,
         SUM(i.total) total
     FROM invoice i
     INNER JOIN customer c ON i.customer_id = c.customer_id
     GROUP BY 1,2
    )

SELECT
    e.first_name || " " || e.last_name employee,
    e.hire_date,
    SUM(csrs.total) total_sales
FROM customer_support_rep_sales csrs
INNER JOIN employee e ON e.employee_id = csrs.support_rep_id
GROUP BY 1;
'''

run_query(employee_sales_performance)


# ### Creating a plot of the results of the above query

# In[5]:


employee_sales = run_query(employee_sales_performance)

employee_sales.set_index("employee", drop=True, inplace=True)
employee_sales.sort_values("total_sales", inplace=True)
employee_sales.plot.barh(
    legend=False,
    title='Sales Breakdown by Employee',
    colormap=plt.cm.Accent
)
plt.ylabel('')
plt.show()


# While there is a 20% difference in sales between Jane (the top employee) and Steve (the bottom employee), the difference roughly corresponds with the differences in their hiring dates.
# 
# ### Analyzing Sales by Country
# Writing a query that collates data on purchases from different countries.
# - Where a country has only one customer, collect them into an "Other" group.
# - The results should be sorted by the total sales from highest to lowest, with the "Other" group at the very bottom.
# - For each country, include:
#     - total number of customers
#     - total value of sales
#     - average value of sales per customer
#     - average order value

# In[6]:


sales_by_country = '''
WITH country_or_other AS
    (
     SELECT
       CASE
           WHEN (
                 SELECT count(*)
                 FROM customer
                 where country = c.country
                ) = 1 THEN "Other"
           ELSE c.country
       END AS country,
       c.customer_id,
       il.*
     FROM invoice_line il
     INNER JOIN invoice i ON i.invoice_id = il.invoice_id
     INNER JOIN customer c ON c.customer_id = i.customer_id
    )

SELECT
    country,
    customers,
    total_sales,
    average_order,
    customer_lifetime_value
FROM
    (
    SELECT
        country,
        count(distinct customer_id) customers,
        SUM(unit_price) total_sales,
        SUM(unit_price) / count(distinct customer_id) customer_lifetime_value,
        SUM(unit_price) / count(distinct invoice_id) average_order,
        CASE
            WHEN country = "Other" THEN 1
            ELSE 0
        END AS sort
    FROM country_or_other
    GROUP BY country
    ORDER BY sort ASC, total_sales DESC
    );
'''

run_query(sales_by_country)


# ### Visualizing Sales by Country
# 
# Now that we have our data, we've to create a series of visualizations which communicate our findings, and then make recommendations on which countries may have potential for growth, so the Chinook marketing team can create some new advertising campaigns.
# 
# When we're working with data that has many dimensions, it can be tempting to try and communicate every dimension in a single plot. This often results in complex and hard to read visualizations. Instead of this, we should create different plots for each dimension.
# 
# The best way to communicate the data - this includes not only plot types, but how you use color, spacing and layout.
# 
# For each dimension, creating a visualization which demonstrates the data we collated in the previous step.
# - We should also decide whether the "Other" group is relevant to the analysis and make decisions on where to include it (if anywhere) in the visualizations.

# In[7]:


country_metrics = run_query(sales_by_country)
country_metrics.set_index("country", drop=True, inplace=True)
colors = [plt.cm.Accent(i) for i in np.linspace(0, 1, country_metrics.shape[0])]

fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(9, 10))
ax1, ax2, ax3, ax4 = axes.flatten()
fig.subplots_adjust(hspace=.5, wspace=.3)


# top left
sales_breakdown = country_metrics["total_sales"].copy().rename('')
sales_breakdown.plot.pie(
    ax=ax1,
    startangle=-90,
    counterclock=False,
    title='Sales Breakdown by Country,\nNumber of Customers',
    colormap=plt.cm.Accent,
    fontsize=8,
    wedgeprops={'linewidth':0}
    
)

# top right
cvd_cols = ["customers","total_sales"]
custs_vs_dollars = country_metrics[cvd_cols].copy()
custs_vs_dollars.index.name = ''
for c in cvd_cols:
    custs_vs_dollars[c] /= custs_vs_dollars[c].sum() / 100
custs_vs_dollars.plot.bar(
    ax=ax2,
    colormap=plt.cm.Set1,
    title="Pct Customers vs Sales"
)
ax2.tick_params(top="off", right="off", left="off", bottom="off")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)


# bottom left
avg_order = country_metrics["average_order"].copy()
avg_order.index.name = ''
difference_from_avg = avg_order * 100 / avg_order.mean() - 100
difference_from_avg.drop("Other", inplace=True)
difference_from_avg.plot.bar(
    ax=ax3,
    color=colors,
    title="Average Order,\nPct Difference from Mean"
)
ax3.tick_params(top="off", right="off", left="off", bottom="off")
ax3.axhline(0, color='k')
ax3.spines["top"].set_visible(False)
ax3.spines["right"].set_visible(False)
ax3.spines["bottom"].set_visible(False)

# bottom right
ltv = country_metrics["customer_lifetime_value"].copy()
ltv.index.name = ''
ltv.drop("Other",inplace=True)
ltv.plot.bar(
    ax=ax4,
    color=colors,
    title="Customer Lifetime Value, Dollars"
)
ax4.tick_params(top="off", right="off", left="off", bottom="off")
ax4.spines["top"].set_visible(False)
ax4.spines["right"].set_visible(False)

plt.show()


# Based on the data, there may be opportunity in the following countries:
# 
# - Czech Republic
# - United Kingdom
# - India
# 
# It's worth keeping in mind that because the amount of data from each of these countries is relatively low. Because of this, we should be cautious spending too much money on new marketing campaigns, as the sample size is not large enough to give us high confidence. A better approach would be to run small campaigns in these countries, collecting and analyzing the new customers to make sure that these trends hold with new customers.
# 
# ### Albums vs Individual Tracks
# 
# Writing a query that categorizes each invoice as either an album purchase or not, and calculates the following summary statistics:
# - Number of invoices
# - Percentage of invoices

# In[8]:


albums_vs_tracks = '''
WITH invoice_first_track AS
    (
     SELECT
         il.invoice_id invoice_id,
         MIN(il.track_id) first_track_id
     FROM invoice_line il
     GROUP BY 1
    )

SELECT
    album_purchase,
    COUNT(invoice_id) number_of_invoices,
    CAST(count(invoice_id) AS FLOAT) / (
                                         SELECT COUNT(*) FROM invoice
                                      ) percent
FROM
    (
    SELECT
        ifs.*,
        CASE
            WHEN
                 (
                  SELECT t.track_id FROM track t
                  WHERE t.album_id = (
                                      SELECT t2.album_id FROM track t2
                                      WHERE t2.track_id = ifs.first_track_id
                                     ) 

                  EXCEPT 

                  SELECT il2.track_id FROM invoice_line il2
                  WHERE il2.invoice_id = ifs.invoice_id
                 ) IS NULL
             AND
                 (
                  SELECT il2.track_id FROM invoice_line il2
                  WHERE il2.invoice_id = ifs.invoice_id

                  EXCEPT 

                  SELECT t.track_id FROM track t
                  WHERE t.album_id = (
                                      SELECT t2.album_id FROM track t2
                                      WHERE t2.track_id = ifs.first_track_id
                                     ) 
                 ) IS NULL
             THEN "yes"
             ELSE "no"
         END AS "album_purchase"
     FROM invoice_first_track ifs
    )
GROUP BY album_purchase;
'''

run_query(albums_vs_tracks)


# Album purchases account for 18.6% of purchases. Based on this data, I would recommend against purchasing only select tracks from albums from record companies, since there is potential to lose one fifth of revenue.
# 
# ### Further practice
# 
# We can practice more, like we can look at the schema and come up with some more business questions, and then write queries to answer them. Here are a few to get you started:
# 
# - Which artist is used in the most playlists?
# - How many tracks have been purchased vs not purchased?
# - Is the range of tracks in the store reflective of their sales popularity?
# - Do protected vs non-protected media types have an effect on popularity?

# In[ ]:




