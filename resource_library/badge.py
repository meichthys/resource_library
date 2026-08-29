# Copyright (c) 2026, Meichthys and contributors
# For license information, please see license.txt

"""Per-resource "Recommended on Freely.Giving" embed badge.

Served as a real SVG image so it can be dropped into an <img> tag on someone
else's site. Two constraints shape this module:

1. An SVG rendered inside <img> runs in a restricted mode: it cannot load any
   external resource. The resource icon therefore has to be inlined as a
   base64 data URI rather than referenced by URL.
2. The badge asserts a recommendation, so it is generated on demand and 404s
   the moment a resource stops being published or recommended. A static file
   could not be revoked once someone had embedded it.
"""

import base64
import mimetypes
import os
from html import escape
from urllib.parse import unquote

import frappe
from frappe.website.page_renderers.base_renderer import BaseRenderer
from frappe.website.utils import build_response

BADGE_SIZE = 200
THEMES = ("dark", "light")

# Icon is base64-inlined into every badge request, so cap it. Anything larger
# falls back to the lettermark rather than bloating a third-party page load.
MAX_ICON_BYTES = 150 * 1024

# Title wraps instead of truncating. These are tuned for 15px bold Helvetica
# inside the 200px badge, leaving ~12px side padding.
MAX_TITLE_CHARS_PER_LINE = 21
MAX_TITLE_LINES = 3

PLACEHOLDER_GRADIENTS = (
	("#7c3aed", "#4f46e5"),
	("#0d9488", "#059669"),
	("#db2777", "#e11d48"),
	("#ca8a04", "#a16207"),
	("#2563eb", "#0891b2"),
	("#ea580c", "#dc2626"),
	("#9333ea", "#c026d3"),
	("#64748b", "#334155"),
)

FONT_STACK = "Helvetica Neue, Helvetica, Arial, sans-serif"


def _icon_data_uri(icon):
	"""Inline a locally stored icon as a data URI, or None if unusable."""
	if not icon or icon.startswith(("http://", "https://")):
		# Remote icons cannot be fetched at render time and cannot be
		# referenced from an <img>-rendered SVG, so fall back to the lettermark.
		return None

	relative = icon.lstrip("/")
	if icon.startswith("/private/"):
		path = frappe.get_site_path(*relative.split("/"))
	else:
		path = frappe.get_site_path("public", *relative.split("/"))

	if not os.path.isfile(path) or os.path.getsize(path) > MAX_ICON_BYTES:
		return None

	mime = mimetypes.guess_type(path)[0] or "image/png"
	with open(path, "rb") as f:
		encoded = base64.b64encode(f.read()).decode()

	return f"data:{mime};base64,{encoded}"


def _placeholder_gradient(title):
	total = sum(ord(c) for c in title or "")
	return PLACEHOLDER_GRADIENTS[total % len(PLACEHOLDER_GRADIENTS)]


def _wrap(title, max_chars=MAX_TITLE_CHARS_PER_LINE, max_lines=MAX_TITLE_LINES):
	"""Greedily wrap a title into display lines, ellipsizing only past max_lines."""
	words = (title or "").strip().split()
	if not words:
		return [""]

	lines = []
	current = ""

	for word in words:
		# A single word wider than the line has to be hard split
		while len(word) > max_chars:
			if current:
				lines.append(current)
				current = ""
			lines.append(word[: max_chars - 1] + "-")
			word = word[max_chars - 1 :]

		candidate = f"{current} {word}".strip()
		if len(candidate) <= max_chars:
			current = candidate
		else:
			lines.append(current)
			current = word

	if current:
		lines.append(current)

	if len(lines) > max_lines:
		lines = lines[:max_lines]
		lines[-1] = lines[-1][: max_chars - 1].rstrip() + "…"

	return lines


def build_badge_svg(doc, theme="dark"):
	"""Return the badge SVG markup for a Resource document."""
	if theme not in THEMES:
		theme = "dark"

	dark = theme == "dark"
	raw_title = (doc.title or doc.name or "").strip()
	title = escape(raw_title)
	lines = _wrap(raw_title)

	name_fill = "#ffffff" if dark else "#0f172a"
	kicker_fill = "#ffffff" if dark else "#64748b"
	kicker_opacity = ' fill-opacity="0.72"' if dark else ""
	rule_stroke = "#ffffff" if dark else "#e2e8f0"
	rule_opacity = ' stroke-opacity="0.22"' if dark else ""
	wordmark_fill = "#ffffff" if dark else "url(#rlAccent)"

	# Lay out bottom-up so the wordmark stays pinned while a longer title grows
	# upward, shrinking and raising the icon rather than overflowing the badge.
	wordmark_y = 178
	kicker_y = 157
	divider_y = 140
	line_height = 17
	title_last_y = 127
	title_first_y = title_last_y - (len(lines) - 1) * line_height

	icon_bottom = title_first_y - 16
	icon_r = min(32, (icon_bottom - 14) / 2)
	icon_cy = icon_bottom - icon_r
	icon_d = icon_r * 2

	if dark:
		backdrop = '<rect width="200" height="200" rx="18" fill="url(#rlAccent)"/>'
	else:
		backdrop = (
			'<rect x="0.5" y="0.5" width="199" height="199" rx="17.5" fill="#ffffff" stroke="#e2e8f0"/>'
		)

	data_uri = _icon_data_uri(doc.icon)
	if data_uri:
		icon_markup = (
			f'<clipPath id="rlIconClip"><circle cx="100" cy="{icon_cy}" r="{icon_r}"/></clipPath>'
			f'<image href="{escape(data_uri)}" x="{100 - icon_r}" y="{icon_cy - icon_r}" '
			f'width="{icon_d}" height="{icon_d}" '
			'preserveAspectRatio="xMidYMid slice" clip-path="url(#rlIconClip)"/>'
		)
	else:
		start, end = _placeholder_gradient(raw_title)
		letter = escape((raw_title or "?")[:1].upper())
		icon_markup = (
			f'<linearGradient id="rlPlaceholder" x1="0%" y1="0%" x2="100%" y2="100%">'
			f'<stop offset="0%" stop-color="{start}"/><stop offset="100%" stop-color="{end}"/>'
			f"</linearGradient>"
			f'<circle cx="100" cy="{icon_cy}" r="{icon_r}" fill="url(#rlPlaceholder)"/>'
			f'<text x="100" y="{icon_cy + icon_r * 0.36}" font-family="{FONT_STACK}" '
			f'font-size="{round(icon_r * 0.95, 1)}" font-weight="700" '
			f'fill="#ffffff" text-anchor="middle">{letter}</text>'
		)

	title_markup = "\n  ".join(
		f'<text x="100" y="{title_first_y + i * line_height}" font-family="{FONT_STACK}" '
		f'font-size="15" font-weight="700" fill="{name_fill}" text-anchor="middle">{escape(line)}</text>'
		for i, line in enumerate(lines)
	)

	return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{BADGE_SIZE}" height="{BADGE_SIZE}" viewBox="0 0 200 200" role="img" aria-label="{title} is recommended on Freely.Giving">
  <title>{title} is recommended on Freely.Giving</title>
  <defs>
    <linearGradient id="rlAccent" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#5b21b6"/>
      <stop offset="45%" stop-color="#1d4ed8"/>
      <stop offset="100%" stop-color="#0d9488"/>
    </linearGradient>
  </defs>
  {backdrop}
  {icon_markup}
  {title_markup}
  <line x1="56" y1="{divider_y}" x2="144" y2="{divider_y}" stroke="{rule_stroke}"{rule_opacity} stroke-width="1"/>
  <text x="100" y="{kicker_y}" font-family="{FONT_STACK}" font-size="7.5" font-weight="600" letter-spacing="1.3" fill="{kicker_fill}"{kicker_opacity} text-anchor="middle">RECOMMENDED ON</text>
  <text x="100" y="{wordmark_y}" font-family="{FONT_STACK}" font-size="15" font-weight="700" fill="{wordmark_fill}" text-anchor="middle">Freely.Giving</text>
</svg>
"""


def get_badge(resource_name, theme):
	"""Return badge SVG bytes, or None if this resource should not have a badge."""
	fields = ["name", "title", "icon", "published", "recommended", "modified"]
	doc = frappe.db.get_value("Resource", resource_name, fields, as_dict=True)

	if not doc or not doc.published or not doc.recommended:
		return None

	cache_key = f"resource_badge::{resource_name}::{theme}::{doc.modified}"
	cached = frappe.cache.get_value(cache_key)
	if cached:
		return cached

	svg = build_badge_svg(doc, theme).encode("utf-8")
	frappe.cache.set_value(cache_key, svg, expires_in_sec=60 * 60)
	return svg


class BadgeRenderer(BaseRenderer):
	"""Serves /badge/<theme>/<resource>.svg"""

	def can_render(self):
		parts = self.path.split("/")
		return len(parts) >= 3 and parts[0] == "badge" and parts[1] in THEMES and self.path.endswith(".svg")

	def render(self):
		parts = self.path.split("/")
		theme = parts[1]
		resource_name = unquote("/".join(parts[2:]))[: -len(".svg")]

		svg = get_badge(resource_name, theme)
		if not svg:
			from frappe.website.page_renderers.not_found_page import NotFoundPage

			return NotFoundPage(self.path).render()

		return build_response(
			self.path,
			svg,
			200,
			{
				"Content-Type": "image/svg+xml",
				"Cache-Control": "public, max-age=3600",
			},
		)
