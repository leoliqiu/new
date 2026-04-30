You are a senior software architect and refactoring engineer.

Goal:
Break down this monolithic code file into a clean, structured multi-file project without changing the existing behavior.

Important rules:
1. Do not rewrite business logic unless absolutely necessary.
2. Preserve all existing function names, class names, inputs, outputs, and behavior.
3. Split the code based on responsibility.
4. Avoid circular imports.
5. Keep the code easy to test and maintain.
6. Add clear file names and folder structure.
7. Explain what moved where.
8. If something is risky to move, flag it before changing it.
9. Create or update imports correctly.
10. Keep backward compatibility where possible.

Process:
Step 1: Analyze the monolith and identify logical areas:
- configuration
- constants
- models / data classes
- utilities / helpers
- API routes / controllers
- business logic / services
- database / repository layer
- UI / CLI layer
- test execution logic
- logging
- error handling

Step 2: Propose a target folder structure before making code changes.

Step 3: Create a migration plan:
- which functions/classes move to which files
- what imports need to change
- what dependencies exist
- any possible circular import risks

Step 4: Refactor the code into multiple files.

Step 5: Provide the final project tree.

Step 6: Provide the full content of each new file.

Step 7: Provide validation steps:
- how to run the application
- how to run tests
- what behavior should remain the same
