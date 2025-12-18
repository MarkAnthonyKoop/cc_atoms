# Review Request for cc_atoms Conversation

Please paste this into the cc_atoms conversation:

---

I have a detailed specification for refactoring cc_atoms to make atom orchestration **embeddable** as a library, while maintaining 100% backward compatibility with the existing CLI.

**Background:** I'm building a GUI automation tool that needs atom's iteration/retry/context logic internally. Rather than duplicating that logic, I want to extract cc_atoms' core orchestration into reusable components (`atom_core`). This will allow any tool or project to embed atom capabilities without users needing to know about atoms.

**The Spec:** Please review `CC_ATOMS_REFACTOR_SPEC.md` in this directory.

**Key Changes Proposed:**
1. Extract core logic from `atom.py` into `atom_core/` package (runtime, retry, context, prompt loading)
2. Add tool/prompt search paths to support project-local tools (`.atom_tools/`)
3. Refactor `atom.py` to use `atom_core` - **same behavior, cleaner code**
4. Create example `gui_control` tool demonstrating embedded usage

**Critical Questions:**
1. Does this architecture make sense for cc_atoms' design philosophy?
2. Are there atom patterns this won't support?
3. Is the `AtomRuntime` API intuitive?
4. Does the tool/prompt search path mechanism work?
5. Any backward compatibility concerns?
6. Is the migration path reasonable?
7. What tests would give you confidence this works?

**Important:** The existing atom CLI behavior stays **identical**. All existing atoms, tools, and prompts continue working exactly as they do now. This is purely extracting reusable components and adding optional embedded usage.

**Next Steps:** If you approve the design, I'll implement it in another conversation that has full context on both cc_atoms architecture and the GUI automation use case. You can then validate the implementation.

Please review the spec and let me know your thoughts, concerns, or suggestions.

---
