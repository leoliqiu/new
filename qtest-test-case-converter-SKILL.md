---
name: qtest-test-case-converter
description: Convert any test case input, multiple source test cases, Jira story, high-level background, existing Markdown process documentation, scenario, acceptance criteria, user story, bug reproduction flow, requirements text, informal QA notes, or directory of background information into qTest-ready test cases with organized test steps, concrete validations, preconditions, user/login details, qTest parameters, access/setup option tables, workflow option tables, source grouping decisions, and clarification questions for missing information. Use when the user asks to format, rewrite, convert, structure, consolidate, split, parameterize, or prepare test cases for qTest.
---

# qTest Test Case Converter

Convert the user's provided test case input into qTest-ready test case content.

## Core Rules

- Do not invent missing business data, user credentials, environment details, test data, expected values, permissions, statuses, URLs, or application behavior.
- Use only information provided by the user or clearly present in the input.
- If required information is missing, write `Needs clarification` in the relevant field and ask a clarification question after the draft.
- Preserve all meaningful detail from the source input.
- Organize the test case as a logical application process from setup through completion and verification.
- Detect when the input contains multiple source test cases, source flows, examples, scenarios, or expected results.
- Try to group related source test cases into a single qTest test case when one qTest case can cover them cleanly with options, parameters, or workflow tables.
- Split source test cases into separate qTest test cases when they represent independent flows, incompatible outcomes, different business objectives, or would make one qTest case confusing.
- Each test step must complete a concrete unit of work, such as completing a page, completing a form section, submitting a transaction, approving a request, validating a report, or finishing a task.
- Each step must be a complete concept and include as much execution detail as the input supports.
- Avoid overly tiny steps such as single clicks unless the click itself is the concrete business action.
- Avoid merging unrelated workflows into one step unless they are part of the same concrete task.
- Put repeated, branching, multi-user, multi-role, access-management, setup-option, parameter-value, or workflow-option details into tables inside the relevant step.
- Every step must include a validation/expected result that verifies something concrete.
- When qTest parameters and values are provided, check that each parameter used in the test case has provided values, and each provided parameter is either used in the draft or called out as not used.
- When the user provides a directory of background information, inspect the relevant files, summarize the sources used, and use them only as supporting context for the qTest conversion.

## Source Intake and Background Material

The user may provide test case text directly, a Jira story, high-level background, existing Markdown process documentation, upload/source files, or point to a directory containing background information. Use provided background material to build a more complete qTest output.

Supported source types include:

- Jira story title, description, acceptance criteria, business rules, linked defects, comments, labels, components, priority, attachments, or implementation notes
- High-level business or application background
- Existing `.md` process documentation, workflow documentation, role/access documentation, or runbooks
- Requirements, user stories, test cases, QA notes, bug reproduction flows, sample data, parameter lists, or role/access matrices

When a Jira story is provided:

- Use the story summary/title to help name the qTest test case.
- Use the description and acceptance criteria to identify business objective, flow, preconditions, test steps, validations, parameters, and edge cases.
- Use comments, labels, components, linked issues, or attachments only when they are provided and relevant.
- Do not infer implementation behavior from a Jira key or title alone.
- If acceptance criteria are missing, ambiguous, or not testable, mark the missing expected behavior as `Needs clarification`.

When high-level background is provided:

- Use it to understand the application process and terminology.
- Convert only the parts that support concrete test steps or validations.
- Do not turn vague background into specific test data, statuses, permissions, or expected messages unless they are explicitly stated.

When existing Markdown process documentation is provided:

- Read the relevant `.md` files or sections before drafting.
- Use headings, ordered lists, tables, role descriptions, business rules, screenshots with extracted text, and examples to build the qTest process.
- Preserve important process terminology from the documentation.
- Treat Markdown tables as likely sources for access/setup options, parameter values, workflow options, validations, or test data.
- If documentation conflicts with the test case input or Jira story, preserve the conflict as `Needs clarification` and ask which source is authoritative.

When a directory is provided:

- Inspect the directory contents before drafting.
- Prefer relevant files such as Jira exports, requirements, test cases, user stories, acceptance criteria, Markdown process documents, role/access matrices, parameter lists, sample data, and screenshots with extracted text when available.
- Ignore unrelated files unless they appear necessary.
- Track which files or source sections informed the output.
- Do not treat background information as permission to invent values.
- If background files conflict, preserve the conflict as `Needs clarification` and ask a question.
- If the directory is inaccessible, empty, or missing expected background information, say so and continue with the available input.

Include this optional section when background files or multiple source cases are used:

```markdown
### Source Analysis
| Source | Relevant Information Used | Notes |
|---|---|---|
| <Jira story, file, Markdown section, background note, or source case> | <facts used in the qTest draft> | <conflicts, gaps, or mapping notes> |
```

## Multiple Source Test Cases

The input may contain multiple test cases or multiple result outputs. First identify source case boundaries, then decide whether to consolidate or split.

Use one consolidated qTest test case when:

- The source cases test the same business objective.
- The flow is mostly the same and differences can be represented as qTest parameters, access/setup options, data options, or validation options.
- One logical end-to-end qTest case can cover the scenarios without losing clarity.

Split into multiple qTest test cases when:

- The source cases have different business objectives.
- The flows start from different preconditions that cannot reasonably be combined.
- The outcomes are mutually exclusive and cannot be represented as options.
- Combining them would create an unclear, overly broad, or hard-to-run qTest case.

When making the decision, include a short grouping note:

```markdown
### Source Grouping Decision
<Consolidated into one qTest test case because...>
```

or:

```markdown
### Source Grouping Decision
<Split into separate qTest test cases because...>
```

When split is required, repeat the required qTest output structure for each test case.

## Required qTest Output Structure

Use this structure unless the user provides a different qTest template:

```markdown
## Test Case: <clear test case name>

### Source Analysis
<include when background files or multiple source cases are used; otherwise omit>

### Source Grouping Decision
<include when multiple source cases are consolidated or split; otherwise omit>

### Description
<brief description of the full test case purpose and business process>

### Preconditions
<required setup, system state, permissions, data, feature flags, integrations, or environment>

### Login / User Details
| User / Role | Purpose in Test Case | Required Access or Permissions | Known Login Details |
|---|---|---|---|
| <role or user> | <what this user performs> | <access needed> | <provided login details or Needs clarification> |

### Access / Setup Options
| Option | User / Role | Setup Steps | Access Management Option | When to Use This Option | Notes |
|---|---|---|---|---|---|
| <option name> | <user or role> | <setup required or Needs clarification> | <access option or Needs clarification> | <condition for running this option> | <provided notes> |

### qTest Parameters
| Parameter | Values Provided | Used In | Parameter Check |
|---|---|---|---|
| <parameter name> | <provided values or Needs clarification> | <section, option, or step where used> | <Verified, Needs clarification, or Provided but not used> |

### Test Data
| Data Item | Value | Source / Notes |
|---|---|---|
| <data item> | <provided value or Needs clarification> | <where it came from or why needed> |

### qTest Steps
| Step # | Step | Validation / Expected Result |
|---:|---|---|
| 1 | <complete concrete action or task> | <specific observable result to verify> |
```

If there are no special preconditions, user details, access/setup options, qTest parameters, or test data in the input, include the section and write `None specified`.

## qTest Parameters

Use qTest parameters when the input provides parameter names, value lists, or reusable test values that should be fed into the test case.

- Preserve the parameter names and value lists exactly as provided.
- Do not create new parameter names or values unless the user explicitly asks for suggested parameters.
- If the input uses a specific parameter notation, preserve that notation in the test steps.
- If the input provides parameter names without notation, list the parameter in `qTest Parameters` and refer to it clearly in the steps.
- Check every parameter referenced in the description, preconditions, option tables, test data, steps, and validations.
- Check every provided parameter and value list before finalizing the draft.
- Mark a parameter as `Verified` only when it has provided values and is used in the draft.
- Mark a parameter as `Needs clarification` when the parameter is referenced but no value list is provided, or when values are ambiguous.
- Mark a parameter as `Provided but not used` when the user provided it but the draft does not require it.
- Ask clarification questions for missing values, unclear parameter meaning, conflicting values, or parameter/value lists that do not match the process.

When parameters create different ways to run the same test case, show them in an option table instead of writing separate duplicate steps.

Example qTest parameter table:

```markdown
| Parameter | Values Provided | Used In | Parameter Check |
|---|---|---|---|
| UserRole | Requester, Approver, Admin | Access / Setup Options; Steps 1-4 | Verified |
| AccessType | Read Only, Edit, Approve | Access / Setup Options | Verified |
| AccountId | Needs clarification | Test Data; Step 1 | Needs clarification |
```

## Step Construction

For each qTest step:

- Start with an action verb.
- Describe the role/user performing the action when multiple users are involved.
- Include navigation, inputs, selections, submitted values, and relevant system state when provided.
- Keep the step focused on a complete task or page-level outcome.
- Include embedded tables when the step contains multiple fields, validations, users, branches, roles, access options, setup options, parameter values, workflow stages, or repeated actions.
- Use the validation column to confirm a concrete outcome, not a vague statement.

Good step pattern:

```markdown
| 3 | As the Approver, review the submitted request on the approval page and complete the approval decision using the provided approval data:<br><br>| Field | Value |<br>|---|---|<br>| Decision | Approve |<br>| Comment | Needs clarification | | The request status changes to `Approved`, the approval comment is saved, and the request is available for the next workflow stage. |
```

Poor step pattern:

```markdown
| 3 | Click Approve. | Works as expected. |
```

## Multi-User and Multi-Workflow Handling

When multiple users, roles, or logins are involved:

- Include all users in `Login / User Details`.
- Identify which user performs each step.
- Use `Needs clarification` for missing usernames, roles, permissions, or login details.
- Do not create fictional users or credentials.

When multiple users have different setup steps or access-management choices:

- Add an `Access / Setup Options` table.
- Show the available options for running the same test case.
- Include the user/role, setup steps, access-management option, parameter values if applicable, and when that option should be used.
- Keep the main qTest steps focused on the process, and reference the selected option or parameter rather than duplicating the same process for each access variant.
- If a required option is named but its setup or access details are missing, use `Needs clarification`.

Example access/setup option table:

```markdown
| Option | User / Role | Setup Steps | Access Management Option | qTest Parameter Values | When to Use This Option |
|---|---|---|---|---|---|
| Requester Standard Access | Requester | User is active and assigned requester permissions. | Standard requester access | UserRole = Requester; AccessType = Standard | Run when validating normal request submission. |
| Approver Elevated Access | Approver | User is active and assigned approval queue access. | Approval permission enabled | UserRole = Approver; AccessType = Approval | Run when validating approval workflow. |
| Admin Access Review | Admin | Needs clarification | Admin access management option | UserRole = Admin; AccessType = Needs clarification | Run when validating access-management behavior. |
```

When multiple workflows or process paths are present:

- Keep the main qTest steps in logical execution order.
- Use tables inside steps to show workflow-specific options, parameter values, actions, or validations.
- Split into separate test cases only when the workflows are independent or cannot be executed as one coherent scenario.
- If unsure whether to split or combine workflows, create the best draft and ask a `qTest structure` clarification question.

Example option table inside a step:

```markdown
| Run Option | User / Role | Parameter Values | Action Details | Validation |
|---|---|---|---|---|
| Submission path | Requester | UserRole = Requester | Submit the completed request. | Request is created and assigned a submitted status. |
| Approval path | Approver | UserRole = Approver | Review and approve the request. | Request moves to approved status. |
| Fulfillment path | Processor | UserRole = Processor | Complete fulfillment. | Request is marked fulfilled/complete. |
```

## Preconditions

Include preconditions when the input implies setup is required before execution. Preconditions may include:

- User accounts, roles, permissions, or login access
- Existing records, customers, orders, claims, policies, projects, or other application data
- Required configuration, feature flags, workflows, integrations, queues, or notifications
- Required system state, environment, browser, device, or test region
- Prior approvals, completed forms, uploaded documents, or submitted transactions

If a precondition appears necessary but is not specified, write it with `Needs clarification`.

## Validation Column

Every validation must verify a concrete result of the step. Validations may check:

- Page, screen, or component loaded
- Record created, updated, submitted, approved, rejected, canceled, or deleted
- Status, field value, calculation, message, notification, audit log, or assignment changed
- Required validation error shown
- Data persisted after refresh or navigation
- Correct user or role can or cannot perform the action
- Downstream workflow, queue, report, document, or integration result appears

Do not use vague validations such as:

- `Verify success`
- `Works correctly`
- `System behaves as expected`
- `User can proceed`

Replace vague validations with specific observable outcomes using only known information. If the exact expected outcome is missing, write `Needs clarification`.

## Clarification Questions

After producing the qTest draft, include a `Clarifications Needed` section if any required detail is missing or if there is ambiguity.

Group questions by type:

```markdown
### Clarifications Needed

#### qTest Structure
- Should the approval and fulfillment workflows be one end-to-end test case or separate qTest test cases?
- Should source test cases A and B be consolidated into one qTest case, or should they remain separate because they represent different business flows?

#### Step Process
- What exact status should display after the requester submits the form?

#### Users / Login
- Which user account or role should execute the approval step?

#### Access / Setup Options
- Which access-management option should be used for the Admin run option?

#### qTest Parameters
- What values should be provided for the `AccountId` parameter?
- Should the provided `Region` parameter be used in this test case?

#### Test Data
- What customer/account/order data should be used for this test?

#### Validation
- What confirmation message or final record status should be verified after submission?

#### Other Process
- Are there any environment, integration, or notification requirements for this scenario?
- Which files in the provided background directory should be treated as authoritative if sources conflict?
- Should the Jira story acceptance criteria or the Markdown process documentation be treated as authoritative where they differ?
```

Only ask questions that are actually needed. Do not ask for information already provided.

## Final Output Behavior

- First provide the converted qTest draft.
- Then provide clarification questions, if needed.
- If no clarification is needed, state: `No clarifications needed based on the provided input.`
- Keep the output ready for copy into qTest or qTest import preparation.
