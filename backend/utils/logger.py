import logging
import os
import sys

LOG_DIR = "backend/logs"
LOG_FILE = f"{LOG_DIR}/system.log"

def setup_logger(name="IDS_System", log_prefix=None):
    """
    Configures a shared file logger for all processes.
    Output format: [TIME] [PROCESS/PREFIX] [LEVEL] Message
    """
    os.makedirs(LOG_DIR, exist_ok=True)
    
    fmt_str = '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
    if log_prefix:
         fmt_str = f'[%(asctime)s] [{log_prefix}] [%(name)s] [%(levelname)s] %(message)s'

    formatter = logging.Formatter(
        fmt_str,
        datefmt='%H:%M:%S'
    )
    
    file_handler = logging.FileHandler(LOG_FILE, mode='a')
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    logger.propagate = False
        
    root_log = logging.getLogger()
    if not root_log.handlers:
        root_log.addHandler(file_handler)
        root_log.addHandler(console_handler)
        root_log.setLevel(logging.INFO)
        
    return logger

def clear_logs():
    """Wipes the log file for a fresh start."""
    if os.path.exists(LOG_FILE):
        open(LOG_FILE, 'w').close()
