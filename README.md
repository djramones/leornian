# Leornian

## Development notes

Development environment:

- Ubuntu 22.04 in WSL2
- Python 3.10 (default in Ubuntu 22.04)
- Visual Studio Code, with the following extensions
    - [Pylint](https://marketplace.visualstudio.com/items?itemName=ms-python.pylint)
    - [Black Formatter](https://marketplace.visualstudio.com/items?itemName=ms-python.black-formatter)

Before installing Python dependencies (from `requirements-lock.txt`), see the [`psycopg` docs on local installation](https://www.psycopg.org/psycopg3/docs/basic/install.html#local-installation). On Ubuntu 22.04, this means having to `sudo apt install python3-dev libpq-dev build-essential`.

Create a virtual environment under `venv/`: `python3 -m venv venv`.

After setting up a Postgres database, execute the following for the DB user:

    ALTER ROLE <myprojectuser> SET client_encoding TO 'utf8';
    ALTER ROLE <myprojectuser> SET default_transaction_isolation TO 'read committed';
    ALTER ROLE <myprojectuser> SET timezone TO 'UTC';
    GRANT ALL PRIVILEGES ON DATABASE <myproject> TO <myprojectuser>;
    ALTER ROLE <myprojectuser> CREATEDB; -- to allow creation of test DB

Create a `.env` file from `.env.dist`.

For the `SECRET_KEY`, this snippet can be used to generate a secure value:

    import string
    import secrets
    choices = string.ascii_letters + string.digits
    print(''.join(secrets.choice(choices) for i in range(64)))
