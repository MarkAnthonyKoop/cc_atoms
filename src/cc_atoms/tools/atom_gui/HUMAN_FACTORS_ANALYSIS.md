# Human Factors Analysis: Prompt and Completion Editing

## Overview

This document analyzes the user experience (UX) and human factors considerations for editing prompts and completions in the Atom GUI.

## Current Workflow

### 1. Finding and Selecting a Prompt

**Current Implementation**:
1. User navigates hierarchical tree: `cc_atoms` → `tools` → `atom_gui`
2. Expands session to see prompts (👤 user, 🤖 assistant)
3. Clicks on a prompt to select it

**Human Factors**:
- ✅ **Visual hierarchy** makes navigation intuitive
- ✅ **Icons (👤/🤖)** clearly distinguish user vs assistant prompts
- ✅ **Preview text** (80 chars) helps identify specific prompts
- ⚠️ **Long sessions** with many prompts require scrolling
- ⚠️ **No search function** to quickly find specific prompts

**Cognitive Load**: **Low to Medium**
- Easy for small sessions (< 20 prompts)
- Moderate for large sessions (20-100 prompts)
- High for very large sessions (100+ prompts)

### 2. Understanding What You're Editing

**Current Implementation**:
- Automatic switch to "Edit Prompt" tab
- Label shows: "Editing: User Prompt" or "Editing: Assistant Response"
- Color coding: Blue for user, Green for assistant
- Full prompt content displayed in editable text area

**Human Factors**:
- ✅ **Clear labeling** of prompt type
- ✅ **Color coding** provides quick visual confirmation
- ✅ **Automatic tab switch** reduces navigation steps
- ✅ **Full context** available in adjacent tabs (README, Session Log)
- ⚠️ **No indication of prompt position** in conversation (e.g., "Prompt 5 of 27")
- ⚠️ **No preview of surrounding context** (previous/next prompts)

**Cognitive Load**: **Low**
- Clear and unambiguous what's being edited

### 3. Editing Process

**Current Implementation**:
- Standard scrolled text widget with:
  - Cut/Copy/Paste buttons
  - Built-in undo/redo (Ctrl+Z, Ctrl+Y)
  - Insert Image button
  - Monospace font (Courier 9pt)

**Human Factors**:

**Strengths**:
- ✅ **Familiar editing interface** (standard text editor controls)
- ✅ **Explicit buttons** for common operations (no need to remember shortcuts)
- ✅ **Image insertion** supported (though as text references, not visual)
- ✅ **Monospace font** good for code snippets
- ✅ **Word wrap** enabled for readability

**Weaknesses**:
- ⚠️ **No syntax highlighting** for code blocks
- ⚠️ **No markdown preview** while editing
- ⚠️ **Image references** shown as text, not actual images
- ⚠️ **No spell check** for prose content
- ⚠️ **Cut/Copy/Paste buttons redundant** (keyboard shortcuts work anyway)
- ⚠️ **No line numbers** or length indicators
- ⚠️ **No auto-save** or draft saving

**Cognitive Load**: **Low to Medium**
- Low for simple text edits
- Medium for complex multi-paragraph rewrites
- Medium for edits with code formatting

### 4. Save Confirmation

**Current Implementation**:
1. User clicks "Save Edits" button
2. Dialog box asks: "This will modify the Claude Code session JSONL file. The changes will affect the original session data. Do you want to save?"
3. Options: Yes/No
4. If Yes: Saves to JSONL, shows success message
5. Asks: "Save successful! Extract updated session log?"

**Human Factors**:

**Strengths**:
- ✅ **Clear warning** about permanent changes
- ✅ **Explicit confirmation** prevents accidental saves
- ✅ **Status feedback** (blue during save, green on success, red on failure)
- ✅ **Option to refresh** session log after save

**Weaknesses**:
- ⚠️ **Two confirmation dialogs** (save + refresh) is one too many
- ⚠️ **No preview of changes** before saving (no diff view)
- ⚠️ **No "Save As" option** for experimental edits
- ⚠️ **Destructive by default** (no automatic backup)
- ⚠️ **No batch save** for multiple edits

**Risk Assessment**:
- **High**: Modifying JSONL directly affects Claude Code sessions
- **Medium**: Undo feature provides safety net
- **Low**: Confirmation dialog prevents accidental saves

**Cognitive Load**: **Medium**
- Need to understand JSONL implications
- Need to decide about refresh option
- Interrupts workflow with multiple dialogs

### 5. Undo/Redo System

**Current Implementation**:
- Unlimited depth history
- Undo/Redo buttons in toolbar
- History position indicator (e.g., "History: 3/5")
- Buttons disabled when unavailable
- Each undo/redo asks to refresh session log

**Human Factors**:

**Strengths**:
- ✅ **Unlimited history** removes artificial constraints
- ✅ **Visual feedback** (disabled buttons, position counter)
- ✅ **Persistent across sessions** (as long as GUI is open)
- ✅ **Clear state indication** (can't undo/redo when unavailable)

**Weaknesses**:
- ⚠️ **No history browser** to see what each undo level contains
- ⚠️ **No textual description** of each edit (e.g., "Edited prompt 5")
- ⚠️ **Branching history not supported** (undoing discards future history)
- ⚠️ **Dialog for each undo/redo** asking about refresh is annoying
- ⚠️ **History lost on GUI restart** (not persistent to disk)
- ⚠️ **No keyboard shortcuts** for undo/redo (only buttons)

**Cognitive Load**: **Medium**
- Position counter helps track depth
- But lack of history browser requires mental tracking of edits
- Multiple dialogs interrupts flow

### 6. Error Handling

**Current Implementation**:
- Error dialogs for:
  - Cannot find JSONL file
  - Cannot find prompt at index
  - File write errors
- Status messages in toolbar
- Red text for errors in editor status bar

**Human Factors**:
- ✅ **Clear error messages** explain what went wrong
- ✅ **Multiple feedback channels** (dialog, status bar, toolbar)
- ⚠️ **No recovery suggestions** (what to do when error occurs)
- ⚠️ **No automatic retry** mechanism
- ⚠️ **Technical jargon** (JSONL, mangled paths) may confuse non-technical users

### 7. Context Preservation

**Current Implementation**:
- Selected session remains highlighted
- Selected prompt remains highlighted
- Current tab remains active
- Scroll position maintained

**Human Factors**:
- ✅ **Selection persistence** prevents disorientation
- ✅ **Scroll position** maintained across tab switches
- ⚠️ **No breadcrumb trail** showing current location
- ⚠️ **No "Back" button** to return to previous selection

## Pain Points and Recommendations

### Critical Issues

1. **Multiple Confirmation Dialogs**
   - **Problem**: Save requires 2 dialogs, undo/redo requires 1 dialog each
   - **Impact**: Interrupts workflow, annoying for frequent edits
   - **Solution**: Combine dialogs, make refresh optional checkbox in save dialog
   - **Solution 2**: Add preferences to disable confirmations

2. **No Diff Preview**
   - **Problem**: Can't see what changed before saving
   - **Impact**: Risk of accidental overwrites
   - **Solution**: Add side-by-side diff view before save confirmation

3. **No Search Function**
   - **Problem**: Finding specific prompts in large sessions is tedious
   - **Impact**: Time-consuming, frustrating for power users
   - **Solution**: Add search box that filters tree view or highlights matches

### Important Issues

4. **No Context Indication**
   - **Problem**: Don't know which prompt # you're editing
   - **Impact**: Easy to lose track in long conversations
   - **Solution**: Add "Prompt 5 of 27" to editor label

5. **No History Browser**
   - **Problem**: Can't see what each undo level contains
   - **Impact**: Hard to undo to specific point
   - **Solution**: Add history panel showing list of edits with descriptions

6. **No Keyboard Shortcuts**
   - **Problem**: Undo/redo require mouse clicks on buttons
   - **Impact**: Slower for keyboard users
   - **Solution**: Add Ctrl+Z/Ctrl+Shift+Z for global undo/redo (separate from text editor undo)

7. **No Auto-save**
   - **Problem**: GUI crash loses unsaved edits
   - **Impact**: Data loss risk
   - **Solution**: Auto-save drafts to temp files

### Nice to Have

8. **No Markdown Preview**
   - **Solution**: Add preview tab showing rendered markdown

9. **No Syntax Highlighting**
   - **Solution**: Detect code blocks and add syntax highlighting

10. **No Spell Check**
    - **Solution**: Integrate spell checker for prose content

## Workflow Efficiency Analysis

### Time to Edit a Single Prompt

**Current Workflow**:
1. Navigate tree: ~3-5 seconds
2. Click prompt: ~1 second
3. Wait for tab switch: ~0.5 seconds
4. Read and edit: ~30-300 seconds (varies)
5. Click Save Edits: ~1 second
6. Confirm save: ~2 seconds
7. Decide on refresh: ~2 seconds
8. Wait for save: ~1 second
9. **Total overhead: ~10-12 seconds** (not counting actual editing time)

**Potential Improvements**:
- Remove refresh dialog: Save 2 seconds
- Combine confirmations: Save 1 second
- Add keyboard shortcut for save: Save 1 second
- **Optimized overhead: ~6 seconds** (40% reduction)

### Time to Edit Multiple Prompts

**Current Workflow** (5 prompts):
- Per-prompt overhead: ~10 seconds
- **Total overhead: ~50 seconds**
- Plus context switching overhead between prompts

**With Batch Editing**:
- Navigate once: ~3 seconds
- Edit all 5: (edit time)
- Batch save: ~5 seconds
- **Total overhead: ~8 seconds** (84% reduction)

## Cognitive Load Summary

| Task | Current Load | Optimal Load | Gap |
|------|--------------|--------------|-----|
| Navigation | Low-Medium | Low | Small |
| Selection | Low | Low | None |
| Editing | Low-Medium | Low | Small |
| Saving | Medium | Low | **Significant** |
| Undo/Redo | Medium | Low | **Significant** |
| Error Recovery | Medium-High | Low | **Large** |

**Overall Assessment**: The editing interface is functional but has significant friction points in the save/undo workflows.

## Usability Heuristics Analysis

### 1. Visibility of System Status
- ✅ Good: Status bar shows current operation
- ✅ Good: Button states show available actions
- ⚠️ Poor: No indication of unsaved changes

### 2. Match Between System and Real World
- ✅ Good: File explorer metaphor for sessions
- ✅ Good: Standard edit controls
- ⚠️ Poor: JSONL terminology unfamiliar to users

### 3. User Control and Freedom
- ✅ Good: Unlimited undo/redo
- ⚠️ Poor: No cancel during save operation
- ⚠️ Poor: No draft mode for experimental edits

### 4. Consistency and Standards
- ✅ Good: Standard GUI controls
- ✅ Good: Consistent color coding
- ⚠️ Poor: Multiple confirmation patterns (some operations ask, some don't)

### 5. Error Prevention
- ✅ Good: Confirmation dialogs
- ⚠️ Poor: No diff preview
- ⚠️ Poor: No automatic backups

### 6. Recognition Rather Than Recall
- ✅ Good: Icons show prompt types
- ✅ Good: Labels show current state
- ⚠️ Poor: No visual indication of modified prompts

### 7. Flexibility and Efficiency of Use
- ⚠️ Poor: No keyboard shortcuts for main operations
- ⚠️ Poor: No batch operations
- ⚠️ Poor: No templates or macros

### 8. Aesthetic and Minimalist Design
- ✅ Good: Clean interface
- ⚠️ Poor: Redundant cut/copy/paste buttons
- ⚠️ Poor: Multiple tabs when single view might suffice

### 9. Help Users Recognize, Diagnose, and Recover from Errors
- ⚠️ Poor: Error messages technical
- ⚠️ Poor: No recovery suggestions
- ⚠️ Poor: No automatic retry

### 10. Help and Documentation
- ⚠️ Poor: No in-app help
- ⚠️ Poor: No tooltips
- ⚠️ Poor: No getting started guide

## Priority Recommendations

### High Priority (Do First)
1. **Combine confirmation dialogs** - Biggest friction point
2. **Add keyboard shortcuts** - Ctrl+S to save, Ctrl+Z/Y for undo/redo
3. **Add unsaved changes indicator** - Asterisk (*) in tab or prompt label
4. **Add prompt position** - "Prompt 5 of 27"

### Medium Priority (Important)
5. **Add diff preview** - Show changes before saving
6. **Add search/filter** - Find prompts quickly
7. **Add history browser** - See list of edits
8. **Improve error messages** - Less technical, more helpful

### Low Priority (Nice to Have)
9. **Add markdown preview** - See formatted output
10. **Add auto-save** - Save drafts periodically
11. **Add tooltips** - Help for all buttons
12. **Add batch operations** - Edit multiple prompts at once

## Accessibility Considerations

### Visual
- ✅ Color coding supplemented with icons
- ⚠️ Font size fixed (no user control)
- ⚠️ No high contrast mode

### Motor
- ⚠️ Requires precise mouse control
- ⚠️ Many buttons instead of keyboard shortcuts
- ✅ Resizable panes for ergonomics

### Cognitive
- ⚠️ Technical terminology (JSONL, mangled paths)
- ⚠️ Multiple dialogs disrupt flow
- ✅ Clear visual hierarchy

## Conclusion

The Atom GUI provides a functional editing interface with good visual design and basic safety features. However, it has significant friction in the save/undo workflows due to multiple confirmation dialogs and lack of keyboard shortcuts. The highest priority improvements are:

1. Streamline confirmation dialogs
2. Add keyboard shortcuts
3. Add diff preview before saving
4. Add search function for large sessions

These changes would reduce workflow overhead by 40-60% and significantly improve the user experience for frequent editors.
