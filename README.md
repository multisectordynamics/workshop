## MSD Workshop Review App

A workshop administration app to aid in reviewing attendance submissions

### Getting started

#### Installation
NOTE:  We have tested this application using Python 3.11.7 though other version >= 3.9 will likely function correctly.

1. Clone the repo 

Terminal users can use:
```sh
git clone https://github.com/multisectordynamics/workshop.git
```
or using your preferred GUI for GitHub and navigate to the `workshop` directory in your terminal.

2. Set up your environment

**Python environment**
We encourage users to setup a virtual environment for this project.  There are many ways to do this depending on your package management preferences and configuration.  If you do not have familiarity with virtual environments in Python, you can start here with the [Python Packaging Users Guide](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/).

Once you have established a virtual envionment, you can install the package dependencies using the folowing:
```sh
pip install -r requirements.txt
```

We have the requirements pinned to specific versions known to be compatible.  Feel free to explore updating these packages, we simply provide the stable versions for our purposes.

**App environment**
The app requires two environment variables to be set which control access to the following two key: password pairs for the app:
- `WORKSHOP_LEVEL_0` which allows access to the administrative panel
- `WORKSHOP_LEVEL_1` which allows access to the reviewer panel

For Linux or Mac users, these can be added to your bash, zsh, or perferred shell configuration file and then sourced to have them stick.  For Windows users, they will need to be added to your environment variables.

### Setting up a review




