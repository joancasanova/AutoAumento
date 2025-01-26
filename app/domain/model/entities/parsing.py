# domain/model/entities/parsing.py

from dataclasses import dataclass
from typing import Dict, List, Optional, Literal
from enum import Enum

class ParseMode(Enum):
    """
    Defines parsing strategies for text extraction.
    
    Options:
        REGEX: Uses regular expressions for pattern matching. Ideal for structured text patterns.
        KEYWORD: Uses keyword search with boundary detection. Effective for free-form text extraction.
    """
    REGEX = "regex"
    KEYWORD = "keyword"

@dataclass(frozen=True)
class ParseMatch:
    """
    Represents a single successful match from a parsing rule.
    
    Attributes:
        rule_name: Identifier of the rule that produced this match
        value: Extracted text value. May contain fallback value if rule failed
    """
    rule_name: str
    value: str

@dataclass
class ParseResult:
    """
    Contains complete results from parsing operation with structured access methods.
    
    Attributes:
        entries: List of dictionaries mapping rule names to extracted values.
                 Each dictionary represents one parsed entity/segment.
    """
    entries: List[Dict[str, str]]

    def to_list_of_dicts(self) -> List[Dict[str, str]]:
        """
        Serializes results for easy JSON conversion.
        
        Returns:
            List of entries in native dictionary format
        """
        return self.entries

    def get_all_matches_for_rule(self, rule_name: str) -> List[str]:
        """
        Aggregates all values extracted by a specific rule across all entries.
        
        Args:
            rule_name: Target rule identifier to collect values for
            
        Returns:
            List of extracted values (strings). Empty list if no matches found.
        """
        return [entry[rule_name] for entry in self.entries if rule_name in entry]

@dataclass(frozen=True)
class ParseRule:
    """
    Configuration for a single text parsing pattern.
    
    Attributes:
        name: Unique identifier for the rule
        pattern: Primary search pattern (regex or keyword)
        mode: ParseMode determining interpretation of pattern
        secondary_pattern: Optional boundary marker for KEYWORD mode 
            (defines substring end point)
        fallback_value: Default value if pattern matching fails
        
    Immutable to ensure consistent parsing behavior
    """
    name: str
    pattern: str
    mode: ParseMode
    secondary_pattern: Optional[str] = None
    fallback_value: Optional[str] = None

@dataclass
class ParseRequest:
    """
    Parameters for text parsing operation.
    
    Attributes:
        text: Input text to parse
        rules: Ordered collection of ParseRules to apply
        output_filter: Result filtering strategy:
            - 'all': Return all parsed entries
            - 'successful': Only entries where all rules matched successfully
            - 'first_n': Return first N entries meeting criteria
        output_limit: Required when filter='first_n' 
            (maximum number of entries to return)
    """
    text: str
    rules: List[ParseRule]
    output_filter: Literal["all", "successful", "first_n"] = "all"
    output_limit: Optional[int] = None

@dataclass
class ParseResponse:
    """
    Final output of parsing operation after applying filters.
    
    Attributes:
        parse_result: Processed results containing only entries that 
            match the requested filter criteria
    """
    parse_result: ParseResult