import os

from app import create_app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("FLASK_RUN_PORT", "5050")))
    app.run(host="127.0.0.1", port=port)

