from html.parser import HTMLParser


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._pieces: list[str] = []
        self._block_tags = {
            "address",
            "article",
            "aside",
            "blockquote",
            "div",
            "footer",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "header",
            "li",
            "p",
            "section",
            "tr",
        }
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"head", "script", "style"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == "br":
            self._pieces.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"head", "script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return
        if tag in self._block_tags:
            self._pieces.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        self._pieces.append(data)

    def text(self) -> str:
        lines = []
        for line in "".join(self._pieces).replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            cleaned = " ".join(line.split())
            if cleaned:
                lines.append(cleaned)
        return "\n".join(lines).strip()


def text_from_html(body_html: str | None) -> str:
    if not body_html:
        return ""
    parser = _HtmlTextExtractor()
    parser.feed(body_html)
    return parser.text()
