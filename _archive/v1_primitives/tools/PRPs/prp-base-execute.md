---
name: "Execute Base PRP"
description: "Implement a feature by executing a given Base PRP file, including planning, implementation, and validation."
arguments: "$ARGUMENTS"
keywords:
  - prp
  - base
  - execute
  - implement
  - validate
---

# Execute BASE PRP

Implement a feature using the PRP file.

## PRP File: $ARGUMENTS

## Execution Process

1. **Load PRP**
   - Read the specified PRP file
   - Understand all context and requirements
   - Follow all instructions in the PRP and extend the research if needed
   - Ensure you have all needed context to implement the PRP fully
   - Do more web searches and codebase exploration as needed

2. **ULTRATHINK**
   - Ultrathink before you execute the plan. Create a comprehensive plan addressing all requirements.
   - Break down the PRP into clear todos using the TodoWrite tool.
   - Use agents subagents and batchtool to enhance the process.
   - **Important** YOU MUST ENSURE YOU HAVE EXTREMELY CLEAR TASKS FOR SUBAGENTS AND REFERENCE CONTEXT AND MAKE SURE EACH SUBAGENT READS THE PRP AND UNDERSTANDS ITS CONTEXT.
   - Identify implementation patterns from existing code to follow.
   - Never guess about imports, file names funtion names etc, ALWAYS be based in reality and real context gathering

3. ## **Execute the plan**

   ## Execute the PRP step by step
   - Implement all the code

4. **Validate**
   - Run each validation command
   - The better validation that is done, the more confident we can be that the implementation is correct.
   - Fix any failures
   - Re-run until all pass
   - Always re-read the PRP to validate and review the implementation to ensure it meets the requirements

5. **Complete**
   - Ensure all checklist items done
   - Run final validation suite
   - Report completion status
   - Read the PRP again to ensure you have implemented everything

6. **Reference the PRP**
   - You can always reference the PRP again if needed

Note: If validation fails, use error patterns in PRP to fix and retry.
