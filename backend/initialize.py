from backend.bootstrap import initialize_database
from backend.db import engine


def main() -> None:
    initialize_database(engine)


if __name__ == "__main__":
    main()
