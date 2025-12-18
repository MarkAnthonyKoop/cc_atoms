
Create a tool that logs a claude code session.    Do research to see if there are already tools available that you can leverage, and if so document them and exit so I can review them.

If there are not adequate tools already available:

1.  review the format in ~/.claude/projects.
2.  create a tool that by default exgtracts the conversation for the current directory
     (for example  for this session you should be able to find it in .claude/projects/-cc_atoms-tools-session_logger...)
3.  create a directory called session_logs in the current directory and provide the session details in <session_description>_<session_id>.log
4.  it should be human readable and include meta data and each turn of the conversion

test it thoroughly!
