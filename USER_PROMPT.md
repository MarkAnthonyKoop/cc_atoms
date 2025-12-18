
modify atom.py to make the following enhancements and refactors:

1.  all the code in main before the iteration loop should be refactored into one or more helper functions
2.  add a feature that extracts the system file based on the name of the .py file:
      eg if the .py file is called atom_my_tool.py it should use ATOM_MY_TOOL.md as the system prompt.
      also, if it starts with "atom" it should also include ATOM.md before (eg) ATOM_MY_TOOL.md

