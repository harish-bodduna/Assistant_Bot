#!/usr/bin/env python3
"""Test App Protection keyword matching."""

from services.demo_qa_service import select_document

def test_app_protection_keywords():
    # Test App Protection keywords
    test_questions = [
        'What is app protection policy?',
        'How does mobile app security work?',
        'Tell me about application protection',
        'Device management policies',
        'Intune configuration',
        'Mobile device policy steps',
        'Explain multi factor authentication steps',  # Should still match MFA
        'How to connect to wifi?',  # Should still match wifi
        'What is the weather today?'  # Should default to MFA
    ]

    print('Testing App Protection keyword matching:')
    for question in test_questions:
        result = select_document(question)
        print(f'"{question}" -> {result}')

if __name__ == "__main__":
    test_app_protection_keywords()