# Data Schema

---

## PTProfile dataclass

```python
from dataclasses import dataclass

@dataclass
class PTProfile:
    # Required
    name: str
    gym_name: str
    gym_slug: str           # extracted from URL: /clubs/{gym_slug}/...

    # From contacts pad
    suburb: str | None
    qualifications: list[str]   # split on comma, strip whitespace
    phone: str | None           # normalised to E.164: +27...
    email: str | None
    website: str | None
    instagram_handle: str | None
    facebook_url: str | None
    whatsapp_number: str | None

    # Meta
    profile_url: str
    profile_image_url: str | None
    scraped_at: str             # ISO 8601
```

---

## Field notes

**qualifications** — `<p3>` contains a comma-separated string:
```python
raw = "Advanced Certificate in Exercise Science,Higher Certificate in Exercise Science,Other"
qualifications = [q.strip() for q in raw.split(",")]
```

**phone** — site is inconsistent with format, always normalise:
```python
def to_e164_za(num: str) -> str:
    num = num.strip().replace(" ", "")
    if num.startswith("0"):  return "+27" + num[1:]
    if num.startswith("27"): return "+" + num
    return num
```

**whatsapp_number** — often the same as phone but sourced from `wa.me` href:
```
https://wa.me/27645174975?text=Hi  →  strip prefix + query string  →  +27645174975
```

---

## Edge cases

| Situation | Handling |
|---|---|
| No `contacts` pad | Emit record with all contact fields as `None`, don't crash |
| Instagram URL has trailing slash | Always `.rstrip('/')` before splitting |
| Bio contains `@username` text | Ignore — use `href` extraction instead (see selectors.md) |
| `/group-exercise` listing pages | Skip entirely, these are not PTs |
| Duplicate profiles across gym pages | Deduplicate on `(gym_slug, profile_url)` before DB insert |

---

## Output format

**JSONL** (preferred for incremental runs — append-safe):
```python
import json
from dataclasses import asdict

with open("pts.jsonl", "a") as f:
    f.write(json.dumps(asdict(profile)) + "\n")
```

**SQLite / PostgreSQL** — insert into `personal_trainers` table, deduplicate on `(gym_slug, profile_url)`.