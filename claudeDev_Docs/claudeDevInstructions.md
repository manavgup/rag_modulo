# Claude Dev Instructions for rag_modulo

====

CLAUDE DEV PROJECT DEVELOPMENT GUIDELINES

RAPID MVP DEVELOPMENT:
The primary goal is to create a functional Minimum Viable Product (MVP) as quickly as possible. Focus on core features, rapid prototyping, and getting a working product for user feedback. Do not recreate files or directories that already exist.

PREPARATION:
- Read the 'Opening Message for Next Session' in `currentTask.md`
- Review the current sprint document and task from currentTask.md
- Recursively view the project file structure
- Summarize key points from devNotes.md at the start of each new session

DEVELOPMENT PROCESS:
- Follow sprint Design Documents in order, implementing features screen by screen. Users may ask you to create new sprint Documents
- Use claudeDev_docs/wireframes.csv and images in claudeDev_docs/wireframes as primary UI implementation guides
- Adhere to specified tech stack and UI component library. Utilize these components when building.
- Utilize theme file for consistent styling
- After implementing each feature, document the approach in devNotes.md under 'Best Practices'
- Implement and test features in small, incremental steps. Run the development server frequently to verify changes.
- Focus test case generation for rapid MVP development. Implement automated tests for robust, production-ready code.
- Prioritize getting user feedback early and often. Encourage testing of partially completed features to guide development.

TOOLS AND RESOURCES:
- wireframes.csv: Primary source of truth for UI implementation
- claudeDev_docs/wireframes: Directory containing wireframe images
- theme file: For consistent application styling
- devNotes.md: CRUCIAL documentation of development practices, solutions, and error handling

TASKS:
- ALWAYS request wireframe images from the user for the current task
- Regularly start the development server for testing
- Prompt user for feedback after implementing features or making significant changes
- After each significant development step, update devNotes.md with new insights or practices

SESSION MANAGEMENT:
- Update 'Opening Message for Next Session' in `currentTask.md`
- Commit changes: `git add . && git commit -m 'Brief description of changes'`
- Review and update devNotes.md with any new information from the session

ERROR HANDLING:
- When encountering errors:
  1. Check devNotes.md for similar issues and solutions
  2. If new, analyze thoroughly and document in devNotes.md:
     - Error description
     - Solution
     - Prevention steps
  3. Apply the solution and update the code accordingly
  4. Ensure the error and its solution are properly categorized in devNotes.md

CONSISTENCY MAINTENANCE:
- Regularly review the entire project for consistency with guidelines in devNotes.md
- Update devNotes.md with any new best practices or style guidelines discovered during development
- Ensure all new code adheres to the documented best practices and style guidelines

COMPLETION CRITERIA:
- Meet all criteria in current sprint document before proceeding
- Ensure all required dependencies are correctly installed
- Update currentTask.md at the end of every session
- Review and update devNotes.md with any new information, best practices, or error solutions from the completed task

NOTE: The devNotes.md file is critical for maintaining consistent development practices and solving recurring issues. Always prioritize its use and keep it updated throughout the development process.

====

Note: Some setup steps, like database configuration, will be handled by the user outside of this environment.