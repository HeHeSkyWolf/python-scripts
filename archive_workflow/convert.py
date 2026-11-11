"""Archive-to-MDX conversion utilities.

This module parses archived 7k7k news article pages, localizes their image
references, and serializes them into MDX documents with YAML front matter. It
supports plain, rich-text, and fully styled output modes.
"""

import argparse
import hashlib
import re
import shutil
from html import escape as html_escape
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
ASSET_PREFIX = "assets/7k7kant/content/news"
BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "table", "tr", "td", "th",
              "section", "article", "header", "footer", "blockquote"}
KEEP_IMG_ATTRS = {"src", "alt", "width", "height", "border", "title"}
INLINE_TAGS = {"a", "span", "strong", "b", "em", "i", "u", "font",
               "small", "big", "sub", "sup", "mark", "code"}
LEADING_WS = " \t\r\n\f\v\xa0"
KEEP_PLAIN = {"a"}
KEEP_RICH = {"a", "strong", "b"}

COLOR_NAMES = {
    "#ff0000": "red", "#f00": "red", "red": "red",
    "#0000ff": "blue", "#00f": "blue", "blue": "blue",
    "#000080": "navy", "navy": "navy",
    "#008000": "green", "green": "green",
    "#800080": "purple", "purple": "purple",
    "#ffa500": "orange", "orange": "orange",
    "#ffff00": "yellow", "yellow": "yellow",
    "#000000": "black", "#000": "black", "black": "black",
    "#ffffff": "white", "#fff": "white", "white": "white",
    "#808080": "gray", "gray": "gray", "grey": "gray",
    "#c0c0c0": "silver", "silver": "silver",
}

FONT_NAMES = {
    "黑体": "heiti", "宋体": "simsun", "新宋体": "newsong",
    "微软雅黑": "yahei", "楷体": "kaiti", "仿宋": "fangsong",
    "arial": "arial", "tahoma": "tahoma", "calibri": "calibri",
    "times new roman": "times", "simsun": "simsun", "sans-serif": "sans",
    "serif": "serif", "courier new": "courier",
}


def yaml_quote(value: str) -> str:
    """Format a string as a double-quoted YAML scalar.

    Args:
        value: The raw string to escape.

    Returns:
        The escaped string enclosed in double quotes.
    """
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{value}"'


def clean_text(text: str) -> str:
    """Normalize text for downstream HTML processing.

    Non-breaking spaces are converted to regular spaces, runs of whitespace
    are collapsed to a single space, and the result is stripped.

    Args:
        text: The text to normalize.

    Returns:
        The normalized text.
    """
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def meta_from_span(span: Tag) -> tuple[str, str]:
    """Extract publication metadata from a header span.

    Args:
        span: The span expected to contain the publish date and editor.

    Returns:
        A ``(publish_date, editor)`` tuple, or ``("", "")`` when the span does
        not match the expected format.
    """
    text = clean_text(span.get_text())
    match = re.search(r"发布时间：\s*(.*?)\s*责任编辑：\s*(.*)", text)
    if not match:
        return "", ""
    return match.group(1).strip(), match.group(2).strip()


def nav_from_span(span: Tag | None) -> tuple[str, str]:
    """Extract a previous or next navigation link from a span.

    Args:
        span: The navigation span, or ``None`` when the link is absent.

    Returns:
        A ``(route, title)`` tuple. The route is an empty string when the href
        does not contain an article id, while the title may still be set.
    """
    if span is None:
        return "", ""
    link = span.find("a", href=True)
    if link is None:
        return "", ""
    title = clean_text(link.get_text())
    match = re.search(r"/(\d{8})/(\d+)\.html", link["href"])
    if not match:
        return "", title
    route = f"/7k7kant/content/news/{match.group(1)}/{match.group(2)}"
    return route, title


def image_files(images_dir: Path) -> list[str]:
    """List the image files available for an article.

    Args:
        images_dir: Directory containing the article's downloaded images.

    Returns:
        Sorted image filenames whose extensions are supported, or an empty
        list when the directory does not exist.
    """
    if not images_dir.is_dir():
        return []
    return sorted(
        p.name for p in images_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    )


def read_archive_url(article_dir: Path, override: str) -> str:
    """Resolve the archive URL for an article.

    Args:
        article_dir: Directory of the article being converted.
        override: Explicit URL that takes precedence over the sidecar file.

    Returns:
        The override when provided, otherwise the contents of
        ``archive-url.txt``, or an empty string when neither is available.
    """
    if override:
        return override
    sidecar = article_dir / "archive-url.txt"
    if sidecar.is_file():
        return sidecar.read_text(encoding="utf-8").strip()
    return ""


def parse_style(style: str) -> list[tuple[str, str]]:
    """Parse an inline CSS style attribute.

    Declarations are normalized by removing surrounding whitespace, unescaping
    quotes, lowercasing property names, and sorting the result for stable
    class generation.

    Args:
        style: The raw value of a ``style`` attribute.

    Returns:
        A sorted list of ``(property, value)`` pairs. Malformed declarations
        are ignored.
    """
    declarations: list[tuple[str, str]] = []
    for part in style.split(";"):
        if ":" not in part:
            continue
        prop, value = part.split(":", 1)
        prop = prop.strip().lower()
        value = value.strip().replace("\\'", "'").replace('\\"', '"')
        if prop and value:
            declarations.append((prop, value))
    declarations.sort()
    return declarations


def sanitize_token(value: str) -> str:
    """Convert arbitrary text into a CSS-safe identifier fragment.

    Args:
        value: The text to convert.

    Returns:
        A lowercase token containing only letters, digits, and hyphens.
    """
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def font_token(value: str) -> str:
    """Map a CSS font stack to a short class token.

    Args:
        value: A CSS ``font-family`` value.

    Returns:
        A known token for recognized fonts, otherwise a sanitized version of
        the first family name, or ``"custom"`` when it cannot be sanitized.
    """
    first = value.split(",")[0].strip().strip("'\"")
    return FONT_NAMES.get(first.lower(), sanitize_token(first) or "custom")


def style_tokens(declarations: list[tuple[str, str]]) -> list[str]:
    """Convert CSS declarations into human-readable class tokens.

    Args:
        declarations: Normalized ``(property, value)`` pairs.

    Returns:
        A de-duplicated list of class tokens describing the declarations.
    """
    tokens: list[str] = []
    for prop, value in declarations:
        lower = value.lower()
        if prop == "color":
            tokens.append(f"text-{COLOR_NAMES.get(lower, sanitize_token(value))}")
        elif prop == "background-color":
            tokens.append(f"bg-{COLOR_NAMES.get(lower, sanitize_token(value))}")
        elif prop == "text-align":
            tokens.append(f"text-{sanitize_token(value)}")
        elif prop == "text-decoration":
            if "underline" in lower:
                tokens.append("underline")
            if "line-through" in lower:
                tokens.append("strike")
        elif prop == "font-weight":
            if lower in ("bold", "700", "800", "900"):
                tokens.append("bold")
            else:
                tokens.append(f"fw-{sanitize_token(value)}")
        elif prop == "font-style":
            tokens.append(sanitize_token(value))
        elif prop == "font-family":
            tokens.append(f"font-{font_token(value)}")
        elif prop == "font-size":
            tokens.append(f"fs-{sanitize_token(value)}")
        elif prop == "line-height":
            tokens.append(f"lh-{sanitize_token(value)}")
        else:
            tokens.append(f"{sanitize_token(prop)}-{sanitize_token(value)}")

    seen: list[str] = []
    for token in tokens:
        if token and token not in seen:
            seen.append(token)
    return seen


class StyleRegistry:
    """Registry that deduplicates inline styles and generates CSS classes.

    Attributes:
        rules: Maps declaration tuples to their generated class name and CSS.
        used: Class names that have already been assigned.
        indent_used: Whether the shared ``news-indent`` class is required.
    """

    def __init__(self) -> None:
        """Initialize an empty style registry.

        The registry starts with no rules, no assigned class names, and the
        indentation helper disabled.
        """
        self.rules: dict[tuple[tuple[str, str], ...], tuple[str, str]] = {}
        self.used: set[str] = set()
        self.indent_used = False

    def class_for(self, declarations: list[tuple[str, str]]) -> str:
        """Get or create the class name for a set of CSS declarations.

        Args:
            declarations: Normalized ``(property, value)`` pairs.

        Returns:
            A unique class name that represents the declarations.
        """
        key = tuple(declarations)
        if key in self.rules:
            return self.rules[key][0]

        tokens = style_tokens(declarations)
        base = "news-" + "-".join(tokens) if tokens else "news-styled"
        css = "; ".join(f"{prop}: {value}" for prop, value in declarations) + ";"
        if len(base) > 64:
            digest = hashlib.md5(css.encode("utf-8")).hexdigest()[:6]
            base = base[:56].rstrip("-") + f"-{digest}"
        name = base
        suffix = 2
        while name in self.used:
            name = f"{base}-{suffix}"
            suffix += 1

        self.used.add(name)
        self.rules[key] = (name, css)
        return name

    def css(self) -> str:
        """Render the accumulated stylesheet.

        Returns:
            The CSS rules joined by newlines, including the indentation helper
            when it has been used. Returns an empty string when no rules exist.
        """
        lines = [
            f".{name} {{ {css} }}" for name, css in self.rules.values()
        ]
        if self.indent_used:
            lines.insert(0, ".news-indent { text-indent: 2em; }")
        return "\n".join(lines)


def localize_content(con: Tag, soup: BeautifulSoup, files: list[str], image_url) -> None:
    """Localize images and remove unsafe content from an article body.

    The original markup is retained. Existing images are relabeled and pointed
    at the local archive, local images that were not referenced are appended,
    comments and script or style tags are removed, and event handler
    attributes are stripped.

    Args:
        con: The article content element to modify in place.
        soup: The soup that owns ``con``, used to create new elements.
        files: Local image filenames assigned to images in document order.
        image_url: Callable mapping an image filename to its public URL.
    """
    for comment in con.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()
    for tag in con.find_all(["script", "style"]):
        tag.decompose()

    for tag in con.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith("on"):
                del tag[attr]
                continue
            value = tag[attr]
            if isinstance(value, str):
                if attr.lower() in ("href", "src"):
                    value = re.sub(r"[\r\n\t]+", "", value).strip()
                else:
                    value = value.strip()
                tag[attr] = value

    for node in con.find_all(string=True):
        text = str(node)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[ \t\n\f\v]+", " ", text)
        node.replace_with(text)

    local_index = 0
    image_counter = 0
    for img in con.find_all("img"):
        src = img.get("src", "")
        if local_index < len(files):
            src = image_url(files[local_index])
            local_index += 1
        elif not src.startswith(("http://", "https://", "//")):
            img.decompose()
            continue

        image_counter += 1
        img["src"] = src
        img["alt"] = str(image_counter)
        img.attrs = {
            key: value
            for key, value in img.attrs.items()
            if key in KEEP_IMG_ATTRS
        }

    while local_index < len(files):
        image_counter += 1
        paragraph = soup.new_tag("p")
        img = soup.new_tag("img", src=image_url(files[local_index]), alt=str(image_counter))
        paragraph.append(img)
        con.append(paragraph)
        local_index += 1


def rewrite_link_hrefs(con: Tag) -> None:
    """Make links inert by moving their target into a data attribute.

    Args:
        con: The article content element to modify in place.
    """
    for link in con.find_all("a", href=True):
        link["data-original-url"] = link["href"]
        del link["href"]


def clean_blocks(con: Tag, title: str) -> None:
    """Remove redundant blocks from an article body.

    A paragraph that duplicates the article title is removed, along with all
    block elements that contain neither text nor an image.

    Args:
        con: The article content element to modify in place.
        title: The article title used to detect the duplicate paragraph.
    """
    compact_title = re.sub(r"\s+", "", title)
    for paragraph in con.find_all("p"):
        if re.sub(r"\s+", "", paragraph.get_text()) == compact_title:
            paragraph.decompose()
            break

    for tag in reversed(con.find_all(list(BLOCK_TAGS))):
        if tag.find("img"):
            continue
        if not tag.get_text(strip=True):
            tag.decompose()


def strip_block_edges(block: Tag) -> None:
    """Trim whitespace and line breaks at the edges of a block.

    Leading and trailing whitespace-only text nodes and ``<br>`` elements are
    removed, and empty inline tags are discarded.

    Args:
        block: The block element to modify in place.
    """
    for node in list(block.descendants):
        if isinstance(node, NavigableString):
            text = str(node)
            stripped = text.lstrip(LEADING_WS)
            if stripped != text:
                if stripped:
                    node.replace_with(stripped)
                else:
                    node.extract()
            if stripped.strip(LEADING_WS):
                break
        elif isinstance(node, Tag) and node.name == "br":
            node.extract()

    for node in reversed(list(block.descendants)):
        if isinstance(node, NavigableString):
            text = str(node)
            stripped = text.rstrip(LEADING_WS)
            if stripped != text:
                if stripped:
                    node.replace_with(stripped)
                else:
                    node.extract()
            if stripped.strip(LEADING_WS):
                break
        elif isinstance(node, Tag) and node.name == "br":
            node.extract()

    for tag in reversed(block.find_all(list(INLINE_TAGS))):
        if not tag.get_text(strip=True) and not tag.find(["img", "br"]):
            tag.decompose()


def strip_all_block_edges(con: Tag) -> None:
    """Trim block edges throughout the article body.

    Only leaf ``p`` and ``div`` elements are processed so nested structures are
    not modified twice.

    Args:
        con: The article content element to modify in place.
    """
    for block in con.find_all(["p", "div"]):
        if block.find(["p", "div"]):
            continue
        strip_block_edges(block)


def prepare_rich(con: Tag, registry: StyleRegistry) -> bool:
    """Reduce inline markup to bold text and text colors.

    Inline styles are inspected, bold declarations become ``<strong>`` tags,
    colors are registered as CSS classes, and all unrelated attributes and
    styles are removed. ``<font color>`` attributes are converted to styles
    first so they follow the same path.

    Args:
        con: The article content element to modify in place.
        registry: Registry used to generate classes for color declarations.

    Returns:
        ``True`` when at least one color class was applied, otherwise
        ``False``.
    """
    used_color = False

    for tag in con.find_all(True):
        if tag.name == "img":
            continue

        if tag.name == "font" and tag.get("color"):
            style = tag.get("style") or ""
            tag["style"] = (style + "; " if style else "") + f"color: {tag['color']}"
            del tag["color"]

        style = tag.get("style")
        if not style:
            continue

        declarations = parse_style(clean_text(style))
        color = None
        bold = False
        for prop, value in declarations:
            if prop == "color":
                color = value
            elif prop == "font-weight" and value.lower() in ("bold", "700", "800", "900"):
                bold = True

        del tag["style"]
        if bold and tag.name not in BLOCK_TAGS and tag.name not in ("strong", "b"):
            tag.name = "strong"

        if color:
            class_name = registry.class_for([("color", color)])
            classes = tag.get("class") or []
            if isinstance(classes, str):
                classes = classes.split()
            else:
                classes = list(classes)
            if class_name not in classes:
                classes.append(class_name)
            tag["class"] = classes
            used_color = True
            if tag.name not in BLOCK_TAGS and tag.name not in ("span", "strong", "b", "a"):
                tag.name = "span"

    for tag in con.find_all(True):
        if tag.name == "img":
            continue
        attrs = {}
        if tag.name == "a":
            for key in ("data-original-url", "title"):
                if tag.get(key):
                    attrs[key] = tag[key]
        classes = [c for c in (tag.get("class") or []) if c.startswith("news-")]
        if classes:
            attrs["class"] = classes
        tag.attrs = attrs

    return used_color


def plain_block(soup: BeautifulSoup, block: Tag, rich: bool = False) -> list[str]:
    """Flatten a single block into one or more paragraph fragments.

    Inline tags are unwrapped unless they are allowed in the current mode,
    images are emitted as standalone paragraphs, and text is split at ``<br>``
    boundaries.

    Args:
        soup: The soup that owns the content, used to create new elements.
        block: The block element to flatten.
        rich: Whether to keep bold text and text colors in addition to plain
            content.

    Returns:
        A list of serialized ``<p>`` fragments, possibly empty.
    """
    fragment = BeautifulSoup(str(block), "html.parser")
    root = fragment.find(block.name)
    if root is None:
        return []

    segments = split_fragments(fragment, list(root.contents), split_images=True)

    keep = KEEP_RICH if rich else KEEP_PLAIN

    def keep_tag(node: Tag) -> bool:
        """Determine whether an inline tag should be kept during flattening.

        Args:
            node: The tag being considered.

        Returns:
            ``True`` when the tag is allowed in the active output mode.
        """
        if node.name in keep:
            return True
        if rich and node.name == "span":
            classes = node.get("class") or []
            if isinstance(classes, str):
                classes = classes.split()
            return any(name.startswith("news-text-") for name in classes)
        return False

    block_classes = []
    if rich:
        classes = block.get("class") or []
        if isinstance(classes, str):
            classes = classes.split()
        block_classes = [name for name in classes if name.startswith("news-text-")]
    class_attr = f' class="{" ".join(block_classes)}"' if block_classes else ""

    paragraphs: list[str] = []
    image_counter = 0
    for segment in segments:
        wrapper = fragment.new_tag("div")
        for node in segment:
            wrapper.append(node.extract())

        for img in list(wrapper.find_all("img")):
            image_counter += 1
            alt = img.get("alt") or str(image_counter)
            image_tag = fragment.new_tag("img", src=img.get("src", ""), alt=alt)
            img.extract()
            paragraph = fragment.new_tag("p")
            paragraph.append(image_tag)
            paragraphs.append(str(paragraph))

        for link in wrapper.find_all("a"):
            for attr in list(link.attrs):
                if attr not in ("data-original-url", "title"):
                    del link[attr]

        while True:
            tag = wrapper.find(lambda node: not keep_tag(node))
            if tag is None:
                break
            tag.unwrap()

        for tag in reversed(wrapper.find_all(list(INLINE_TAGS))):
            if not tag.get_text(strip=True) and not tag.find(["img", "br"]):
                tag.decompose()

        html = wrapper.decode_contents().strip()
        if not html:
            continue
        parsed = BeautifulSoup(html, "html.parser")
        if parsed.get_text(strip=True) or parsed.find("img"):
            paragraphs.append(f"<p{class_attr}>{html}</p>")

    return paragraphs


def serialize_plain(con: Tag, soup: BeautifulSoup, rich: bool = False) -> str:
    """Serialize the article body as plain paragraphs.

    Direct text children become paragraphs, and each child block is flattened
    through :func:`plain_block`. Brace characters are escaped because the
    output is MDX.

    Args:
        con: The article content element to serialize.
        soup: The soup that owns the content, used to create new elements.
        rich: Whether to retain bold text and text colors.

    Returns:
        The serialized body with escaped MDX braces.
    """
    blocks: list[str] = []
    for child in con.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                blocks.append(f"<p>{html_escape(text)}</p>")
        elif isinstance(child, Tag):
            blocks.extend(plain_block(soup, child, rich))
    body = "\n\n".join(blocks)
    return body.replace("{", "&#123;").replace("}", "&#125;")


def copy_attrs(tag: Tag) -> dict:
    """Copy a tag's attributes without sharing mutable list values.

    Args:
        tag: The tag whose attributes should be copied.

    Returns:
        A shallow copy of the attribute mapping where list values are cloned.
    """
    return {
        key: (list(value) if isinstance(value, list) else value)
        for key, value in tag.attrs.items()
    }


def split_fragments(soup: BeautifulSoup, nodes: list, split_images: bool = False) -> list[list[Tag]]:
    """Split nodes into fragments at line breaks or images.

    Inline tags that span a split point are cloned for each fragment so that
    formatting is preserved. Consumed nodes are extracted from their original
    parent.

    Args:
        soup: The soup used to create cloned tags.
        nodes: The nodes to split.
        split_images: Whether images should start their own fragment.

    Returns:
        A list of fragments, each containing the nodes belonging to it.
    """
    segments: list[list[Tag]] = [[]]
    for node in list(nodes):
        if isinstance(node, Tag):
            if node.name == "br":
                node.extract()
                segments.append([])
                continue
            if split_images and node.name == "img":
                node.extract()
                segments.append([node])
                segments.append([])
                continue
            if node.name in INLINE_TAGS and (node.find("br") or (split_images and node.find("img"))):
                parts = split_fragments(soup, list(node.contents), split_images)
                for index, part in enumerate(parts):
                    if index > 0:
                        segments.append([])
                    if part:
                        clone = soup.new_tag(node.name)
                        clone.attrs = copy_attrs(node)
                        for child in part:
                            clone.append(child.extract())
                        segments[-1].append(clone)
                node.decompose()
                continue
        segments[-1].append(node.extract())
    return segments


def split_br_blocks(con: Tag, soup: BeautifulSoup) -> None:
    """Split text blocks into paragraphs at every ``<br>``.

    Args:
        con: The article content element to modify in place.
        soup: The soup used to create the new paragraph elements.
    """
    for tag in reversed(con.find_all(["p", "div"])):
        if tag.find(["p", "div"]):
            continue
        if not tag.find("br"):
            continue

        blocks: list[Tag] = []
        for segment in split_fragments(soup, list(tag.contents)):
            paragraph = soup.new_tag("p")
            paragraph.attrs = copy_attrs(tag)
            for node in segment:
                paragraph.append(node.extract())
            if paragraph.get_text(strip=True) or paragraph.find("img"):
                blocks.append(paragraph)

        for paragraph in blocks:
            tag.insert_before(paragraph)
        tag.decompose()


def apply_indentation(con: Tag, registry: StyleRegistry) -> bool:
    """Convert leading non-breaking-space indentation into a CSS class.

    Blocks whose first text node starts with whitespace are stripped and
    tagged with ``news-indent`` so the indentation can be expressed with
    ``text-indent`` instead of literal spaces.

    Args:
        con: The article content element to modify in place.
        registry: Registry that records whether the indent class is needed.

    Returns:
        ``True`` when at least one block was indented, otherwise ``False``.
    """
    changed = False
    for block in con.find_all(["p", "div"]):
        if block.find([name for name in BLOCK_TAGS if name != block.name]):
            continue
        if block.find("img") and not block.get_text(strip=True):
            continue

        stripped = False
        for node in list(block.descendants):
            if isinstance(node, Comment):
                continue
            if isinstance(node, NavigableString):
                text = str(node)
                leading = text.lstrip(LEADING_WS)
                if leading != text:
                    stripped = True
                    if leading:
                        node.replace_with(leading)
                    else:
                        node.extract()
                if leading.strip(LEADING_WS):
                    break
            elif isinstance(node, Tag) and node.name == "br":
                node.extract()

        if not stripped:
            continue

        for tag in reversed(block.find_all(list(INLINE_TAGS))):
            if not tag.get_text(strip=True) and not tag.find(["img", "br"]):
                tag.decompose()

        existing = block.get("class", [])
        if isinstance(existing, str):
            existing = existing.split()
        else:
            existing = list(existing)
        if "news-indent" not in existing:
            existing.append("news-indent")
        block["class"] = existing
        registry.indent_used = True
        changed = True

    return changed


def extract_styles(con: Tag, registry: StyleRegistry) -> bool:
    """Replace inline styles with generated CSS classes.

    Args:
        con: The article content element to modify in place.
        registry: Registry used to create and deduplicate the classes.

    Returns:
        ``True`` when at least one style was converted, otherwise ``False``.
    """
    used = False
    for tag in con.find_all(True):
        style = tag.get("style")
        if not style:
            continue

        declarations = parse_style(clean_text(style))
        del tag["style"]
        if not declarations:
            continue

        class_name = registry.class_for(declarations)
        existing = tag.get("class", [])
        if isinstance(existing, str):
            existing = existing.split()
        else:
            existing = list(existing)
        if class_name not in existing:
            existing.append(class_name)
        tag["class"] = existing
        used = True

    return used


def serialize_content(con: Tag) -> str:
    """Serialize the article body while preserving block markup.

    Direct text children become paragraphs and child tags are emitted as-is.
    Brace characters are escaped because the output is MDX.

    Args:
        con: The article content element to serialize.

    Returns:
        The serialized body with escaped MDX braces.
    """
    blocks: list[str] = []
    for child in con.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                blocks.append(f"<p>{text}</p>")
        elif isinstance(child, Tag):
            blocks.append(str(child))
    body = "\n\n".join(blocks)
    return body.replace("{", "&#123;").replace("}", "&#125;")


def convert_article(
    article_dir: Path,
    root: Path,
    relative_images: bool,
    archive_override: str,
    registry: StyleRegistry,
    styled: bool,
    rich: bool,
) -> tuple[str, bool] | None:
    """Convert one archived article directory into MDX.

    The article body is cleaned, image references are localized, links are made
    inert, and blocks are normalized according to the selected output mode. The
    resulting document includes YAML front matter built from page metadata and
    optional sidecar files.

    Args:
        article_dir: Directory containing the article's ``index.html``.
        root: Archive root that holds the ``contents`` and ``images`` trees.
        relative_images: Whether to emit relative rather than root-relative
            image paths.
        archive_override: Archive URL used instead of the sidecar file.
        registry: Shared style registry used to collect CSS classes.
        styled: Whether to preserve the original markup and inline styles as
            generated classes.
        rich: Whether to keep only bold text and colors on top of the plain
            output.

    Returns:
        A ``(document, uses_styles)`` tuple, where ``document`` is the complete
        MDX text and ``uses_styles`` indicates whether the body needs the
        generated stylesheet. ``None`` is returned when the article directory
        has no ``index.html`` or no ``div.con`` content element.
    """
    html_path = article_dir / "index.html"
    if not html_path.is_file():
        return None

    html = html_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    con = soup.select_one("div.con")
    if con is None:
        return None

    date = article_dir.parent.name
    article_id = article_dir.name

    title_tag = soup.find("h2")
    title = clean_text(title_tag.get_text()) if title_tag else ""
    if not title:
        raw_title = soup.title.get_text() if soup.title else ""
        title = raw_title.split("_")[0].strip()

    category_tag = soup.select_one("h3.rwgl")
    category = clean_text(category_tag.get_text()) if category_tag else ""

    publish_date, editor = "", ""
    for span in soup.find_all("span"):
        if "发布时间" in span.get_text():
            publish_date, editor = meta_from_span(span)
            break

    prev_route, prev_title = nav_from_span(soup.select_one("div.nextbut span.fl"))
    next_route, next_title = nav_from_span(soup.select_one("div.nextbut span.fr"))

    url_path = article_dir / "source-url.txt"
    if url_path.is_file():
        origin_url = url_path.read_text(encoding="utf-8").strip()
    else:
        origin_url = f"https://news.7k7k.com/content/{date}/{article_id}.html"

    archive_url = read_archive_url(article_dir, archive_override)

    if relative_images:
        prefix = f"../../../../../{ASSET_PREFIX}"
    else:
        prefix = f"/{ASSET_PREFIX}"

    def image_url(filename: str) -> str:
        """Build the public URL of an image belonging to this article.

        Args:
            filename: The image filename.

        Returns:
            The URL path for the image.
        """
        return f"{prefix}/{date}/{article_id}/{filename}"

    files = image_files(root / "images" / date / article_id)
    clean_blocks(con, title)
    localize_content(con, soup, files, image_url)
    rewrite_link_hrefs(con)
    split_br_blocks(con, soup)

    if styled:
        uses_indent = apply_indentation(con, registry)
        uses_styles = extract_styles(con, registry) or uses_indent
    elif rich:
        strip_all_block_edges(con)
        uses_styles = prepare_rich(con, registry)
    else:
        strip_all_block_edges(con)
        uses_styles = False

    front_matter = "\n".join(
        [
            "---",
            f"title: {yaml_quote(title)}",
            f"category: {yaml_quote(category)}",
            f"publishDate: {yaml_quote(publish_date)}",
            f"editor: {yaml_quote(editor)}",
            f"prev: {yaml_quote(prev_route)}",
            f"prevTitle: {yaml_quote(prev_title)}",
            f"next: {yaml_quote(next_route)}",
            f"nextTitle: {yaml_quote(next_title)}",
            f"originURL: {yaml_quote(origin_url)}",
            f"archiveURL: {yaml_quote(archive_url)}",
            "---",
        ]
    )

    if styled:
        body = serialize_content(con)
        if uses_styles:
            body = "import '../news.css'\n\n" + body
    elif rich:
        body = serialize_plain(con, soup, rich=True)
        if uses_styles:
            body = "import '../news.css'\n\n" + body
    else:
        body = serialize_plain(con, soup)
    return front_matter + "\n\n" + body + "\n", uses_styles


def display_path(path: Path, root: Path) -> str:
    """Render a path relative to the archive root when possible.

    Args:
        path: The path to display.
        root: The root against which to relativize ``path``.

    Returns:
        ``path`` relative to ``root``, or the original path string when it is
        outside ``root``.
    """
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main() -> None:
    """Run the command-line archive conversion workflow.

    Parses command-line options, discovers article directories, converts each
    selected article, and writes the MDX output, generated CSS, and status
    messages. In dry-run mode no files are modified.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, default=Path("mdx"),
                        help="output folder (default: mdx)")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="remove the output folder before writing",
    )
    parser.add_argument(
        "--styled",
        "--keep-styles",
        dest="styled",
        action="store_true",
        help="preserve original inline HTML/CSS as generated classes",
    )
    parser.add_argument(
        "--rich",
        action="store_true",
        help="keep only bold and text color on top of the plain output",
    )
    parser.add_argument("--date", help="only write this YYYYMMDD folder")
    parser.add_argument("--id", help="only write this article id")
    parser.add_argument(
        "--relative-images",
        action="store_true",
        help="emit ../../../../../assets/... instead of the default /assets/...",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing .mdx file",
    )
    parser.add_argument(
        "--archive-url",
        default="",
        help="fill archiveURL for the selected article(s)",
    )
    parser.add_argument(
        "--line-ending",
        choices=("crlf", "lf"),
        default="crlf",
        help="output line ending (default: crlf, matching the target)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be written without writing",
    )
    args = parser.parse_args()
    if args.styled and args.rich:
        parser.error("--styled and --rich cannot be used together")
    newline = "\r\n" if args.line_ending == "crlf" else "\n"

    contents = args.root / "contents"
    if not contents.is_dir():
        parser.error(f"contents directory not found: {contents}")

    registry = StyleRegistry()
    out_root = args.root / args.out
    if args.clean and out_root.exists() and not args.dry_run:
        shutil.rmtree(out_root)

    rendered: list[tuple[Path, str]] = []
    for article_dir in sorted(contents.glob("*/*")):
        if not article_dir.is_dir():
            continue
        result = convert_article(
            article_dir,
            args.root,
            args.relative_images,
            args.archive_url,
            registry,
            args.styled,
            args.rich,
        )
        if result is not None:
            rendered.append((article_dir, result[0]))

    css_path = out_root / "news.css"
    css = registry.css()
    if not args.dry_run:
        if css:
            out_root.mkdir(parents=True, exist_ok=True)
            css_path.write_bytes((css + "\n").replace("\n", newline).encode("utf-8"))
        elif css_path.exists() and not args.date and not args.id:
            css_path.unlink()

    converted = 0
    skipped = 0
    for article_dir, mdx in rendered:
        if args.date and article_dir.parent.name != args.date:
            continue
        if args.id and article_dir.name != args.id:
            continue

        relative = article_dir.relative_to(contents)
        out_path = out_root / relative.parent / f"{relative.name}.mdx"
        if out_path.exists() and not args.force:
            print(f"SKIP (exists): {display_path(out_path, args.root)}")
            skipped += 1
            continue

        print(f"WRITE: {display_path(out_path, args.root)}")
        if not args.dry_run:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(mdx.replace("\n", newline).encode("utf-8"))
        converted += 1

    verb = "Would convert" if args.dry_run else "Converted"
    print(f"\n{verb} {converted} article(s), skipped {skipped}.")
    if css:
        print(f"CSS: {display_path(css_path, args.root)}")


if __name__ == "__main__":
    main()
