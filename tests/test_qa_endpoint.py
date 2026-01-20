import requests
import json

def test_qa_endpoint():
    url = "http://localhost:8000/api/qa/answer"
    payload = {
        "question": "Explain multifactor authentication steps?"
    }
    
    print(f"Sending question to {url}...")
    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()
        
        print("Response received, streaming chunks:\n")
        
        source_markdown_shown = False
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    data_str = decoded_line[len('data: '):]
                    
                    if data_str == "[DONE]":
                        print("\n\n[DONE]")
                        break
                        
                    try:
                        data = json.loads(data_str)
                        
                        # Check for llm_ready_sas_markdown in the first chunk
                        if 'llm_ready_sas_markdown' in data and data['llm_ready_sas_markdown'] and not source_markdown_shown:
                            print("="*60)
                            print("SOURCE DOCUMENT DRAFT (llm_ready_sas_markdown):")
                            print("="*60)
                            print(data['llm_ready_sas_markdown'])
                            print("="*60)
                            print("\nLLM RESPONSE:")
                            print("="*60)
                            source_markdown_shown = True
                            
                        if 'chunk' in data:
                            print(data['chunk'], end='', flush=True)
                        elif 'error' in data:
                            print(f"\nError from server: {data['error']}")
                    except json.JSONDecodeError:
                        print(f"\nFailed to decode: {data_str}")
        print("\n\nStream finished.")
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_qa_endpoint()
