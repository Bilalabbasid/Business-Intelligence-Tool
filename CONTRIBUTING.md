# Contributing to Business Intelligence Tool

We love your input! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

## Pull Requests

Pull requests are the best way to propose changes to the codebase. We actively welcome your pull requests:

1. Fork the repo and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Issue that pull request!

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report bugs using GitHub's [issue tracker](https://github.com/Bilalabbasid/Business-Intelligence-Tool/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/Bilalabbasid/Business-Intelligence-Tool/issues/new); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Development Setup

1. Fork and clone the repository
2. Install dependencies:
   ```bash
   # Backend
   cd bi_tool
   pip install -r requirements.txt
   
   # Frontend
   cd bi-frontend
   npm install
   ```
3. Set up your development environment (see README.md)
4. Create a feature branch: `git checkout -b my-new-feature`
5. Make your changes and add tests
6. Run tests: `npm test` and `python manage.py test`
7. Commit your changes: `git commit -am 'Add some feature'`
8. Push to the branch: `git push origin my-new-feature`
9. Create a Pull Request

## Code Style

### Python (Backend)
- Follow PEP 8
- Use Black for code formatting
- Use flake8 for linting
- Add type hints where applicable
- Write docstrings for functions and classes

### JavaScript/React (Frontend)
- Use Prettier for code formatting
- Use ESLint for linting
- Follow React best practices
- Use functional components with hooks
- Write meaningful component and variable names

### Git Commit Messages
- Use conventional commit format: `type(scope): description`
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- Keep the first line under 50 characters
- Reference issues and pull requests when applicable

## License

By contributing, you agree that your contributions will be licensed under its MIT License.