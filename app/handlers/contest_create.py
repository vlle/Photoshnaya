import pathlib
import tomllib


def build_contest_msg():
    text_toml = pathlib.Path(__file__).absolute().parent / "handlers_text" / "text.toml"
    print(text_toml)
    with open(text_toml, "rb") as f:
        msg = tomllib.load(f)


def main():
    build_contest_msg()


if __name__ == "__main__":
    main()
