# DOM Selectors

Verified against live site HTML. Update this file if selectors break.

---

## Listing page — PT cards

| Element | Selector |
|---|---|
| All PT cards | `.trainer-card` |
| Profile link / slug | `a[href*="/personal-trainers/"]` inside each card |
| Next page button | `button.pagination__next` — disabled attribute present on last page |

> If `.trainer-card` returns nothing, run `page.content()` and grep for a known PT name to find
> the real selector. The site may render inside a React shadow subtree.

---

## Detail page — contacts pad

All contact data lives inside:

```html
<pad class="contacts">
  <a><icon class="profile-icon-{type}"></icon><p3>VALUE</p3></a>
  ...
</pad>
```

Extract each field by icon class or `href` pattern:

| Field | Selector / strategy |
|---|---|
| `suburb` | `pad.contacts icon.profile-icon-location` → sibling `p3` text |
| `qualifications` | `pad.contacts icon.profile-icon-qualifications` → sibling `p3` text |
| `phone` | `a[href^="tel:"]` → strip `tel:` prefix |
| `email` | `a[href^="mailto:"]` → strip `mailto:` prefix |
| `website` | `a > icon.profile-icon-web` → sibling `p3` text or parent `href` |
| `instagram_handle` | `a[href*="instagram.com"]` → extract from href (see below) |
| `facebook_url` | `a[href*="facebook.com"]` → `href` value |
| `whatsapp_number` | `a[href*="wa.me/"]` → strip `https://wa.me/` prefix |

### Instagram handle extraction

```python
url = await page.get_attribute('a[href*="instagram.com"]', 'href')
# e.g. "https://www.instagram.com/Matthew_fah"
handle = url.rstrip('/').split('/')[-1] if url else None
```

Prefer extracting from `href` over parsing the bio text — more reliable.