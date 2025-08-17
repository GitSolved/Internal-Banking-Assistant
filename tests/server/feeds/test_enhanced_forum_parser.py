#!/usr/bin/env python3
"""Test enhanced forum directory parser."""

import sys
import asyncio
import logging

# Enable debug logging to see all the detailed logs
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Import modules to test
sys.path.append('.')
from internal_assistant.server.feeds.simple_forum_service import SimpleForumDirectoryService


def test_comprehensive_html_parsing():
    """Test enhanced parsing with comprehensive test HTML."""
    print("Testing Enhanced Forum Parser...")
    
    service = SimpleForumDirectoryService()
    
    # More comprehensive test HTML that mimics various tor.taxi structures
    test_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Tor.taxi</title></head>
    <body>
    
    <!-- Forums Section with Heading -->
    <h2>Forums</h2>
    <div class="forums-section">
        <div>
            <a href="https://dread.onion">Dread</a>
            <p>Main discussion forum</p>
        </div>
        <div>
            <a href="http://pitch6u6h5l4xr5ygs7nutzjvp6n22h7dltyeqgavxknyh6r5g6agd.onion">Pitch - 2</a>
            <p>Community discussions</p>
        </div>
        <div>
            <a href="https://nzdarknmgtforum.onion">NZ Darknet Market Forum</a>
            <p>New Zealand discussions</p>
        </div>
        <div>
            <a href="http://germania7ky2opxnhru2qfk3yryg5fhtzrbctlutmyzq3zqe4bnzqpqd.onion">Germania</a>
            <p>German community forum</p>
        </div>
    </div>
    
    <!-- Additional Forums in different structure -->
    <section id="forums-additional">
        <h3>More Forums</h3>
        <ul>
            <li><a href="https://endchan.onion">EndChan</a> - Image board discussions</li>
            <li><a href="http://xss.is">XSS.is</a> - Security forum</li>
        </ul>
    </section>
    
    <!-- Forums in table format -->
    <table class="forum-table">
        <tr><th>Forum</th><th>Description</th></tr>
        <tr>
            <td><a href="https://anotherforum.onion">Another Forum</a></td>
            <td>General discussions</td>
        </tr>
        <tr>
            <td><a href="http://techforum456789abcdef.onion">Tech Forum</a></td>
            <td>Technology discussions</td>
        </tr>
    </table>
    
    <!-- Mixed content section (should filter out markets) -->
    <h2>Mixed Section</h2>
    <div>
        <a href="https://somemarket.onion">Drug Market</a> - Illegal marketplace
        <a href="https://validforum.onion">Valid Discussion Forum</a> - General discussions
        <a href="https://weaponshop.onion">Weapon Shop</a> - Illegal weapons
    </div>
    
    <!-- Text-only onion addresses -->
    <div class="text-forums">
        <p>Hidden Forum: hiddenforum123456789.onion</p>
        <p>Secret Board: secretboard987654321.onion - Discussion board</p>
    </div>
    
    </body>
    </html>
    """
    
    print("Parsing test HTML with enhanced parser...")
    forums = service._parse_forums_section(test_html)
    
    print(f"\n=== PARSING RESULTS ===")
    print(f"Total forums extracted: {len(forums)}")
    print(f"\nExtracted Forums:")
    for i, forum in enumerate(forums, 1):
        print(f"  {i}. {forum['name']} -> {forum['onion_link']}")
    
    # Validate expected forums are found
    expected_forums = [
        "Dread",
        "Pitch - 2", 
        "NZ Darknet Market Forum",  # Should be allowed as it contains "Forum"
        "Germania",
        "EndChan",
        "Another Forum",
        "Tech Forum",
        "Valid Discussion Forum"
    ]
    
    found_names = [forum['name'] for forum in forums]
    
    print(f"\n=== VALIDATION ===")
    for expected in expected_forums:
        if any(expected.lower() in name.lower() for name in found_names):
            print(f"+ Found: {expected}")
        else:
            print(f"- Missing: {expected}")
    
    # Check that dangerous content was filtered out
    dangerous_names = ["Drug Market", "Weapon Shop"]
    for dangerous in dangerous_names:
        if any(dangerous.lower() in name.lower() for name in found_names):
            print(f"- ERROR: Dangerous content not filtered: {dangerous}")
        else:
            print(f"+ Correctly filtered: {dangerous}")
    
    # Validate onion links
    print(f"\n=== ONION LINK VALIDATION ===")
    valid_onions = 0
    for forum in forums:
        if '.onion' in forum['onion_link']:
            valid_onions += 1
        else:
            print(f"- Invalid onion link: {forum['name']} -> {forum['onion_link']}")
    
    print(f"+ Valid onion links: {valid_onions}/{len(forums)}")
    
    return len(forums) >= 6  # Should find at least 6 valid forums


def test_parsing_strategies():
    """Test different parsing strategies individually."""
    print("\n=== TESTING PARSING STRATEGIES ===")
    
    service = SimpleForumDirectoryService()
    
    # Test with different HTML structures
    test_cases = [
        {
            'name': 'Header-based forums',
            'html': '''
            <h2>Forums</h2>
            <div><a href="https://test1.onion">Test Forum 1</a></div>
            <div><a href="https://test2.onion">Test Forum 2</a></div>
            '''
        },
        {
            'name': 'ID-based section',
            'html': '''
            <section id="forums">
                <a href="https://idforum1.onion">ID Forum 1</a>
                <a href="https://idforum2.onion">ID Forum 2</a>
            </section>
            '''
        },
        {
            'name': 'Class-based section',
            'html': '''
            <div class="forum-list">
                <a href="https://classforum1.onion">Class Forum 1</a>
                <a href="https://classforum2.onion">Class Forum 2</a>
            </div>
            '''
        },
        {
            'name': 'Multiple onion links container',
            'html': '''
            <div>
                <p>Community forums:</p>
                <a href="https://multi1.onion">Multi Forum 1</a>
                <a href="https://multi2.onion">Multi Forum 2</a>
                <a href="https://multi3.onion">Multi Forum 3</a>
            </div>
            '''
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        forums = service._parse_forums_section(test_case['html'])
        print(f"  Found {len(forums)} forums:")
        for forum in forums:
            print(f"    - {forum['name']} -> {forum['onion_link']}")


async def test_service_integration():
    """Test the service with enhanced parsing."""
    print("\n=== TESTING SERVICE INTEGRATION ===")
    
    service = SimpleForumDirectoryService()
    
    # Test cache functionality
    cache_info = service.get_cache_info()
    print(f"Initial cache info: {cache_info}")
    
    # Test with mock data
    mock_forums = [
        {"name": "Test Forum 1", "onion_link": "https://test1.onion"},
        {"name": "Test Forum 2", "onion_link": "https://test2.onion"}
    ]
    
    service.forums_cache = mock_forums
    service.last_refresh = service.last_refresh or service.__class__.last_refresh
    
    forums = service.get_forums()
    print(f"Retrieved {len(forums)} forums from cache")
    
    cache_info = service.get_cache_info()
    print(f"Updated cache info: {cache_info}")


def main():
    """Run all enhanced parser tests."""
    print("ENHANCED FORUM DIRECTORY PARSER TEST SUITE")
    print("=" * 60)
    
    success = True
    
    try:
        # Test comprehensive parsing
        result1 = test_comprehensive_html_parsing()
        if not result1:
            print("- Comprehensive parsing test failed")
            success = False
        else:
            print("+ Comprehensive parsing test passed")
        
        # Test individual strategies
        test_parsing_strategies()
        
        # Test service integration
        asyncio.run(test_service_integration())
        
        if success:
            print("\n" + "=" * 60)
            print("+ ALL ENHANCED PARSER TESTS PASSED")
            print("Enhanced parser successfully extracts forums comprehensively")
        else:
            print("\n" + "=" * 60) 
            print("- SOME TESTS FAILED")
            
    except Exception as e:
        print(f"\n- TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()