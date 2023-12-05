from enum import Enum
from decouple import config

class LogLevel(Enum):
    DEBUG = 1
    INFO = 2
    MINOR_WARN = 3
    SEVERE_WARN = 4
    ERROR = 5
    CRITICAL_INFO = float('inf')

class Logger:
    calling_class = None
    def __init__(self, caller):
        self.calling_class = caller

    def log(self, log_level, msg):
        '''
        If the log level is equal to or greater than the global config for logging, 
        print the message with an appropriate prefix
        '''
        if log_level.value >= int(config('LOG_LEVEL')):
            premsg = ''
            if (log_level == LogLevel.DEBUG):
                premsg = "\033[90mDebug (" + self.calling_class + "):\t"
            if (log_level == LogLevel.INFO):
                premsg = "\033[37mInfo (" + self.calling_class + "):\t"
            if (log_level == LogLevel.MINOR_WARN):
                premsg = "\033[35mWarn (" + self.calling_class + "):\t"
            if (log_level == LogLevel.SEVERE_WARN):
                premsg = "\033[93mWarn (" + self.calling_class + "):\t"
            if (log_level == LogLevel.ERROR):
                premsg = "\033[91mError (" + self.calling_class + "):\t"
                print(premsg, msg, '\033[0m', flush=True)
                exit(1)
            if (log_level == LogLevel.CRITICAL_INFO):
                premsg = "\033[36mInfo (" + self.calling_class + "):\t"
            print(premsg, msg, '\033[0m', flush=True)
