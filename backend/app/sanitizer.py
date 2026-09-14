import html
import re
from html.parser import HTMLParser

# Allowed HTML tags for rendered artifacts
ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr", "blockquote", "pre", "code",
    "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "caption",
    "div", "span", "section", "article", "header", "footer", "main", "nav", "aside",
    "strong", "b", "em", "i", "u", "s", "mark", "small", "sub", "sup", "kbd",
    "a", "img", "svg", "path", "circle", "rect", "line", "polyline", "polygon",
    "style"
}

# Allowed attributes per tag
ALLOWED_ATTRIBUTES = {
    "*": {"class", "id", "style", "title", "aria-label", "aria-hidden", "role", "data-theme"},
    "a": {"href", "target", "rel"},
    "img": {"src", "alt", "width", "height", "loading"},
    "th": {"scope", "colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
    "svg": {"viewbox", "width", "height", "fill", "stroke", "xmlns"},
    "path": {"d", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin"},
    "circle": {"cx", "cy", "r", "fill", "stroke"},
    "rect": {"x", "y", "width", "height", "rx", "ry", "fill", "stroke"},
}

DISALLOWED_TAGS = {"script", "noscript", "iframe", "embed", "object", "form", "input", "button", "link", "meta", "base", "applet"}


class HTMLSanitizer(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result: list[str] = []
        self.tag_stack: list[str] = []
        self.in_disallowed_tag = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        tag_lower = tag.lower()
        if tag_lower in DISALLOWED_TAGS:
            self.in_disallowed_tag += 1
            return

        if self.in_disallowed_tag > 0:
            return

        if tag_lower not in ALLOWED_TAGS:
            return

        sanitized_attrs: list[str] = []
        allowed_global = ALLOWED_ATTRIBUTES.get("*", set())
        allowed_for_tag = ALLOWED_ATTRIBUTES.get(tag_lower, set())

        for attr_name, attr_value in attrs:
            attr_name_lower = attr_name.lower()
            # Strip all event handlers (onclick, onerror, onload, etc.)
            if attr_name_lower.startswith("on"):
                continue

            if attr_name_lower in allowed_global or attr_name_lower in allowed_for_tag:
                if attr_value is None:
                    sanitized_attrs.append(attr_name_lower)
                    continue

                val = attr_value.strip()

                # Block javascript: or vbscript: or data: URIs in href/src
                if attr_name_lower in ("href", "src"):
                    val_lower = re.sub(r"\s+", "", val.lower())
                    if val_lower.startswith("javascript:") or val_lower.startswith("vbscript:") or val_lower.startswith("data:text/html"):
                        continue

                # Sanitize style attribute: strip expression, behavior, javascript
                if attr_name_lower == "style":
                    val_lower = val.lower()
                    if "javascript:" in val_lower or "expression(" in val_lower or "url(" in val_lower:
                        continue

                # Escape value
                escaped_val = html.escape(val, quote=True)
                sanitized_attrs.append(f'{attr_name_lower}="{escaped_val}"')

        attrs_str = (" " + " ".join(sanitized_attrs)) if sanitized_attrs else ""
        self.result.append(f"<{tag_lower}{attrs_str}>")
        self.tag_stack.append(tag_lower)

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in DISALLOWED_TAGS:
            if self.in_disallowed_tag > 0:
                self.in_disallowed_tag -= 1
            return

        if self.in_disallowed_tag > 0:
            return

        if tag_lower in ALLOWED_TAGS:
            self.result.append(f"</{tag_lower}>")

    def handle_data(self, data: str):
        if self.in_disallowed_tag == 0:
            self.result.append(data)

    def get_sanitized_html(self) -> str:
        return "".join(self.result)


def sanitize_html(raw_html: str) -> str:
    """
    Sanitizes HTML content by stripping disallowed tags (<script>, <iframe>, etc.),
    removing event handlers (onclick, onerror), and enforcing an allowlist of tags and attributes.
    """
    if not raw_html:
        return ""
    # Strip dangerous XML/script blocks beforehand as extra defense
    cleaned = re.sub(r"<\s*script[^>]*>[\s\S]*?<\s*/\s*script\s*>", "", raw_html, flags=re.IGNORECASE)
    cleaned = re.sub(r"<\s*style[^>]*>[\s\S]*?url\(.*?\)[\s\S]*?<\s*/\s*style\s*>", "", cleaned, flags=re.IGNORECASE)
    parser = HTMLSanitizer()
    parser.feed(cleaned)
    parser.close()
    return parser.get_sanitized_html().strip()
