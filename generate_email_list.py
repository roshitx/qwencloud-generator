#!/usr/bin/env python3
"""Generate dot variants for one or more Gmail local parts.

Rules:
- insert at most one '.' per gap between original characters
- no adjacent '.' (no yudi..luia)
- no leading/trailing '.'
- optionally limit the total number of dots per local part (default 2)
  because Kimchi rejects Gmail aliases with too many dots with
  "Email addresses format is not allowed."

Plus labels are intentionally disabled because many signup flows reject
addresses containing '+' or route them to the wrong inbox.
"""
import argparse
import itertools
import random
from pathlib import Path


def generate_variants(base_local: str, domain: str = "gmail.com", max_dots: int = 2):
    """Yield Gmail dot alias variants with at most `max_dots` dots.

    - Dots can be placed in any gap of the local part.
    - No plus labels (disabled to avoid signup rejection/misrouting).
    - No leading/trailing dots, no adjacent dots.
    - Only variants with <= max_dots dots are kept.
    """
    n = len(base_local)
    if n < 2:
        return [f"{base_local}@{domain}"]

    variants = []
    for combo in itertools.product(("", "."), repeat=n - 1):
        if combo.count(".") > max_dots:
            continue
        parts = [base_local[i] + combo[i] for i in range(n - 1)]
        parts.append(base_local[-1])
        variants.append("".join(parts) + f"@{domain}")
    return variants


def main():
    parser = argparse.ArgumentParser(description="Generate shuffled dot-only Gmail variants.")
    parser.add_argument("bases", nargs="*", default=["yourgmailuser"], help="local parts")
    parser.add_argument("-o", "--output", default="email_list.txt", help="output file")
    parser.add_argument("-m", "--max", type=int, default=None, help="max total variants (sample if exceeded)")
    parser.add_argument("--max-dots", type=int, default=2,
                        help="maximum number of dots per local part (default: 2). Kimchi rejects emails with too many dots.")
    args = parser.parse_args()

    output = Path(args.output)
    all_variants = []
    for base in args.bases:
        all_variants.extend(generate_variants(base, max_dots=args.max_dots))

    unique = list(set(all_variants))
    if args.max and len(unique) > args.max:
        unique = random.sample(unique, args.max)

    random.shuffle(unique)
    output.write_text("\n".join(unique) + "\n")
    print(f"Generated {len(unique)} unique variants (max {args.max_dots} dots) from {len(args.bases)} base(s) -> {output}")


if __name__ == "__main__":
    main()
