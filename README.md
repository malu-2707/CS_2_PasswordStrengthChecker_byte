# Password Strength Checker

## Project Overview

The Password Strength Checker is a Python-based educational cybersecurity tool designed to evaluate password strength using multiple security indicators.

The program analyzes password length, character diversity, uniqueness, common-password patterns, dictionary words, keyboard patterns, sequences, repeated structures, years, dates, predictable password structures, and supplied personal terms.

It produces a score from 0 to 100, a strength category, detected weaknesses, recommendations, and detailed pattern analysis.

---

## Objectives

- Evaluate password strength using multiple security rules.
- Detect common and predictable passwords.
- Detect simple password modification techniques such as leetspeak and common suffixes.
- Identify keyboard walks and predictable sequences.
- Detect repeated characters and repeated password blocks.
- Identify year, date, and predictable `Word123!`-style structures.
- Detect supplied personal terms.
- Provide understandable security recommendations.
- Provide automated test cases for validation.

---

## Features

### Password Strength Score

The checker calculates a score from **0 to 100** using:

- Password length
- Character diversity
- Character uniqueness
- Common-password detection
- Dictionary-word detection
- Sequence detection
- Keyboard-pattern detection
- Repeated-character detection
- Repeated-block detection
- Year and date detection
- Predictable password structures
- Personal-term detection

### Strength Categories

| Score | Strength |
|---:|---|
| 0–29 | Very Weak |
| 30–49 | Weak |
| 50–69 | Moderate |
| 70–84 | Strong |
| 85–100 | Very Strong |

Security-related hard caps can reduce the final score when serious weaknesses are detected.

---

## Scoring Model

### Length

Password length is an important part of the score.

| Password Length | Maximum Length Points |
|---:|---:|
| Below 8 | 0 |
| 8–9 | 15 |
| 10–11 | 25 |
| 12–15 | 35 |
| 16–19 | 45 |
| 20+ | 50 |

### Character Diversity

The checker evaluates four character types:

- Lowercase letters
- Uppercase letters
- Digits
- Special characters

Each character type contributes up to 5 points.

**Maximum: 20 points**

### Uniqueness

The checker considers the ratio of distinct characters to total password length.

**Maximum: 10 points**

### Clean Bonus

A password may receive an additional bonus when it is sufficiently long and no significant weakness is detected.

**Maximum: 20 points**

### Penalties

Penalties may be applied for:

- Common passwords
- Dictionary words
- Alphabetic sequences
- Numeric sequences
- Keyboard walks
- Repeated characters
- Repeated blocks
- Years
- Dates
- Predictable `Word123!` structures
- Supplied personal terms
- Low character diversity

---

## Pattern Detection

### Common Password Detection

The checker compares passwords against a built-in common-password blocklist and normalized forms.

It can detect simple variations such as:

- `password`
- `Password123!`
- `P@ssw0rd`

Normalization helps identify common password modifications involving capitalization, leetspeak, separators, and common suffixes.

An optional `common_passwords.txt` file can be used to extend the local blocklist.

---

### Dictionary Word Detection

The checker searches for recognizable dictionary words inside password structures.

Very short fragments are avoided to reduce meaningless matches.

---

### Keyboard Pattern Detection

The checker detects predictable keyboard walks such as:

- `qwerty`
- `asdfgh`
- `1qaz`

Long keyboard patterns can significantly reduce the final score.

---

### Sequence Detection

The checker detects predictable sequences such as:

- `123456`
- `abcdef`
- `654321`
- `fedcba`

Common odd/even numeric patterns are also considered.

---

### Repeated Characters

Examples:

```text
aaaaaaaa
11111111
```

Repeated characters reduce password strength.

---

### Repeated Blocks

Example:

```text
Aa1!Aa1!Aa1!
```

Repeated password blocks can significantly reduce the final score.

---

### Year and Date Detection

The checker identifies common year and date patterns that may make passwords easier to guess.

---

### Predictable Password Structures

The checker detects structures similar to:

```text
Word123!
```

These patterns are commonly used in passwords and therefore receive additional penalties.

---

### Personal-Term Detection

The user can optionally provide dummy personal terms for testing.

Example:

```text
testuser, demo
```

The checker identifies whether supplied terms occur in the password.

**Do not enter real passwords or sensitive personal information.**

---

## Password Input Privacy

The interactive checker uses hidden terminal input.

The program does not intentionally save entered passwords to reports or databases.

For demonstrations and screenshots, use dummy test passwords only.

---

## Automated Testing

The project includes automated tests covering:

- Common passwords
- Common passwords with suffixes
- Leetspeak
- Short passwords
- Seasonal and year patterns
- Keyboard walks
- Repeated characters
- Repeated blocks
- Blocklisted passphrases
- Unpredictable passphrases
- Random-looking passwords
- Dictionary-word combinations
- Numeric sequences
- Common account-style passwords
- Empty input
- Personal-term detection

The automated test suite currently contains:

**16/16 category tests passed**

Additional validation checks also passed.

Example successful result:

```text
Category tests : 16/16
Extra checks   : PASS
All tests passed.
```

---

## How to Run

### Interactive Mode

Run:

```text
python password_checker.py
```

The main menu provides:

```text
1. Analyze password
2. Run automated tests
3. Scoring model and limitations
4. Exit
```

### Automated Test Mode

Run:

```text
python password_checker.py --test
```

---

## Example Analysis

The program displays:

```text
PASSWORD SECURITY ANALYSIS

Score              : XX/100
Strength           : CATEGORY
Length             : XX characters
Unique ratio       : X.XX
Theoretical entropy: XX.X bits
Effective entropy  : XX.X bits
```

It also provides:

- Score breakdown
- Strengths
- Weaknesses
- Recommendations
- Pattern analysis

---

## Project Structure

```text
CS_2_PasswordStrengthChecker_byte
│
├── password_checker.py
├── README.md
├── common_passwords.txt
│
└── screenshots
    ├── 01_project_structure.png
    ├── 02_automated_tests.png
    ├── 03_password_analysis.png
    └── 04_scoring_model.png
```

If `common_passwords.txt` is not present, the program can operate using its built-in demonstration blocklist.

---

## Screenshots

The project contains screenshots demonstrating:

1. Project structure and source code
2. Automated test execution
3. Password security analysis
4. Scoring model and limitations

Demonstration inputs should contain dummy test information only.

---

## Entropy Information

The checker reports two entropy-related values.

### Theoretical Entropy

Theoretical entropy estimates entropy from password length and character pool size under the assumption of random character selection.

### Effective Entropy

Effective entropy is a heuristic adjustment based on detected patterns such as:

- Common passwords
- Dictionary words
- Keyboard walks
- Sequences
- Repeated structures
- Predictable password structures

These values are estimates and should not be interpreted as guaranteed cracking-time measurements.

---

## Limitations

This is an educational password-analysis tool and is not a complete password-security assessment system.

Important limitations include:

- The built-in common-password and dictionary lists are limited demonstration lists.
- A larger local `common_passwords.txt` file can extend blocklist coverage.
- The tool does not perform a live breach-database lookup.
- The checker cannot prove that a password is truly random.
- Entropy values are estimates rather than guaranteed cracking-time predictions.
- Personal-term detection depends on the terms supplied by the user.
- No password-strength checker can guarantee that a password will never be guessed.

---

## Security and Ethical Notice

This project is intended for educational cybersecurity practice and authorized security testing.

Use the tool only with passwords and test data that you are authorized to analyze.

Do not enter real account passwords into demonstrations, screenshots, shared terminals, or public repositories.

Never commit real passwords, credentials, API keys, tokens, or other secrets to GitHub.

---

## Technologies Used

- Python
- Regular Expressions
- Dataclasses
- Hidden terminal input
- Automated test cases
- Git
- GitHub

---

## Testing Status

The current automated test suite completed successfully:

```text
Category tests : 16/16
Extra checks   : PASS
All tests passed.
```

---

## Author

**AVIP Cybersecurity Internship Project**

**Task 2 – Password Strength Checker**
