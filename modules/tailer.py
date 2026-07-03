import time


class Tailer:

    def __init__(self, logfile):
        self.logfile = logfile

    def follow(self):

        with open(self.logfile, "r") as f:

            f.seek(0, 2)

            while True:

                line = f.readline()

                if not line:
                    time.sleep(0.2)
                    continue

                yield line.strip()
