#!/usr/bin/env python3
"""Debug keyword matching for the specific question."""

from services.demo_qa_service import select_document
import re

def debug_keywords():
    # Test the specific question
    question = 'Explain multi factor authentication steps'
    result = select_document(question)

    print(f'Question: "{question}"')
    print(f'Selected document: {result}')
    print()

    # Debug the matching process
    question_lower = question.lower()
    print('Debugging keyword matching:')
    print(f'Lowercase question: "{question_lower}"')

    # Check MFA keywords
    mfa_keywords = [
        "multi.*factor.*authentication", "mfa", "multifactor.*authentication",
        "authentication.*steps", "microsoft.*authenticator", "authenticator.*app"
    ]

    print('\nChecking MFA keywords:')
    mfa_match_found = False
    for keyword in mfa_keywords:
        if re.search(keyword, question_lower, re.IGNORECASE):
            print(f'  [MATCH] "{keyword}"')
            mfa_match_found = True
            break

    if not mfa_match_found:
        print('  [NO MATCH] No MFA keyword matches')

    # Check WiFi keywords
    wifi_keywords = [
        "wifi", "network", "connect", "connection", "password", "credentials",
        "wifi.*steps", "wifi.*connect", "wifi.*password", "wifi.*credentials",
        "wireless", "internet.*connect"
    ]

    print('\nChecking WiFi keywords:')
    wifi_match_found = False
    for keyword in wifi_keywords:
        if re.search(keyword, question_lower, re.IGNORECASE):
            print(f'  [MATCH] "{keyword}"')
            wifi_match_found = True
            break

    if not wifi_match_found:
        print('  [NO MATCH] No WiFi keyword matches')

    print(f'\nFinal result: {result}')

if __name__ == "__main__":
    debug_keywords()