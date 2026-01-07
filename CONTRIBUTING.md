# Contributing to Raspberry Pi Digital Clock

Thank you for your interest in contributing to the Raspberry Pi Digital Clock project! This document provides guidelines for contributing to the project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description** of the issue
- **Steps to reproduce** the problem
- **Expected behavior** vs actual behavior
- **Screenshots** if applicable
- **Environment details**:
  - Raspberry Pi model
  - balena.io version
  - Python version
  - Relevant configuration settings
- **Log output** from balena dashboard or terminal

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:

- **Clear description** of the enhancement
- **Use case** - why would this be useful?
- **Possible implementation** approach (if you have ideas)
- **Mockups or examples** if applicable

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the code style guidelines
3. **Test your changes** thoroughly
4. **Update documentation** if needed
5. **Write clear commit messages**
6. **Submit a pull request**

## Development Setup

### Local Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/rpi-digital-clock.git
cd rpi-digital-clock

# Install dependencies
pip install -r requirements.txt

# Copy example config
cp .env.example .env
# Edit .env with your settings

# Run locally (may have limited functionality on non-RPi systems)
cd app
python main.py
```

### Testing on Raspberry Pi

For full testing, deploy to a Raspberry Pi using balena.io:

```bash
# Login to balena
balena login

# Push to your balena fleet
balena push YOUR_APP_NAME
```

## Code Style Guidelines

### Python Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and concise
- Use type hints where appropriate

Example:
```python
def calculate_brightness(hour: int, config: dict) -> float:
    """
    Calculate display brightness based on time of day.
    
    Args:
        hour: Current hour (0-23)
        config: Configuration dictionary
    
    Returns:
        Brightness value between 0.0 and 1.0
    """
    # Implementation here
    pass
```

### Documentation Style

- Use clear, concise language
- Include code examples where helpful
- Keep README.md updated with new features
- Update CHANGELOG.md for all notable changes

### Commit Message Guidelines

Use clear, descriptive commit messages:

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Formatting, missing semicolons, etc.
- **refactor**: Code restructuring
- **test**: Adding tests
- **chore**: Maintenance tasks

Examples:
```
feat: Add support for multiple timezones
fix: Resolve weather API timeout issue
docs: Update installation instructions
```

## Project Structure

```
rpi-digital-clock/
├── app/
│   ├── main.py          # Entry point
│   ├── clock_ui.py      # UI logic
│   ├── weather.py       # Weather service
│   ├── utils.py         # Utilities
│   ├── config.yaml      # Default config
│   └── start.sh         # Startup script
├── Dockerfile.template  # balena Dockerfile
├── docker-compose.yml   # Service definition
├── requirements.txt     # Python deps
└── README.md           # Main docs
```

## Adding New Features

When adding a new feature:

1. **Check existing issues** - maybe someone is already working on it
2. **Create an issue** describing the feature
3. **Discuss the approach** before implementing
4. **Write tests** if applicable
5. **Update documentation**
6. **Add to CHANGELOG.md**

### Feature Checklist

- [ ] Code implements the feature correctly
- [ ] Feature is configurable via config.yaml
- [ ] Environment variables supported where appropriate
- [ ] Error handling is comprehensive
- [ ] Logging is appropriate (INFO for key events, DEBUG for details)
- [ ] Documentation is updated
- [ ] README.md reflects new functionality
- [ ] config.yaml has sensible defaults
- [ ] CHANGELOG.md is updated

## Testing Guidelines

### Manual Testing

Test your changes on actual hardware when possible:

- Raspberry Pi Zero (primary target)
- Various display sizes/resolutions
- Different network conditions
- Edge cases (no internet, invalid config, etc.)

### Test Cases to Consider

- Startup behavior
- Screen burn-in prevention features
- Weather API failures
- Configuration validation
- Time synchronization
- Graceful shutdown

## Getting Help

- **Documentation**: Check README.md first
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions
- **balena Forums**: https://forums.balena.io/

## Recognition

Contributors will be acknowledged in:
- CHANGELOG.md for specific contributions
- README.md contributors section (for significant contributions)
- GitHub contributors page

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to open an issue with the "question" label if you need clarification on anything!

---

Thank you for contributing to make this project better! 🎉
