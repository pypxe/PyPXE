'''

This file contains helper functions used throughout the PyPXE services

'''

import os.path
import logging

class PathTraversalException(Exception):
    pass

def normalize_path(base, filename):
    '''
        Join and normalize a base path and filename.

       `base` may be relative, in which case it's converted to absolute.

        Args:
            base (str): Base path
            filename (str): Filename (optionally including path relative to
                            base)

        Returns:
            str: The joined and normalized path

        Raises:
            PathTraversalException: if an attempt to escape the base path is
                                    detected
    '''
    abs_path = os.path.abspath(base)
    joined = os.path.join(abs_path, filename)
    normalized = os.path.normpath(joined)
    if normalized.startswith(os.path.join(abs_path, '')):
        return normalized
    raise PathTraversalException('Path Traversal detected')

def get_child_logger(logger, name):
    '''
        Get a descendant of an existing Logger.

        This only exists because logger.getChild isn't in Python 2.6.

        Args:
            logger (Logger): Parent logger to create descendant of
            name (str): Name to append to parent's name

        Returns:
            Logger: new Logger with `name` appended
    '''
    return logging.getLogger("{0}.{1}".format(logger.name, name))
