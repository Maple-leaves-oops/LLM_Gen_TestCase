from streamlit.web import cli
import os
import sys


if __name__ == "__main__":
    # sys.argv会在Python程序启动时作为命令行参数传递给程序
    sys.argv = [
        "streamlit",
        "run",
        os.path.abspath(os.path.join(os.getcwd(), "Page/page.py")),
    ]
    # cli.main()会读取sys.argv中的参数并根据这些参数来决定如何启动Streamlit应用
    sys.exit(cli.main())
