from typing import Dict, Set


class UsernameChecker:
    def __init__(self):
        self.similar_chars: Dict[str, str] = {
            "l": "I1|",  # lowercase L, uppercase i, one, pipe
            "O": "0",  # uppercase O, zero
            "i": "l1|",  # lowercase i, lowercase L, one, pipe
            "I": "l1|",  # uppercase i, lowercase L, one, pipe
        }
        self.confused_chars: Set[str] = set("Il1|O0")

    def is_unrealistic(self, username: str) -> bool:
        """
        Check if a username appears to be unrealistic/problematic.
        Returns True if the username is likely to be problematic.
        """
        if not username:
            return False

        # Convert username to a simplified pattern
        consecutive_similar = 0

        for char in username:
            is_similar = False
            for group in self.similar_chars.values():
                if char in group:
                    consecutive_similar += 1
                    is_similar = True
                    break

            if not is_similar:
                if (
                    consecutive_similar >= 3
                ):  # If we found 3 or more similar characters in a row
                    return True
                consecutive_similar = 0

        # Check final count of consecutive similar characters
        if consecutive_similar >= 3:
            return True

        # Check if more than 50% of the username consists of commonly confused characters
        confused_char_count = sum(1 for c in username if c in self.confused_chars)
        if len(username) > 4 and confused_char_count / len(username) > 0.5:
            return True

        return False
