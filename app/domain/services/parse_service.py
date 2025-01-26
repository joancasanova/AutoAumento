# domain/services/parse_service.py

import logging
import re
from typing import List, Dict, Optional, Literal
from domain.model.entities.parsing import ParseResult, ParseRule, ParseMode

logger = logging.getLogger(__name__)

class ParseService:
    """
    Text parsing service implementing rule-based extraction.
    Handles both regex patterns and keyword-based extraction with boundary detection.
    """

    def parse_text(self, text: str, rules: List[ParseRule]) -> ParseResult:
        """
        Main parsing method that processes text through multiple rule-based stages.
        
        Args:
            text: Input text to parse
            rules: Ordered list of parsing rules to apply
            
        Returns:
            ParseResult: Structured parsing results with extracted values
        """
        logger.debug("Starting text parsing process")
        
        # Stage 1: Find all rule matches in text
        all_matches = []
        for rule_idx, rule in enumerate(rules):
            # Get matches for current rule
            occurrences = self._find_all_occurrences(text, rule)
            for (start, end, matched_str) in occurrences:
                all_matches.append({
                    "start": start,
                    "end": end,
                    "rule_idx": rule_idx,
                    "rule_name": rule.name,
                    "value": matched_str
                })

        # Stage 2: Sort matches by position and rule order
        all_matches.sort(key=lambda x: (x["start"], x["rule_idx"]))

        # Stage 3: Build structured entries from matches
        entries: List[Dict[str, str]] = []
        current_entry: Dict[str, str] = {}
        rules_matched_in_entry = set()
        expected_rule_index = 0  # Tracks expected rule order

        def finalize_current_entry():
            """Complete current entry by adding fallback values for missing rules"""
            for rule in rules:
                if rule.name not in rules_matched_in_entry:
                    # Use fallback value or default missing indicator
                    fallback = rule.fallback_value or f"missing_{rule.name}"
                    current_entry[rule.name] = fallback
            entries.append(dict(current_entry))
            current_entry.clear()
            rules_matched_in_entry.clear()

        # Process each match to build coherent entries
        for match_info in all_matches:
            rule_idx = match_info["rule_idx"]
            rule_name = match_info["rule_name"]
            matched_str = match_info["value"]

            # Case 1: Duplicate rule in current entry
            if rule_name in rules_matched_in_entry:
                finalize_current_entry()
                expected_rule_index = 0

            # Case 2: Rule appears before expected order
            if rule_idx < expected_rule_index:
                finalize_current_entry()
                expected_rule_index = 0

            # Case 3: Expected rule in sequence
            if rule_idx == expected_rule_index:
                current_entry[rule_name] = matched_str
                rules_matched_in_entry.add(rule_name)
                expected_rule_index += 1
                
            # Case 4: Rule appears after expected position
            elif rule_idx > expected_rule_index:
                # Fill missing rules with fallbacks
                for missing_idx in range(expected_rule_index, rule_idx):
                    missing_rule = rules[missing_idx]
                    fallback = missing_rule.fallback_value or f"missing_{missing_rule.name}"
                    current_entry[missing_rule.name] = fallback
                    rules_matched_in_entry.add(missing_rule.name)
                
                current_entry[rule_name] = matched_str
                rules_matched_in_entry.add(rule_name)
                finalize_current_entry()
                expected_rule_index = 0

        # Finalize any remaining partial entry
        if rules_matched_in_entry:
            finalize_current_entry()

        logger.debug(f"Parsing completed with {len(entries)} entries")
        return ParseResult(entries=entries)

    def _find_all_occurrences(self, text: str, rule: ParseRule) -> List[tuple]:
        """
        Find all occurrences of a rule's pattern in the text.
        
        Returns list of tuples containing:
        (start_index, end_index, matched_string)
        """
        logger.debug(f"Processing rule: {rule.name} ({rule.mode})")
        results = []

        if rule.mode == ParseMode.REGEX:
            # Regex pattern matching with full capture
            for match in re.finditer(rule.pattern, text):
                results.append((
                    match.start(), 
                    match.end(),
                    match.group().strip()
                ))
                
        elif rule.mode == ParseMode.KEYWORD:
            # Keyword-based extraction with boundary detection
            start = 0
            while True:
                key_pos = text.find(rule.pattern, start)
                if key_pos == -1:
                    break
                
                # Calculate extraction boundaries
                segment_start = key_pos + len(rule.pattern)
                segment_end = len(text)
                
                # Use secondary pattern as end boundary if available
                if rule.secondary_pattern:
                    end_pos = text.find(rule.secondary_pattern, segment_start)
                    if end_pos != -1:
                        segment_end = end_pos
                
                # Extract and clean matched content
                matched_str = text[segment_start:segment_end].strip()
                results.append((key_pos, segment_end, matched_str))
                
                # Move search window forward
                start = segment_end + 1

        return results

    def filter_entries(self, parse_result: ParseResult, 
                      filter_type: Literal["all", "successful", "first_n"],
                      n: Optional[int], 
                      rules: List[ParseRule]) -> ParseResult:
        """
        Filter parsing results based on specified criteria.
        
        Args:
            filter_type: Filtering strategy
            n: Required for 'first_n' filter type
            rules: Original rules for validation
            
        Returns:
            Filtered ParseResult
        """
        if filter_type == "all":
            return parse_result
            
        if filter_type == "successful":
            # Only include entries where all rules succeeded
            filtered = []
            for entry in parse_result.entries:
                valid = True
                for rule in rules:
                    fallback = rule.fallback_value or f"missing_{rule.name}"
                    if entry.get(rule.name, "") == fallback:
                        valid = False
                        break
                if valid:
                    filtered.append(entry)
            return ParseResult(entries=filtered)
            
        if filter_type == "first_n" and n is not None:
            return ParseResult(entries=parse_result.entries[:n])
            
        return parse_result