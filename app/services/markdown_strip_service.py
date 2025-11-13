"""
Markdown stripping service - Remove links, images, and HTML from markdown
Adapted from markdown-strip tool
"""
from markdown_it import MarkdownIt
from markdown_it.token import Token
from typing import List


def strip_markdown_tokens(tokens: List[Token]) -> List[Token]:
    """
    Strip unwanted elements from markdown tokens while preserving text content.

    Removes:
    - Images (completely)
    - Links (keeps the text content only)
    - HTML blocks and inline HTML

    Preserves:
    - Headers
    - Bold/italic/strikethrough formatting
    - Tables
    - Lists
    - Code blocks and inline code
    - Blockquotes
    - Horizontal rules
    - Plain text
    """
    stripped_tokens = []
    skip_until_close = None

    for i, token in enumerate(tokens):
        # Skip tokens if we're inside a link or other skippable block
        if skip_until_close:
            if token.type == skip_until_close and token.nesting == -1:
                skip_until_close = None
            elif token.type == 'text' and skip_until_close == 'link_close':
                # Keep the text content of links
                stripped_tokens.append(token)
            continue

        # Remove images completely
        if token.type == 'image':
            continue

        # Remove HTML blocks and inline HTML
        if token.type in ['html_block', 'html_inline']:
            continue

        # For links, skip the link tags but keep the text
        if token.type == 'link_open':
            skip_until_close = 'link_close'
            continue

        # Remove auto-links (email/URL)
        if token.type in ['autolink_open', 'autolink_close']:
            continue

        # Keep everything else
        stripped_tokens.append(token)

    return stripped_tokens


def tokens_to_markdown(tokens: List[Token]) -> str:
    """
    Convert tokens back to markdown format.
    """
    result = []
    list_stack = []  # Track nested list levels

    for i, token in enumerate(tokens):
        # Headings
        if token.type == 'heading_open':
            level = int(token.tag[1])  # h1 -> 1, h2 -> 2, etc.
            result.append('#' * level + ' ')
        elif token.type == 'heading_close':
            result.append('\n\n')

        # Paragraphs
        elif token.type == 'paragraph_open':
            pass  # Will be handled by paragraph_close
        elif token.type == 'paragraph_close':
            result.append('\n\n')

        # Emphasis
        elif token.type == 'em_open':
            result.append('*')
        elif token.type == 'em_close':
            result.append('*')

        # Strong
        elif token.type == 'strong_open':
            result.append('**')
        elif token.type == 'strong_close':
            result.append('**')

        # Strikethrough
        elif token.type == 's_open':
            result.append('~~')
        elif token.type == 's_close':
            result.append('~~')

        # Code inline
        elif token.type == 'code_inline':
            result.append(f'`{token.content}`')

        # Code block/fence
        elif token.type == 'fence':
            lang = token.info or ''
            result.append(f'```{lang}\n{token.content}```\n\n')
        elif token.type == 'code_block':
            result.append(f'    {token.content}\n')

        # Blockquote
        elif token.type == 'blockquote_open':
            result.append('> ')
        elif token.type == 'blockquote_close':
            result.append('\n\n')

        # Lists
        elif token.type == 'bullet_list_open':
            list_stack.append('bullet')
        elif token.type == 'bullet_list_close':
            list_stack.pop()
            if not list_stack:  # Only add newline after outermost list
                result.append('\n')
        elif token.type == 'ordered_list_open':
            list_stack.append('ordered')
        elif token.type == 'ordered_list_close':
            list_stack.pop()
            if not list_stack:
                result.append('\n')
        elif token.type == 'list_item_open':
            indent = '  ' * (len(list_stack) - 1)
            if list_stack[-1] == 'bullet':
                result.append(f'{indent}- ')
            else:
                result.append(f'{indent}1. ')
        elif token.type == 'list_item_close':
            result.append('\n')

        # Horizontal rule
        elif token.type == 'hr':
            result.append('---\n\n')

        # Line break
        elif token.type == 'hardbreak':
            result.append('  \n')
        elif token.type == 'softbreak':
            result.append('\n')

        # Tables
        elif token.type == 'table_open':
            pass
        elif token.type == 'table_close':
            result.append('\n')
        elif token.type == 'thead_open' or token.type == 'thead_close':
            pass
        elif token.type == 'tbody_open' or token.type == 'tbody_close':
            pass
        elif token.type == 'tr_open':
            result.append('| ')
        elif token.type == 'tr_close':
            result.append('\n')
        elif token.type == 'th_open':
            pass
        elif token.type == 'th_close':
            result.append(' | ')
            # Check if this is the last th in the row
            next_idx = i + 1
            if next_idx < len(tokens) and tokens[next_idx].type == 'tr_close':
                result.pop()  # Remove last separator
                result.append(' |\n')
                # Add separator row
                # Count number of columns
                col_count = 1
                j = i
                while j >= 0 and tokens[j].type != 'tr_open':
                    if tokens[j].type == 'th_close':
                        col_count += 1
                    j -= 1
                result.append('| ' + ' | '.join(['---'] * col_count) + ' |\n')
                result.append('| ')
        elif token.type == 'td_open':
            pass
        elif token.type == 'td_close':
            result.append(' | ')
            # Check if this is the last td in the row
            next_idx = i + 1
            if next_idx < len(tokens) and tokens[next_idx].type == 'tr_close':
                result.pop()  # Remove last separator
                result.append(' |')

        # Text content
        elif token.type == 'text':
            result.append(token.content)

        # Inline container
        elif token.type == 'inline':
            # Process inline children recursively
            if token.children:
                inline_result = tokens_to_markdown(token.children)
                result.append(inline_result)

    return ''.join(result)


def strip_markdown(markdown_content: str) -> str:
    """
    Strip links, images, and HTML from markdown content while preserving text.

    Args:
        markdown_content: Raw markdown string

    Returns:
        Stripped markdown with:
        - Links converted to plain text (link text only)
        - Images removed
        - HTML removed
        - Formatting preserved (bold, italic, headers, etc.)
    """
    # Parse markdown
    md = MarkdownIt()
    tokens = md.parse(markdown_content)

    # Strip unwanted elements
    stripped_tokens = strip_markdown_tokens(tokens)

    # Convert back to markdown
    output_content = tokens_to_markdown(stripped_tokens)

    # Clean up excessive newlines
    while '\n\n\n' in output_content:
        output_content = output_content.replace('\n\n\n', '\n\n')

    output_content = output_content.strip() + '\n'

    return output_content
