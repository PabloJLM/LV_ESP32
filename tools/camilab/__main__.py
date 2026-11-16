import os
import sys

if not __package__:
    sys.path[0] = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from camilab.app import main

if __name__ == "__main__":
    main()
