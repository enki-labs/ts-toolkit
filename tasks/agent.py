"""
A task agent that retrieves outstanding tasks and 
runs them on the local machine.

"""

import sys
import httplib
import json
import urllib
import time
import argparse
import logging
import autologging
from autologging import logged, traced, TracedMethods


__logger = logging.getLogger("agent.py")
__logger.setLevel(autologging.TRACE)
__stdout_handler = logging.StreamHandler(sys.stdout)
__stdout_handler.setLevel(autologging.TRACE)
__formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
__stdout_handler.setFormatter(__formatter)
__logger.addHandler(__stdout_handler)


@traced
def main ():
    """
    Processing loop.

    """

    parser = argparse.ArgumentParser(description="Task agent")
    parser.add_argument('--taskhost', action='store', help='Task management host')
    parser.add_argument('--taskport', action='store', type=int, default=3000, help='Task management port')
    args, dummy_unknown = parser.parse_known_args()

    supported = ["fx", "bbg,files", 
                 "sosc", "sopo", 
                 "sopc", "popc", 
                 "posc", "pcsc", 
                 "night", "continuous", 
                 "5day", "filtered,tick", 
                 "1min", "60min", "1week"]
    index = 0
    __logger.debug("Connect to task management server")
    conn = httplib.HTTPConnection(args.taskhost, args.taskport)

    while True:
        task_path = "/task/queue?action=get&tags=" + supported[index]
        retry = 5

        while retry > 0:

            try:
                __logger.debug(task_path)   
                conn.request("GET", task_path)
                res = conn.getresponse()
                data = res.read()
                res.close()
                retry = 0
            except Exception, ex:
                __logger.warning(str(ex))
                retry = retry - 1
                time.sleep(5)
                conn = httplib.HTTPConnection(args.taskhost, args.taskport)

        __logger.debug("--------------------------------------------")
        __logger.debug(data)
        __logger.debug("--------------------------------------------")

        task_info = json.loads(data)
        __logger.debug(task_info)
        __logger.debug("--------------------------------------------")

        if task_info != None:

            run_code = compile(task_info["childData"]["detail"]["code"], '<string>', 'exec')
            namespace = dict(taskInfo=task_info, conn=conn)
            exec run_code in namespace
            output = namespace['run']()

            __logger.debug("--------------- DONE ------------------")
            quoted_output = urllib.quote(str(output))
            quoted_tags = urllib.quote(",".join(task_info["node"]["tags"]))
            quoted_id = urllib.quote(task_info["node"]["_id"])

            __logger.debug("----------- UPDATE STATUS --------------")
            retry = 5

            while retry > 0:
                try:
                    conn.request("GET", "/task/queue?action=release&id=%s&status=complete&output=%s&tags=%s" 
                                 % (quoted_id, quoted_output, quoted_tags))
                    res = conn.getresponse()
                    res.close()
                    retry = 0
                    __logger.debug("------------ UPDATED ------------")
                except Exception, ex:
                    __logger.warning(str(ex))
                    retry = retry - 1
                    time.sleep(5)
                    conn = httplib.HTTPConnection(args.taskhost, args.taskport)
	
        else:
            __logger.debug("-------- Wait for data ----------")
            index = (index+1) % len(supported)
            time.sleep(2)


if __name__ == "__main__":
    main()

