from __init__ import create_app
from seed import init_db

app = create_app()
init_db(app)

if __name__ == '__main__':
    app.run()
