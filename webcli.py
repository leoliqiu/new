"""Interactive browser exploration from a terminal using Python Playwright."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Locator,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)


INTERACTIVE_SELECTOR = (
    "a, button, input, textarea, select, summary, "
    "[role=button], [role=link], [role=checkbox], [role=radio], "
    "[role=tab], [role=menuitem], [contenteditable=true], [tabindex]"
)


def find_local_chrome(explicit_path: str | None = None) -> Path:
    """Find an existing Chrome executable without downloading a browser."""
    if explicit_path:
        requested = Path(explicit_path).expanduser().resolve()
        if requested.is_file():
            return requested
        raise FileNotFoundError(f"Chrome executable does not exist: {requested}")

    candidates: list[Path] = []
    for command in ("chrome", "google-chrome", "google-chrome-stable", "chromium"):
        found = shutil.which(command)
        if found:
            candidates.append(Path(found))

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        candidates.extend(
            [
                Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
                Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            ]
        )
        if local_app_data:
            candidates.append(Path(local_app_data) / "Google/Chrome/Application/chrome.exe")
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"))

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "Google Chrome was not found. Pass its existing executable with --chrome-path."
    )


@dataclass(frozen=True)
class ElementRef:
    query: str
    index: int
    description: str


def clipped(value: Any, limit: int = 160) -> str:
    """Return compact one-line text for terminal output."""
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


class WebCLI:
    """Stateful Playwright browser and command dispatcher."""

    def __init__(
        self,
        *,
        chrome_path: str | None = None,
        headless: bool = False,
        timeout_ms: int = 10_000,
        user_agent: str | None = None,
    ) -> None:
        self.chrome_path = chrome_path
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.user_agent = user_agent
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.refs: dict[int, ElementRef] = {}
        self.running = True

    async def start(self) -> None:
        chrome_executable = find_local_chrome(self.chrome_path)
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            executable_path=str(chrome_executable), headless=self.headless
        )
        context_options: dict[str, Any] = {"viewport": {"width": 1440, "height": 900}}
        if self.user_agent:
            context_options["user_agent"] = self.user_agent
        self.context = await self.browser.new_context(**context_options)
        self.context.set_default_timeout(self.timeout_ms)
        self.page = await self.context.new_page()

    async def close(self) -> None:
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def _page(self) -> Page:
        if self.page is None:
            raise RuntimeError("Browser has not started")
        return self.page

    def _locator(self, target: str) -> Locator:
        page = self._page()
        if target.startswith("@") and target[1:].isdigit():
            number = int(target[1:])
            ref = self.refs.get(number)
            if ref is None:
                raise ValueError(f"Unknown element reference {target}; run 'elements' again")
            return page.locator(ref.query).nth(ref.index)
        labelled = re.fullmatch(
            r"(?P<tag>[a-zA-Z][\w-]*)\[(?:label|text)=(?P<quote>['\"])(?P<label>.*?)(?P=quote)\]",
            target,
        )
        if labelled:
            tag = labelled.group("tag").lower()
            label = labelled.group("label")
            role_by_tag = {"button": "button", "a": "link"}
            if tag in role_by_tag:
                return page.get_by_role(role_by_tag[tag], name=label, exact=True)
            return page.get_by_label(label, exact=True)
        return page.locator(target)

    async def execute(self, line: str) -> bool:
        line = line.strip()
        if not line or line.startswith("#"):
            return True
        try:
            parts = shlex.split(line, posix=False)
            parts = [part[1:-1] if len(part) >= 2 and part[0] == part[-1] == '"' else part for part in parts]
        except ValueError as exc:
            print(f"Parse error: {exc}")
            return False
        command = parts[0].lower().replace("-", "_")
        handler = getattr(self, f"cmd_{command}", None)
        if handler is None:
            print(f"Unknown command: {parts[0]}. Type 'help' to list commands.")
            return False
        try:
            await handler(parts[1:])
            return True
        except (ValueError, PlaywrightTimeoutError) as exc:
            print(f"Error: {exc}")
            return False
        except PlaywrightError as exc:
            print(f"Browser error: {exc}")
            return False

    async def repl(self) -> None:
        print("Playwright Web CLI. Type 'help' for commands; 'quit' to exit.")
        while self.running:
            page = self._page()
            host = page.url if page.url != "about:blank" else "blank"
            try:
                line = await asyncio.to_thread(input, f"web[{clipped(host, 45)}]> ")
            except (EOFError, KeyboardInterrupt):
                print()
                break
            await self.execute(line)

    @staticmethod
    def _pipe_event(event: str, **details: Any) -> None:
        payload = json.dumps({"event": event, **details}, ensure_ascii=False)
        print(f"::webcli-event::{payload}", flush=True)

    async def pipe_loop(self) -> None:
        """Accept JSON-line commands over stdin while preserving browser state."""
        self._pipe_event("ready", url=self._page().url)
        while self.running:
            raw_line = await asyncio.to_thread(sys.stdin.readline)
            if raw_line == "":
                break
            try:
                request = json.loads(raw_line)
                command_id = int(request["id"])
                command = str(request["command"]).strip()
                if not command:
                    raise ValueError("command cannot be empty")
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                self._pipe_event("protocol_error", error=str(exc))
                continue
            self._pipe_event("command_started", id=command_id, command=command)
            succeeded = await self.execute(command)
            self._pipe_event(
                "command_finished",
                id=command_id,
                command=command,
                ok=succeeded,
                url=self._page().url,
            )

    async def cmd_help(self, _: list[str]) -> None:
        print(
            """
Navigation
  goto <url>                 Open a URL (https:// is added when omitted)
  back | forward | reload    Move through browser history or reload
  url | title                Print current URL or page title

Interaction
  elements [selector]        List visible interactive elements and assign @refs
  click <selector|@ref>      Click an element
  fill <selector|@ref> <text> Replace an input value
  type <selector|@ref> <text> Type into an element
  focus <selector|@ref>      Move keyboard focus to an element
  enter <text>               Type into the currently focused element
  press <selector|@ref> <key> Press a key, e.g. Enter or Control+A
  check <selector|@ref>      Check a checkbox/radio
  select <selector|@ref> <value> Select an option by value
  hover <selector|@ref>      Hover over an element
  wait <ms|selector>         Wait for time or for a selector to become visible

Learning / inspection
  learn [selector]           Summarize page/region: headings, links, forms, controls
  text [selector]            Print visible text (body by default)
  links [selector]           List links in the page/region
  inspect <selector|@ref>    Print tag, text, attributes and bounding box
  html [selector]            Print HTML for the page/element
  js <expression>            Evaluate JavaScript in the page

Output / session
  screenshot [path]          Save a full-page PNG
  cookies                    Print browser cookies as JSON
  new [url]                  Open a new tab
  tabs                       List open tabs
  use <number>               Switch tab (1-based)
  close_tab                  Close current tab
  quit | exit                Close the browser

Selectors are Playwright/CSS selectors, for example:
  click "text=Sign in"
  fill "input[name=email]" "me@example.com"
  elements
  click @3
""".strip()
        )

    async def cmd_goto(self, args: list[str]) -> None:
        if not args:
            raise ValueError("Usage: goto <url>")
        url = args[0]
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url):
            url = "https://" + url
        response = await self._page().goto(url, wait_until="domcontentloaded")
        self.refs.clear()
        status = response.status if response else "no response"
        print(f"{status}  {await self._page().title()}\n{self._page().url}")

    async def cmd_open(self, args: list[str]) -> None:
        await self.cmd_goto(args)

    async def cmd_back(self, _: list[str]) -> None:
        await self._page().go_back(wait_until="domcontentloaded")
        self.refs.clear()
        print(self._page().url)

    async def cmd_forward(self, _: list[str]) -> None:
        await self._page().go_forward(wait_until="domcontentloaded")
        self.refs.clear()
        print(self._page().url)

    async def cmd_reload(self, _: list[str]) -> None:
        await self._page().reload(wait_until="domcontentloaded")
        self.refs.clear()
        print(self._page().url)

    async def cmd_url(self, _: list[str]) -> None:
        print(self._page().url)

    async def cmd_title(self, _: list[str]) -> None:
        print(await self._page().title())

    async def cmd_elements(self, args: list[str]) -> None:
        query = " ".join(args) if args else INTERACTIVE_SELECTOR
        locator = self._page().locator(query)
        count = await locator.count()
        self.refs.clear()
        shown = 0
        for index in range(min(count, 500)):
            item = locator.nth(index)
            if not await item.is_visible():
                continue
            info = await item.evaluate(
                """el => ({
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type'),
                    role: el.getAttribute('role'),
                    name: el.getAttribute('aria-label') || el.getAttribute('name') || '',
                    placeholder: el.getAttribute('placeholder') || '',
                    text: el.innerText || el.value || el.getAttribute('alt') || ''
                })"""
            )
            shown += 1
            desc = clipped(
                f"<{info['tag']}> {info['text']} "
                f"name={info['name']} placeholder={info['placeholder']} "
                f"type={info['type']} role={info['role']}"
            )
            self.refs[shown] = ElementRef(query=query, index=index, description=desc)
            print(f"@{shown:<3} {desc}")
            if shown >= 100:
                print(f"… stopped after 100 visible elements ({count} matched)")
                break
        if shown == 0:
            print("No visible matching elements.")

    async def cmd_click(self, args: list[str]) -> None:
        if not args:
            raise ValueError("Usage: click <selector|@ref>")
        target = " ".join(args)
        locator: Locator | None = None
        text_target = re.fullmatch(r"text=(?:\"([^\"]*)\"|'([^']*)'|(.+))", target)
        if text_target:
            label = next(value for value in text_target.groups() if value is not None)
            for role in ("link", "button"):
                candidates = self._page().get_by_role(role, name=label, exact=True)
                for index in range(min(await candidates.count(), 50)):
                    candidate = candidates.nth(index)
                    if await candidate.is_visible():
                        locator = candidate
                        break
                if locator is not None:
                    break
        if locator is None:
            candidates = self._locator(target)
            count = await candidates.count()
            for index in range(min(count, 100)):
                candidate = candidates.nth(index)
                if await candidate.is_visible():
                    locator = candidate
                    break
            if locator is None:
                locator = candidates.first
        await locator.click()
        print(f"Clicked {target}  ->  {self._page().url}")

    async def cmd_fill(self, args: list[str]) -> None:
        if len(args) < 2:
            raise ValueError("Usage: fill <selector|@ref> <text>")
        await self._locator(args[0]).fill(" ".join(args[1:]))
        print(f"Filled {args[0]}")

    async def cmd_type(self, args: list[str]) -> None:
        if len(args) < 2:
            raise ValueError("Usage: type <selector|@ref> <text>")
        await self._locator(args[0]).press_sequentially(" ".join(args[1:]))
        print(f"Typed into {args[0]}")

    async def cmd_focus(self, args: list[str]) -> None:
        if not args:
            raise ValueError("Usage: focus <selector|@ref>")
        target = " ".join(args)
        await self._locator(target).focus()
        print(f"Focused {target}")

    async def cmd_enter(self, args: list[str]) -> None:
        if not args:
            raise ValueError("Usage: enter <text>")
        focused = self._page().locator(":focus")
        if await focused.count() == 0:
            raise ValueError("No element is focused; run 'focus <selector>' or click a field first")
        tag = await focused.first.evaluate("el => el.tagName.toLowerCase()")
        if tag in {"body", "html"}:
            raise ValueError("No input is focused; run 'focus <selector>' or click a field first")
        text = " ".join(args)
        await focused.first.press_sequentially(text)
        print(f"Entered {text!r} into the focused element")

    async def cmd_press(self, args: list[str]) -> None:
        if len(args) < 2:
            raise ValueError("Usage: press <selector|@ref> <key>")
        target = " ".join(args[:-1])
        key = args[-1]
        await self._locator(target).press(key)
        print(f"Pressed {key} on {target}")

    async def cmd_check(self, args: list[str]) -> None:
        if not args:
            raise ValueError("Usage: check <selector|@ref>")
        target = " ".join(args)
        await self._locator(target).check()
        print(f"Checked {target}")

    async def cmd_select(self, args: list[str]) -> None:
        if len(args) < 2:
            raise ValueError("Usage: select <selector|@ref> <value>")
        target = " ".join(args[:-1])
        selected = await self._locator(target).select_option(args[-1])
        print(f"Selected {selected}")

    async def cmd_hover(self, args: list[str]) -> None:
        if not args:
            raise ValueError("Usage: hover <selector|@ref>")
        target = " ".join(args)
        await self._locator(target).hover()
        print(f"Hovered {target}")

    async def cmd_wait(self, args: list[str]) -> None:
        if not args:
            raise ValueError("Usage: wait <milliseconds|selector>")
        if args[0].isdigit():
            await self._page().wait_for_timeout(int(args[0]))
            print(f"Waited {args[0]} ms")
        else:
            target = " ".join(args)
            await self._locator(target).wait_for(state="visible")
            print(f"Visible: {target}")

    async def cmd_text(self, args: list[str]) -> None:
        selector = " ".join(args) if args else "body"
        print((await self._page().locator(selector).first.inner_text()).strip())

    async def cmd_links(self, args: list[str]) -> None:
        root = self._page().locator(" ".join(args)).first if args else self._page().locator("body")
        links = await root.locator("a[href]").evaluate_all(
            """els => els.slice(0, 200).map(a => ({
                text: (a.innerText || a.getAttribute('aria-label') || '').trim(),
                href: a.href
            }))"""
        )
        for number, link in enumerate(links, 1):
            print(f"{number:>3}. {clipped(link['text'], 80) or '(no text)'}\n     {link['href']}")
        print(f"{len(links)} link(s) shown")

    async def cmd_inspect(self, args: list[str]) -> None:
        if not args:
            raise ValueError("Usage: inspect <selector|@ref>")
        locator = self._locator(" ".join(args)).first
        result = await locator.evaluate(
            """el => ({
                tag: el.tagName.toLowerCase(),
                text: (el.innerText || el.value || '').trim(),
                attributes: Object.fromEntries([...el.attributes].map(a => [a.name, a.value])),
                boundingBox: (() => {
                    const r = el.getBoundingClientRect();
                    return {x: r.x, y: r.y, width: r.width, height: r.height};
                })()
            })"""
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    async def cmd_html(self, args: list[str]) -> None:
        if args:
            print(await self._page().locator(" ".join(args)).first.evaluate("el => el.outerHTML"))
        else:
            print(await self._page().content())

    async def cmd_js(self, args: list[str]) -> None:
        if not args:
            raise ValueError("Usage: js <JavaScript expression>")
        result = await self._page().evaluate(" ".join(args))
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    async def cmd_learn(self, args: list[str]) -> None:
        root = self._page().locator(" ".join(args)).first if args else self._page().locator("body")
        data = await root.evaluate(
            """root => {
                const clean = s => (s || '').replace(/\\s+/g, ' ').trim();
                const visible = el => {
                    const s = getComputedStyle(el), r = el.getBoundingClientRect();
                    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
                };
                const cssValue = value => {
                    const quote = String.fromCharCode(39), slash = String.fromCharCode(92);
                    const escaped = String(value).split(slash).join(slash + slash)
                        .split(quote).join(slash + '27 ');
                    return quote + escaped + quote;
                };
                const uniqueVisible = selector => {
                    try {
                        return [...document.querySelectorAll(selector)].filter(visible).length === 1;
                    } catch {
                        return false;
                    }
                };
                const implicitRole = el => {
                    const tag = el.tagName.toLowerCase(), type = (el.type || '').toLowerCase();
                    if (tag === 'a' && el.hasAttribute('href')) return 'link';
                    if (tag === 'button' || (tag === 'input' && ['button', 'submit', 'reset'].includes(type))) return 'button';
                    if (tag === 'select') return 'combobox';
                    if (tag === 'textarea') return 'textbox';
                    if (tag === 'input' && type === 'search') return 'searchbox';
                    if (tag === 'input' && ['checkbox', 'radio'].includes(type)) return type;
                    if (tag === 'input' && !['button', 'submit', 'reset', 'hidden'].includes(type)) return 'textbox';
                    return '';
                };
                const accessibleName = el => clean(
                    el.getAttribute('aria-label') ||
                    [...(el.labels || [])].map(label => label.innerText).join(' ') ||
                    el.getAttribute('alt') || el.getAttribute('placeholder') ||
                    el.innerText || el.getAttribute('title') || el.getAttribute('name')
                );
                const visibleInteractive = [
                    ...document.querySelectorAll('a[href],button,[role],input,textarea,select')
                ].filter(visible);
                const selectorCandidates = el => {
                    const tag = el.tagName.toLowerCase(), candidates = [];
                    const addCss = selector => {
                        if (uniqueVisible(selector) && !candidates.includes(selector)) candidates.push(selector);
                    };
                    if (el.id) addCss('#' + CSS.escape(el.id));
                    for (const attribute of ['data-testid', 'data-test', 'data-qa', 'name', 'aria-label', 'placeholder']) {
                        const value = el.getAttribute(attribute);
                        if (value) addCss(`${tag}[${attribute}=${cssValue(value)}]`);
                    }
                    const role = el.getAttribute('role') || implicitRole(el);
                    const name = accessibleName(el);
                    if (role && name && name.length <= 120) {
                        const peers = visibleInteractive.filter(candidate =>
                            (candidate.getAttribute('role') || implicitRole(candidate)) === role &&
                            accessibleName(candidate) === name
                        );
                        if (peers.length === 1) candidates.push(`role=${role}[name=${cssValue(name)}]`);
                    }
                    const text = clean(el.innerText);
                    if (['a', 'button'].includes(tag) && text && text.length <= 120) {
                        const peers = visibleInteractive.filter(candidate =>
                            candidate.tagName.toLowerCase() === tag && clean(candidate.innerText) === text
                        );
                        if (peers.length === 1) candidates.push(`text=${text}`);
                    }
                    return [...new Set(candidates)].slice(0, 5);
                };
                const describe = el => ({
                    tag: el.tagName.toLowerCase(),
                    type: el.getAttribute('type') || '',
                    role: el.getAttribute('role') || implicitRole(el),
                    id: el.id || '',
                    name: el.getAttribute('name') || '',
                    accessibleName: accessibleName(el),
                    placeholder: el.getAttribute('placeholder') || '',
                    text: clean(el.innerText || (['button', 'submit'].includes(el.type) ? el.value : '')),
                    selectorCandidates: selectorCandidates(el)
                });
                const take = (selector, mapper, n = 40) =>
                    [...root.querySelectorAll(selector)].filter(visible).slice(0, n).map(mapper);
                return {
                    description: document.querySelector('meta[name=description]')?.content || '',
                    language: document.documentElement.lang || '',
                    headings: take('h1,h2,h3,h4,h5,h6', el => ({level: el.tagName, text: clean(el.innerText)})),
                    links: take('a[href]', el => ({
                        text: clean(el.innerText), href: el.href,
                        selectorCandidates: selectorCandidates(el)
                    }), 60),
                    forms: take('form', form => ({
                        action: form.action,
                        method: form.method,
                        accessibleName: accessibleName(form),
                        fields: [...form.querySelectorAll('input,textarea,select,button')]
                            .filter(visible).slice(0, 30).map(describe)
                    }), 20),
                    controls: take('button,[role=button],input,textarea,select', describe, 80),
                    textPreview: clean(root.innerText).slice(0, 1500)
                };
            }"""
        )
        summary = {
            "url": self._page().url,
            "title": await self._page().title(),
            **data,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))

    async def cmd_screenshot(self, args: list[str]) -> None:
        target = Path(args[0] if args else "screenshots/page.png").expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        await self._page().screenshot(path=str(target), full_page=True)
        print(target)

    async def cmd_cookies(self, _: list[str]) -> None:
        if self.context is None:
            raise RuntimeError("Browser has not started")
        print(json.dumps(await self.context.cookies(), indent=2, ensure_ascii=False))

    async def cmd_new(self, args: list[str]) -> None:
        if self.context is None:
            raise RuntimeError("Browser has not started")
        self.page = await self.context.new_page()
        self.refs.clear()
        if args:
            await self.cmd_goto(args)
        print(f"Active tab: {self.page.url}")

    async def cmd_tabs(self, _: list[str]) -> None:
        if self.context is None:
            raise RuntimeError("Browser has not started")
        for index, page in enumerate(self.context.pages, 1):
            marker = "*" if page is self.page else " "
            print(f"{marker} {index}. {clipped(await page.title(), 50)}  {page.url}")

    async def cmd_use(self, args: list[str]) -> None:
        if self.context is None or not args or not args[0].isdigit():
            raise ValueError("Usage: use <tab-number>")
        index = int(args[0]) - 1
        if not 0 <= index < len(self.context.pages):
            raise ValueError("Tab number is out of range")
        self.page = self.context.pages[index]
        await self.page.bring_to_front()
        self.refs.clear()
        print(f"Active tab: {self.page.url}")

    async def cmd_close_tab(self, _: list[str]) -> None:
        if self.context is None or self.page is None:
            raise RuntimeError("Browser has not started")
        pages = self.context.pages
        if len(pages) == 1:
            print("Cannot close the only tab; use 'quit' to exit.")
            return
        current = self.page
        self.page = next(page for page in pages if page is not current)
        await current.close()
        self.refs.clear()
        print(f"Active tab: {self.page.url}")

    async def cmd_quit(self, _: list[str]) -> None:
        self.running = False

    async def cmd_exit(self, args: list[str]) -> None:
        await self.cmd_quit(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Navigate and inspect websites from an interactive Playwright CLI."
    )
    parser.add_argument("url", nargs="?", help="Optional URL to open at startup")
    parser.add_argument(
        "-c",
        "--command",
        action="append",
        default=[],
        help="Run a CLI command; repeat to run several commands in order",
    )
    parser.add_argument(
        "--chrome-path", help="Path to an existing Chrome executable (normally auto-detected)"
    )
    parser.add_argument("--headless", action="store_true", help="Run without a browser window")
    parser.add_argument(
        "--stay-open", action="store_true", help="Enter the REPL after --command commands finish"
    )
    parser.add_argument(
        "--pipe",
        action="store_true",
        help="Keep the browser open and accept JSON-line commands over standard input",
    )
    parser.add_argument("--timeout", type=int, default=10_000, help="Action timeout in milliseconds")
    parser.add_argument("--user-agent", help="Override the browser user agent")
    return parser


async def async_main(args: argparse.Namespace) -> int:
    cli = WebCLI(
        chrome_path=args.chrome_path,
        headless=args.headless,
        timeout_ms=args.timeout,
        user_agent=args.user_agent,
    )
    try:
        await cli.start()
        if args.url:
            await cli.cmd_goto([args.url])
        for command in args.command:
            await cli.execute(command)
            if not cli.running:
                break
        if cli.running and args.pipe:
            await cli.pipe_loop()
        elif cli.running and (not args.command or args.stay_open):
            await cli.repl()
        return 0
    except (FileNotFoundError, PlaywrightError) as exc:
        print(f"Could not start or control the browser: {exc}", file=sys.stderr)
        print("This CLI uses the existing local Python, Playwright module, and Chrome.", file=sys.stderr)
        return 1
    finally:
        await cli.close()


def main() -> int:
    return asyncio.run(async_main(build_parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
