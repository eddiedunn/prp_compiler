# Root Cause Analysis (RCA) Pattern for Debugging

## 1. Understand and Reproduce the Issue

- **Symptom:** What is the exact error message or incorrect behavior observed? (e.g., "`TypeError: 'NoneType' object is not iterable`")
- **Context:** Where and when does it happen? (e.g., "In the `process_data` function when the input from the API is empty.")
- **Replication Steps:** Provide a minimal, reliable set of steps to trigger the bug. 
    1. Start the application.
    2. Call the `/api/v1/data` endpoint with an empty payload `{}`.
    3. Observe the 500 server error and check the logs for the TypeError.
- **Expected Behavior:** What should have happened instead? (e.g., "The API should return a 400 Bad Request with a clear error message.")

## 2. Gather Evidence (Isolate the Fault)

- **Logs:** Collect relevant application logs, server logs, and stack traces. The stack trace is critical for identifying the exact line of failure.
- **Code Review:** Examine the code pointed to by the stack trace. Look at the functions involved, variable assignments, and control flow.
- **Hypothesis Formulation:** Based on the evidence, form a clear hypothesis. (e.g., "Hypothesis: The `api_data` variable is `None` because the external API is returning an empty response, and there is no null check before the code attempts to iterate over it.")

## 3. Test the Hypothesis

- **Unit/Integration Test:** Write a failing test that specifically reproduces the bug. This confirms your understanding and will prevent regressions.
    ```python
    def test_process_data_handles_none_input():
        # This should not raise a TypeError
        result = process_data(None)
        assert result is None # Or some other expected outcome
    ```
- **Debugger:** Use a debugger to step through the code execution. Inspect the state of variables at each step to confirm your hypothesis.
- **Temporary Logging:** Add print statements or enhanced logging to trace the value of the variable in question through the call stack.

## 4. Identify the Root Cause

Once the hypothesis is confirmed, state the root cause clearly. Distinguish it from the symptom.

- **Symptom:** `TypeError` on line 42 of `data_processor.py`.
- **Root Cause:** Lack of input validation. The system does not properly handle cases where the external data source provides a null or empty payload, leading to a downstream processing error.

## 5. Propose and Implement a Fix

- **The Fix:** Describe the code change required. (e.g., "Add a guard clause at the beginning of `process_data` to check if the input is `None` and return early or raise a specific `ValueError`.")
- **Code Change:**
    ```python
    def process_data(data):
        if data is None:
            # Handle the case gracefully
            return None 
        # ... rest of the function
    ```
- **Verification:** Run the failing test you wrote earlier. It should now pass. Run the full test suite to ensure no new issues were introduced (regression testing).

## 6. Document and Communicate

- **Pull Request Description:** Clearly explain the bug, the root cause, and the fix in the pull request.
- **Code Comments:** Add comments to the code if the fix is non-obvious.
- **Post-Mortem (for critical issues):** Document what was learned and what process changes could prevent similar bugs in the future.
