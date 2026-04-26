"""Faker provider for generating synthetic Indian Government IDs."""

import random
import string

from faker.providers import BaseProvider


class IndianIDProvider(BaseProvider):
    """Custom Faker provider for Indian Government ID numbers."""

    # Indian state codes for Driving License
    STATE_CODES = [
        "AP", "AR", "AS", "BR", "CG", "GA", "GJ", "HR", "HP", "JK",
        "JH", "KA", "KL", "MP", "MH", "MN", "ML", "MZ", "NL", "OD",
        "PB", "RJ", "SK", "TN", "TS", "TR", "UP", "UK", "WB", "AN",
        "CH", "DN", "DD", "DL", "LD", "PY",
    ]

    def aadhaar(self, format: str = "space") -> str:
        """
        Generate a synthetic Aadhaar number.

        Aadhaar format: 12 digits, first digit 2-9

        Args:
            format: Output format - "plain", "space", or "hyphen"

        Returns:
            str: Synthetic Aadhaar number

        Examples:
            plain: "234567890123"
            space: "2345 6789 0123"
            hyphen: "2345-6789-0123"
        """
        # First digit: 2-9 (Aadhaar doesn't start with 0 or 1)
        first_digit = random.randint(2, 9)

        # Remaining 11 digits
        remaining_digits = "".join([str(random.randint(0, 9)) for _ in range(11)])

        aadhaar_plain = f"{first_digit}{remaining_digits}"

        if format == "space":
            return f"{aadhaar_plain[:4]} {aadhaar_plain[4:8]} {aadhaar_plain[8:]}"
        elif format == "hyphen":
            return f"{aadhaar_plain[:4]}-{aadhaar_plain[4:8]}-{aadhaar_plain[8:]}"
        else:  # plain
            return aadhaar_plain

    def pan(self) -> str:
        """
        Generate a synthetic PAN number.

        PAN format: 5 uppercase letters + 4 digits + 1 uppercase letter

        Returns:
            str: Synthetic PAN number

        Example:
            "ABCDE1234F"
        """
        # 5 random uppercase letters
        letters1 = "".join(random.choices(string.ascii_uppercase, k=5))

        # 4 random digits
        digits = "".join([str(random.randint(0, 9)) for _ in range(4)])

        # 1 random uppercase letter
        letter2 = random.choice(string.ascii_uppercase)

        return f"{letters1}{digits}{letter2}"

    def driving_license(self) -> str:
        """
        Generate a synthetic Indian Driving License number.

        DL format: 2 uppercase letters (state code) + 2 digits (RTO code) +
                   4 digits (year) + 7 digits (sequence)

        Returns:
            str: Synthetic DL number

        Examples:
            "MH01 2023 1234567"
            "DL14 2022 9876543"
        """
        # Random state code
        state_code = random.choice(self.STATE_CODES)

        # RTO code: 01-99
        rto_code = f"{random.randint(1, 99):02d}"

        # Year: 2000-2026
        year = random.randint(2000, 2026)

        # Sequence: 7 digits
        sequence = "".join([str(random.randint(0, 9)) for _ in range(7)])

        # Randomly add spaces or not (both formats are valid)
        if random.choice([True, False]):
            return f"{state_code}{rto_code} {year} {sequence}"
        else:
            return f"{state_code}{rto_code}{year}{sequence}"
