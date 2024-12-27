# domain/model/entities/parsing.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Literal
from enum import Enum

class ParseMode(Enum):
    """
    Defines the mode of parsing:
     - REGEX: Use regular expressions.
     - KEYWORD: Use a keyword-based approach with optional secondary patterns.
    """
    REGEX = "regex"
    KEYWORD = "keyword"

@dataclass(frozen=True)
class ParseMatch:
    """
    Represents a single parse match, storing the rule name and the extracted value.
    This might be used to link matched text to a specific parse rule.
    """
    rule_name: str
    value: str

@dataclass
class ParseResult:
    """
    Represents the entire result of parsing an input string.
    It stores a list of parsed entries as dictionaries where each dictionary
    associates rule names with their matched values (or fallback).
    """
    entries: List[Dict[str, str]]

    def to_list_of_dicts(self) -> List[Dict[str, str]]:
        """
        Converts the internal storage to a list of dictionaries for easy JSON serialization.
        """
        return self.entries

    def get_all_matches_for_rule(self, rule_name: str) -> List[str]:
        """
        Retrieves all matched strings for a specific rule name across all entries.
        """
        matches = []
        for entry in self.entries:
            if rule_name in entry:
                matches.append(entry[rule_name])
        return matches

@dataclass(frozen=True)
class ParseRule:
    """
    Defines a parsing rule:
     - name: Identifier for the rule.
     - pattern: Regex or keyword pattern to match in the text.
     - mode: The parsing mode (ParseMode.REGEX or ParseMode.KEYWORD).
     - secondary_pattern: In KEYWORD mode, indicates a substring boundary or stopping pattern.
     - fallback_value: If a rule doesn't match, fallback_value will be used.
    """
    name: str
    pattern: str
    mode: ParseMode
    secondary_pattern: Optional[str] = None
    fallback_value: Optional[str] = None

@dataclass
class ParseRequest:
    """
    Input object for parsing:
     - text: The string to parse.
     - rules: The list of parse rules (ParseRule objects).
     - output_filter: How to filter the parsing results (all, successful, first_n).
     - output_limit: Limit for 'first_n' filter.
    """
    text: str
    rules: List[ParseRule]
    output_filter: Literal["all", "successful", "first_n"] = "all"
    output_limit: Optional[int] = None

@dataclass
class ParseResponse:
    """
    Represents the final parse response after applying the parse rules and filtering.
    """
    parse_result: ParseResult