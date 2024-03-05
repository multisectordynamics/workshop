# MSD Workshop Review App

A workshop administration app to aid in reviewing attendance submissions

## Installation
NOTE:  We have tested this application using Python 3.11.7 though other version >= 3.9 will likely function correctly.

### Clone the repo 

Terminal users can use:
```sh
git clone https://github.com/multisectordynamics/workshop.git
```
or using your preferred GUI for GitHub and navigate to the `workshop` directory in your terminal.

### Set up your environment

#### Python environment

We encourage users to setup a virtual environment for this project.  There are many ways to do this depending on your package management preferences and configuration.  If you do not have familiarity with virtual environments in Python, you can start here with the [Python Packaging Users Guide](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/).

Once you have established a virtual envionment, you can install the package dependencies using the folowing:
```sh
pip install -r requirements.txt
```

We have the requirements pinned to specific versions known to be compatible.  Feel free to explore updating these packages, we simply provide the stable versions for our purposes.

#### App environment

The app requires two environment variables to be set which control access to the following two key: password pairs for the app:
- `WORKSHOP_LEVEL_0`: which allows access to the administrative panel
- `WORKSHOP_LEVEL_1`: which allows access to the reviewer panel

For Linux or Mac users, these can be added to your bash, zsh, or perferred shell configuration file and then sourced to have them stick.  For Windows users, they will need to be added to your environment variables.

### Setting up a review

#### File setup
The following two files are included that you will need to populate with data specific to your study. These files are stored in the `workshop/data` directory of this repostiory.  If you chage the field names or the types in these fields, the app will break.  These are not intened to be trifled with.
- `tbl_reviewers.csv`: a CSV file with reviewer information using a sythetic identifier
- `tbl_source.csv`:  a CSV file with information from your applications

This app uses a [DuckDB](https://duckdb.org/) database to house the information used in your review process.  To set this up for your project you can use the following code or follow the Jupyter notebook version found in the `workshop/notebooks/db_tools.ipynb` file in this repository.  

NOTE:  Constraints are not setup in the scehma of the database that prohibit dupicate insertions.  Place these in if you like.  

**Import packages**

```python
import os

import duckdb
import pandas as pd
```

**Set directory structure**

```python
# the local data you have cloned the workshop repo to
data_directory = "<your_local_directory_where_clonded>/workshop/data"

# path to where you want to create or the current database
db_file = os.path.join(data_directory, "data.duckdb")

# path to files used to build the input data
tbl_reviewer_file = os.path.join(data_directory, "tbl_reviewers.csv")
tbl_source_file = os.path.join(data_directory, "tbl_source.csv")
```

**Define table schema**

```python
tbl_schema = """
CREATE TABLE tbl_log
(
reviewer_id INTEGER, 
document_id INTEGER, 
conflict VARCHAR
);

CREATE TABLE tbl_response
(
reviewer_id INTEGER, 
reviewer_name VARCHAR,
document_id INTEGER,
alignment INTEGER,
science INTEGER,
benefits INTEGER,
comments VARCHAR,
screening_order INTEGER
);

CREATE TABLE tbl_reviewer
(
reviewer_id INTEGER, 
reviewer_name VARCHAR,
);

CREATE TABLE tbl_source
(
document_id INTEGER,
submission_timestamp TIMESTAMP,
email VARCHAR,
first_name VARCHAR,
last_name VARCHAR,
phone VARCHAR,
institution VARCHAR,
authors VARCHAR,
title VARCHAR,
abstract VARCHAR,
biosketch VARCHAR,
leverage_plan VARCHAR,
student VARCHAR,
early_career VARCHAR,
registration_waiver VARCHAR,
travel_award VARCHAR,
poster_competition VARCHAR,
breakout_sessions VARCHAR
);
"""
```

**Build database**
Just as easily as you can build this database, you can delete it and start over again. I set up a Cron job to run that backed up the database to a versioned file name nightly when we were in review to avoid any possiblity of deleting the active db.

```python
with duckdb.connect(db_file) as con:
    cursor = con.cursor()
    con.sql(tbl_schema)
```

**Check build**

```python
# create a connection to a file
with duckdb.connect(db_file) as con:

    cursor = con.cursor()

    cursor.execute("SHOW TABLES")

    tables = cursor.fetchall()
    for table in tables:
        print(table[0])

    sql = "DESCRIBE tbl_response;"
    cursor.execute(sql)
    x = cursor.fetchall()
    
print(x)
```

**Add starter data from CSV files**

```python
df_source = pd.read_csv(tbl_source_file)
df_reviewer = pd.read_csv(tbl_reviewer_file)

with duckdb.connect(db_file) as con:

    cursor = con.cursor()

    con.execute("INSERT INTO tbl_source SELECT * FROM df_source")
    con.execute("INSERT INTO tbl_reviewer SELECT * FROM df_reviewer")
```

**View data**

```python
with duckdb.connect(db_file) as con:

    cursor = con.cursor()

    x = con.execute("SELECT * FROM tbl_source").df()

print(x)
```

#### Settings setup
There are two main settings that are actually hard-coded as global variables in the app (bad form I know - if you want to contribute adding in a YAML config for these, more power to you):

- `MAX_REVIEWS_PER_DOCUMENT`: the maximum number of reviews allowed per document
- `MAX_REVIEWS_PER_REVIEWER`:  the maximum number of review allowed per reviewer

Set these as you like.

### Launching the app
Assuming you have built and activated your virtual environment, run the following from the root directory of this repository to launch the app:

```sh
streamlit run app.py
```

NOTE:  I have seen this conflict with Jupyter ports once in a blue moon, so if you have issues and Jupyter or other apps that require different port configurations, consider closing them and trying again.

