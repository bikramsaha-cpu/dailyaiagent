from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Sequence

from core.llm_client import LLMConfig, OpenAICompatibleLLM
from core.browser_diagnostics import collect_page_diagnostics
from core.locator_registry import LocatorRegistry, RegistryEntry
from core.settings import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from core.store import ExecutionStore


@dataclass(slots=True)
class LocatorSpec:
    name: str
    selectors: Sequence[str]
    role: str | None = None
    role_name: str | None = None
    text: str | None = None
    exact: bool = False
    intent: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LocatorHealer:
    def __init__(self, store: ExecutionStore | None = None, llm: OpenAICompatibleLLM | None = None):
        self.store = store or ExecutionStore()
        self.registry = LocatorRegistry()
        self.llm = llm or OpenAICompatibleLLM(
            LLMConfig(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, model=LLM_MODEL)
        )

    def resolve(
        self,
        page,
        spec: LocatorSpec,
        *,
        suite_name: str | None = None,
        module_name: str | None = None,
        test_name: str | None = None,
        action: str | None = None,
    ):
        context = collect_page_diagnostics(page, action=action, locator_name=spec.name, intent=spec.intent)
        origin_selector = spec.selectors[0] if spec.selectors else None
        tried: list[str] = []
        failure_notes: list[str] = []
        registry_entry = self.registry.get(spec.name)
        candidate_selectors = []
        if registry_entry and registry_entry.selector:
            candidate_selectors.append(registry_entry.selector)
        for selector in spec.selectors:
            candidate_selectors.extend(self._expand_selector_variants(selector, spec))

        for selector in candidate_selectors:
            if selector in tried:
                continue
            tried.append(selector)
            locator = self._safe_locator(page, selector)
            try:
                if locator.count() > 0 and self._candidate_is_good(locator.first, spec, action):
                    strategy = "registry" if registry_entry and selector == registry_entry.selector else ("primary" if selector == spec.selectors[0] else "fallback")
                    healed = locator.first
                    self._record_heal(
                        spec,
                        healed,
                        selector,
                        strategy,
                        suite_name,
                        module_name,
                        test_name,
                        context,
                        previous_selector=origin_selector,
                    )
                    return healed
                failure_notes.append(f"{selector}:present-but-rejected")
            except Exception:
                failure_notes.append(f"{selector}:error")
                continue

        for role_selector in self._role_candidates(page, spec):
            tried.append(role_selector["selector"])
            locator = role_selector["locator"]
            try:
                if locator.count() > 0 and self._candidate_is_good(locator.first, spec, action):
                    self._record_heal(
                        spec,
                        locator.first,
                        role_selector["selector"],
                        role_selector["strategy"],
                        suite_name,
                        module_name,
                        test_name,
                        context,
                        previous_selector=origin_selector,
                    )
                    return locator.first
                failure_notes.append(f"{role_selector['selector']}:present-but-rejected")
            except Exception:
                failure_notes.append(f"{role_selector['selector']}:error")
                continue

        for text_selector in self._text_candidates(page, spec):
            if text_selector["selector"] in tried:
                continue
            locator = text_selector["locator"]
            try:
                if locator.count() > 0 and self._candidate_is_good(locator.first, spec, action):
                    self._record_heal(
                        spec,
                        locator.first,
                        text_selector["selector"],
                        text_selector["strategy"],
                        suite_name,
                        module_name,
                        test_name,
                        context,
                        previous_selector=origin_selector,
                    )
                    return locator.first
                failure_notes.append(f"{text_selector['selector']}:present-but-rejected")
            except Exception:
                failure_notes.append(f"{text_selector['selector']}:error")
                continue

        for intent_selector in self._intent_candidates(page, spec):
            if intent_selector["selector"] in tried:
                continue
            locator = intent_selector["locator"]
            try:
                if locator.count() > 0 and self._candidate_is_good(locator.first, spec, action):
                    self._record_heal(
                        spec,
                        locator.first,
                        intent_selector["selector"],
                        intent_selector["strategy"],
                        suite_name,
                        module_name,
                        test_name,
                        context,
                        previous_selector=origin_selector,
                    )
                    return locator.first
                failure_notes.append(f"{intent_selector['selector']}:present-but-rejected")
            except Exception:
                failure_notes.append(f"{intent_selector['selector']}:error")
                continue

        for selector in self._llm_candidates(spec, context):
            if selector in tried:
                continue
            locator = self._safe_locator(page, selector)
            try:
                if locator.count() > 0 and self._candidate_is_good(locator.first, spec, action):
                    healed = locator.first
                    self._record_heal(
                        spec,
                        healed,
                        selector,
                        "llm",
                        suite_name,
                        module_name,
                        test_name,
                        context,
                        previous_selector=origin_selector,
                    )
                    return healed
                failure_notes.append(f"{selector}:present-but-rejected")
            except Exception:
                failure_notes.append(f"{selector}:error")
                continue

        for candidate in self._dom_candidates(page, spec):
            selector = candidate["selector"]
            if selector in tried:
                continue
            locator = candidate["locator"]
            try:
                if locator.count() > 0 and self._candidate_is_good(locator.first, spec, action):
                    healed = locator.first
                    self._record_heal(
                        spec,
                        healed,
                        selector,
                        candidate["strategy"],
                        suite_name,
                        module_name,
                        test_name,
                        context,
                        previous_selector=origin_selector,
                        evidence=candidate.get("evidence"),
                    )
                    return healed
                failure_notes.append(f"{selector}:present-but-rejected")
            except Exception:
                failure_notes.append(f"{selector}:error")
                continue

        self._record_unresolved(spec, suite_name, module_name, test_name, context, origin_selector, tried, failure_notes)
        raise LookupError(f"Could not resolve locator '{spec.name}'")

    def click(self, page, spec: LocatorSpec, **kwargs):
        locator = self.resolve(page, spec, action="click", **kwargs)
        locator.scroll_into_view_if_needed()
        self._click_with_recovery(page, locator)
        return locator

    def fill(self, page, spec: LocatorSpec, value: str, **kwargs):
        locator = self.resolve(page, spec, action="fill", **kwargs)
        locator.scroll_into_view_if_needed()
        locator.fill(value)
        return locator

    def select_option(self, page, spec: LocatorSpec, value: str, **kwargs):
        locator = self.resolve(page, spec, action="select", **kwargs)
        locator.select_option(value)
        return locator

    def _role_candidates(self, page, spec: LocatorSpec):
        candidates = []
        if spec.role and spec.role_name:
            role_locator = page.get_by_role(spec.role, name=spec.role_name, exact=spec.exact)
            candidates.append(
                {
                    "selector": f"role={spec.role}[name={spec.role_name}]",
                    "locator": role_locator,
                    "strategy": "role",
                }
            )
        if spec.text:
            text_locator = page.get_by_text(spec.text, exact=spec.exact)
            candidates.append({"selector": f"text={spec.text}", "locator": text_locator, "strategy": "text"})
        return candidates

    def _text_candidates(self, page, spec: LocatorSpec):
        candidates = []
        texts = list(spec.metadata.get("keywords", []))
        if spec.name:
            texts.extend(self._selector_keywords(spec.name))
        if spec.text:
            texts.append(spec.text)

        seen: set[str] = set()
        for text in texts:
            normalized = text.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            candidates.append(
                {
                    "selector": f"text={normalized}",
                    "locator": page.get_by_text(normalized, exact=False),
                    "strategy": "text",
                }
            )
            candidates.append(
                {
                    "selector": f"role=button[name={normalized}]",
                    "locator": page.get_by_role("button", name=normalized, exact=False),
                    "strategy": "role",
                }
            )
        return candidates

    def _llm_candidates(self, spec: LocatorSpec, context: dict[str, Any]) -> list[str]:
        if not self.llm.enabled:
            return []
        enriched_context = dict(context)
        enriched_context.update(
            {
                "locator_name": spec.name,
                "selectors": list(spec.selectors),
                "metadata": spec.metadata,
                "intent": spec.intent,
            }
        )
        return self.llm.suggest_selectors(spec.name, list(spec.selectors), context=enriched_context)

    def _intent_candidates(self, page, spec: LocatorSpec):
        haystack = " ".join(
            item for item in [spec.intent or "", spec.text or "", spec.name or ""] if item
        ).lower()
        if "contact supplier" not in haystack and "suplr" not in haystack and "contactsupplier" not in haystack:
            return []

        selectors = [
            "[data-click^='CTAContactSupplier']",
            "button[data-click^='CTAContactSupplier']",
            "[data-click*='ContactSupplier']",
            "button[data-click*='ContactSupplier']",
            "#head-suplr",
            "[id*='suplr']",
            "[class*='contactsupplier']",
            "button.contactsupplier",
            "button:has-text('Contact Supplier')",
            "a:has-text('Contact Supplier')",
            "span:has-text('Contact Supplier')",
            "text=Contact Supplier",
            "[aria-label*='Contact Supplier']",
            "[title*='Contact Supplier']",
            "text=Get Best Quote",
        ]
        candidates = []
        for selector in selectors:
            if selector.startswith("text="):
                locator = page.get_by_text(selector.replace("text=", "", 1), exact=False)
            else:
                locator = self._safe_locator(page, selector)
            candidates.append(
                {
                    "selector": selector,
                    "locator": locator,
                    "strategy": "intent",
                }
            )
        return candidates

    def _dom_candidates(self, page, spec: LocatorSpec) -> list[dict[str, Any]]:
        try:
            elements = page.evaluate(
                """
                () => {
                    const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                    const nodes = Array.from(document.querySelectorAll(
                        'button, a, input, textarea, select, label, [role], [aria-label], [title], [data-testid], [data-click], [name]'
                    ));
                    return nodes.slice(0, 120).map((el, index) => ({
                        index,
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        role: el.getAttribute('role') || '',
                        type: el.getAttribute('type') || '',
                        text: normalize(el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || ''),
                        ariaLabel: el.getAttribute('aria-label') || '',
                        title: el.getAttribute('title') || '',
                        name: el.getAttribute('name') || '',
                        dataTestid: el.getAttribute('data-testid') || '',
                        dataClick: el.getAttribute('data-click') || '',
                        className: normalize(el.className || ''),
                        outerHTML: (el.outerHTML || '').slice(0, 400),
                    }));
                }
                """
            )
        except Exception:
            return []

        keywords = self._candidate_keywords(spec)
        candidates: list[dict[str, Any]] = []
        for element in elements:
            score = self._score_dom_candidate(element, keywords, spec)
            if score <= 0:
                continue
            for candidate in self._locators_from_dom_element(page, element):
                candidate["score"] = score
                candidate["evidence"] = element
                candidates.append(candidate)
        candidates.sort(key=lambda item: item["score"], reverse=True)
        return self._dedupe_candidates(candidates)

    def _locators_from_dom_element(self, page, element: dict[str, Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        text = (element.get("text") or "").strip()
        tag = (element.get("tag") or "").strip().lower()
        role = (element.get("role") or "").strip().lower() or self._default_role_for_tag(tag)

        for key in ("dataTestid", "dataClick", "ariaLabel", "title", "name", "id"):
            value = (element.get(key) or "").strip()
            if not value:
                continue
            selector = self._attribute_selector(key, value)
            if not selector:
                continue
            candidates.append(
                {
                    "selector": selector,
                    "locator": self._safe_locator(page, selector),
                    "strategy": f"dom-{key.lower()}",
                }
            )

        if text:
            if role:
                candidates.append(
                    {
                        "selector": f"role={role}[name={text}]",
                        "locator": page.get_by_role(role, name=text, exact=False),
                        "strategy": "dom-role",
                    }
                )
            candidates.append(
                {
                    "selector": f"text={text}",
                    "locator": page.get_by_text(text, exact=False),
                    "strategy": "dom-text",
                }
            )

        if tag in {"button", "a", "label", "div", "span"} and text:
            candidates.append(
                {
                    "selector": f'{tag}:has-text({json.dumps(text)})',
                    "locator": page.locator(f'{tag}:has-text({json.dumps(text)})'),
                    "strategy": "dom-has-text",
                }
            )

        return candidates

    def _attribute_selector(self, key: str, value: str) -> str | None:
        quoted = json.dumps(value)
        if key == "id":
            if re.match(r"^[A-Za-z_][A-Za-z0-9_\-:.]*$", value):
                return f"#{value}"
            return f'[id={quoted}]'
        if key == "dataTestid":
            return f'[data-testid={quoted}]'
        if key == "dataClick":
            return f'[data-click={quoted}]'
        if key == "ariaLabel":
            return f'[aria-label={quoted}]'
        if key == "title":
            return f'[title={quoted}]'
        if key == "name":
            return f'[name={quoted}]'
        return None

    def _score_dom_candidate(self, element: dict[str, Any], keywords: list[str], spec: LocatorSpec) -> int:
        haystack = " ".join(
            str(element.get(field) or "")
            for field in ("tag", "role", "type", "id", "text", "ariaLabel", "title", "name", "dataTestid", "dataClick", "className")
        ).lower()
        score = 0
        intent_keywords = self._intent_keywords(spec)
        for keyword in intent_keywords:
            keyword = keyword.lower().strip()
            if keyword and keyword in haystack:
                score += 6
        for keyword in keywords:
            keyword = keyword.lower().strip()
            if not keyword:
                continue
            if keyword in haystack:
                score += 4
            else:
                ratio = SequenceMatcher(None, keyword, haystack).ratio()
                if ratio >= 0.75:
                    score += 2
        if spec.text and str(element.get("text") or "").strip().lower() == spec.text.strip().lower():
            score += 5
        if spec.intent and self._intent_phrase(spec.intent).lower() in haystack:
            score += 4
        if spec.name and str(spec.name).lower() in haystack:
            score += 2
        if element.get("dataClick"):
            score += 1
        if element.get("dataTestid"):
            score += 1
        if element.get("ariaLabel"):
            score += 1
        return score

    @staticmethod
    def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for candidate in candidates:
            selector = candidate.get("selector", "")
            if selector in seen:
                continue
            seen.add(selector)
            deduped.append(candidate)
        return deduped

    @staticmethod
    def _default_role_for_tag(tag: str) -> str | None:
        return {
            "button": "button",
            "a": "link",
            "input": "textbox",
            "textarea": "textbox",
            "select": "combobox",
        }.get(tag)

    @staticmethod
    def _is_usable(locator, action: str | None) -> bool:
        try:
            if action == "click":
                return locator.is_visible() and locator.is_enabled()
            if action == "fill":
                return locator.is_visible() and locator.is_editable()
            if action == "select":
                return locator.is_visible() and locator.is_enabled()
            return locator.is_visible()
        except Exception:
            return False

    def _candidate_is_good(self, locator, spec: LocatorSpec, action: str | None) -> bool:
        if not self._is_usable(locator, action):
            return False
        try:
            evidence = self._locator_evidence(locator)
        except Exception:
            evidence = {}
        return self._evidence_matches_spec(evidence, spec)

    @staticmethod
    def _locator_evidence(locator) -> dict[str, Any]:
        return locator.evaluate(
            """el => {
                const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
                return {
                    tag: el.tagName.toLowerCase(),
                    id: el.id || '',
                    role: el.getAttribute('role') || '',
                    type: el.getAttribute('type') || '',
                    text: normalize(el.innerText || el.value || ''),
                    ariaLabel: el.getAttribute('aria-label') || '',
                    title: el.getAttribute('title') || '',
                    name: el.getAttribute('name') || '',
                    dataTestid: el.getAttribute('data-testid') || '',
                    dataClick: el.getAttribute('data-click') || '',
                    className: normalize(el.className || ''),
                };
            }"""
        )

    @staticmethod
    def _evidence_matches_spec(evidence: dict[str, Any], spec: LocatorSpec) -> bool:
        haystack = " ".join(
            str(evidence.get(field) or "")
            for field in ("tag", "role", "type", "id", "text", "ariaLabel", "title", "name", "dataTestid", "dataClick", "className")
        ).lower()
        if LocatorHealer._is_contact_supplier_intent(spec):
            return LocatorHealer._matches_contact_supplier_cta(haystack)
        intent_keywords = LocatorHealer._intent_keywords(spec)
        selector_keywords = LocatorHealer._candidate_keywords(spec)
        strong_terms = [term.lower() for term in intent_keywords + selector_keywords if term]
        if spec.text and str(evidence.get("text") or "").strip().lower() == spec.text.strip().lower():
            return True
        if spec.role and str(evidence.get("role") or "").strip().lower() == spec.role.lower():
            if spec.role_name and spec.role_name.lower() in haystack:
                return True
            if spec.intent and any(term in haystack for term in intent_keywords):
                return True
        return any(term in haystack for term in strong_terms if len(term) >= 3)

    @staticmethod
    def _is_contact_supplier_intent(spec: LocatorSpec) -> bool:
        joined = " ".join(item for item in [spec.intent or "", spec.text or "", spec.name or ""] if item).lower()
        return "contact supplier" in joined or "contactsupplier" in joined or "suplr" in joined

    @staticmethod
    def _matches_contact_supplier_cta(haystack: str) -> bool:
        positive_signals = [
            "contact supplier",
            "contactsupplier",
            "ctacontactsupplier",
            "get best quote",
            "suplr",
            "enquiry",
            "enq",
        ]
        negative_signals = [
            "explore",
            "similar products",
            "advertisement",
            "noida",
            "hyderabad",
            "producttitle",
            "prod0name",
            "tablist",
            "carousel",
        ]
        if any(signal in haystack for signal in negative_signals):
            return False
        return any(signal in haystack for signal in positive_signals)

    def _record_heal(
        self,
        spec: LocatorSpec,
        locator,
        selector: str,
        strategy: str,
        suite_name: str | None,
        module_name: str | None,
        test_name: str | None,
        context: dict[str, Any],
        previous_selector: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        html_snapshot = self._snapshot_html(locator)
        entry = RegistryEntry(
            selector=selector,
            strategy=strategy,
            page_url=context.get("page_url"),
            page_title=context.get("page_title"),
            html_snapshot=html_snapshot,
            updated_at=datetime_now(),
            metadata={
                "source": spec.name,
                "selectors": list(spec.selectors),
                "metadata": spec.metadata,
                "previous_selector": previous_selector,
                "strategy": strategy,
                "evidence": evidence or {},
            },
        )
        self.registry.set(spec.name, entry)
        self.store.record_locator_healing(
            locator_name=spec.name,
            previous_selector=previous_selector,
            strategy=strategy,
            chosen_selector=selector,
            suite_name=suite_name,
            module_name=module_name,
            test_name=test_name,
            page_url=context.get("page_url"),
            page_title=context.get("page_title"),
            html_snapshot=html_snapshot,
            details={
                "selectors": list(spec.selectors),
                "metadata": spec.metadata,
                "evidence": evidence or {},
                "registry_selector": selector,
                "diagnostics": {
                    "provider": context.get("provider"),
                    "interceptors": context.get("interceptors", []),
                    "candidates": context.get("candidates", [])[:10],
                    "devtools": context.get("devtools"),
                },
            },
        )

    def _record_unresolved(
        self,
        spec: LocatorSpec,
        suite_name: str | None,
        module_name: str | None,
        test_name: str | None,
        context: dict[str, Any],
        previous_selector: str | None,
        tried: list[str],
        failure_notes: list[str],
    ) -> None:
        self.store.record_locator_healing(
            locator_name=spec.name,
            previous_selector=previous_selector,
            strategy="unresolved",
            chosen_selector=previous_selector or spec.name,
            suite_name=suite_name,
            module_name=module_name,
            test_name=test_name,
            page_url=context.get("page_url"),
            page_title=context.get("page_title"),
            html_snapshot=None,
            details={
                "selectors": list(spec.selectors),
                "metadata": spec.metadata,
                "tried": tried,
                "failure_notes": failure_notes[-20:],
                "page_text": context.get("page_text"),
                "diagnostics": {
                    "provider": context.get("provider"),
                    "interceptors": context.get("interceptors", []),
                    "candidates": context.get("candidates", [])[:10],
                    "devtools": context.get("devtools"),
                },
            },
        )

    @staticmethod
    def _safe_locator(page, selector: str):
        selectors = [part.strip() for part in selector.split(",") if part.strip()]
        if len(selectors) == 1:
            return page.locator(selectors[0])
        try:
            return page.locator(selector)
        except Exception:
            # Fall back to the first usable selector in the comma chain.
            return page.locator(selectors[0])

    def _click_with_recovery(self, page, locator, **kwargs) -> None:
        try:
            locator.click(**kwargs)
            return
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}".lower()
            if "intercepts pointer events" not in message and "another element would receive the click" not in message:
                raise

        self._dismiss_interceptors(page)
        locator.scroll_into_view_if_needed()
        try:
            retry_kwargs = dict(kwargs)
            retry_kwargs.setdefault("timeout", 5000)
            locator.click(**retry_kwargs)
            return
        except Exception:
            pass

        self._dismiss_interceptors(page)
        locator.scroll_into_view_if_needed()
        final_kwargs = dict(kwargs)
        final_kwargs.setdefault("timeout", 5000)
        final_kwargs["force"] = True
        locator.click(**final_kwargs)

    @staticmethod
    def _dismiss_interceptors(page) -> None:
        selectors = [
            "#t0102_blkwrap",
            ".blckbg",
            ".imgDivs",
            "#cityPopupOverlay",
            ".modal-backdrop",
            "[class*='overlay']",
            "[class*='backdrop']",
        ]
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        for selector in selectors:
            try:
                page.evaluate(
                    """selector => {
                        for (const node of document.querySelectorAll(selector)) {
                            node.style.pointerEvents = 'none';
                            node.style.visibility = 'hidden';
                            node.style.opacity = '0';
                        }
                    }""",
                    selector,
                )
            except Exception:
                continue

    @staticmethod
    def _snapshot_html(locator) -> str | None:
        try:
            if locator is None:
                return None
            return locator.evaluate(
                """el => {
                    const attrs = Array.from(el.attributes).map(a => `${a.name}="${a.value}"`).join(" ");
                    const text = (el.innerText || el.value || '').trim().replace(/\\s+/g, ' ').slice(0, 240);
                    return `<${el.tagName.toLowerCase()} ${attrs}>${text}</${el.tagName.toLowerCase()}>`;
                }"""
            )
        except Exception:
            return None

    @staticmethod
    def _selector_keywords(selector: str) -> list[str]:
        tokens = re.split(r"[^A-Za-z0-9]+", selector)
        keywords = []
        for token in tokens:
            if len(token) < 4:
                continue
            if token.lower() in {"span", "button", "input", "div", "form", "class", "value", "type"}:
                continue
            cleaned = re.sub(r"\d+", "", token)
            if cleaned and cleaned.lower() not in {"span", "button", "input", "div", "form"}:
                keywords.append(cleaned.replace("camel", " ").strip())
        return keywords

    @staticmethod
    def _candidate_keywords(spec: LocatorSpec) -> list[str]:
        keywords = list(spec.metadata.get("keywords", []))
        keywords.extend(LocatorHealer._intent_keywords(spec))
        if spec.name:
            keywords.extend(LocatorHealer._selector_keywords(spec.name))
        if spec.text:
            keywords.extend(LocatorHealer._selector_keywords(spec.text))
        return [keyword for keyword in keywords if keyword]

    @staticmethod
    def _intent_keywords(spec: LocatorSpec) -> list[str]:
        return LocatorHealer._intent_keywords_from_text(spec.intent) + LocatorHealer._intent_keywords_from_text(spec.name)

    @staticmethod
    def _intent_keywords_from_text(text: str | None) -> list[str]:
        if not text:
            return []
        pieces = re.split(r"[^A-Za-z0-9]+", text)
        stop_words = {"click", "tap", "press", "open", "enter", "fill", "select", "wait", "for", "the", "to", "a", "an", "on"}
        return [piece for piece in pieces if piece and piece.lower() not in stop_words]

    @staticmethod
    def _intent_phrase(text: str | None) -> str:
        if not text:
            return ""
        return " ".join(LocatorHealer._intent_keywords_from_text(text))

    @staticmethod
    def _expand_selector_variants(selector: str, spec: LocatorSpec) -> list[str]:
        variants: list[str] = []
        for candidate in [selector]:
            if candidate and candidate not in variants:
                variants.append(candidate)

        split_selectors = [part.strip() for part in selector.split(",") if part.strip()]
        for candidate in split_selectors:
            if candidate not in variants:
                variants.append(candidate)

        startswith_matches = re.findall(r"\[([a-zA-Z0-9_-]+)=['\"]\^([^'\"]+)['\"]\]", selector)
        for attr, value in startswith_matches:
            for variant in [
                selector.replace(f"[{attr}='^{value}']", f"[{attr}^='{value}']"),
                selector.replace(f'[{attr}="^{value}"]', f'[{attr}^="{value}"]'),
                selector.replace(f"[{attr}='^{value}']", f"[{attr}*='{value}']"),
                selector.replace(f'[{attr}="^{value}"]', f'[{attr}*="{value}"]'),
                f"[{attr}^='{value}']",
                f"[{attr}*='{value}']",
            ]:
                if variant not in variants:
                    variants.append(variant)

        if "contactsupplier" in selector.lower() or "contact supplier" in (spec.intent or "").lower():
            for variant in [
                "button:has-text('Contact Supplier')",
                "a:has-text('Contact Supplier')",
                "span:has-text('Contact Supplier')",
                "[data-click^='CTAContactSupplier']",
                "[data-click*='ContactSupplier']",
                "button.contactsupplier",
                "#head-suplr",
            ]:
                if variant not in variants:
                    variants.append(variant)

        return variants


def datetime_now() -> str:
    from datetime import datetime

    return datetime.now().isoformat(timespec="seconds")


class HealingLocator:
    def __init__(self, page, locator, healer: LocatorHealer, spec: LocatorSpec, context: dict[str, Any]):
        self._page = page
        self._locator = locator
        self._healer = healer
        self._spec = spec
        self._context = context

    def __getattr__(self, item):
        attr = getattr(self._locator, item)
        if item in {"first", "last"} and attr is not None:
            return HealingLocator(self._page, attr, self._healer, self._spec, self._context)
        return attr

    def nth(self, index: int):
        return HealingLocator(self._page, self._locator.nth(index), self._healer, self._spec, self._context)

    def click(self, **kwargs):
        try:
            return self._healer._click_with_recovery(self._page, self._locator, **kwargs)
        except Exception:
            healed = self._healer.resolve(
                self._page,
                self._spec,
                suite_name=self._context.get("suite_name"),
                module_name=self._context.get("module_name"),
                test_name=self._context.get("test_name"),
                action="click",
            )
            return self._healer._click_with_recovery(self._page, healed, **kwargs)

    def fill(self, value, **kwargs):
        try:
            return self._locator.fill(value, **kwargs)
        except Exception:
            healed = self._healer.resolve(
                self._page,
                self._spec,
                suite_name=self._context.get("suite_name"),
                module_name=self._context.get("module_name"),
                test_name=self._context.get("test_name"),
                action="fill",
            )
            return healed.fill(value, **kwargs)

    def select_option(self, value=None, **kwargs):
        try:
            if value is None:
                return self._locator.select_option(**kwargs)
            return self._locator.select_option(value, **kwargs)
        except Exception:
            healed = self._healer.resolve(
                self._page,
                self._spec,
                suite_name=self._context.get("suite_name"),
                module_name=self._context.get("module_name"),
                test_name=self._context.get("test_name"),
                action="select",
            )
            if value is None:
                return healed.select_option(**kwargs)
            return healed.select_option(value, **kwargs)


class HealingPage:
    def __init__(self, page, healer: LocatorHealer | None = None, *, suite_name: str | None = None, module_name: str | None = None, test_name: str | None = None):
        self._page = page
        self._healer = healer or DEFAULT_HEALER
        self._context = {
            "suite_name": suite_name,
            "module_name": module_name,
            "test_name": test_name,
        }

    def __getattr__(self, item):
        return getattr(self._page, item)

    def locator(self, selector, **kwargs):
        locator = self._page.locator(selector, **kwargs)
        spec = LocatorSpec(
            name=selector,
            selectors=[selector],
            metadata={"keywords": LocatorHealer._selector_keywords(selector)},
        )
        return HealingLocator(self._page, locator, self._healer, spec, self._context)

    def click(self, selector, **kwargs):
        spec = self._build_spec(selector, kwargs)
        locator = self._page.locator(selector)
        return HealingLocator(self._page, locator, self._healer, spec, self._context).click(**kwargs)

    def fill(self, selector, value, **kwargs):
        spec = self._build_spec(selector, kwargs)
        locator = self._page.locator(selector)
        return HealingLocator(self._page, locator, self._healer, spec, self._context).fill(value, **kwargs)

    def select_option(self, selector, value=None, **kwargs):
        spec = self._build_spec(selector, kwargs)
        locator = self._page.locator(selector)
        return HealingLocator(self._page, locator, self._healer, spec, self._context).select_option(value, **kwargs)

    def wait_for_selector(self, selector, **kwargs):
        try:
            return self._page.wait_for_selector(selector, **kwargs)
        except Exception:
            healed = self._healer.resolve(
                self._page,
                LocatorSpec(name=selector, selectors=[selector], metadata={"keywords": LocatorHealer._selector_keywords(selector)}),
                suite_name=self._context.get("suite_name"),
                module_name=self._context.get("module_name"),
                test_name=self._context.get("test_name"),
            )
            state = kwargs.get("state", "visible")
            timeout = kwargs.get("timeout")
            healed.wait_for(state=state, timeout=timeout)
            return healed.element_handle()

    @property
    def mouse(self):
        return self._page.mouse

    @property
    def keyboard(self):
        return self._page.keyboard

    @property
    def url(self):
        return self._page.url

    def title(self):
        return self._page.title()

    def goto(self, *args, **kwargs):
        return self._page.goto(*args, **kwargs)

    def wait_for_timeout(self, *args, **kwargs):
        return self._page.wait_for_timeout(*args, **kwargs)

    def wait_for_load_state(self, *args, **kwargs):
        return self._page.wait_for_load_state(*args, **kwargs)

    def _build_spec(self, selector: str, kwargs: dict[str, Any]) -> LocatorSpec:
        keywords = list(kwargs.pop("keywords", []))
        text = kwargs.pop("text", None)
        intent = kwargs.pop("intent", None)
        role = kwargs.pop("role", None)
        role_name = kwargs.pop("role_name", None)
        exact = kwargs.pop("exact", False)
        if text:
            keywords.extend(LocatorHealer._selector_keywords(text))
        if intent:
            keywords.extend(LocatorHealer._intent_keywords_from_text(intent))
        if not keywords:
            keywords = LocatorHealer._selector_keywords(selector)
        selectors = [part.strip() for part in selector.split(",") if part.strip()] or [selector]
        return LocatorSpec(
            name=selector,
            selectors=selectors,
            role=role,
            role_name=role_name,
            text=text,
            exact=exact,
            intent=intent,
            metadata={
                "keywords": keywords,
                "intent": intent,
            },
        )


def attach_healing(page, *, suite_name: str | None = None, module_name: str | None = None, test_name: str | None = None, healer: LocatorHealer | None = None):
    return HealingPage(page, healer=healer, suite_name=suite_name, module_name=module_name, test_name=test_name)


DEFAULT_HEALER = LocatorHealer()
