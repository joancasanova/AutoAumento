# domain/services/parse_service.py

import logging
import re
from typing import List, Dict, Optional, Literal
from domain.model.entities.parsing import (
    ParseResult, ParseRule, ParseMode
)

logger = logging.getLogger(__name__)

class ParseService:
    """
    Service responsible for parsing text according to a list of ParseRule objects.
    Each ParseRule can specify either a REGEX-based approach or a KEYWORD-based approach.
    """

    def parse_text(self, text: str, rules: List[ParseRule]) -> ParseResult:
        logger.debug("Starting parse_text in ParseService.")
        # 1) Gather all matches for each rule
        all_matches = []
        for rule_idx, rule in enumerate(rules):
            occurrences = self._find_all_occurrences(text, rule)
            for (start, end, matched_str) in occurrences:
                all_matches.append({
                    "start": start,
                    "end": end,
                    "rule_idx": rule_idx,
                    "rule_name": rule.name,
                    "value": matched_str
                })

        # 2) Sort matches
        all_matches.sort(key=lambda x: (x["start"], x["rule_idx"]))

        # 3) Build parse 'entries'
        entries: List[Dict[str, str]] = []
        current_entry: Dict[str, str] = {}
        rules_matched_in_entry = set()
        expected_rule_index = 0

        def finalize_current_entry():
            for i, rule in enumerate(rules):
                if rule.name not in rules_matched_in_entry:
                    fallback_val = rule.fallback_value if rule.fallback_value else f"missing_{rule.name}"
                    current_entry[rule.name] = fallback_val
            entries.append(dict(current_entry))
            current_entry.clear()
            rules_matched_in_entry.clear()

        for match_info in all_matches:
            rule_idx = match_info["rule_idx"]
            rule_name = match_info["rule_name"]
            matched_str = match_info["value"]

            # CASE 1: Collision (same rule again)
            if rule_name in rules_matched_in_entry:
                finalize_current_entry()
                expected_rule_index = 0

            # CASE 2: Match belongs to a rule *before* the expected index
            if rule_idx < expected_rule_index:
                finalize_current_entry()
                expected_rule_index = 0

            # CASE 3: If it’s the expected rule
            if rule_idx == expected_rule_index:
                current_entry[rule_name] = matched_str
                rules_matched_in_entry.add(rule_name)
                expected_rule_index += 1
            # CASE 4: If the match is for a rule after the expected
            elif rule_idx > expected_rule_index:
                for missing_idx in range(expected_rule_index, rule_idx):
                    missing_rule = rules[missing_idx]
                    fallback_val = missing_rule.fallback_value if missing_rule.fallback_value else f"missing_{missing_rule.name}"
                    current_entry[missing_rule.name] = fallback_val
                    rules_matched_in_entry.add(missing_rule.name)
                current_entry[rule_name] = matched_str
                rules_matched_in_entry.add(rule_name)
                finalize_current_entry()
                expected_rule_index = 0

        # finalize if there's an unfinished entry
        if rules_matched_in_entry:
            finalize_current_entry()

        logger.debug(f"parse_text produced {len(entries)} entries.")
        return ParseResult(entries=entries)

    def _find_all_occurrences(self, text: str, rule: ParseRule) -> List[tuple]:
        logger.debug(f"Finding occurrences for rule '{rule.name}' with pattern '{rule.pattern}' in mode '{rule.mode}'.")
        results = []
        if rule.mode == ParseMode.REGEX:
            for m in re.finditer(rule.pattern, text):
                results.append((m.start(), m.end(), m.group()))
        elif rule.mode == ParseMode.KEYWORD:
            start = 0
            while True:
                key_pos = text.find(rule.pattern, start)
                if key_pos == -1:
                    break
                segment_start = key_pos + len(rule.pattern)
                segment_end = len(text)
                if rule.secondary_pattern:
                    second_pos = text.find(rule.secondary_pattern, segment_start)
                    if second_pos != -1:
                        segment_end = second_pos
                matched_str = text[segment_start:segment_end].strip()
                results.append((key_pos, segment_end, matched_str))
                start = segment_end + 1
        return results

    def filter_entries(self, parse_result: ParseResult, filter_type: Literal["all", "successful", "first_n"],
                       n: Optional[int], rules: List[ParseRule]) -> ParseResult:
        logger.debug(f"Filtering entries with type '{filter_type}' and limit '{n}'.")
        if filter_type == "all":
            return parse_result
        elif filter_type == "successful":
            filtered_entries = []
            for entry in parse_result.entries:
                is_success = True
                for r in rules:
                    fb = r.fallback_value if r.fallback_value else f"missing_{r.name}"
                    if entry[r.name] == fb:
                        is_success = False
                        break
                if is_success:
                    filtered_entries.append(entry)
            return ParseResult(entries=filtered_entries)
        elif filter_type == "first_n" and n is not None:
            return ParseResult(entries=parse_result.entries[:n])
        return parse_result
