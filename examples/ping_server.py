"""This script pings the server every 5 minutes and tries to reauthenticate in case it looses it."""

from datetime import datetime
import time

import ibcp


if __name__ == "__main__":
    sleep_interval = 60 * 5
    api = ibcp.REST()

    while True:
        status = api.ping_server()
        if not status["iserver"]["authStatus"]["authenticated"]:
            api.re_authenticate()
            time.sleep(5)
            status = api.get_auth_status()
            now = datetime.now()
            print(now.strftime("%Y/%m/%d %H:%M:%S") + "  " + str(status))
        time.sleep(sleep_interval)
