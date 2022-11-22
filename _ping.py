import re
import os
import sys
import time
import socket
import argparse
import subprocess
from datetime import datetime
from colorama import Fore, Back, Style, init
import encodings.idna  # To fix decoding issues when converting code to exe on some devices

init() #initialize colorama module

# _ping is script to manipulate window ping.exe
# And display pings with time stamp and colorized output based on ping time threshold
# Also you can save ping output to log file
# colorama credits goes to Jonathan Hartley & Arnon Yaari. https://github.com/tartley/colorama
# _ping credits goes to Islam Mouhsen
#
def main():
    args = parsing_config()
    # run Logger class to track log - if log is enabled
    if args.log: run_logger(args)
    # Reset any console Style
    print(Style.RESET_ALL, end="")
    # initiate ping class:
    ping_module = _Ping(hostname=args.target_name, title=args.title, count=args.count, threshold=args.threshold, timeout=args.wait,
                        buffer=args.buffer, pause=args.pause)
    # set count to None if it minus or eq 0
    if args.count <= 0: args.count = None
    pings_count = args.count
    while pings_count is None or pings_count > 0:
        try:
            print(ping_module.ping())
            if isinstance(pings_count, int): pings_count -= 1  # reduce count by 1
        except KeyboardInterrupt:
            try:
                if ping_module.responses_count >= 1 : ping_module.responses_count -= 1
                ping_module.responses_times.pop(len(ping_module.responses_times) - 1)
            except Exception:
                pass # ignore errors
            break
        except Exception as err:
            print('Error while calling ping: ' + str(err))
    # print statistics to console
    # check if responses more than 1 to calculate statistics
    if ping_module.responses_count >= 1:
        ping_module.statistics()
    # Pause Console Until any key is pressed
    try:
        if not args.pause:
            print(Style.RESET_ALL, end="\n")
            os.system('pause')
    except Exception as err:
        print(str(err))


def parsing_config():
    # Initialize parser
    parser = argparse.ArgumentParser(prog='_Ping', prefix_chars='-', description='Sample Use: _Ping [Hosname or IP]')
    parser.add_argument('target_name', help='IP Address or hostname.')
    parser.add_argument('-title', '-t', dest='title', nargs='+', metavar='', help='Set Console Window Title.', type=str)
    parser.add_argument('-c', '-count', dest='count', help='Number of echo requests to send.', metavar='', type=int, default='0')
    parser.add_argument('-n', '-number', dest='count', help='Number of echo requests to send.', metavar='', type=int, default='0')
    parser.add_argument('-th', '-threshold', dest='threshold', help='Maximum ping threshold (to be colorized).', metavar='', type=int, default='400')
    parser.add_argument('-w', '-wait', dest='wait', help='Timeout in milliseconds to wait for each reply.', metavar='', type=int,
                        default='4000')
    parser.add_argument('-l', '-buffer', dest='buffer', help='Send buffer size.', metavar='', type=int,
                        default='32')
    parser.add_argument('-p', '-pause', dest='pause', help='Disable Pause after script exit.', action='store_true')
    parser.add_argument('-log', '-LOG', dest='log', help='Enable saving ping log to file (Default at user\\Documents\\_Ping_Logs)',
                        action='store_true')
    parser.add_argument('-path', '-LogPath', dest='LogPath', help='Path to ping log file', type=str, default=None)
    parser.parse_args()
    try:
        args, extra = parser.parse_known_args()
        # check if timeout more than 0
        if args.wait <= 0: #ignore if time is less or equal 0
            timeout = 3000
        else:
            timeout = args.wait
        args.wait = timeout
    except Exception as e:
        print('Error While loading Parser Module:\n' + str(e))
    return args


def run_logger(args):
    filename = datetime.now().strftime("%Y%m%d-%H%M%S") + f' {args.target_name}.log'
    if args.LogPath:
        if not os.path.exists(args.LogPath):
            try:
                os.mkdir(args.LogPath)
            except Exception as err:
                print(str(err))
        if os.path.exists(args.LogPath):
            sys.stdout = Logger(log=True, path=args.LogPath, filename=filename)
    else:
        sys.stdout = Logger(log=True, filename=filename)


class _Ping:
    def __init__(self, hostname=None, title=None, count=0, threshold=400, timeout=4000, buffer=32, pause=False, interval=0.9):
        # check that buffer size is valid between 0 and 65500
        if buffer < 0 or buffer > 65500:
            print('Bad value for option -l, valid range is from 0 to 65500.')
            sys.exit(1)
        # Set Window Title if title value not None
        if title:
            # set custom title
            os.system(f'title {" ".join(title).title()}')
        else:
            # set title same as command requested
            os.system(f'title ' + '_ping ' + ' '.join(sys.argv[1:]))
        # Resolve IP to Address
        try:
            self.ip = socket.gethostbyname(hostname)
        except Exception as err:
            print(str(err))
            sys.exit(1)

        ####______________________________________________________________________________
        self.response_time = 0  # last response time, used to colorise input and compare it to threshold
        self.responses_times = []  # All Responses to Calculate avreage at the end
        self.responses_count = 0  # all responses count to calculate average
        self.lost_response_count = 0  # all lost responses count to calculate average
        self.response_min = 0  # Lowest response time
        self.response_max = 0  # Highest response time
        self.response_avg = 0  # sum of responses divided by its count
        self.hostname = hostname
        self.timeout = timeout
        self.buffer = buffer
        self.threshold = threshold
        self.count = count
        self.pause = pause
        self.interval = interval  # interval between each ping request is set to 0.9 Second
        #####_______________________________________________________________________________
        # Print First Line (Pinging google.com [142.250.75.238] with 32 bytes of data:)
        print(f'Pinging {self.hostname} [{self.ip}] with {str(self.buffer)} bytes of data:')

    def ping(self):
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S") + ' '
        process = subprocess.run(["ping", self.ip, "/n", "1", "/w", str(self.timeout), "/l", str(self.buffer)], stdout=subprocess.PIPE)
        # # # --------- Try to decode stdout --------- # # #
        try:
            stdout = process.stdout.decode('utf-8').strip().split('\n')
        except Exception as err:
            print('stdout error: ' + str(err))
            stdout = process.stdout
        result = stdout[1]

        # # # --------- Find Response Time --------- # # #
        try:
            find_res_time = re.search(r"time.(\d+)ms", result)
            self.responses_count += 1  # no matter what and respones count will be increased weather its Response or Timed Out
            if find_res_time:
                self.response_time = int(find_res_time.group(1))  # set response time to \d+
                self.responses_times.append(self.response_time)  # add response time to the responses List
                time.sleep(self.interval)  # time between 2 pings
            else:
                # if Request timed not in line, it will be TTL expire or any other error
                if 'Request timed' not in result:
                    time.sleep(self.interval)
                self.response_time = None
                self.lost_response_count += 1  # if response time is not found add 1 to lost

            self.colorize_results()  # call colorize
            return current_time + result
        except Exception as err:
            print(str(err))

    def colorize_results(self):
        if self.response_time is not None and self.response_time > self.threshold:
            print(Fore.LIGHTGREEN_EX + Back.BLACK, end="")
        elif self.response_time is not None and self.response_time < self.threshold:
            print(Style.RESET_ALL, end="")
        else:
            print(Style.DIM + Fore.GREEN + Back.BLACK, end="")

    def statistics(self):
        # Edit Color to Green
        print(Fore.LIGHTGREEN_EX + Back.BLACK, end="")
        if len(self.responses_times) > 0 and sum(self.responses_times) > 0:  # check if there any valid ping before calulating avg
            self.response_min = min(self.responses_times)  # set lowest response
            self.response_max = max(self.responses_times)  # set highest response
            self.response_avg = int(sum(self.responses_times) / len(self.responses_times))  # calculate average
        else:
            self.response_min = 0
            self.response_max = 0
            self.response_avg = 0
        # 'Ping statistics for x.x.x.x:
        print(f'Ping statistics for {self.hostname}')
        fail_percent = round((self.lost_response_count / self.responses_count) * 100, 1)
        # Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)
        print(
            f'    Packets: Sent = {str(self.responses_count)}, Received = {str(len(self.responses_times))}, Lost = {str(self.lost_response_count)} ({str(fail_percent)}% loss)')
        # Approximate round trip times in milli-seconds:
        print('Approximate round trip times in milli-seconds:')
        # Minimum = 59ms, Maximum = 937ms, Average = 492ms
        print(f'    Minimum = {str(self.response_min)}ms, Maximum = {str(self.response_max)}ms, Average = {str(self.response_avg)}ms')


class Logger(object):
    def __init__(self, log=False, path=None, filename="logfile.log"):
        self.terminal = sys.stdout
        self.log = log
        if path and os.path.exists(path):
            self.file = os.path.join(path, filename)
        else:
            user_profile = os.getenv('UserProfile')
            ping_logs_path = os.path.join(user_profile, "Documents", '_Ping_Logs')
            if not os.path.exists(ping_logs_path): os.mkdir(ping_logs_path)  # create folder if it not exists
            self.file = os.path.join(ping_logs_path, filename)

    def write(self, message):
        self.terminal.write(message)

        if self.log:
            try:
                with open(self.file, 'a') as file:
                    # remove unwanted outputs from log file
                    if message.strip() != '' and len(message.strip()) > 16:
                        file.write(message.strip() + '\n')
            except Exception as e:
                self.terminal.write(str(e))

    def flush(self):
        # this flush method is needed for python 3 compatibility.
        # this handles the flush command by doing nothing.
        # you might want to specify some extra behavior here.
        pass


if __name__ == '__main__':
    main()
