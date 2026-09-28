import getpass
import math
import os
import re
import sys
from dataclasses import dataclass

# ============================================================
# CONFIGURATION
# ============================================================

# Length tiers: (minimum length, points). Checked from highest to lowest.
LENGTH_TIERS = [(20, 50), (16, 45), (12, 35), (10, 25), (8, 15), (0, 0)]

POINTS_PER_CHARACTER_CLASS = 5      # lower, upper, digit, special -> max 20
UNIQUENESS_FULL_POINTS = 10
UNIQUENESS_PARTIAL_POINTS = 5
CLEAN_BONUS_POINTS = 20             # no weakness flags and length >= 12

# Score boundaries (inclusive upper limits)
VERY_WEAK_MAX = 29
WEAK_MAX = 49
MODERATE_MAX = 69
STRONG_MAX = 84

# Hard score caps
SHORT_PASSWORD_CAP = 25             # length < 8
MEDIUM_SHORT_PASSWORD_CAP = 55      # length < 10
COMMON_PASSWORD_CAP = 20
DICTIONARY_STRUCTURE_CAP = 49       # dictionary word plus a predictable pattern
PERSONAL_TERM_CAP = 49
REPEATED_STRUCTURE_CAP = 39
LOW_DIVERSITY_CAP = 39
KEYBOARD_HEAVY_CAP = 25
FEW_CLASSES_CAP = STRONG_MAX        # fewer than 3 character classes

# Penalties
PENALTY_COMMON = 60
PENALTY_DICTIONARY_PER_WORD = 10
PENALTY_DICTIONARY_MAX = 30
PENALTY_SEQUENCE = 15
PENALTY_KEYBOARD = 15
PENALTY_REPEATED_CHARS = 10
PENALTY_REPEATED_BLOCK = 25
PENALTY_YEAR = 10
PENALTY_DATE = 15
PENALTY_STRUCTURE = 10
PENALTY_PERSONAL = 25
PENALTY_LOW_DIVERSITY = 15

MIN_RUN_LENGTH = 4                  # shortest sequence / keyboard run flagged
MAX_TRIM = 6                        # how many suffix characters are stripped
MAX_PREFIX_TRIM = 3                 # how many prefix characters are stripped
REPORT_WIDTH = 72


# ============================================================
# BLOCKLISTS (DEMO SIZE)
# ============================================================

COMMON_PASSWORDS = {
    "password", "password1", "password123", "passw0rd", "pass", "pass123",
    "admin", "admin123", "administrator", "root", "toor", "guest", "user",
    "welcome", "welcome1", "welcome123", "letmein", "changeme", "default",
    "qwerty", "qwerty123", "qwertyuiop", "asdfgh", "asdfghjkl", "zxcvbnm",
    "qazwsx", "1qaz2wsx", "1q2w3e4r", "1q2w3e", "zaq12wsx",
    "abc123", "abcd1234", "test", "test123", "testing", "hello", "hello123",
    "123", "1234", "12345", "123456", "1234567", "12345678", "123456789",
    "1234567890", "111111", "000000", "123123", "654321", "666666",
    "121212", "112233", "987654321",
    "iloveyou", "monkey", "dragon", "master", "login", "secret",
    "football", "baseball", "soccer", "hockey", "superman", "batman",
    "princess", "sunshine", "shadow", "mustang", "trustno1", "access",
    "michael", "jordan", "harley", "ranger", "buster", "thomas", "robert",
    "charlie", "andrew", "michelle", "jennifer", "jessica", "daniel",
    "pepper", "killer", "hunter", "george",
    # Famous passphrases (spaces and hyphens are removed before matching)
    "correcthorsebatterystaple", "letmeinplease", "iloveyou2",
}

COMMON_WORDS = {
    "password", "admin", "administrator", "welcome", "summer", "winter",
    "spring", "autumn", "sunshine", "football", "baseball", "dragon",
    "monkey", "master", "secret", "login", "letmein", "superman",
    "princess", "qwerty", "computer", "internet", "security", "secure",
    "strong", "example", "testing", "test", "hello", "freedom", "flower",
    "coffee", "tiger", "blue", "green", "orange", "purple", "love",
    "shadow", "batman", "soccer", "hockey", "michael", "jordan",
}


def _load_external_list(filename):
    """Load extra entries from a text file next to this script, if present."""
    directory = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(directory, filename)
    entries = set()

    if not os.path.isfile(path):
        return entries

    try:
        with open(path, encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                value = line.strip().casefold()
                if value:
                    entries.add(value)
    except OSError:
        pass

    return entries


COMMON_PASSWORDS |= _load_external_list("common_passwords.txt")


# ============================================================
# NORMALIZATION (LEETSPEAK, SEPARATORS, SUFFIX / PREFIX TRIMMING)
# ============================================================

LEET_BASE = {
    "@": "a", "4": "a", "0": "o", "3": "e",
    "5": "s", "$": "s", "7": "t", "+": "t",
}


def _leet_variants(value):
    """
    "1" and "!" can stand for either "i" or "l", so both readings are tried.
    """
    variants = set()

    for target in ("i", "l"):
        table = str.maketrans({**LEET_BASE, "1": target, "!": target})
        variants.add(value.translate(table))

    return variants


def _strip_separators(value):
    return re.sub(r"[\s._\-]+", "", value)


def _trimmed_forms(value):
    """
    Returns the value plus versions with trailing and leading
    digits/symbols removed (for example "password123!" -> "password").
    """
    forms = {value}

    tail = value
    for _ in range(MAX_TRIM):
        if tail and not tail[-1].isalpha():
            tail = tail[:-1]
            forms.add(tail)
        else:
            break

    for form in list(forms):
        head = form
        for _ in range(MAX_PREFIX_TRIM):
            if head and not head[0].isalpha():
                head = head[1:]
                forms.add(head)
            else:
                break

    return {form for form in forms if form}


def comparison_forms(password):
    """
    Every reasonable "plain" reading of a password, used for blocklist
    lookups. The original password is never modified or stored.
    """
    base = _strip_separators(password.casefold())
    forms = set()

    for trimmed in _trimmed_forms(base):
        forms.add(trimmed)
        forms |= _leet_variants(trimmed)

    letters_only = set()
    for form in forms:
        letters = re.sub(r"[^a-z]", "", form)
        if letters:
            letters_only.add(letters)

    return forms | letters_only


# ============================================================
# CHARACTER ANALYSIS
# ============================================================

def has_lowercase(password):
    return any(char.islower() for char in password)


def has_uppercase(password):
    return any(char.isupper() for char in password)


def has_digit(password):
    return any(char.isdigit() for char in password)


def has_special(password):
    """Anything that is not a letter or digit (symbols, spaces, hyphens)."""
    return any(not char.isalnum() for char in password)


def character_type_count(password):
    return sum([
        has_lowercase(password),
        has_uppercase(password),
        has_digit(password),
        has_special(password),
    ])


def unique_character_count(password):
    return len(set(password.casefold()))


def unique_ratio(password):
    if not password:
        return 0.0
    return unique_character_count(password) / len(password)


def is_low_diversity(password):
    if len(password) < 8:
        return False

    unique = unique_character_count(password)
    return unique < 6 or unique / len(password) < 0.35


# ============================================================
# COMMON PASSWORD AND DICTIONARY DETECTION
# ============================================================

def is_common_password(password):
    return any(form in COMMON_PASSWORDS for form in comparison_forms(password))


def find_dictionary_words(password):
    base = _strip_separators(password.casefold())
    haystacks = {base} | _leet_variants(base)

    found = set()
    for word in COMMON_WORDS:
        if len(word) >= 4 and any(word in text for text in haystacks):
            found.add(word)

    # Drop words that are only part of a longer detected word
    found = {
        word for word in found
        if not any(word != other and word in other for other in found)
    }

    return sorted(found, key=lambda word: (-len(word), word))


# ============================================================
# SEQUENCE AND KEYBOARD PATTERN DETECTION
# ============================================================

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
SEQUENCE_SOURCES = [
    _ALPHABET,
    _ALPHABET[::-1],
    "0123456789",
    "9876543210",
]

_KEYBOARD_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"]
KEYBOARD_SOURCES = (
    _KEYBOARD_ROWS
    + [row[::-1] for row in _KEYBOARD_ROWS]
    + ["1qaz2wsx3edc4rfv5tgb6yhn7ujm8ik9ol0p", "qazwsxedcrfvtgbyhnujmikolp"]
)


def _run_coverage(text, sources, min_len=MIN_RUN_LENGTH):
    """
    Finds runs of at least `min_len` characters that appear inside any
    source string. Returns (characters covered, longest run).
    """
    covered = [False] * len(text)
    longest = 0

    for start in range(len(text)):
        best = 0

        for size in range(min_len, len(text) - start + 1):
            chunk = text[start:start + size]

            if any(chunk in source for source in sources):
                best = size
            else:
                break

        if best:
            for index in range(start, start + best):
                covered[index] = True
            longest = max(longest, best)

    return sum(covered), longest


def sequence_coverage(password):
    return _run_coverage(password.casefold(), SEQUENCE_SOURCES)


def keyboard_coverage(password):
    return _run_coverage(password.casefold(), KEYBOARD_SOURCES)


def has_sequential_pattern(password):
    return sequence_coverage(password)[0] > 0


def has_keyboard_pattern(password):
    return keyboard_coverage(password)[0] > 0


# ============================================================
# REPETITION, YEAR AND DATE DETECTION
# ============================================================

def has_repeated_characters(password):
    return bool(re.search(r"(.)\1{2,}", password))


def has_repeated_block(password):
    """Detects abcabc, Aa1!Aa1!, xyzxyzxyz and similar repeated blocks."""
    return bool(re.search(r"(.{2,})\1", password.casefold()))


def has_year_pattern(password):
    return bool(re.search(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)", password))


def _valid_date(day, month):
    return 1 <= day <= 31 and 1 <= month <= 12


def has_date_pattern(password):
    digits_text = re.sub(r"[\s/.\-]", "", password)

    for run in re.findall(r"\d{6,8}", digits_text):
        candidates = []

        if len(run) == 8:
            candidates.append((int(run[0:2]), int(run[2:4])))   # ddmmyyyy
            candidates.append((int(run[2:4]), int(run[0:2])))   # mmddyyyy
            candidates.append((int(run[6:8]), int(run[4:6])))   # yyyymmdd

        if len(run) == 6:
            candidates.append((int(run[0:2]), int(run[2:4])))   # ddmmyy
            candidates.append((int(run[2:4]), int(run[0:2])))   # mmddyy

        if any(_valid_date(day, month) for day, month in candidates):
            return True

    return False


# ============================================================
# STRUCTURE, PASSPHRASE AND PERSONAL INFORMATION
# ============================================================

def has_predictable_structure(password):
    """
    Detects the classic "Word123!" shape: one capitalised or lowercase word
    followed (or preceded) by a few digits or symbols.
    """
    suffix_shape = r"[A-Z]?[a-z]{3,}[\d!@#$%^&*._\-]{1,6}"
    prefix_shape = r"[\d!@#$%^&*]{1,4}[A-Z]?[a-z]{3,}"

    return bool(
        re.fullmatch(suffix_shape, password)
        or re.fullmatch(prefix_shape, password)
    )


def passphrase_words(password):
    """Returns the word list if the password looks like a passphrase."""
    if len(password) < 20:
        return []

    words = [part for part in re.split(r"[\s\-_.]+", password) if part]

    if len(words) >= 4 and all(w.isalpha() and len(w) >= 3 for w in words):
        return words

    return []


def contains_personal_term(password, personal_terms=None):
    if not personal_terms:
        return False

    forms = comparison_forms(password)
    base = _strip_separators(password.casefold())
    haystacks = forms | {base}

    for term in personal_terms:
        normalized = _strip_separators(term.casefold())

        if len(normalized) >= 4 and any(normalized in text for text in haystacks):
            return True

    return False


# ============================================================
# ENTROPY
# ============================================================

def _character_pool(password):
    pool = 0

    if has_lowercase(password):
        pool += 26
    if has_uppercase(password):
        pool += 26
    if has_digit(password):
        pool += 10
    if has_special(password):
        pool += 33

    return pool


def estimate_entropy(password, common, words, keyboard_chars, sequence_chars,
                     repeated_structure, passphrase):
    """
    Returns (theoretical_bits, effective_bits).

    Theoretical: length * log2(character pool). Assumes every character is
    chosen randomly, so it is an upper bound only.

    Effective: a rough estimate that treats dictionary words, keyboard walks,
    sequences and repeated content as far less random.
    """
    pool = _character_pool(password)

    if pool == 0:
        return 0.0, 0.0

    bits_per_char = math.log2(pool)
    theoretical = len(password) * bits_per_char

    if common:
        return theoretical, min(12.0, theoretical)

    if passphrase:
        return theoretical, min(theoretical, 13.0 * len(passphrase))

    effective_length = len(password)

    if repeated_structure:
        effective_length = min(effective_length, len(set(password)))

    predictable_chars = sum(len(word) for word in words)
    predictable_chars += keyboard_chars + sequence_chars
    predictable_chars = min(predictable_chars, effective_length)

    random_chars = effective_length - predictable_chars

    effective = random_chars * bits_per_char
    effective += 12.0 * len(words)

    if keyboard_chars or sequence_chars:
        effective += 6.0

    return theoretical, min(effective, theoretical)


# ============================================================
# RESULT OBJECT
# ============================================================

@dataclass
class PasswordResult:
    score: int
    category: str
    length: int
    unique_ratio: float
    dictionary_words: list
    common_password: bool
    sequence: bool
    keyboard: bool
    repeated_chars: bool
    repeated_block: bool
    year: bool
    date: bool
    predictable_structure: bool
    low_diversity: bool
    personal_term: bool
    passphrase: bool
    theoretical_entropy: float
    effective_entropy: float
    strengths: list
    weaknesses: list
    recommendations: list
    score_breakdown: dict
    caps_applied: list


def _empty_result():
    return PasswordResult(
        score=0, category="Very Weak", length=0, unique_ratio=0.0,
        dictionary_words=[], common_password=False, sequence=False,
        keyboard=False, repeated_chars=False, repeated_block=False,
        year=False, date=False, predictable_structure=False,
        low_diversity=False, personal_term=False, passphrase=False,
        theoretical_entropy=0.0, effective_entropy=0.0, strengths=[],
        weaknesses=["Password is empty."],
        recommendations=["Enter a password for analysis."],
        score_breakdown={}, caps_applied=[],
    )


# ============================================================
# SCORE ENGINE
# ============================================================

def _length_points(length):
    for minimum, points in LENGTH_TIERS:
        if length >= minimum:
            return points
    return 0


def _apply_cap(score, cap, label, applied):
    if score > cap:
        applied.append(f"{label} (max {cap})")
        return cap
    return score


def _category(score):
    if score <= VERY_WEAK_MAX:
        return "Very Weak"
    if score <= WEAK_MAX:
        return "Weak"
    if score <= MODERATE_MAX:
        return "Moderate"
    if score <= STRONG_MAX:
        return "Strong"
    return "Very Strong"


def calculate_score(password, personal_terms=None):
    if not password:
        return _empty_result()

    length = len(password)
    ratio = unique_ratio(password)
    unique_count = unique_character_count(password)

    lower = has_lowercase(password)
    upper = has_uppercase(password)
    digit = has_digit(password)
    special = has_special(password)
    classes = character_type_count(password)

    common = is_common_password(password)
    words = find_dictionary_words(password)
    sequence_chars, _ = sequence_coverage(password)
    keyboard_chars, keyboard_longest = keyboard_coverage(password)
    sequence = sequence_chars > 0
    keyboard = keyboard_chars > 0
    repeated_chars = has_repeated_characters(password)
    repeated_block = has_repeated_block(password)
    year = has_year_pattern(password)
    date = has_date_pattern(password)
    structure = has_predictable_structure(password)
    low_diversity = is_low_diversity(password)
    personal = contains_personal_term(password, personal_terms)
    phrase = passphrase_words(password)

    strengths = []
    weaknesses = []
    recommendations = []
    breakdown = {}
    caps = []

    score = 0

    # ---------------- length ----------------
    points = _length_points(length)
    score += points
    breakdown["length"] = points

    if length >= 16:
        strengths.append("Password has strong length.")
    elif length >= 12:
        strengths.append("Password has good length.")
    else:
        weaknesses.append("Password length is below the preferred range.")
        recommendations.append("Use at least 12 characters, ideally 16 or more.")

    # ---------------- character variety ----------------
    points = POINTS_PER_CHARACTER_CLASS * classes
    score += points
    breakdown["character_diversity"] = points

    if classes == 4:
        strengths.append("Uses lowercase, uppercase, digits and special characters.")
    else:
        missing = []
        if not lower:
            missing.append("lowercase letters")
        if not upper:
            missing.append("uppercase letters")
        if not digit:
            missing.append("digits")
        if not special:
            missing.append("special characters")

        weaknesses.append("Missing character types: " + ", ".join(missing) + ".")

    # ---------------- uniqueness ----------------
    points = 0

    if length >= 12 and unique_count >= 10 and ratio >= 0.40:
        points = UNIQUENESS_FULL_POINTS
        strengths.append("Has a good variety of distinct characters.")
    elif length >= 10 and unique_count >= 8 and ratio >= 0.60:
        points = UNIQUENESS_PARTIAL_POINTS

    score += points
    breakdown["uniqueness"] = points

    # ---------------- clean bonus ----------------
    flags = [
        common, bool(words), sequence, keyboard, repeated_chars,
        repeated_block, year, date, structure, low_diversity, personal,
    ]

    points = 0
    if length >= 12 and not any(flags):
        points = CLEAN_BONUS_POINTS
        strengths.append("No predictable patterns were detected.")

    score += points
    breakdown["clean_bonus"] = points

    if phrase and not any(flags):
        strengths.append("Long multi-word passphrase: length outweighs composition rules.")

    # ---------------- penalties ----------------
    penalties = 0

    if common:
        penalties += PENALTY_COMMON
        weaknesses.append("Matches a common password or a simple variation of one.")
        recommendations.append(
            "Do not use common passwords, even with digits, symbols or leetspeak added."
        )

    if words:
        penalties += min(PENALTY_DICTIONARY_MAX,
                         PENALTY_DICTIONARY_PER_WORD * len(words))
        weaknesses.append("Contains common words: " + ", ".join(words) + ".")
        recommendations.append("Avoid predictable words and word combinations.")

    if sequence:
        penalties += PENALTY_SEQUENCE
        weaknesses.append("Contains a predictable sequence (such as abcd or 4321).")
        recommendations.append("Avoid alphabetical and numeric sequences.")

    if keyboard:
        penalties += PENALTY_KEYBOARD
        weaknesses.append("Contains a keyboard-walk pattern (such as qwerty).")
        recommendations.append("Avoid keyboard patterns.")

    if repeated_chars:
        penalties += PENALTY_REPEATED_CHARS
        weaknesses.append("Contains three or more identical characters in a row.")
        recommendations.append("Avoid repeating the same character.")

    if repeated_block:
        penalties += PENALTY_REPEATED_BLOCK
        weaknesses.append("Contains a repeated character block.")
        recommendations.append("Avoid repeating the same group of characters.")

    if year:
        penalties += PENALTY_YEAR
        weaknesses.append("Contains a year-like number.")
        recommendations.append("Avoid years and other predictable numbers.")

    if date:
        penalties += PENALTY_DATE
        weaknesses.append("Contains a date-like number.")
        recommendations.append("Avoid birthdays and other dates.")

    if structure:
        penalties += PENALTY_STRUCTURE
        weaknesses.append('Follows the predictable "Word + digits/symbols" shape.')
        recommendations.append(
            "Adding digits or a symbol to a word is one of the first things attackers try."
        )

    if personal:
        penalties += PENALTY_PERSONAL
        weaknesses.append("Contains a supplied personal-information term.")
        recommendations.append("Avoid names, usernames and other personal details.")

    if low_diversity:
        penalties += PENALTY_LOW_DIVERSITY
        weaknesses.append("Very few distinct characters are used.")
        recommendations.append("Use more distinct characters instead of repeating them.")

    score -= penalties
    breakdown["penalties"] = -penalties

    # ---------------- hard caps ----------------
    if length < 8:
        score = _apply_cap(score, SHORT_PASSWORD_CAP, "Shorter than 8 characters", caps)
    elif length < 10:
        score = _apply_cap(score, MEDIUM_SHORT_PASSWORD_CAP, "Shorter than 10 characters", caps)

    if common:
        score = _apply_cap(score, COMMON_PASSWORD_CAP, "Common password", caps)

    if words and (structure or year or date or sequence or keyboard or repeated_block):
        score = _apply_cap(score, DICTIONARY_STRUCTURE_CAP,
                           "Dictionary word with a predictable pattern", caps)

    if personal:
        score = _apply_cap(score, PERSONAL_TERM_CAP, "Contains personal information", caps)

    if repeated_block and (low_diversity or ratio < 0.55):
        score = _apply_cap(score, REPEATED_STRUCTURE_CAP, "Repeated structure", caps)

    if low_diversity:
        score = _apply_cap(score, LOW_DIVERSITY_CAP, "Low character diversity", caps)

    if keyboard and (keyboard_longest >= 6 or keyboard_chars >= 0.4 * length):
        score = _apply_cap(score, KEYBOARD_HEAVY_CAP, "Mostly a keyboard pattern", caps)

    if classes < 3:
        score = _apply_cap(
            score, FEW_CLASSES_CAP,
            "Randomness of a low-variety password cannot be verified", caps,
        )

    score = max(0, min(round(score), 100))

    theoretical, effective = estimate_entropy(
        password=password,
        common=common,
        words=words,
        keyboard_chars=keyboard_chars,
        sequence_chars=sequence_chars,
        repeated_structure=repeated_block or low_diversity,
        passphrase=phrase,
    )

    return PasswordResult(
        score=score,
        category=_category(score),
        length=length,
        unique_ratio=ratio,
        dictionary_words=words,
        common_password=common,
        sequence=sequence,
        keyboard=keyboard,
        repeated_chars=repeated_chars,
        repeated_block=repeated_block,
        year=year,
        date=date,
        predictable_structure=structure,
        low_diversity=low_diversity,
        personal_term=personal,
        passphrase=bool(phrase),
        theoretical_entropy=theoretical,
        effective_entropy=effective,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
        score_breakdown=breakdown,
        caps_applied=caps,
    )


# ============================================================
# DISPLAY
# ============================================================

def _heading(title):
    print()
    print(title)
    print("-" * REPORT_WIDTH)


def _score_bar(score, width=20):
    filled = round(score / 100 * width)
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def display_result(result):
    print()
    print("=" * REPORT_WIDTH)
    print("PASSWORD SECURITY ANALYSIS")
    print("=" * REPORT_WIDTH)

    print(f"Score              : {result.score}/100  {_score_bar(result.score)}")
    print(f"Strength           : {result.category}")
    print(f"Length             : {result.length} characters")
    print(f"Unique ratio       : {result.unique_ratio:.2f}")

    print(f"Theoretical entropy: {result.theoretical_entropy:.1f} bits "
          "(assumes fully random characters)")
    print(f"Effective entropy  : {result.effective_entropy:.1f} bits "
          "(adjusted for patterns)")

    _heading("SCORE BREAKDOWN")
    for key, value in result.score_breakdown.items():
        print(f"{key.replace('_', ' ').title():24}: {value:+d}" if key == "penalties"
              else f"{key.replace('_', ' ').title():24}: {value}")

    if result.caps_applied:
        _heading("SCORE LIMITS APPLIED")
        for item in result.caps_applied:
            print(f"! {item}")

    _heading("STRENGTHS")
    if result.strengths:
        for item in result.strengths:
            print(f"+ {item}")
    else:
        print("No significant strengths detected.")

    _heading("WEAKNESSES")
    if result.weaknesses:
        for item in result.weaknesses:
            print(f"- {item}")
    else:
        print("No major weaknesses detected.")

    _heading("RECOMMENDATIONS")
    seen = set()
    shown = False
    for item in result.recommendations:
        if item not in seen:
            print(f"> {item}")
            seen.add(item)
            shown = True
    if result.score < 70:
        print("> Consider a passphrase of 4+ unrelated words, or a password "
              "manager generated 16+ character password.")
        shown = True
    if not shown:
        print("No additional recommendations.")

    _heading("PATTERN ANALYSIS")
    checks = [
        ("Common password", result.common_password),
        ("Dictionary words", bool(result.dictionary_words)),
        ("Sequence", result.sequence),
        ("Keyboard pattern", result.keyboard),
        ("Repeated characters", result.repeated_chars),
        ("Repeated block", result.repeated_block),
        ("Year pattern", result.year),
        ("Date pattern", result.date),
        ("Word + digits shape", result.predictable_structure),
        ("Low diversity", result.low_diversity),
        ("Personal term", result.personal_term),
    ]
    for name, detected in checks:
        print(f"{name:24}: {'DETECTED' if detected else 'NOT DETECTED'}")

    print("=" * REPORT_WIDTH)


# ============================================================
# INTERACTIVE MODE
# ============================================================

def interactive_mode():
    print()
    print("=" * REPORT_WIDTH)
    print("ANALYZE A PASSWORD")
    print("=" * REPORT_WIDTH)
    print("Input is hidden and nothing is stored or saved.")
    print("Do not enter a real account password.")

    while True:
        print()
        password = getpass.getpass("Enter test password (blank to go back): ")

        if not password:
            return

        print()
        print("Optional personal terms (dummy examples: username, nickname).")
        print("Separate with commas, or press ENTER to skip.")
        raw_terms = input("Personal terms: ").strip()

        personal_terms = [t.strip() for t in raw_terms.split(",") if t.strip()]

        display_result(calculate_score(password, personal_terms))


# ============================================================
# AUTOMATED TEST SUITE
# ============================================================

TEST_CASES = [
    # (password, expected category, why)
    ("password", "Very Weak", "most common password"),
    ("Password123!", "Very Weak", "common base + digits + symbol"),
    ("P@ssw0rd", "Very Weak", "leetspeak of a common password"),
    ("Ab1!xy", "Very Weak", "too short"),
    ("Summer2026!", "Very Weak", "season + year + symbol"),
    ("qwerty123", "Very Weak", "keyboard walk + digits"),
    ("aaaaaaaa", "Very Weak", "single repeated character"),
    ("Aa1!Aa1!Aa1!", "Very Weak", "repeated block"),
    ("correct horse battery staple", "Very Weak", "famous, blocklisted passphrase"),
    ("lantern-orbit-velvet-quarry-mango", "Strong", "unpredictable long passphrase"),
    ("kT7#vQ9$mW2@xL5!", "Very Strong", "random 16-character password"),
    ("Sunshine!Tiger#Coffee9", "Moderate", "three dictionary words with separators"),
    ("qwerty!QWERTY123", "Very Weak", "keyboard walk repeated"),
    ("12345678", "Very Weak", "numeric sequence"),
    ("Admin@2026", "Very Weak", "common word + symbol + year"),
    ("Welcome@123", "Very Weak", "common word + symbol + digits"),
]


def test_mode():
    print()
    print("=" * REPORT_WIDTH)
    print("AUTOMATED PASSWORD TEST SUITE")
    print("=" * REPORT_WIDTH)

    passed = 0

    for number, (password, expected, reason) in enumerate(TEST_CASES, start=1):
        result = calculate_score(password)
        ok = result.category == expected
        passed += ok

        print()
        print(f"Test {number:02}  ({reason})")
        print("-" * REPORT_WIDTH)
        print(f"Password : {password}")
        print(f"Expected : {expected}")
        print(f"Actual   : {result.category} ({result.score}/100)")
        print(f"Result   : {'PASS' if ok else 'FAIL'}")

    total = len(TEST_CASES)

    # Extra checks that are not category comparisons
    extra_ok = True

    empty = calculate_score("")
    if empty.score != 0 or empty.category != "Very Weak":
        extra_ok = False

    personal = calculate_score("Rahul@Kumar-91x", ["rahul", "kumar"])
    if not personal.personal_term or personal.score > PERSONAL_TERM_CAP:
        extra_ok = False

    print()
    print("=" * REPORT_WIDTH)
    print("TEST SUMMARY")
    print("=" * REPORT_WIDTH)
    print(f"Category tests : {passed}/{total}")
    print(f"Extra checks   : {'PASS' if extra_ok else 'FAIL'} (empty input, personal terms)")

    success = passed == total and extra_ok
    print("All tests passed." if success else "Some tests need review.")
    print("=" * REPORT_WIDTH)

    return success


# ============================================================
# ABOUT / LIMITATIONS
# ============================================================

def show_model_and_limits():
    print()
    print("=" * REPORT_WIDTH)
    print("SCORING MODEL AND LIMITATIONS")
    print("=" * REPORT_WIDTH)
    print("""
SCORING (max 100)
  Length            up to 50   (8 chars = 15, 12 = 35, 16 = 45, 20+ = 50)
  Character types   up to 20   (5 each: lower, upper, digit, special)
  Uniqueness        up to 10   (variety of distinct characters)
  Clean bonus       up to 20   (12+ chars and no weakness detected)
  Penalties         subtract   (common, words, sequences, keyboard walks,
                                repeats, years, dates, "Word123!" shape,
                                personal terms, low diversity)

HARD CAPS
  Under 8 chars -> 25, under 10 -> 55, common password -> 20,
  word + pattern -> 49, mostly keyboard walk -> 25,
  fewer than 3 character types -> 84 (cannot be Very Strong).

LIMITATIONS
  * The blocklist and word list are small demo lists. Add a larger list in
    common_passwords.txt next to this script to extend the blocklist.
  * No breach-database lookup (for example Have I Been Pwned).
  * A passphrase is assumed to be random; the tool cannot verify that.
  * Effective entropy is a rough estimate, not a cracking-time guarantee.
  * Educational tool only. Never enter a real password.
""")
    print("=" * REPORT_WIDTH)


# ============================================================
# MAIN MENU
# ============================================================

def main():
    if "--test" in sys.argv[1:]:
        sys.exit(0 if test_mode() else 1)

    while True:
        print()
        print("=" * REPORT_WIDTH)
        print("PASSWORD STRENGTH CHECKER")
        print("=" * REPORT_WIDTH)
        print()
        print("1. Analyze password")
        print("2. Run automated tests")
        print("3. Scoring model and limitations")
        print("4. Exit")

        try:
            choice = input("\nSelect option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return

        try:
            if choice == "1":
                interactive_mode()
            elif choice == "2":
                test_mode()
            elif choice == "3":
                show_model_and_limits()
            elif choice == "4":
                print("Exiting.")
                return
            else:
                print("Invalid option. Enter 1, 2, 3 or 4.")
        except (EOFError, KeyboardInterrupt):
            print("\nReturning to menu.")


if __name__ == "__main__":
    main()