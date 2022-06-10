import re

def run_once(f):
	def wrapper(*args, **kwargs):
		if not wrapper.has_run:
			wrapper.has_run = True
			return f(*args, **kwargs)
	wrapper.has_run = False
	return wrapper

def _mysql_escape_characters(match):
    char = match.group()

    escapes = {
        "\0": "\\0",
        "\x08": "\\b",
        "\x09": "\\t",
        "\x1a": "\\z",
        "\n": "\\n",
        "\r": "\\r",
        "\"": "\\\"",
        "'": "\\'",
        "\\": "\\\\",
        "%": "\\%"
    }

    return escapes.get(char, char)

def mysql_escape_string(string):
    return re.sub(r"[\0\x08\x09\x1a\n\r\"\'\\\%]", _mysql_escape_characters, string)
