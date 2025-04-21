# Rules for Development

1. **Language**:
   - All code and comments must be written in English.

2. **Standards**:
   - Code must adhere to Python 3.12 idioms and PEP standards.

3. **Development Process**:
   - Changes to the code must be made iteratively.
   - Each iteration must not "break" the program.

4. **Commit Messages**:
   - Commit messages must be written in English.
   - Follow the format: `<type>: <short description>` (e.g., `feat: add PDF to PNG conversion feature`).
   - Types can include `feat` (feature), `fix` (bug fix), `docs` (documentation), `style` (formatting), `refactor` (code restructuring), `test` (adding tests), and `chore` (maintenance).

5. **Linting and Formatting**:
   - Run the linter (`flake8`) and formatter (`black`, `isort`) before committing code.
   - Ensure no linting errors or warnings are present.

6. **Code Reviews**:
   - All changes must be reviewed by at least one other developer before merging into the main branch.

7. **Testing**:
   - Write unit tests for all new features and bug fixes.
   - Ensure all tests pass before committing.

8. **Branching**:
   - Use a branching strategy such as `feature/<feature-name>` for new features and `bugfix/<bug-name>` for bug fixes.
   - Avoid committing directly to the `main` branch.

9. **Documentation**:
   - Update the `README.md` or other relevant documentation files for any changes that affect usage or setup.

10. **Dependencies**:
    - Add new dependencies to `requirements.txt` or `dev-requirements.txt` and ensure they are pinned to specific versions.

11. **Code Quality**:
    - Avoid introducing commented-out code or unused imports.
    - Write clear and concise comments where necessary.