import difflib
import re

ALLOWED_CHARS_MATERIAL_PARSER = ['', 'g', 'S', '7', 'j', 'X', 'w', 'υ', ')', 'h', 'α', 'y', 'v', '1', 'O', '·', 'r', 'ς', 'p', 'b', 'E', 'B', 'd', 'ω', 'Z', 'β', '□', 'ε', 'c', 'J', 'R', 'U', 'q', 'n', 'u', '9', 'Q', 'H', 't', '0', 'N', 'Y', 'ψ', '5', 'o', 'M', 'T', 'ο', 'G', '8', 'σ', 'φ', 'A', '∓', 'τ', 'I', 'μ', 'λ', 'x', 'f', 'η', 'θ', '.', '+', '/', '2', 'K', 'e', 'χ', '3', 's', 'l', 'm', 'V', '(', 'P', 'ρ', '*', 'ν', 'F', 'γ', 'π', 'ξ', '±', 'k', '-', 'δ', 'L', 'ζ', 'W', 'D', 'a', 'i', 'κ', 'ι', 'C', 'z', ',', '4', '6']

def find_closest_character(input_char, allowed_chars):
    return difflib.get_close_matches(input_char, allowed_chars, n=1, cutoff=0.8)

def replace_with_closest(input_list, allowed_chars):
    result_list = []

    for char in input_list:
        closest_match = find_closest_character(char, allowed_chars)
        if closest_match:
            result_list.append(closest_match[0])
        else:
            # If no close match is found, you may choose to keep the original character
            result_list.append(char)

    return "".join(result_list)


def rewrite_comparison_symbol(expression):
    # Define a regular expression pattern to match the specified pattern
    pattern = re.compile(r'\s*([0-9]+)\s*(≤|<)\s*')

    # Use re.sub() to replace the matched pattern with the desired format
    result = re.sub(pattern, r'\2 \1', expression)

    # Invert the inequality sign
    result = result.replace('<', '>')
    result = result.replace('≤', '>=')

    return result