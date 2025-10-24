#!/usr/bin/env python3
"""
Test script to verify embedding model limits for chunk size planning.

Tests both:
1. IBM Slate 125M (ibm/slate-125m-english-rtrvr)
2. Sentence Transformers (sentence-transformers/all-MiniLM-L6-v2)

With varying text lengths to find the actual limits.
"""

import os

from dotenv import load_dotenv
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import Embeddings as wx_Embeddings
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams

# Load environment variables
load_dotenv(dotenv_path=".env.backup", override=True)

# Sample texts of varying lengths
SAMPLE_TEXTS = {
    "400_chars": """
IBM's strategy has evolved significantly over the years, transitioning from a traditional technology hardware company
to a problem-solving firm that emphasizes research and development (R&D), convenes capabilities like workplace
experience, inclusion, pride, and employer branding. The company prioritizes industry-leading talent practices,
enhances employee engagement.""",
    "1000_chars": """
IBM's strategy has evolved significantly over the years, transitioning from a traditional technology hardware company
to a problem-solving firm that emphasizes research and development (R&D), convenes capabilities like workplace
experience, inclusion, pride, and employer branding. The company prioritizes industry-leading talent practices,
enhances employee engagement, and retains employees at higher rates. Diversity and inclusion are essential for
fostering innovation. Additionally, IBM has transitioned to a services-oriented business model, focusing on
higher-value segments of enterprise IT, such as cloud, AI, and hybrid computing. This shift has been well-received
by the markets initially, as it allowed IBM to capitalize on emerging technologies and differentiate itself from
competitors. However, in recent years, the market's reception has become more mixed. While IBM has made significant
strides in areas like cloud and AI, concerns have been raised about the company's ability to compete with other
major players in these markets. Some analysts have questioned IBM's growth prospects and its ability to maintain
its position as a leader in the technology industry.""",
    "1500_chars": """
IBM's strategy has evolved significantly over the years, transitioning from a traditional technology hardware company
to a problem-solving firm that emphasizes research and development (R&D), convenes capabilities like workplace
experience, inclusion, pride, and employer branding. The company prioritizes industry-leading talent practices,
enhances employee engagement, and retains employees at higher rates. Diversity and inclusion are essential for
fostering innovation. Additionally, IBM has transitioned to a services-oriented business model, focusing on
higher-value segments of enterprise IT, such as cloud, AI, and hybrid computing. This shift has been well-received
by the markets initially, as it allowed IBM to capitalize on emerging technologies and differentiate itself from
competitors. However, in recent years, the market's reception has become more mixed. While IBM has made significant
strides in areas like cloud and AI, concerns have been raised about the company's ability to compete with other
major players in these markets. Some analysts have questioned IBM's growth prospects and its ability to maintain
its position as a leader in the technology industry. The company has invested heavily in quantum computing, blockchain,
and other emerging technologies, but it remains to be seen whether these investments will pay off in the long term.
IBM's leadership team has also undergone significant changes, with new executives bringing fresh perspectives and
strategies to the company. Overall, IBM's evolution reflects the broader changes in the technology industry, as
companies must continuously adapt to stay competitive in a rapidly changing market landscape. The future success of
IBM will depend on its ability to innovate, execute its strategic vision, and maintain strong relationships with
customers and partners across various industries and geographic regions worldwide.""",
    "2000_chars": """
IBM's strategy has evolved significantly over the years, transitioning from a traditional technology hardware company
to a problem-solving firm that emphasizes research and development (R&D), convenes capabilities like workplace
experience, inclusion, pride, and employer branding. The company prioritizes industry-leading talent practices,
enhances employee engagement, and retains employees at higher rates. Diversity and inclusion are essential for
fostering innovation. Additionally, IBM has transitioned to a services-oriented business model, focusing on
higher-value segments of enterprise IT, such as cloud, AI, and hybrid computing. This shift has been well-received
by the markets initially, as it allowed IBM to capitalize on emerging technologies and differentiate itself from
competitors. However, in recent years, the market's reception has become more mixed. While IBM has made significant
strides in areas like cloud and AI, concerns have been raised about the company's ability to compete with other
major players in these markets. Some analysts have questioned IBM's growth prospects and its ability to maintain
its position as a leader in the technology industry. The company has invested heavily in quantum computing, blockchain,
and other emerging technologies, but it remains to be seen whether these investments will pay off in the long term.
IBM's leadership team has also undergone significant changes, with new executives bringing fresh perspectives and
strategies to the company. Overall, IBM's evolution reflects the broader changes in the technology industry, as
companies must continuously adapt to stay competitive in a rapidly changing market landscape. The future success of
IBM will depend on its ability to innovate, execute its strategic vision, and maintain strong relationships with
customers and partners across various industries and geographic regions worldwide. Furthermore, IBM's commitment to
sustainability and corporate social responsibility has become increasingly important, as stakeholders demand that
companies take action on environmental and social issues. IBM has set ambitious goals for reducing its carbon
footprint and promoting diversity and inclusion within its workforce, demonstrating its commitment to being a
responsible corporate citizen in the 21st century technology sector.""",
}


def test_embedding_model(model_id: str, text_samples: dict[str, str]) -> dict:
    """
    Test an embedding model with various text lengths.

    Args:
        model_id: The embedding model ID (e.g., 'ibm/slate-125m-english-rtrvr')
        text_samples: Dictionary of {label: text} to test

    Returns:
        Dictionary with test results
    """
    print(f"\n{'=' * 80}")
    print(f"Testing Model: {model_id}")
    print(f"{'=' * 80}\n")

    # Get credentials from environment (try both naming conventions)
    wx_api_key = os.getenv("WX_API_KEY") or os.getenv("WATSONX_APIKEY")
    wx_url = os.getenv("WX_URL") or os.getenv("WATSONX_URL")
    wx_project_id = os.getenv("WX_PROJECT_ID") or os.getenv("WATSONX_INSTANCE_ID")

    print("Debug - Found credentials:")
    print(f"  API Key: {'✅' if wx_api_key else '❌'}")
    print(f"  URL: {wx_url if wx_url else '❌'}")
    print(f"  Project ID: {wx_project_id if wx_project_id else '❌'}\n")

    if not all([wx_api_key, wx_url, wx_project_id]):
        print("❌ ERROR: Missing WatsonX credentials in environment")
        print("   Required: WX_API_KEY/WATSONX_APIKEY, WX_URL/WATSONX_URL, WX_PROJECT_ID/WATSONX_INSTANCE_ID")
        return {"error": "Missing credentials"}

    # Configure embedding parameters
    embed_params = {
        EmbedParams.TRUNCATE_INPUT_TOKENS: 3,  # 0=no truncate, 1=start, 2=end, 3=both
        EmbedParams.RETURN_OPTIONS: {"input_text": True},
    }

    # Create embeddings client
    try:
        embed_client = wx_Embeddings(
            persistent_connection=True,
            model_id=model_id,
            params=embed_params,
            project_id=wx_project_id,
            credentials=Credentials(api_key=wx_api_key, url=wx_url),
        )
        print(f"✅ Successfully created embedding client for {model_id}\n")
    except Exception as e:
        print(f"❌ ERROR creating embedding client: {e}")
        return {"error": str(e)}

    results = {}

    # Test each text sample
    for label, text in text_samples.items():
        char_count = len(text)
        print(f"\nTesting {label} ({char_count} characters):")
        print(f"  First 100 chars: {text[:100]}...")

        try:
            # Generate embedding
            embeddings = embed_client.embed_documents(texts=[text], concurrency_limit=1)

            if embeddings and len(embeddings) > 0:
                embedding_dim = len(embeddings[0])
                print("  ✅ SUCCESS")
                print(f"     - Embedding dimension: {embedding_dim}")
                print(f"     - Character count: {char_count}")

                results[label] = {
                    "success": True,
                    "char_count": char_count,
                    "embedding_dim": embedding_dim,
                }
            else:
                print("  ⚠️  WARNING: Empty embedding returned")
                results[label] = {
                    "success": False,
                    "char_count": char_count,
                    "error": "Empty embedding",
                }

        except Exception as e:
            error_msg = str(e)
            print("  ❌ FAILED")
            print(f"     Error: {error_msg}")

            results[label] = {
                "success": False,
                "char_count": char_count,
                "error": error_msg,
            }

    # Close connection
    try:
        embed_client.close_persistent_connection()
    except:
        pass

    return results


def main():
    """Run embedding tests for both models."""
    print("\n" + "=" * 80)
    print("EMBEDDING MODEL LIMIT TESTING")
    print("=" * 80)
    print("\nThis script tests embedding generation with varying text lengths")
    print("to determine the actual limits for chunk sizing.\n")

    # Test IBM Slate model
    ibm_results = test_embedding_model(model_id="ibm/slate-125m-english-rtrvr", text_samples=SAMPLE_TEXTS)

    # Test Sentence Transformers model
    st_results = test_embedding_model(model_id="sentence-transformers/all-MiniLM-L6-v2", text_samples=SAMPLE_TEXTS)

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}\n")

    print("IBM Slate 125M Results:")
    if isinstance(ibm_results, dict) and "error" in ibm_results:
        print(f"  ❌ Model initialization failed: {ibm_results.get('error', 'Unknown')}")
    else:
        for label, result in ibm_results.items():
            if isinstance(result, dict) and "success" in result:
                status = "✅" if result["success"] else "❌"
                print(f"  {status} {label}: {result.get('char_count', 0)} chars - {result.get('error', 'OK')}")

    print("\nSentence Transformers Results:")
    if isinstance(st_results, dict) and "error" in st_results:
        print(f"  ❌ Model initialization failed: {st_results.get('error', 'Unknown')}")
    else:
        for label, result in st_results.items():
            if isinstance(result, dict) and "success" in result:
                status = "✅" if result["success"] else "❌"
                print(f"  {status} {label}: {result.get('char_count', 0)} chars - {result.get('error', 'OK')}")

    print(f"\n{'=' * 80}")
    print("RECOMMENDATIONS")
    print(f"{'=' * 80}\n")

    # Determine safe chunk size
    ibm_max = max(
        [r.get("char_count", 0) for r in ibm_results.values() if isinstance(r, dict) and r.get("success")], default=0
    )
    st_max = max(
        [r.get("char_count", 0) for r in st_results.values() if isinstance(r, dict) and r.get("success")], default=0
    )

    safe_size = min(ibm_max, st_max) if ibm_max > 0 and st_max > 0 else 400

    print(f"IBM Slate max successful: {ibm_max} characters")
    print(f"Sentence Transformers max successful: {st_max} characters")
    print(f"\nRecommended safe chunk size: {safe_size} characters")
    print(f"Recommended with 20% buffer: {int(safe_size * 0.8)} characters")
    print()


if __name__ == "__main__":
    main()
