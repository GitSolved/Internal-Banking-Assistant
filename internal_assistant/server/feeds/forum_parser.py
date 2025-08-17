"""HTML parser for tor.taxi forum directory extraction."""

import logging
import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class ForumLink:
    """Represents a forum link from tor.taxi."""
    
    def __init__(
        self,
        name: str,
        url: str,
        description: str = "",
        category: str = "General"
    ):
        self.name = name.strip()
        self.url = url.strip()
        self.description = description.strip()
        self.category = category.strip()
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format."""
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "category": self.category
        }
    
    def is_valid(self) -> bool:
        """Check if forum link contains valid data."""
        return (
            bool(self.name) and 
            bool(self.url) and 
            self.url.startswith(('http://', 'https://'))
        )


class ForumDirectoryParser:
    """Parser for extracting forum links from tor.taxi forum directory."""
    
    # Safety patterns to identify and skip non-forum content
    EXCLUDED_KEYWORDS = {
        'market', 'marketplace', 'drug', 'illegal', 'weapon', 'fraud',
        'counterfeit', 'fake', 'stolen', 'hack', 'exploit', 'malware',
        'ransomware', 'phishing', 'scam', 'carding', 'cvv', 'fullz'
    }
    
    FORUM_INDICATORS = {
        'forum', 'discussion', 'community', 'board', 'talk', 'chat',
        'social', 'general', 'misc', 'random', 'off-topic'
    }
    
    def __init__(self):
        self.parsed_forums: List[ForumLink] = []
    
    def parse_forum_directory(self, html_content: str) -> List[ForumLink]:
        """
        Parse HTML content to extract forum links.
        
        SAFETY: Only extracts links from forum-related sections,
        excludes marketplace and illegal content sections.
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            self.parsed_forums = []
            
            # Target forum-specific sections using multiple strategies
            forum_sections = self._find_forum_sections(soup)
            
            for section in forum_sections:
                section_name = self._extract_section_name(section)
                
                # Safety check: skip if section appears to be marketplace/illegal
                if self._is_excluded_section(section_name):
                    logger.info(f"Skipping excluded section: {section_name}")
                    continue
                
                # Extract forum links from this section
                links = self._extract_links_from_section(section, section_name)
                self.parsed_forums.extend(links)
            
            # Final safety filter
            safe_forums = [forum for forum in self.parsed_forums if self._is_safe_forum(forum)]
            
            logger.info(f"Extracted {len(safe_forums)} forum links from {len(forum_sections)} sections")
            return safe_forums
            
        except Exception as e:
            logger.error(f"Error parsing forum directory: {e}")
            return []
    
    def _find_forum_sections(self, soup: BeautifulSoup) -> List[Tag]:
        """Find HTML sections that likely contain forum links."""
        forum_sections = []
        
        # Strategy 1: Look for sections with forum-related headings
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4'], string=re.compile(r'forum|discussion|community', re.I))
        for heading in headings:
            section = heading.find_parent(['div', 'section', 'article'])
            if section and section not in forum_sections:
                forum_sections.append(section)
        
        # Strategy 2: Find sections with class/id containing 'forum'
        forum_containers = soup.find_all(['div', 'section'], {'class': re.compile(r'forum', re.I)})
        forum_containers.extend(soup.find_all(['div', 'section'], {'id': re.compile(r'forum', re.I)}))
        
        for container in forum_containers:
            if container not in forum_sections:
                forum_sections.append(container)
        
        # Strategy 3: Look for list structures that might contain forums
        lists = soup.find_all(['ul', 'ol'])
        for lst in lists:
            if self._contains_forum_links(lst):
                forum_sections.append(lst)
        
        # If no specific sections found, search the entire document cautiously
        if not forum_sections:
            forum_sections = [soup]
        
        return forum_sections
    
    def _extract_section_name(self, section: Tag) -> str:
        """Extract a descriptive name for the section."""
        # Try to find heading within or before the section
        heading = section.find(['h1', 'h2', 'h3', 'h4'])
        if heading:
            return heading.get_text(strip=True)
        
        # Try previous sibling headings
        for sibling in section.find_previous_siblings():
            if sibling.name in ['h1', 'h2', 'h3', 'h4']:
                return sibling.get_text(strip=True)
        
        # Use class/id as fallback
        if section.get('class'):
            return ' '.join(section['class'])
        if section.get('id'):
            return section['id']
        
        return "General"
    
    def _is_excluded_section(self, section_name: str) -> bool:
        """Check if section should be excluded based on content type."""
        section_lower = section_name.lower()
        
        # Check for excluded keywords
        for keyword in self.EXCLUDED_KEYWORDS:
            if keyword in section_lower:
                return True
        
        return False
    
    def _contains_forum_links(self, element: Tag) -> bool:
        """Check if element likely contains forum links."""
        text = element.get_text(strip=True).lower()
        
        # Must contain forum indicators
        has_forum_indicators = any(indicator in text for indicator in self.FORUM_INDICATORS)
        
        # Must not contain excluded keywords
        has_excluded = any(keyword in text for keyword in self.EXCLUDED_KEYWORDS)
        
        # Must contain actual links
        has_links = bool(element.find_all('a', href=True))
        
        return has_forum_indicators and not has_excluded and has_links
    
    def _extract_links_from_section(self, section: Tag, category: str) -> List[ForumLink]:
        """Extract forum links from a specific section."""
        links = []
        
        # Find all anchor tags with href attributes
        anchor_tags = section.find_all('a', href=True)
        
        for anchor in anchor_tags:
            try:
                name = anchor.get_text(strip=True)
                url = anchor['href']
                
                # Skip empty or invalid links
                if not name or not url:
                    continue
                
                # Clean and validate URL
                if not url.startswith(('http://', 'https://')):
                    if url.startswith('//'):
                        url = 'https:' + url
                    elif url.startswith('/'):
                        continue  # Skip relative URLs as we can't resolve base
                    else:
                        continue
                
                # Extract description from surrounding context
                description = self._extract_description(anchor)
                
                forum_link = ForumLink(
                    name=name,
                    url=url,
                    description=description,
                    category=category
                )
                
                if forum_link.is_valid():
                    links.append(forum_link)
                    
            except Exception as e:
                logger.warning(f"Error extracting link from anchor: {e}")
                continue
        
        return links
    
    def _extract_description(self, anchor: Tag) -> str:
        """Extract description text near the forum link."""
        description = ""
        
        # Check parent element for additional text
        parent = anchor.parent
        if parent:
            parent_text = parent.get_text(strip=True)
            anchor_text = anchor.get_text(strip=True)
            
            # Remove anchor text from parent text to get description
            if anchor_text in parent_text:
                description = parent_text.replace(anchor_text, '').strip()
                # Clean up extra whitespace and punctuation
                description = re.sub(r'\s+', ' ', description)
                description = description.strip('- :')
        
        return description[:200]  # Limit description length
    
    def _is_safe_forum(self, forum: ForumLink) -> bool:
        """Final safety check for forum content."""
        # Check name and description for excluded keywords
        text_to_check = f"{forum.name} {forum.description}".lower()
        
        # Exclude if contains dangerous keywords
        for keyword in self.EXCLUDED_KEYWORDS:
            if keyword in text_to_check:
                logger.debug(f"Excluding forum due to keyword '{keyword}': {forum.name}")
                return False
        
        # Must be a reasonable forum name (not just URL or random text)
        if len(forum.name) < 3 or forum.name.lower() in ['click here', 'link', 'url']:
            return False
        
        return True
    
    def get_forum_categories(self) -> Dict[str, int]:
        """Get count of forums by category."""
        categories = {}
        for forum in self.parsed_forums:
            categories[forum.category] = categories.get(forum.category, 0) + 1
        return categories
    
    def get_parsing_stats(self) -> Dict[str, int]:
        """Get parsing statistics."""
        return {
            "total_forums": len(self.parsed_forums),
            "categories": len(self.get_forum_categories()),
            "valid_forums": len([f for f in self.parsed_forums if f.is_valid()])
        }